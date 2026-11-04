#!/usr/bin/env python3
"""Check a user's own Quan MCP and voice setup without exposing credentials.

This is a local readiness check. The agent must still confirm the active MCP tools
and that the selected voice and models belong to the connected Quan account.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


REQUIRED_TOOLS = {
    "quantv_list_models",
    "quantv_list_voices",
    "quantv_generate_speech",
    "quantv_generate_image",
}
PLACEHOLDERS = ("<", "your", "replace", "example", "填入", "本人")


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value


def filled(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not any(
        word in value.lower() for word in PLACEHOLDERS
    )


def resolve_local(value: str, base: Path) -> Path:
    path = Path(os.path.expandvars(value)).expanduser()
    return path if path.is_absolute() else base / path


def tools_in_report(path: Path) -> set[str]:
    payload = load_json(path)
    if "mcpServers" in payload or "env" in payload:
        raise ValueError("Pass a tool-name report, never a credential-bearing MCP config")
    entries = payload.get("tools")
    if not isinstance(entries, list):
        raise ValueError("Tool report needs a tools array")
    result = set()
    for entry in entries:
        name = entry if isinstance(entry, str) else entry.get("name") if isinstance(entry, dict) else None
        if isinstance(name, str):
            result.add(name)
    return result


def check(setup_path: Path, report_path: Path | None = None) -> tuple[int, list[str]]:
    messages: list[str] = []
    errors = 0

    def item(label: str, ok: bool, detail: str = "") -> None:
        nonlocal errors
        errors += not ok
        messages.append(f"{'PASS' if ok else 'FAIL'} {label}{': ' + detail if detail else ''}")

    try:
        setup = load_json(setup_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return 1, [f"FAIL setup: {type(exc).__name__}; create a private setup file from setup.example.json"]

    mcp_value = setup.get("mcp_config")
    mcp_path = resolve_local(mcp_value, setup_path.parent) if filled(mcp_value) else None
    item("own MCP config path", bool(mcp_path and mcp_path.is_file()))
    server = None
    if mcp_path and mcp_path.is_file():
        try:
            payload = load_json(mcp_path)
            servers = payload.get("mcpServers", {})
            server = servers.get(setup.get("mcp_server", "quantv-generation")) if isinstance(servers, dict) else None
        except (OSError, ValueError, json.JSONDecodeError):
            server = None
    item("selected MCP server", isinstance(server, dict))
    env = server.get("env", {}) if isinstance(server, dict) else {}
    if not isinstance(env, dict):
        env = {}
    base_url = env.get("QUANTV_BASE_URL")
    parsed = urlparse(base_url) if filled(base_url) else None
    host = parsed.hostname.lower() if parsed and parsed.hostname else ""
    item("Quan API address", bool(parsed and parsed.scheme == "https" and (host == "quantv.com" or host.endswith(".quantv.com"))))
    item("own Quan access token", filled(env.get("QUANTV_ACCESS_TOKEN")))

    voice_value = setup.get("voice_mp3")
    voice_path = resolve_local(voice_value, setup_path.parent) if filled(voice_value) else None
    item("own voice MP3 path", bool(voice_path and voice_path.is_file()))
    if voice_path and voice_path.is_file():
        try:
            proc = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1", str(voice_path)],
                capture_output=True, text=True, timeout=15, check=False,
            )
            item("voice audio codec", proc.returncode == 0 and proc.stdout.strip() == "mp3")
        except (OSError, subprocess.TimeoutExpired):
            item("voice audio codec", False, "install ffprobe and verify the file")
    else:
        item("voice audio codec", False)

    for field in ("voice_reference_id", "speech_model_id", "image_model_id"):
        item(field, filled(setup.get(field)))

    if report_path:
        try:
            names = tools_in_report(report_path)
            missing = sorted(REQUIRED_TOOLS - names)
            item("MCP tool names", not missing, ", ".join(missing) if missing else "required names found")
        except (OSError, ValueError, json.JSONDecodeError):
            item("MCP tool names", False, "invalid token-free tool report")
    else:
        messages.append("UNVERIFIED active MCP tools and account ownership; inspect them in the agent runtime")

    if errors == 0:
        messages.append("LOCAL_SETUP_READY; confirm voice_reference_id and model IDs through the active MCP before generation")
    return (1 if errors else 0), messages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setup", type=Path, default=Path(os.environ.get("QUAN_STORY_SETUP", ".quan-story.local.json")))
    parser.add_argument("--tools-json", type=Path, help="Optional token-free report with tool names only")
    args = parser.parse_args()
    status, messages = check(args.setup.expanduser().resolve(), args.tools_json)
    print("\n".join(messages))
    return status


if __name__ == "__main__":
    sys.exit(main())
