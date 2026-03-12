from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from gh2ghx.converter import convert_gh_to_ghx, convert_gh_to_ghx_detailed


class ConverterTests(unittest.TestCase):
    def test_binary_fixture_emits_structured_report(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "islamic.gh"
        self.assertTrue(fixture.exists(), "Missing fixture: tests/fixtures/islamic.gh")

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "islamic.ghx"
            result = convert_gh_to_ghx_detailed(fixture, target)
            output = target.read_text(encoding="utf-8")

        self.assertEqual(result.mode, "binary_structured_report")
        self.assertIn("GrasshopperStructuredReport", output)
        self.assertNotIn("<GrasshopperArchive>", output)
        self.assertIn("<SourceFile>islamic.gh</SourceFile>", output)
        self.assertIn("Circle", output)
        self.assertIn("Divide Curve", output)

        expected_sha = hashlib.sha256(fixture.read_bytes()).hexdigest()
        self.assertIn(f"<SHA256>{expected_sha}</SHA256>", output)

    def test_compat_wrapper_returns_mode_prefixed_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "input.gh"
            target = Path(tmpdir) / "output.ghx"
            source.write_bytes(b"binary")
            reconstructed, message = convert_gh_to_ghx(source, target)

        self.assertFalse(reconstructed)
        self.assertTrue(message.startswith("["))
        self.assertIn("xml_wrapper_base64", message)


if __name__ == "__main__":
    unittest.main()

