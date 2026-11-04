#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quan 故事工坊 · 本地工具链

把「正文 -> quan 配音 -> 转录 -> 分镜定时 -> quan 配图 -> 剪映草稿」里
所有需要算时间、查一致性、拼图复核的机械动作固定下来。

子命令
    doctor   检查运行环境（依赖、ffprobe、Coli、剪映草稿根目录）
    probe    读音频/正文，报时长、字数、实际语速
    suggest  按实测语速给出三档镜数建议，供用户挑图片数量
    build    正文 + 镜头草稿 -> STORYBOARD.json（锚点定位，自动分配时间）
    realign  配音换版后，按字符位置把旧镜界重映射到新转录
    plan     STORYBOARD.json -> plan.json（剪映草稿时间轴）
    verify   校验时间轴、图片、语速分布，出问题就非零退出
    contact  生成带镜号的缩略图拼版，供人工一次看完所有画面

设计约束
    - 只依赖标准库；contact 需要 Pillow，verify 读图片尺寸也要 Pillow。
    - 不写死任何机器路径，运行时配置从外部 runtime.json / 环境变量取。
    - 时间轴优先用本机转录（Coli）的 cue 时间；无转录时退化为全文匀速，
      并在产物里标注 timing_status，不把估算说成精确。
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCHEMA = "quan-story-studio/1"

# 默认口播语速约每秒 5.3 个汉字，仅用于没有音频时估时长。
# 有音频时一律以实际时长为准；不同用户的音色和语速可能明显不同。
CHARS_PER_SECOND = 5.3
# 每镜目标时长（秒）。太快观众没看清画面，太慢画面会"熬"。
PACE = {"fast": 6.0, "standard": 8.0, "slow": 10.0}
MIN_SHOT_SECONDS = 3.0
MAX_SHOT_SECONDS = 18.0


# ---------------------------------------------------------------- 基础设施

def data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData/Local")
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    return base


def load_runtime() -> dict:
    """读运行时配置；自己没有就继承 story-studio 已验证的那份。"""
    candidates = [
        Path(os.environ.get("QUAN_STORY_CONFIG", "")) if os.environ.get("QUAN_STORY_CONFIG") else None,
        data_dir() / "quan-story-studio" / "runtime.json",
        data_dir() / "story-studio" / "runtime.json",
    ]
    for path in candidates:
        if path and path.is_file():
            try:
                value = json.loads(path.read_text(encoding="utf-8-sig"))
            except (ValueError, OSError):
                continue
            if isinstance(value, dict):
                value["_source"] = str(path)
                return value
    return {}


def tool_path() -> None:
    dirs = load_runtime().get("tool_dirs") or []
    usable = [str(Path(d).expanduser()) for d in dirs if Path(str(d)).expanduser().is_dir()]
    if usable:
        os.environ["PATH"] = os.pathsep.join(usable + os.environ.get("PATH", "").split(os.pathsep))


def find_exe(name: str) -> str | None:
    tool_path()
    configured = load_runtime().get(name + "_bin")
    if configured:
        path = Path(str(configured)).expanduser()
        if path.is_file():
            return str(path)
    if os.name == "nt":
        return shutil.which(name + ".exe") or shutil.which(name + ".cmd") or shutil.which(name)
    return shutil.which(name)


def jianying_root(explicit: str | None = None) -> Path | None:
    selected = explicit or os.environ.get("JY_PROJECTS_ROOT") or load_runtime().get("drafts_root")
    if selected:
        return Path(selected).expanduser()
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        setting = Path(os.environ["LOCALAPPDATA"]) / "JianyingPro/User Data/Config/globalSetting"
        if setting.is_file() and setting.stat().st_size < 1024 * 1024:
            text = setting.read_text(encoding="utf-8-sig", errors="replace")
            match = re.search(r'(?m)^\s*currentCustomDraftPath\s*=\s*(.*?)\s*$', text)
            if match:
                value = match.group(1).strip('"')
                if Path(value).is_absolute():
                    return Path(value)
        candidate = Path(os.environ["LOCALAPPDATA"]) / "JianyingPro/User Data/Projects/com.lveditor.draft"
        return candidate if candidate.is_dir() else None
    if sys.platform == "darwin":
        for candidate in (
            Path.home() / "Movies/JianyingPro/User Data/Projects/com.lveditor.draft",
            Path.home() / "Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Projects/com.lveditor.draft",
        ):
            if candidate.is_dir():
                return candidate
    return None


def probe_audio(path: Path) -> float:
    ffprobe = find_exe("ffprobe")
    if not ffprobe:
        raise SystemExit("找不到 ffprobe：请先按 SKILL.md 的依赖步骤配置 ffmpeg，或改用 --duration 手动给时长")
    out = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, check=True,
    )
    return float(json.loads(out.stdout.decode("utf-8", "replace"))["format"]["duration"])


# ---------------------------------------------------------------- 文本处理

