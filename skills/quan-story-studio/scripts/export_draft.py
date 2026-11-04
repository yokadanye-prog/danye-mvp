#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 plan.json 写进剪映草稿箱（自包含，不依赖其他技能）。

用法
    python export_draft.py <plan.json> --name "人物名_edit_v1"
    python export_draft.py <plan.json> --name "..." --drafts-root "..."

行为
    - 竖屏 1080x1920 / 30fps，图片按 Ken Burns 推拉，关键帧逐帧采样，
      与本地 ffmpeg 渲染的缓动曲线完全一致。
    - 素材复制进草稿的 materials 目录，草稿自包含，不引用项目里的临时路径。
    - 同名草稿已存在时，默认拒绝覆盖；加 --overwrite 会先备份旧草稿。
    - 成功后写 jianying_draft.json / resolved_plan.json 到 plan 同目录，作为凭证。

依赖
    pyJianYingDraft==0.3.1、Pillow、ffprobe。用 quan_story.py doctor 检查。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from quan_story import find_exe, jianying_root, load_runtime  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def activate_runtime() -> None:
    """如果配置了托管 Python（装好 pyJianYingDraft 的那个），换它重跑。"""
    target = load_runtime().get("python")
    if not target:
        return
    exe = Path(str(target)).expanduser().absolute()
    if not exe.is_file():
        return
    if os.path.normcase(str(exe)) == os.path.normcase(os.path.abspath(sys.executable)):
        return
    if os.environ.get("QUAN_STORY_REEXEC") == "1":
        raise SystemExit("托管 Python 无法启动，请检查 runtime.json")
    env = dict(os.environ, QUAN_STORY_REEXEC="1", PYTHONUTF8="1")
    raise SystemExit(subprocess.run([str(exe), "-X", "utf8", *sys.argv], env=env).returncode)


activate_runtime()

from PIL import Image  # noqa: E402
import pyJianYingDraft as draft  # noqa: E402


# ------------------------------------------------------------ 运镜（与本地渲染一致）

def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def ease_out_cubic(u: float) -> float:
    return 1.0 - (1.0 - _clamp(u, 0.0, 1.0)) ** 3


def ease_in_cubic(u: float) -> float:
    return _clamp(u, 0.0, 1.0) ** 3


def smoothstep(u: float) -> float:
    u = _clamp(u, 0.0, 1.0)
    return u * u * (3.0 - 2.0 * u)


def resolve_motion(plan: dict) -> None:
    plan.setdefault("cut_punch", False)
    for shot in plan["shots"]:
        shot.setdefault("cut_punch", bool(plan["cut_punch"]))
        shot.setdefault("punch_in", 1.0)
        shot.setdefault("punch_out", 1.0)
        shot.setdefault("punch_in_dur", 0.0)
        shot.setdefault("punch_out_dur", 0.0)
        shot["has_punch_in"] = False
        shot["has_punch_out"] = False
        shot["duration_s"] = shot["frames"] / plan["fps"]


def zoom_at(shot: dict, t_rel: float, duration_s: float) -> float:
    z0, z1 = float(shot["zoom"][0]), float(shot["zoom"][1])
    if duration_s <= 0:
        return z0
    t = _clamp(float(t_rel), 0.0, duration_s)
    return z0 + (z1 - z0) * smoothstep(t / duration_s)


# ------------------------------------------------------------ 素材与计划

