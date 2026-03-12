"""Conversion helpers for GH to GHX."""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import re
import zlib
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET


@dataclass(frozen=True)
class ConversionResult:
    mode: str
    message: str
    reconstructed: bool


_KEYWORDS = {
    "Root",
    "Definition",
    "DefinitionObjects",
    "Object",
    "ArchiveVersion",
    "DocumentHeader",
    "DefinitionProperties",
    "Description",
    "Name",
    "NickName",
    "Container",
    "Attributes",
    "Bounds",
    "Pivot",
    "InstanceGuid",
    "GUID",
    "ID",
    "Count",
    "Item",
    "Path",
    "Branch",
    "Access",
    "Preview",
    "Date",
    "Projection",
    "Target",
    "Views",
    "View",
    "Anchor",
    "param_input",
    "param_output",
}


def _is_xml(text: str) -> bool:
    stripped = text.lstrip()
    if not stripped.startswith("<"):
        return False
    try:
        ET.fromstring(text)
    except ET.ParseError:
        return False
    return True


def _to_pretty_xml(text: str) -> str:
    root = ET.fromstring(text)
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def _decode_xml_bytes(data: bytes) -> str | None:
    encodings = ("utf-8", "utf-16", "utf-16-le", "utf-16-be", "latin1")
    for encoding in encodings:
        try:
            decoded = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        if _is_xml(decoded):
            return decoded
    return None


def _try_decompress_to_xml(data: bytes) -> str | None:
    decompressors = (
        lambda d: gzip.decompress(d),
        lambda d: zlib.decompress(d),
        lambda d: zlib.decompress(d, wbits=15 | 32),
        lambda d: zlib.decompress(d, wbits=-15),
    )
    for decompress in decompressors:
        try:
            payload = decompress(data)
        except Exception:
            continue
        decoded = _decode_xml_bytes(payload)
        if decoded is not None:
            return decoded
    return None


def _try_raw_deflate(data: bytes) -> bytes | None:
    try:
        return zlib.decompress(data, wbits=-15)
    except Exception:
        return None


def _looks_like_binary_gh_stream(payload: bytes) -> bool:
    return b"Root" in payload and b"DefinitionObjects" in payload


def _extract_printable_tokens(payload: bytes) -> list[str]:
    raw_tokens = re.findall(rb"[ -~]{3,120}", payload)
    tokens = [tok.decode("latin1").strip() for tok in raw_tokens]
    return [tok for tok in tokens if tok]


def _looks_like_noise(value: str) -> bool:
    if value in _KEYWORDS:
        return True
    alpha = sum(ch.isalpha() for ch in value)
    if alpha == 0:
        return True
    return alpha / max(len(value), 1) < 0.45


def _value_after(tokens: list[str], start: int, key: str, max_scan: int = 30) -> str | None:
    end = min(len(tokens), start + max_scan)
    for idx in range(start, end):
        if tokens[idx] == key and idx + 1 < len(tokens):
            candidate = tokens[idx + 1]
            if not _looks_like_noise(candidate):
                return candidate
    return None


def _extract_components(tokens: list[str]) -> list[dict[str, str | None]]:
    components: list[dict[str, str | None]] = []
    seen: set[tuple[str, str | None]] = set()
    for idx, token in enumerate(tokens):
        if token != "Object":
            continue
        name = _value_after(tokens, idx, "Name")
        if not name:
            continue
        nickname = _value_after(tokens, idx, "NickName")
        instance_guid = _value_after(tokens, idx, "InstanceGuid")
        guid = _value_after(tokens, idx, "GUID")
        key = (name, nickname)
        if key in seen:
            continue
        seen.add(key)
        components.append(
            {
                "name": name,
                "nickname": nickname,
                "guid": guid,
                "instance_guid": instance_guid,
            }
        )
    return components


