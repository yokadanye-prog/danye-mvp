#!/usr/bin/env python3
"""Reproduce the fail-closed preflight GIF from the public example setup."""

from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
COMMAND = [sys.executable, str(ROOT / "scripts/preflight.py"), "--setup", str(ROOT / "setup.example.json")]
RESULT = subprocess.run(COMMAND, capture_output=True, text=True, check=False)
if RESULT.returncode != 1:
    raise SystemExit("The public example unexpectedly passed preflight")

font_path = Path("C:/Windows/Fonts/consola.ttf")
font = ImageFont.truetype(str(font_path), 20) if font_path.is_file() else ImageFont.load_default()
title_font = ImageFont.truetype(str(font_path), 24) if font_path.is_file() else ImageFont.load_default()


def frame(lines: list[str]) -> Image.Image:
    canvas = Image.new("RGB", (920, 400), "#151a22")
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((22, 20, 898, 380), radius=16, fill="#202733")
    draw.text((48, 42), "quan-story-studio / local preflight", fill="#c9d8e8", font=title_font)
    y = 100
    for line in lines:
        color = "#ff9b85" if line.startswith("FAIL") else "#8ddbb4"
        draw.text((48, y), line, fill=color, font=font)
        y += 28
    return canvas


first = frame(["> python scripts/preflight.py --setup setup.example.json"])
second = frame(["> python scripts/preflight.py --setup setup.example.json"] + RESULT.stdout.splitlines()[:9])
target = ROOT / "examples/preflight-demo.gif"
first.save(target, save_all=True, append_images=[second], duration=[1500, 4500], loop=0, optimize=True)
print(target)