def probe(path: Path) -> dict:
    ffprobe = find_exe("ffprobe")
    if not ffprobe:
        raise SystemExit("找不到 ffprobe，无法读取音频时长")
    out = subprocess.run(
        [ffprobe, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
        capture_output=True, check=True,
    )
    return json.loads(out.stdout.decode("utf-8", "replace"))


def safe_name(name: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(name)).strip().strip(". ")
    if not value or value in {".", ".."}:
        raise SystemExit(f"草稿名不合法：{name}")
    return value


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_material(source: Path, directory: Path) -> Path:
    target = directory / (file_hash(source)[:24] + source.suffix.lower())
    if not target.exists():
        shutil.copy2(source, target)
    return target


def load_plan(path: Path) -> dict:
    plan = json.loads(path.read_text(encoding="utf-8-sig"))
    for key, default in [("width", 1080), ("height", 1920), ("fps", 30), ("crf", 18)]:
        plan.setdefault(key, default)
    w, h, fps = plan["width"], plan["height"], plan["fps"]
    if any(type(x) is not int or x <= 0 for x in (w, h, fps)) or w % 2 or h % 2:
        raise SystemExit("宽高必须是正偶数、fps 必须是正整数")
    if not plan.get("shots"):
        raise SystemExit("plan 里没有 shots")

    base = path.resolve().parent
    cursor, seen = 0, set()
    for shot in plan["shots"]:
        sid = shot["id"]
        if not re.fullmatch(r"[A-Za-z0-9_-]+", sid) or sid in seen:
            raise SystemExit(f"镜号必须是唯一的安全文件名：{sid}")
        seen.add(sid)
        begin, finish = float(shot["start"]), float(shot["end"])
        if not math.isfinite(begin + finish) or finish <= begin:
            raise SystemExit(f"{sid}: 时间不合法")
        fa, fb = round(begin * fps), round(finish * fps)
        if fa != cursor or fb <= fa:
            raise SystemExit(f"{sid}: 与上一镜有间隙、重叠或零帧")
        shot.update(start_frame=fa, end_frame=fb, frames=fb - fa)
        cursor = fb
        image = shot.get("image")
        if not image:
            raise SystemExit(f"{sid}: 缺少图片")
        shot["image"] = str((base / image).resolve())
        if not Path(shot["image"]).is_file():
            raise SystemExit(f"{sid}: 图片不存在 {shot['image']}")
        with Image.open(shot["image"]) as im:
            im.verify()
        shot.setdefault("zoom", [1.0, 1.07])
        shot.setdefault("pivot", [0.5, 0.5])
        if len(shot["zoom"]) != 2 or any(z < 1 for z in shot["zoom"]):
            raise SystemExit(f"{sid}: zoom 需要两个 >= 1 的值")
        if len(shot["pivot"]) != 2 or any(not 0 <= p <= 1 for p in shot["pivot"]):
            raise SystemExit(f"{sid}: pivot 需要两个 0..1 的值")
    plan["duration"] = cursor / fps
    resolve_motion(plan)

    if plan.get("audio"):
        plan["audio"] = str((base / plan["audio"]).resolve())
        info = probe(Path(plan["audio"]))
        if not any(s["codec_type"] == "audio" for s in info["streams"]):
            raise SystemExit("音频文件没有音轨")
        plan["audio_duration"] = float(info["format"]["duration"])
        if plan["audio_duration"] > plan["duration"] + 1 / fps:
            raise SystemExit("时间轴比配音短，延长末镜后再导出")
    if plan.get("subtitles"):
        plan["subtitles"] = str((base / plan["subtitles"]).resolve())
        if not Path(plan["subtitles"]).is_file():
            raise SystemExit(f"字幕不存在：{plan['subtitles']}")
    return plan


def cover_scale(src_w: int, src_h: int, width: int, height: int) -> float:
    """图片铺满画面所需倍率；留 4% 余量给平移关键帧。"""
    contain = min(width / src_w, height / src_h)
    return max(width / src_w, height / src_h) / contain * 1.04


def ken_burns(zoom: float, pivot: list[float], cover: float) -> tuple[float, float, float]:
    scale = cover * zoom
    extra = max(0.0, scale - 1.0)
    return scale, (0.5 - pivot[0]) * 2 * extra, (0.5 - pivot[1]) * 2 * extra


def media_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return image.size


def motion_samples(shot: dict, fps: int) -> list[tuple[int, float]]:
    frames = shot["frames"]
    duration = frames / fps
    points = [
        (int(round(frame * 1_000_000 / fps)),
         zoom_at(shot, frame / max(1, frames - 1) * duration, duration))
        for frame in range(frames)
    ]
    end = int(round(duration * 1_000_000)) - 1
    if end > points[-1][0]:
        points.append((end, points[-1][1]))
    return points


def apply_motion(segment, shot: dict, fps: int, cover: float) -> None:
    points = motion_samples(shot, fps)
    poses = [ken_burns(z, shot["pivot"], cover) for _, z in points]
    scale, x, y = poses[0]
    segment.clip_settings.scale_x = segment.clip_settings.scale_y = scale
    segment.clip_settings.transform_x, segment.clip_settings.transform_y = x, y
    need_x = any(abs(p[1]) > 1e-8 for p in poses)
    need_y = any(abs(p[2]) > 1e-8 for p in poses)
    for (stamp, _), (scale, x, y) in zip(points, poses):
        segment.add_keyframe(draft.KeyframeProperty.uniform_scale, stamp, scale)
        if need_x:
            segment.add_keyframe(draft.KeyframeProperty.position_x, stamp, x)
        if need_y:
            segment.add_keyframe(draft.KeyframeProperty.position_y, stamp, y)


def srt_seconds(stamp: str) -> float:
    match = re.match(r"^(\d+):(\d{2}):(\d{2})[,.](\d{3})", stamp.strip())
    if not match:
        raise SystemExit("SRT 时间戳格式不对")
    h, m, s, ms = map(int, match.groups())
    return h * 3600 + m * 60 + s + ms / 1000


def parse_srt(path: Path) -> list[dict]:
    cues = []
    raw = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    for block in re.split(r"\n\s*\n", raw.strip()):
        lines = block.splitlines()
        if lines and lines[0].strip().isdigit():
            lines = lines[1:]
        if not lines or "-->" not in lines[0]:
            continue
        start, end = map(srt_seconds, lines[0].split("-->", 1))
        text = "\n".join(lines[1:]).strip()
        if text and end > start:
            cues.append({"start": start, "end": end, "text": text})
    return cues


def relocate(value, staging: Path, target: Path):
    if isinstance(value, dict):
        return {k: relocate(v, staging, target) for k, v in value.items()}
    if isinstance(value, list):
        return [relocate(v, staging, target) for v in value]
    if isinstance(value, str):
        normalized = value.replace("\\", "/")
        prefix = staging.as_posix()
        if normalized == prefix or normalized.startswith(prefix + "/"):
            return target.as_posix() + normalized[len(prefix):]
    return value


def export_plan(plan_path: Path, name: str, overwrite: bool = False,
                drafts_root: str | None = None, with_subtitles: bool = False) -> dict:
    plan_path = plan_path.resolve()
    plan = load_plan(plan_path)
    root = jianying_root(drafts_root)
    if not root:
        raise SystemExit("没找到剪映草稿目录，请用 --drafts-root 指定")
    root.mkdir(parents=True, exist_ok=True)
    name = safe_name(name)
    target = root / name
    if target.exists() and not overwrite:
        raise SystemExit(f"草稿 {name} 已存在：换个新名字（版本号加一），不要覆盖用户正在剪的草稿")
    staging = root / (".quan-story-" + uuid.uuid4().hex)
    warnings: list[str] = []
    cues = parse_srt(Path(plan["subtitles"])) if plan.get("subtitles") and with_subtitles else []
    if cues and max(c["end"] for c in cues) > plan["duration"] + 1 / plan["fps"]:
        raise SystemExit("字幕超出时间轴")

    try:
        script = draft.DraftFolder(str(root)).create_draft(
            staging.name, plan["width"], plan["height"], plan["fps"], maintrack_adsorb=False
        )
        materials = staging / "materials"
        materials.mkdir()
        audio = None
        if plan.get("audio"):
            audio = draft.AudioMaterial(str(copy_material(Path(plan["audio"]), materials)))
            if abs(audio.duration / 1_000_000 - plan["audio_duration"]) > 1 / plan["fps"] + 0.001:
                raise SystemExit("音频时长两次探测差超过一帧，重新编码为 CBR 后再试")
            if audio.duration > round(plan["duration"] * 1_000_000):
                last = plan["shots"][-1]
                end_frame = math.ceil(audio.duration * plan["fps"] / 1_000_000)
                if end_frame - last["end_frame"] > 1:
                    raise SystemExit("末镜没有盖住全部旁白，回到 VERIFY 修时间轴")
                last.update(end_frame=end_frame, frames=end_frame - last["start_frame"],
                            end=end_frame / plan["fps"], duration_s=(end_frame - last["start_frame"]) / plan["fps"])
                plan["duration"] = end_frame / plan["fps"]
                resolve_motion(plan)
                warnings.append("末镜延了一帧以保住最后一句")

        script.append_track(draft.TrackSpec(draft.TrackType.video, "VideoTrack"))
        for shot in plan["shots"]:
            source = Path(shot["image"])
            copied = copy_material(source, materials)
            material = draft.VideoMaterial(str(copied))
            if material.material_type != "photo":
                raise SystemExit(f"{shot['id']}: 素材没被识别为图片")
            start = round(shot["start_frame"] * 1_000_000 / plan["fps"])
            end = round(shot["end_frame"] * 1_000_000 / plan["fps"])
            segment = draft.VideoSegment(material, draft.Timerange(start, end - start), volume=0)
            width, height = media_size(source)
            apply_motion(segment, shot, plan["fps"], cover_scale(width, height, plan["width"], plan["height"]))
            script.add_segment(segment, "VideoTrack")

        if audio is not None:
            script.append_track(draft.TrackSpec(draft.TrackType.audio, "Narration"))
            script.add_segment(draft.AudioSegment(audio, draft.Timerange(0, audio.duration)), "Narration")

        if cues:
            script.append_track(draft.TrackSpec(draft.TrackType.text, "Subtitles"))
            for cue in cues:
                script.add_segment(draft.TextSegment(
                    cue["text"],
                    draft.Timerange(round(cue["start"] * 1_000_000), round((cue["end"] - cue["start"]) * 1_000_000)),
                    style=draft.TextStyle(size=5, align=1, auto_wrapping=True, max_line_width=0.86),
                    border=draft.TextBorder(width=40),
                    clip_settings=draft.ClipSettings(transform_y=-0.8),
                ), "Subtitles")

        script.save()
        content_path = staging / "draft_content.json"
        content = relocate(json.loads(content_path.read_text(encoding="utf-8")), staging, target)
        content["name"] = name
        payload = json.dumps(content, ensure_ascii=False, indent=2)
        content_path.write_text(payload, encoding="utf-8")
        (staging / "draft_info.json").write_text(payload, encoding="utf-8")
        meta_path = staging / "draft_meta_info.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        now = int(time.time() * 1_000_000)
        meta.update(
            draft_name=name, draft_fold_path=target.as_posix(), draft_root_path=root.as_posix(),
            draft_timeline_materials_size_=sum(p.stat().st_size for p in materials.iterdir()),
            tm_draft_create=now, tm_draft_modified=now,
            tm_duration=content["duration"], draft_id=content.get("id", uuid.uuid4().hex),
        )
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        backup = None
        if target.exists():
            backup = root / (name + ".backup-" + uuid.uuid4().hex[:8])
            target.rename(backup)
        staging.rename(target)

        info = {
            "backend": "pyJianYingDraft",
            "draft_name": name,
            "draft_path": str(target),
            "width": plan["width"], "height": plan["height"], "fps": plan["fps"],
            "duration": round(content["duration"] / 1_000_000, 2),
            "shots": len(plan["shots"]),
            "audio": bool(plan.get("audio")),
            "subtitles": bool(cues),
            "warnings": warnings,
        }
        if backup:
            info["previous_draft_backup"] = str(backup)
        (plan_path.parent / "jianying_draft.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        (plan_path.parent / "resolved_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        return info
    except BaseException:
        if staging.is_dir() and staging.name.startswith(".quan-story-"):
            shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--name", required=True, help="草稿名，建议 人物名_edit_v1")
    parser.add_argument("--drafts-root")
    parser.add_argument("--overwrite", action="store_true", help="覆盖同名草稿（先备份旧草稿）")
    parser.add_argument("--with-subtitles", action="store_true", help="把字幕烧进草稿文字轨（默认不上屏）")
    args = parser.parse_args()
    info = export_plan(args.plan, args.name, args.overwrite, args.drafts_root, args.with_subtitles)
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
