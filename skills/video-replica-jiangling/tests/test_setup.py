"""Installation boundary tests; no real model or network is used."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

script = Path(__file__).resolve().parents[1] / "scripts" / "check_setup.py"
spec = importlib.util.spec_from_file_location("check_setup", script)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class InstallationTests(unittest.TestCase):
    def make_skills(self, root, names):
        for name in names:
            for item in setup.REQUIRED_FILES[name]:
                path = root / name / item
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture", encoding="utf-8")

    def statuses(self, report):
        return {item["name"]: item["status"] for item in report["checks"]}

    def test_main_alone_reports_both_missing_skills(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.make_skills(root, ["video-replica-jiangling"])
            report = setup.inspect_setup(root, executable_lookup=lambda _: None)
            state = self.statuses(report)
            self.assertEqual(state["video-depth-anything"], "MISSING")
            self.assertEqual(state["qisi-video-remix"], "MISSING")
            self.assertFalse(report["ready_for_manual_runtime_test"])

    def test_green_basic_mcp_does_not_imply_video_tools(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.make_skills(root, setup.REQUIRED_FILES)
            basic = {"quantv_list_models", "quantv_generate_image", "quantv_generate_speech", "quantv_get_task", "quantv_wait_task"}
            report = setup.inspect_setup(root, tool_names=basic, executable_lookup=lambda _: "fixture")
            state = self.statuses(report)
            self.assertEqual(state["quantv_generate_image"], "PASS")
            self.assertEqual(state["quantv_upload_media"], "MISSING")
            self.assertEqual(state["quantv_generate_video"], "MISSING")

    def test_all_tools_still_require_depth_environment(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.make_skills(root, setup.REQUIRED_FILES)
            report = setup.inspect_setup(root, tool_names=set(setup.REQUIRED_TOOLS), executable_lookup=lambda _: "fixture")
            state = self.statuses(report)
            self.assertEqual(state["depth_tool_root"], "MISSING")
            self.assertFalse(report["ready_for_manual_runtime_test"])
            self.assertFalse(report["generation_tested"])

    def test_absent_mcp_report_is_unverified(self):
        with tempfile.TemporaryDirectory() as folder:
            report = setup.inspect_setup(Path(folder), executable_lookup=lambda _: None)
            self.assertEqual(self.statuses(report)["quantv_get_task"], "UNVERIFIED")

    def test_rejects_credential_config_instead_of_tools_report(self):
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / "input.json"
            report.write_text(json.dumps({"mcpServers": {"example": {"env": {}}}}), encoding="utf-8")
            with self.assertRaises(ValueError):
                setup.read_tool_names(report)


if __name__ == "__main__":
    unittest.main()