def keep_char(ch: str) -> bool:
    if ch.isspace():
        return False
    return unicodedata.category(ch)[0] not in ("P", "Z", "S", "C")


def norm(text: str) -> str:
    """只留实义字符：去标点、空白、符号，用于跨文本/跨版本对齐。"""
    return "".join(ch for ch in text if keep_char(ch))


def read_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig")
    # 去掉 Markdown 标题行和分隔线，口播稿正文才计入语速
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or set(stripped) <= {"-", "*", "_", "="} and stripped:
            continue
        lines.append(line)
    body = "\n".join(lines).strip() or text
    return body


def parse_srt(path: Path) -> list[tuple[float, float, str]]:
    cues = []
    raw = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    for block in re.split(r"\n\s*\n", raw.strip()):
        lines = block.splitlines()
        if lines and lines[0].strip().isdigit():
            lines = lines[1:]
        if not lines or "-->" not in lines[0]:
            continue
        head = lines[0]
        match = re.match(
            r"(\d+):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d+):(\d{2}):(\d{2})[,.](\d{3})", head
        )
        if not match:
            continue
        g = list(map(int, match.groups()))
        start = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
        end = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        text = "\n".join(lines[1:]).strip()
        if text and end > start:
            cues.append((start, end, text))
    return cues


