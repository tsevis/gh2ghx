# gh2ghx

`gh2ghx` is a lightweight macOS-first Tkinter app and Python module for converting Grasshopper `.gh` files into XML-readable `.ghx` output.

It prioritizes:
- readable output for XML tooling
- lossless preservation of original binary content
- graceful fallback when native Grasshopper serializers are unavailable

## Features

- GUI converter (`.gh` -> `.ghx`) with file pickers and status output
- macOS Aqua appearance toggle (`aqua`/`darkaqua`)
- mode-aware conversion engine with explicit result mode
- regression tests with a real binary Grasshopper fixture

## Conversion Modes

- `native_ghx`
  - Source is already XML, compressed XML, or native GH deserialization is available (GH_IO/Grasshopper runtime).
- `binary_structured_report`
  - Raw-deflate binary GH archive detected (`Root` + `DefinitionObjects`).
  - Produces structured XML report (metadata, components, params, recoverable GUID-like links) and embeds lossless Base64 payload.
- `xml_wrapper_base64`
  - Generic fallback for unknown binaries.

## Project Layout

```text
gh2ghx/
  gh2ghx/
    app.py
    converter.py
    theme.py
  tests/
    fixtures/islamic.gh
    test_converter.py
  main.py
  run_gh2ghx.sh
```

## Requirements

- Python 3.10+ (3.12 recommended)
- Tkinter (bundled with standard Python installers on macOS)

## Run (GUI)

```bash
cd /Users/tsevis/AI/ClaudeCode/gh2ghx
./run_gh2ghx.sh
```

Or:

```bash
python3 main.py
```

## Run Tests

```bash
python3 -m unittest discover -s tests -q
```

## Notes

- Without native Grasshopper runtime assemblies, binary `.gh` files cannot always be reconstructed as canonical GHX definitions.
- In those cases, `gh2ghx` emits a structured XML report with preserved original payload.

## License

MIT. See [LICENSE](./LICENSE).