def _extract_parameters(tokens: list[str]) -> list[dict[str, str | None]]:
    params: list[dict[str, str | None]] = []
    for idx, token in enumerate(tokens):
        if token not in {"param_input", "param_output"}:
            continue
        kind = "input" if token == "param_input" else "output"
        name = _value_after(tokens, idx, "Name")
        nickname = _value_after(tokens, idx, "NickName")
        description = _value_after(tokens, idx, "Description")
        instance_guid = _value_after(tokens, idx, "InstanceGuid")
        access = _value_after(tokens, idx, "Access")
        if not (name or nickname or description):
            continue
        params.append(
            {
                "kind": kind,
                "name": name,
                "nickname": nickname,
                "description": description,
                "instance_guid": instance_guid,
                "access": access,
            }
        )
    return params


def _extract_guid_like_strings(tokens: list[str]) -> list[str]:
    guid_re = re.compile(r"[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}")
    found: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        for match in guid_re.findall(token):
            if match in seen:
                continue
            seen.add(match)
            found.append(match)
    return found


def _extract_metadata(tokens: list[str]) -> dict[str, str | bool | int]:
    metadata: dict[str, str | bool | int] = {
        "root_marker_present": "Root" in tokens,
        "definition_objects_present": "DefinitionObjects" in tokens,
        "token_count": len(tokens),
    }
    for idx, token in enumerate(tokens):
        if token == "Name" and idx + 1 < len(tokens):
            candidate = tokens[idx + 1]
            if candidate.lower().endswith(".gh"):
                metadata["document_name"] = candidate
                break
    plugin_version = _value_after(tokens, 0, "plugin_version", max_scan=40)
    if plugin_version:
        metadata["plugin_version"] = plugin_version
    return metadata


def _build_structured_report_xml(data: bytes, payload: bytes, source_name: str) -> str:
    sha256 = hashlib.sha256(data).hexdigest()
    tokens = _extract_printable_tokens(payload)
    metadata = _extract_metadata(tokens)
    components = _extract_components(tokens)
    parameters = _extract_parameters(tokens)
    guid_candidates = _extract_guid_like_strings(tokens)

    root = ET.Element("GrasshopperStructuredReport")
    meta = ET.SubElement(root, "Meta")
    ET.SubElement(meta, "SourceFile").text = source_name
    ET.SubElement(meta, "SourceEncoding").text = "binary_raw_deflate"
    ET.SubElement(meta, "SHA256").text = sha256
    ET.SubElement(meta, "ConversionMode").text = "binary_structured_report"

    doc = ET.SubElement(root, "Document")
    for key, value in metadata.items():
        ET.SubElement(doc, key).text = str(value)

    comps_el = ET.SubElement(root, "Components", count=str(len(components)))
    for comp in components:
        c_el = ET.SubElement(comps_el, "Component")
        for key, value in comp.items():
            ET.SubElement(c_el, key).text = value or ""

    params_el = ET.SubElement(root, "Parameters", count=str(len(parameters)))
    for param in parameters:
        p_el = ET.SubElement(params_el, "Parameter")
        for key, value in param.items():
            ET.SubElement(p_el, key).text = value or ""

    links_el = ET.SubElement(root, "WireLinks")
    if guid_candidates:
        ET.SubElement(links_el, "RecoveredGuidCount").text = str(len(guid_candidates))
        for value in guid_candidates:
            ET.SubElement(links_el, "Guid").text = value
    else:
        ET.SubElement(links_el, "Note").text = (
            "No canonical GUID links were recoverable from printable token stream."
        )

    summary = {
        "component_count": len(components),
        "parameter_count": len(parameters),
        "guid_count": len(guid_candidates),
        "component_names": [component["name"] for component in components if component["name"]],
    }
    ET.SubElement(root, "JsonSummary").text = json.dumps(summary, ensure_ascii=True, indent=2)

    blob = ET.SubElement(root, "LosslessBinaryPayload", encoding="base64")
    blob.text = base64.b64encode(data).decode("ascii")

    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def _try_native_gh_deserialize(source: Path) -> str | None:
    """
    Best-effort .NET path for environments that expose GH_IO/Grasshopper assemblies.
    Falls back to None when not available.
    """
    try:
        import clr  # type: ignore
    except Exception:
        return None

    for assembly_name in ("GH_IO", "Grasshopper"):
        try:
            clr.AddReference(assembly_name)
        except Exception:
            continue

    try:
        from GH_IO.Serialization import GH_Archive  # type: ignore
    except Exception:
        return None

    archive = GH_Archive()
    loaded = False
    read_methods = ("ReadFromFile", "ReadFromBinaryFile")
    for method_name in read_methods:
        method = getattr(archive, method_name, None)
        if method is None:
            continue
        try:
            loaded = bool(method(str(source)))
        except Exception:
            loaded = False
        if loaded:
            break
    if not loaded:
        return None

    for method_name in ("Serialize_Xml", "SerializeXML"):
        method = getattr(archive, method_name, None)
        if method is None:
            continue
        try:
            xml_text = method()
        except Exception:
            continue
        if isinstance(xml_text, str) and _is_xml(xml_text):
            return _to_pretty_xml(xml_text)
    return None