def load_cues(path: Path) -> list[tuple[float, float, str]]:
    if path.suffix.lower() == ".srt":
        return parse_srt(path)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, dict):
        for key in ("cues", "segments", "items"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
        else:
            raise SystemExit(f"{path.name}: 没有 cues/segments 数组")
    cues = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            start = float(item.get("start", item.get("begin_time", 0)) or 0)
            end = float(item.get("end", item.get("finish_time", 0)) or 0)
        except (TypeError, ValueError):
            continue
        text = str(item.get("text", "") or "")
        if end > start and text.strip():
            cues.append((start, end, text))
    return cues


def load_tokens(path: Path) -> tuple[list[tuple[str, float]], float | None] | None:
    """Coli 原始 ASR 带字级时间戳，能把镜界精度从「句」提到「字」。"""
    if path.suffix.lower() != ".json":
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (ValueError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    tokens, stamps = data.get("tokens"), data.get("timestamps")
    if not isinstance(tokens, list) or not isinstance(stamps, list) or len(tokens) != len(stamps):
        return None
    pairs: list[tuple[str, float]] = []
    for token, stamp in zip(tokens, stamps):
        try:
            moment = float(stamp)
        except (TypeError, ValueError):
            continue
        for ch in norm(str(token)):
            pairs.append((ch, moment))
    duration = data.get("duration")
    return (pairs, float(duration) if isinstance(duration, (int, float)) else None) if pairs else None


def load_timing(path: Path) -> dict:
    """统一入口：字级时间戳优先，其次 cue，最后只有时长。"""
    tokens = load_tokens(path)
    if tokens:
        return {"tokens": tokens[0], "cues": None, "duration": tokens[1], "kind": "tokens"}
    cues = load_cues(path)
    if not cues:
        raise SystemExit(f"{path.name}: 没有可用的时间信息")
    return {"tokens": None, "cues": cues, "duration": cues[-1][1], "kind": "cues"}


class Timeline:
    """字符位置 <-> 时间。位置按规范化文本累计，标点不计。

    有字级时间戳时直接查表（误差约 0.12 秒）；只有 cue 时按 cue 内匀速插值；
    什么都没有就按全篇匀速——后者只用于估时长，不写进最终时间轴。
    """

    def __init__(self, cues: list[tuple[float, float, str]] | None = None,
                 duration: float | None = None,
                 tokens: list[tuple[str, float]] | None = None):
        self.segments: list[tuple[int, int, float, float]] = []
        self.chars: list[str] = []
        self.stamps: list[float] = []
        self.text = ""
        self.precise = bool(tokens)
        if tokens:
            self.chars = [ch for ch, _ in tokens]
            self.stamps = [t for _, t in tokens]
            self.text = "".join(self.chars)
            if duration is None and self.stamps:
                duration = self.stamps[-1] + 0.12
        elif cues:
            cursor = 0
            for start, end, text in cues:
                piece = norm(text)
                if not piece:
                    continue
                self.segments.append((cursor, cursor + len(piece), start, end))
                cursor += len(piece)
                self.text += piece
        self.total = len(self.text)
        self.duration = duration
        if self.duration is None and self.segments:
            self.duration = self.segments[-1][3]
        if self.duration is None:
            raise SystemExit("既没有转录也没有音频时长，无法建立时间轴")

    @property
    def anchored(self) -> bool:
        return self.precise or bool(self.segments)

    def pos_to_time(self, pos: float) -> float:
        if self.precise:
            if not self.stamps:
                return float(self.duration)
            index = int(round(pos))
            if index <= 0:
                return 0.0
            if index >= self.total:
                return float(self.duration)
            return self.stamps[index]
        if not self.anchored:
            ratio = 0.0 if not self.total else max(0.0, min(1.0, float(pos) / self.total))
            return ratio * float(self.duration)
        pos = max(0.0, min(float(self.total), float(pos)))
        for cum_start, cum_end, start, end in self.segments:
            if pos <= cum_end:
                span = cum_end - cum_start
                frac = 0.0 if span <= 0 else (pos - cum_start) / span
                return start + (end - start) * max(0.0, min(1.0, frac))
        return float(self.duration)

    def time_to_pos(self, t: float) -> float:
        if self.precise:
            import bisect
            index = bisect.bisect_left(self.stamps, float(t))
            return float(min(max(index, 0), self.total))
        if not self.anchored:
            return float(self.total) * max(0.0, min(1.0, t / float(self.duration)))
        for cum_start, cum_end, start, end in self.segments:
            if t <= end:
                span = end - start
                frac = 0.0 if span <= 0 else (t - start) / span
                return cum_start + (cum_end - cum_start) * max(0.0, min(1.0, frac))
        return float(self.total)


def find_anchor(text: str, anchor: str, occurrence: int = 1) -> int:
    """在规范化文本里找锚点，返回字符位置；-1 表示没找到。"""
    target = norm(anchor)
    if not target:
        return -1
    seen = 0
    start = 0
    while True:
        index = text.find(target, start)
        if index < 0:
            break
        seen += 1
        if seen >= max(1, occurrence):
            return index
        start = index + 1
    # 回退：ASR 可能在锚点中段听错，用前 12 / 前 8 字再试
    for cut in (12, 8, 5):
        if len(target) > cut:
            index = text.find(target[:cut])
            if index >= 0:
                return index
    return -1


def fuzzy_locate(text: str, anchor: str, expected: float, window: int = 140, width: int = 18) -> int:
    """ASR 把同音字听错时，在预估位置附近做相似度滑窗，避免整镜退回比例估算。"""
    import difflib
    target = norm(anchor)[:width]
    if len(target) < 4 or not text:
        return -1
    guess = max(0, min(len(text) - len(target), int(expected)))
    lo = max(0, guess - window)
    hi = min(len(text) - len(target), guess + window)
    best, best_score = -1, 0.0
    matcher = difflib.SequenceMatcher()
    matcher.set_seq2(target)
    for index in range(lo, hi + 1):
        matcher.set_seq1(text[index:index + len(target)])
        score = matcher.quick_ratio()
        if score > best_score:
            # quick_ratio 只做上界估计，命中候选再算真值
            real = difflib.SequenceMatcher(None, text[index:index + len(target)], target).ratio()
            if real > best_score:
                best_score, best = real, index
    return best if best_score >= 0.62 else -1


def enforce_minimum(times: list[list[float]], minimum: float, total: float) -> list[list[float]]:
    """保证每镜不短于 minimum，最后整体压回 total。"""
    for index in range(len(times)):
        if times[index][1] - times[index][0] < minimum:
            need = minimum - (times[index][1] - times[index][0])
            times[index][1] += need
            for j in range(index + 1, len(times)):
                times[j][0] += need
                times[j][1] += need
    span = times[-1][1]
    if span > total + 1e-6:
        scale = total / span
        for item in times:
            item[0] = round(item[0] * scale, 3)
            item[1] = round(item[1] * scale, 3)
    for i in range(1, len(times)):
        times[i][0] = times[i - 1][1]
    times[0][0] = 0.0
    times[-1][1] = round(total, 3)
    return times


# ---------------------------------------------------------------- 子命令

def cmd_doctor(args) -> int:
    runtime = load_runtime()
    print("== Quan 故事工坊 环境检查 ==")
    print(f"Python           : {sys.version.split()[0]}  ({sys.executable})")
    problems = []
    try:
        import PIL  # noqa: F401
        print("Pillow           : 可用")
    except ImportError:
        problems.append("缺 Pillow：contact / verify 读图需要它")
        print("Pillow           : 缺失")
    try:
        import pyJianYingDraft  # noqa: F401
        print("pyJianYingDraft  : 可用")
    except ImportError:
        problems.append("缺 pyJianYingDraft：写剪映草稿需要它（pip install pyJianYingDraft==0.3.1）")
        print("pyJianYingDraft  : 缺失")
    ffprobe = find_exe("ffprobe")
    print(f"ffprobe          : {ffprobe or '缺失'}")
    if not ffprobe:
        problems.append("缺 ffprobe：无法读配音时长")
    coli = find_exe("coli")
    print(f"Coli 转录        : {coli or '缺失（可由用户提供 SRT 代替）'}")
    root = jianying_root(args.drafts_root)
    state = "存在" if root and root.is_dir() else "未找到"
    print(f"剪映草稿根目录   : {root}  [{state}]")
    if not root or not root.is_dir():
        problems.append("没定位到剪映草稿目录：用 --drafts-root 或环境变量 JY_PROJECTS_ROOT 指定")
    print(f"运行时配置来源   : {runtime.get('_source') or '无（使用系统默认）'}")
    if problems:
        print("\n需要处理：")
        for item in problems:
            print(" - " + item)
        return 1
    print("\n全部就绪。")
    return 0


def cmd_probe(args) -> int:
    result = {}
    duration = None
    if args.audio:
        duration = probe_audio(Path(args.audio))
        result["audio"] = str(Path(args.audio).resolve())
        result["duration"] = round(duration, 3)
    if args.text:
        body = read_text(Path(args.text))
        chars = len(norm(body))
        result["text"] = str(Path(args.text).resolve())
        result["chars"] = chars
        if duration:
            result["chars_per_second"] = round(chars / duration, 2)
    if args.timing:
        info = load_timing(Path(args.timing))
        result["timing"] = str(Path(args.timing).resolve())
        result["timing_kind"] = info["kind"]
        if info["kind"] == "tokens":
            result["chars_in_timing"] = len(info["tokens"])
        else:
            result["cues"] = len(info["cues"])
        if duration is None:
            duration = info["duration"]
            result["duration"] = round(duration, 3)
    if duration is None:
        raise SystemExit("至少给 --audio 或 --timing 之一")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_suggest(args) -> int:
    if args.audio:
        duration = args.duration or probe_audio(Path(args.audio))
    elif args.duration:
        duration = args.duration
    elif args.text:
        chars = len(norm(read_text(Path(args.text))))
        duration = chars / CHARS_PER_SECOND
        print(f"（没有音频，按实测语速 {CHARS_PER_SECOND} 字/秒 估算时长）")
    else:
        raise SystemExit("给 --audio 或 --text 或 --duration")
    duration = float(duration)
    chars = len(norm(read_text(Path(args.text)))) if args.text else None

    rows = []
    for name, pace in PACE.items():
        count = max(6, round(duration / pace))
        rows.append({
            "pace": name,
            "shots": count,
            "seconds_per_shot": round(duration / count, 2),
            "chars_per_shot": round(chars / count, 1) if chars else None,
        })
    payload = {
        "duration": round(duration, 3),
        "duration_text": f"{int(duration // 60)}分{round(duration % 60)}秒",
        "chars": chars,
        "chars_per_second": round(chars / duration, 2) if chars else None,
        "options": rows,
        "recommended": "standard",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if not args.json_only:
        print("\n三档节奏（挑一档告诉用户）:")
        label = {"fast": "快节奏 6 秒/镜", "standard": "标准 8 秒/镜", "slow": "舒缓 10 秒/镜"}
        for row in rows:
            extra = f"，每镜约 {row['chars_per_shot']} 字" if row["chars_per_shot"] else ""
            print(f"  {label[row['pace']]:<14} {row['shots']:>3} 张{extra}")
    return 0


def cmd_build(args) -> int:
    sheet_path = Path(args.sheet)
    sheet = json.loads(sheet_path.read_text(encoding="utf-8-sig"))
    shots_in = sheet.get("shots") or []
    if not shots_in:
        raise SystemExit("镜头草稿里没有 shots")

    body = read_text(Path(args.text)) if args.text else ""
    timing = load_timing(Path(args.timing)) if args.timing else {"tokens": None, "cues": None, "duration": None, "kind": "none"}
    duration = args.duration
    if duration is None and args.audio:
        duration = probe_audio(Path(args.audio))
    if duration is None:
        duration = timing["duration"]
    if duration is None:
        raise SystemExit("必须给 --audio / --timing / --duration 之一作为总时长")
    timeline = Timeline(timing["cues"], duration, timing["tokens"])

    # 锚点在"转录文本"里找最准（时间轴就是按它建的）；没有转录就用正文
    search_text = timeline.text if timeline.anchored else norm(body)
    body_norm = norm(body)
    if timeline.anchored and body_norm:
        diff = abs(len(body_norm) - timeline.total) / max(1, timeline.total)
        if diff > 0.08:
            print(f"[警告] 正文与转录字数差 {diff:.1%}，锚点将优先在转录取证，注意核对", file=sys.stderr)

    # 第一轮：逐镜定位。精确匹配 -> 模糊滑窗（ASR 同音字）-> 留待第二轮插值
    anchors: list[str] = []
    body_positions: list[int] = []
    hits: list[int] = []
    warnings: list[str] = []
    counts = {"exact": 0, "fuzzy": 0, "interpolated": 0}
    for index, shot in enumerate(shots_in):
        anchor = str(shot.get("anchor") or shot.get("start_anchor") or "")
        if not anchor:
            raise SystemExit(f"{shot.get('id', index)}: 缺少 anchor（该镜口播的原句开头）")
        occurrence = int(shot.get("anchor_occurrence") or 1)
        anchors.append(anchor)
        body_pos = find_anchor(body_norm, anchor, occurrence) if body_norm else -1
        body_positions.append(body_pos)
        if body_pos >= 0 and body_norm:
            expected = body_pos / len(body_norm) * timeline.total
        else:
            expected = index / max(1, len(shots_in)) * timeline.total
        position = find_anchor(search_text, anchor, occurrence)
        if position >= 0:
            counts["exact"] += 1
        else:
            position = fuzzy_locate(search_text, anchor, expected)
            if position >= 0:
                counts["fuzzy"] += 1
                warnings.append(f"{shot.get('id', index)}: 转录有同音字差异，已用相似度定位")
        hits.append(position)

    # 第二轮：没命中的镜夹在前后已命中镜之间按正文比例插值，避免整篇误差累积
    known = [i for i, hit in enumerate(hits) if hit >= 0]
    for index, hit in enumerate(hits):
        if hit >= 0:
            continue
        sid = shots_in[index].get("id", index)
        before = max((k for k in known if k < index), default=None)
        after = min((k for k in known if k > index), default=None)
        if (before is not None and after is not None
                and body_positions[before] is not None and body_positions[after] is not None):
            span_body = body_positions[after] - body_positions[before]
            span_pos = hits[after] - hits[before]
            frac = (body_positions[index] - body_positions[before]) / span_body if span_body else 0.5
            hits[index] = round(hits[before] + max(0.0, min(1.0, frac)) * span_pos)
            counts["interpolated"] += 1
            warnings.append(f"{sid}: 转录未命中，按相邻镜比例插值，建议听一遍")
        elif body_positions[index] is not None:
            hits[index] = round(body_positions[index] / len(body_norm) * timeline.total)
            counts["interpolated"] += 1
            warnings.append(f"{sid}: 只在正文命中，按全文比例映射，建议听一遍")
        else:
            hits[index] = round(index / max(1, len(shots_in)) * timeline.total)
            counts["interpolated"] += 1
            warnings.append(f"{sid}: 锚点完全未命中，按序号均分，必须人工定位")

    starts: list[float] = []
    for index, hit in enumerate(hits):
        if starts and hit <= starts[-1]:
            hit = int(starts[-1]) + 1
            warnings.append(f"{shots_in[index].get('id', index)}: 锚点顺序回退，已强制后移一位")
        starts.append(float(hit))

    times = []
    for index in range(len(starts)):
        begin = 0.0 if index == 0 else timeline.pos_to_time(starts[index])
        finish = timeline.duration if index == len(starts) - 1 else timeline.pos_to_time(starts[index + 1])
        times.append([round(begin, 3), round(finish, 3)])
    times = enforce_minimum(times, args.min_shot, float(timeline.duration))

    prompt_cfg = sheet.get("prompt") or {}
    prefix = str(prompt_cfg.get("prefix") or "")
    suffix = str(prompt_cfg.get("suffix") or "")
    characters = sheet.get("characters") or []
    by_id = {c.get("id"): c for c in characters if isinstance(c, dict)}

    out_shots = []
    for index, (shot, (begin, finish)) in enumerate(zip(shots_in, times)):
        sid = str(shot.get("id") or f"S{index + 1:03d}")
        chars = shot.get("character_ids") or []
        who = ""
        if chars and chars[0] in by_id:
            person = by_id[chars[0]]
            age = shot.get("character_age") or ""
            label = f"{person.get('name', '')}"
            if age:
                label += f"（{age}）"
            appearance = str(person.get("appearance") or "").strip()
            who = f"主体：{label}" + (f"，{appearance}" if appearance else "") + "。"

        description = str(shot.get("description") or "").strip()
        size = str(shot.get("shot_size") or "中景")
        view = str(shot.get("viewpoint") or "平视")
        body_part = f"{who}{description}" if who else description
        if not body_part.endswith("。"):
            body_part += "。"
        tail = f"景别为{size}，{view}视角。"
        prompt = str(shot.get("prompt") or "").strip()
        if not prompt:
            prompt = f"{prefix}{body_part}{tail}{suffix}"

        narration = ""
        if body_norm:
            body_hit = find_anchor(body_norm, str(shot.get("anchor") or ""), int(shot.get("anchor_occurrence") or 1))
            if body_hit >= 0:
                end = len(body_norm)
                for nxt in shots_in[index + 1:]:
                    nxt_hit = find_anchor(body_norm, str(nxt.get("anchor") or ""), int(nxt.get("anchor_occurrence") or 1))
                    if nxt_hit > body_hit:
                        end = nxt_hit
                        break
                narration = body_norm[body_hit:end]
                body_cursor = end

        out_shots.append({
            "id": sid,
            "narration": narration,
            "start_anchor": str(shot.get("anchor") or ""),
            "anchor_occurrence": int(shot.get("anchor_occurrence") or 1),
            "audio_start": begin,
            "audio_end": finish,
            "description": description,
            "shot_size": size,
            "viewpoint": view,
            "subject": str(shot.get("subject") or ""),
            "character_ids": chars,
            "prompt": prompt,
            "image_filename": str(shot.get("image_filename") or f"{sid}.png"),
            "generation_status": "not_generated",
        })

    style_id = sheet.get("style_id") or "historical-realism"
    result = {
        "schema": SCHEMA,
        "mode": "storyboard",
        "manuscript": str(Path(args.text).resolve()) if args.text else None,
        "style_id": style_id,
        "aspect_ratio": sheet.get("aspect_ratio") or "9:16",
        "era": sheet.get("era") or "",
        "location": sheet.get("location") or "",
        "timing_status": ("token" if timeline.precise else ("anchored" if timeline.anchored else "linear")),
        "timing_basis": {
            "audio": str(Path(args.audio).resolve()) if args.audio else None,
            "duration": round(float(timeline.duration), 3),
            "source": ("transcript-tokens" if timeline.precise
                       else "transcript-cues" if timeline.anchored else "proportional"),
            "cues": len(timing["cues"] or []),
            "tokens": len(timing["tokens"] or []),
        },
        "target_shots": len(out_shots),
        "characters": characters,
        "shots": out_shots,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    durations = [s["audio_end"] - s["audio_start"] for s in out_shots]
    total = out_shots[-1]["audio_end"]

    # 同目录出一份人读的分镜表，用于给用户确认画面方向（闸门 A）
    title = sheet.get("title") or (Path(args.text).stem if args.text else "分镜表")
    md = [
        f"# {title}",
        "",
        f"- 镜数：{len(out_shots)}",
        f"- 总时长：{int(total // 60)} 分 {round(total % 60)} 秒",
        f"- 平均每镜：{sum(durations) / len(durations):.2f} 秒",
        f"- 画风：{result['style_id']}",
        f"- 计时依据：{result['timing_basis']['source']}",
        "",
        "| 镜号 | 时长 | 画面 | 景别 | 机位 | 起句 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for shot, span in zip(out_shots, durations):
        desc = shot["description"].replace("|", "／").replace("\n", " ")
        if len(desc) > 46:
            desc = desc[:46] + "…"
        anchor = norm(shot["start_anchor"])[:14]
        md.append(f"| {shot['id']} | {span:.1f}s | {desc} | {shot['shot_size']} | {shot['viewpoint']} | {anchor} |")
    md_path = out_path.with_suffix(".md")
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"分镜表已写入 {out_path}")
    print(f"人读版：{md_path}")
    print(f"镜数 {len(out_shots)} | 总时长 {durations and out_shots[-1]['audio_end']:.2f}s | "
          f"平均 {sum(durations)/len(durations):.2f}s | 最短 {min(durations):.2f}s | 最长 {max(durations):.2f}s")
    print(f"计时依据：{result['timing_status']}（{result['timing_basis']['source']}）"
          f" | 转录精确 {counts['exact']} 镜 / 相似度 {counts['fuzzy']} 镜 / 插值 {counts['interpolated']} 镜")
    if warnings:
        print("\n需要注意：")
        for item in dict.fromkeys(warnings):
            print(" - " + item)
    return 0


def cmd_realign(args) -> int:
    """配音换版：旧镜界 -> 旧转录字符位置 -> 新转录时间。"""
    old_info = load_timing(Path(args.old_timing))
    new_info = load_timing(Path(args.new_timing))
    old = Timeline(old_info["cues"], old_info["duration"], old_info["tokens"])
    new = Timeline(new_info["cues"], new_info["duration"], new_info["tokens"])
    if not old.anchored or not new.anchored:
        raise SystemExit("两版转录都要有可用 cue")
    sb_path = Path(args.storyboard)
    sb = json.loads(sb_path.read_text(encoding="utf-8-sig"))
    shots = sb["shots"]
    total = float(new.duration)
    times = []
    for shot in shots:
        begin = new.pos_to_time(old.time_to_pos(float(shot["audio_start"])))
        finish = new.pos_to_time(old.time_to_pos(float(shot["audio_end"])))
        times.append([round(begin, 3), round(finish, 3)])
    times = enforce_minimum(times, args.min_shot, total)
    for shot, (begin, finish) in zip(shots, times):
        shot["audio_start"], shot["audio_end"] = begin, finish
    basis = sb.setdefault("timing_basis", {})
    basis["duration"] = round(total, 3)
    basis["source"] = "realigned"
    sb["timing_status"] = "realigned"
    sb_path.write_text(json.dumps(sb, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已按新配音重对齐 {len(shots)} 镜，新总时长 {total:.2f}s")
    print(f"旧字幕字符 {old.total} -> 新字幕字符 {new.total}")
    durs = [b - a for a, b in times]
    print(f"平均 {sum(durs)/len(durs):.2f}s | 最短 {min(durs):.2f}s | 最长 {max(durs):.2f}s")
    return 0


def cmd_plan(args) -> int:
    sb = json.loads(Path(args.storyboard).read_text(encoding="utf-8-sig"))
    shots = sb.get("shots") or []
    if not shots:
        raise SystemExit("分镜表没有 shots")
    sb_dir = Path(args.storyboard).resolve().parent
    image_dir = Path(args.images).resolve() if args.images else sb_dir.parent / "配图"
    base = sb_dir.parent if sb_dir.name == "分镜" else sb_dir

    def rel(target: Path) -> str:
        """同盘写相对路径（草稿可整体搬移），跨盘只能写绝对路径。"""
        try:
            return Path(os.path.relpath(target.resolve(), base)).as_posix()
        except ValueError:
            return target.resolve().as_posix()

    plan_shots = []
    for index, shot in enumerate(shots):
        sid = shot["id"]
        image = Path(args.images) / f"{sid}.png" if args.images else image_dir / f"{sid}.png"
        if args.zoom == "alternate":
            zoom = [1.0, 1.07] if index % 2 == 0 else [1.07, 1.0]
        elif args.zoom == "push":
            zoom = [1.0, 1.07]
        else:
            zoom = [1.0, 1.0]
        plan_shots.append({
            "id": sid,
            "image": rel(image),
            "start": round(float(shot["audio_start"]), 3),
            "end": round(float(shot["audio_end"]), 3),
            "zoom": shot.get("zoom") or zoom,
            "pivot": shot.get("pivot") or [0.5, 0.5],
            "anchor": shot.get("subject") or "",
        })

    plan = {
        "width": args.width,
        "height": args.height,
        "fps": args.fps,
        "crf": 18,
        "audio": rel(Path(args.audio)) if args.audio else None,
        "subtitles": rel(Path(args.subtitles)) if args.subtitles else None,
        "shots": plan_shots,
    }
    if not plan["audio"]:
        plan.pop("audio")
    if not plan["subtitles"]:
        plan.pop("subtitles")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"时间轴已写入 {out}")
    print(f"{len(plan_shots)} 镜 | {plan_shots[0]['start']}s -> {plan_shots[-1]['end']}s | {args.width}x{args.height}@{args.fps}")
    print(f"音频：{plan.get('audio') or '无'} | 字幕：{plan.get('subtitles') or '不上屏'}")
    return 0


def cmd_verify(args) -> int:
    plan_path = Path(args.plan)
    plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
    base = plan_path.resolve().parent
    shots = plan.get("shots") or []
    problems: list[str] = []
    notes: list[str] = []

    if not shots:
        print("没有 shots"); return 1

    cursor = 0.0
    for shot in shots:
        begin, finish = float(shot["start"]), float(shot["end"])
        if abs(begin - cursor) > 0.01:
            problems.append(f"{shot['id']}: 与上一镜不连续（上一镜结束 {cursor:.3f}，本镜开始 {begin:.3f}）")
        if finish <= begin:
            problems.append(f"{shot['id']}: 时长或顺序错误")
        cursor = finish
    if abs(float(shots[0]["start"])) > 0.001:
        problems.append("首镜没有从 0 秒开始")

    duration = float(plan.get("duration") or cursor)
    if plan.get("audio"):
        audio_path = (base / plan["audio"]).resolve()
        if not audio_path.is_file():
            problems.append(f"音频不存在：{audio_path}")
        else:
            actual = probe_audio(audio_path)
            if abs(actual - cursor) > 0.12:
                problems.append(f"时间轴 {cursor:.2f}s 与配音 {actual:.2f}s 相差 {abs(actual-cursor):.2f}s，末镜没盖住旁白")
            else:
                notes.append(f"配音 {actual:.2f}s 与时间轴吻合")

    hashes: dict[str, str] = {}
    try:
        from PIL import Image
        import hashlib
    except ImportError:
        Image = None
    for shot in shots:
        image_value = shot.get("image")
        if not image_value:
            continue
        path = (base / image_value).resolve()
        if not path.is_file():
            problems.append(f"{shot['id']}: 缺图 {path}")
            continue
        span = float(shot["end"]) - float(shot["start"])
        if span < MIN_SHOT_SECONDS - 0.01:
            notes.append(f"{shot['id']}: 仅 {span:.2f}s，偏短")
        if span > MAX_SHOT_SECONDS:
            notes.append(f"{shot['id']}: {span:.2f}s，偏长，考虑补一镜")
        if Image is not None:
            with Image.open(path) as im:
                width, height = im.size
            ratio = width / height
            target = float(plan.get("width", 1080)) / float(plan.get("height", 1920))
            if abs(ratio - target) > 0.02:
                problems.append(f"{shot['id']}: 比例 {ratio:.3f} 不是 {target:.3f}（{width}x{height}）")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest in hashes:
                notes.append(f"{shot['id']}: 与 {hashes[digest]} 是同一张图")
            else:
                hashes[digest] = shot["id"]

    print(f"检查 {len(shots)} 镜 / 总时长 {cursor:.2f}s")
    if notes:
        print("\n提示：")
        for item in notes:
            print(" - " + item)
    if problems:
        print("\n必须处理：")
        for item in problems:
            print(" ! " + item)
        return 1
    print("\n结构与素材检查通过。")
    return 0


def _label_font(size: int):
    from PIL import ImageFont
    for candidate in (
        "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf",
        "/System/Library/Fonts/PingFang.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ):
        if Path(candidate).is_file():
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                continue
    return ImageFont.load_default()


def cmd_contact(args) -> int:
    try:
        from PIL import Image, ImageDraw
        import hashlib
    except ImportError:
        raise SystemExit("需要 Pillow：pip install pillow")
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8-sig"))
    base = Path(args.plan).resolve().parent
    shots = plan.get("shots") or []
    if not shots:
        raise SystemExit("plan 没有 shots")
    columns = args.columns
    thumb_w = args.thumb_width
    thumb_h = int(thumb_w * 16 / 9)
    font_size = max(13, thumb_w // 11)
    font = _label_font(font_size)
    label_h = font_size + 16
    rows = math.ceil(len(shots) / columns)
    sheet = Image.new("RGB", (columns * thumb_w, rows * (thumb_h + label_h)), (22, 22, 24))
    draw = ImageDraw.Draw(sheet)
    missing = 0
    seen: dict[str, str] = {}
    for index, shot in enumerate(shots):
        row, col = divmod(index, columns)
        x, y = col * thumb_w, row * (thumb_h + label_h)
        image_value = shot.get("image")
        path = (base / image_value).resolve() if image_value else None
        if not path or not path.is_file():
            draw.rectangle([x, y, x + thumb_w, y + thumb_h], fill=(70, 24, 24))
            draw.text((x + 8, y + thumb_h // 2), "缺图", fill=(240, 200, 200), font=font)
            missing += 1
        else:
            with Image.open(path) as im:
                sheet.paste(im.convert("RGB").resize((thumb_w, thumb_h), Image.LANCZOS), (x, y))
            if path.stat().st_size:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
                if digest in seen:
                    draw.rectangle([x + 2, y + 2, x + 2 + font_size * 4, y + 2 + font_size + 8], fill=(150, 40, 40))
                    draw.text((x + 8, y + 5), "重复!", fill=(255, 230, 230), font=font)
                else:
                    seen[digest] = shot["id"]
        span = float(shot["end"]) - float(shot["start"])
        draw.rectangle([x, y + thumb_h, x + thumb_w, y + thumb_h + label_h], fill=(22, 22, 24))
        draw.text((x + 8, y + thumb_h + 6), f"{shot['id']}  {span:.1f}s", fill=(235, 235, 235), font=font)
    out = Path(args.out or (Path(args.plan).parent / "contact_sheet.jpg"))
    sheet.save(out, quality=90)
    print(f"拼版已生成 {out}（{len(shots)} 镜，{columns} 列）")
    if missing:
        print(f"其中 {missing} 镜缺图")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("doctor", help="检查运行环境")
    p.add_argument("--drafts-root")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("probe", help="读音频/正文/转录的基础数据")
    p.add_argument("--audio"); p.add_argument("--text"); p.add_argument("--timing")
    p.set_defaults(func=cmd_probe)

    p = sub.add_parser("suggest", help="按实测语速给三档镜数")
    p.add_argument("--audio"); p.add_argument("--text"); p.add_argument("--duration", type=float)
    p.add_argument("--json-only", action="store_true")
    p.set_defaults(func=cmd_suggest)

    p = sub.add_parser("build", help="镜头草稿 -> STORYBOARD.json")
    p.add_argument("--sheet", required=True, help="镜头草稿 JSON")
    p.add_argument("--text", help="正文（用于取每镜旁白与锚点兜底）")
    p.add_argument("--timing", help="Coli 转录 JSON 或 SRT")
    p.add_argument("--audio")
    p.add_argument("--duration", type=float)
    p.add_argument("--out", required=True)
    p.add_argument("--min-shot", type=float, default=MIN_SHOT_SECONDS)
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("realign", help="换配音后重对齐镜界")
    p.add_argument("--storyboard", required=True)
    p.add_argument("--old-timing", required=True)
    p.add_argument("--new-timing", required=True)
    p.add_argument("--min-shot", type=float, default=MIN_SHOT_SECONDS)
    p.set_defaults(func=cmd_realign)

    p = sub.add_parser("plan", help="STORYBOARD.json -> plan.json")
    p.add_argument("--storyboard", required=True)
    p.add_argument("--audio")
    p.add_argument("--subtitles")
    p.add_argument("--images")
    p.add_argument("--out", required=True)
    p.add_argument("--width", type=int, default=1080)
    p.add_argument("--height", type=int, default=1920)
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--zoom", choices=["alternate", "push", "none"], default="alternate")
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("verify", help="校验时间轴与素材")
    p.add_argument("plan")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("contact", help="生成缩略图拼版")
    p.add_argument("--plan", required=True)
    p.add_argument("--out")
    p.add_argument("--columns", type=int, default=6)
    p.add_argument("--thumb-width", type=int, default=180)
    p.set_defaults(func=cmd_contact)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
