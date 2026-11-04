import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "preflight.py"
SPEC = importlib.util.spec_from_file_location("quan_preflight", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PreflightTest(unittest.TestCase):
    def test_public_example_fails_closed(self):
        example = SCRIPT.parents[1] / "setup.example.json"
        code, messages = MODULE.check(example)
        self.assertEqual(code, 1)
        self.assertTrue(any("FAIL own Quan access token" in line for line in messages))

    def test_private_local_setup_passes_without_leaking_token(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            voice = root / "voice.mp3"
            voice.write_bytes(b"test")
            mcp = root / "mcp.json"
            mcp.write_text(json.dumps({"mcpServers": {"quantv-generation": {"env": {
                "QUANTV_BASE_URL": "https://jl5180.quantv.com",
                "QUANTV_ACCESS_TOKEN": "secret-test-token",
            }}}}), encoding="utf-8")
            setup = root / ".quan-story.local.json"
            setup.write_text(json.dumps({
                "mcp_config": str(mcp), "voice_mp3": str(voice),
                "voice_reference_id": "own-voice-id", "speech_model_id": "own-speech-id",
                "image_model_id": "own-image-id",
            }), encoding="utf-8")
            report = root / "tools.json"
            report.write_text(json.dumps({"tools": sorted(MODULE.REQUIRED_TOOLS)}), encoding="utf-8")
            fake_probe = type("Probe", (), {"returncode": 0, "stdout": "mp3\n"})()
            with patch.object(MODULE.subprocess, "run", return_value=fake_probe):
                code, messages = MODULE.check(setup, report)
            self.assertEqual(code, 0)
            self.assertIn("LOCAL_SETUP_READY", messages[-1])
            self.assertNotIn("secret-test-token", "\n".join(messages))

    def test_rejects_credential_bearing_tool_report(self):
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp) / "wrong.json"
            report.write_text('{"mcpServers":{"quantv-generation":{}}}', encoding="utf-8")
            with self.assertRaises(ValueError):
                MODULE.tools_in_report(report)


if __name__ == "__main__":
    unittest.main()