def _wrap_as_xml_blob(data: bytes, source_name: str) -> str:
    sha256 = hashlib.sha256(data).hexdigest()
    root = ET.Element("GrasshopperArchive")
    meta = ET.SubElement(root, "Meta")
    ET.SubElement(meta, "SourceFile").text = source_name
    ET.SubElement(meta, "OriginalEncoding").text = "binary"
    ET.SubElement(meta, "SHA256").text = sha256
    ET.SubElement(meta, "Note").text = (
        "Source GH content could not be decoded to native GHX XML. "
        "Payload is preserved as Base64."
    )
    payload = ET.SubElement(root, "BinaryPayload", encoding="base64")
    payload.text = base64.b64encode(data).decode("ascii")
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def convert_gh_to_ghx_detailed(source: Path, target: Path) -> ConversionResult:
    data = source.read_bytes()

    native_xml = _try_native_gh_deserialize(source)
    if native_xml is not None:
        target.write_text(native_xml, encoding="utf-8")
        return ConversionResult(
            mode="native_ghx",
            message="Converted using native GH deserialization path (GH_IO/Grasshopper).",
            reconstructed=True,
        )

    decoded_xml = _decode_xml_bytes(data)
    if decoded_xml is not None:
        target.write_text(_to_pretty_xml(decoded_xml), encoding="utf-8")
        return ConversionResult(
            mode="native_ghx",
            message="Converted from XML-compatible source.",
            reconstructed=True,
        )

    decompressed_xml = _try_decompress_to_xml(data)
    if decompressed_xml is not None:
        target.write_text(_to_pretty_xml(decompressed_xml), encoding="utf-8")
        return ConversionResult(
            mode="native_ghx",
            message="Converted from compressed XML payload.",
            reconstructed=True,
        )

    raw_deflate_payload = _try_raw_deflate(data)
    if raw_deflate_payload is not None and _looks_like_binary_gh_stream(raw_deflate_payload):
        target.write_text(
            _build_structured_report_xml(data, raw_deflate_payload, source.name),
            encoding="utf-8",
        )
        return ConversionResult(
            mode="binary_structured_report",
            message=(
                "Detected binary GH archive (raw-deflate Root/DefinitionObjects). "
                "Wrote structured extraction report with lossless payload."
            ),
            reconstructed=False,
        )

    target.write_text(_wrap_as_xml_blob(data, source.name), encoding="utf-8")
    return ConversionResult(
        mode="xml_wrapper_base64",
        message="No XML or binary-GH structure detected. Wrote XML wrapper with Base64 payload.",
        reconstructed=False,
    )


def convert_gh_to_ghx(source: Path, target: Path) -> tuple[bool, str]:
    """
    Backward-compatible wrapper used by existing GUI code.
    """
    result = convert_gh_to_ghx_detailed(source, target)
    return result.reconstructed, f"[{result.mode}] {result.message}"
