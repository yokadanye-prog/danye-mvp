"""Read-only installation checks. No token files, network or generation calls."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

REQUIRED_TOOLS = (
    "quantv_list_models", "quantv_generate_image", "quantv_upload_media",
    "quantv_generate_video", "quantv_get_task",
)
REQUIRED_FILES = {
    "video-replica-jiangling": ("SKILL.md",),
    "video-depth-anything": ("SKILL.md", "scripts/infer-depth.ps1", "references/final-replica-workflow.md"),
    "qisi-video-remix": ("SKILL.md", "references/delivery-guide.md", "LICENSE"),
}


def read_tool_names(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict) and "mcpServers" in payload:
        raise ValueError("Pass a tool-name report, never a credential-bearing MCP config")
    items = payload.get("tools", []) if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise ValueError("Expected an array of names or an object with a tools array")
    names = set()
    for item in items:
        name = item if isinstance(item, str) else item.get("name") if isinstance(item, dict) else None
        if isinstance(name, str):
            names.add(name.split("__")[-1])
    return names


def inspect_setup(skills_root, tool_root=None, python_path=None, tool_names=None,
                  probe_python=False, executable_lookup=shutil.which):
    checks = []

    def add(name, status, detail):
        checks.append({"name": name, "status": status, "detail": detail})

    skills_root = Path(skills_root)
    for name, resources in REQUIRED_FILES.items():
        missing = [item for item in resources if not (skills_root / name / item).is_file()]
        add(name, "MISSING" if missing else "PASS", "Missing: " + ", ".join(missing) if missing else "Required skill files found; enable this skill in WorkBuddy")
    for binary in ("ffmpeg", "ffprobe"):
        found = executable_lookup(binary)
        add(binary, "PASS" if found else "MISSING", "Available on PATH" if found else "Install FFmpeg and expose both commands on PATH")

    root = Path(tool_root).expanduser() if tool_root else None
    add("depth_tool_root", "PASS" if root and root.is_dir() else "MISSING",
        "Tool directory exists" if root and root.is_dir() else "Set VIDEO_DEPTH_ANYTHING_HOME or pass --tool-root")
    for relative in ("run_streaming.py", "checkpoints/video_depth_anything_vits.pth"):
        exists = root is not None and (root / relative).is_file()
        add(relative, "PASS" if exists else "MISSING", "Found" if exists else "Prepare this file under the depth tool directory")

    if python_path:
        python_exe = Path(python_path).expanduser()
    elif root:
        python_exe = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    else:
        python_exe = None
    python_exists = python_exe is not None and python_exe.is_file()
    add("depth_python", "PASS" if python_exists else "MISSING", "Configured Python exists" if python_exists else "Prepare the depth .venv or set VIDEO_DEPTH_ANYTHING_PYTHON")
    if python_exists and probe_python:
        try:
            process = subprocess.run(
                [str(python_exe), "-c", "import torch,cv2,numpy;print('DEPTH_IMPORTS_OK');print('CUDA_AVAILABLE='+str(torch.cuda.is_available()))"],
                capture_output=True, text=True, timeout=25,
            )
            ok = process.returncode == 0 and "DEPTH_IMPORTS_OK" in process.stdout
            detail = "Python imports passed; " + next((line for line in process.stdout.splitlines() if line.startswith("CUDA_AVAILABLE=")), "CUDA availability unknown") if ok else "Depth Python cannot import torch, cv2 and numpy; check platform-compatible requirements"
            add("depth_python_packages", "PASS" if ok else "MISSING", detail)
        except (OSError, subprocess.TimeoutExpired):
            add("depth_python_packages", "UNVERIFIED", "Python probe did not complete; no inference was started")
    else:
        add("depth_python_packages", "UNVERIFIED", "Run --probe-python after the depth environment is installed")

    for name in REQUIRED_TOOLS:
        status = "UNVERIFIED" if tool_names is None else "PASS" if name in tool_names else "MISSING"
        add(name, status, "Check current WorkBuddy tool list or pass a token-free --tools-json report" if tool_names is None else "Tool name found" if status == "PASS" else "Enable a Quan MCP version that exposes this tool")
    return {
        "scope": "installation_only",
        "ready_for_manual_runtime_test": all(item["status"] == "PASS" for item in checks),
        "generation_tested": False,
        "checks": checks,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--tool-root", default=os.environ.get("VIDEO_DEPTH_ANYTHING_HOME"))
    parser.add_argument("--python-path", default=os.environ.get("VIDEO_DEPTH_ANYTHING_PYTHON"))
    parser.add_argument("--tools-json", type=Path, help="Only tool names; never mcp.json or tokens")
    parser.add_argument("--probe-python", action="store_true", help="Import depth packages; does not load weights or run inference")
    args = parser.parse_args()
    try:
        names = read_tool_names(args.tools_json) if args.tools_json else None
    except (OSError, ValueError, json.JSONDecodeError):
        parser.error("Invalid tool-name report; supply a JSON array of tool names without credentials")
    report = inspect_setup(args.skills_root, args.tool_root, args.python_path, names, args.probe_python)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready_for_manual_runtime_test"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
