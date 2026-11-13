"""Validate local workflow records. No rendering, network, or semantic inference."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

STAGES = ('G0', 'G1', 'G2', 'G3')
PLAN_FILES = ('SHOT_SCRIPT.csv', 'MOTION_ADAPTATION.csv', 'MOTION_BUDGET.csv', 'STYLE_LOCK.md')
AV_MODES = ('continuous_av', 'segmented_av')
TECH_CHECKS = ('full_decode', 'dimensions_fps', 'duration', 'audio_sync', 'srt', 'subtitle_safe', 'privacy', 'first_last_frame')


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def digest_json(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def split(value: str) -> list[str]:
    return [part.strip() for part in value.split('|') if part.strip()]


class Validator:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.read_paths: set[Path] = set()

    def need(self, condition: bool, message: str) -> bool:
        if not condition:
            self.errors.append(message)
        return bool(condition)

    def path(self, name: str) -> Path | None:
        if not isinstance(name, str) or not name.strip():
            self.errors.append('PATH: missing project-relative path')
            return None
        path = (self.root / name).resolve()
        if Path(name).is_absolute() or not path.is_relative_to(self.root):
            self.errors.append(f'PATH: outside project: {name}')
            return None
        if not path.is_file():
            self.errors.append(f'FILE: missing {name}')
            return None
        self.read_paths.add(path)
        return path

    def data(self, name: str) -> dict:
        path = self.path(name)
        if path is None:
            return {}
        try:
            data = json.loads(path.read_text(encoding='utf-8-sig'))
            if not isinstance(data, dict):
                raise ValueError('JSON root must be an object')
            return data
        except (ValueError, OSError) as error:
            self.errors.append(f'JSON: {name}: {error}')
            return {}

    def table(self, name: str, fields: tuple[str, ...], allow_empty: bool = False) -> list[dict]:
        path = self.path(name)
        if path is None:
            return []
        try:
            with path.open(encoding='utf-8-sig', newline='') as stream:
                reader = csv.DictReader(stream)
                if not self.need(set(fields).issubset(reader.fieldnames or []), f'CSV: {name}: required fields {fields}'):
                    return []
                rows = list(reader)
                if any(None in row or any(value is None for value in row.values()) for row in rows):
                    raise ValueError('malformed column count')
                self.need(bool(rows) or allow_empty, f'CSV: {name}: no rows')
                return rows
        except (OSError, ValueError, csv.Error) as error:
            self.errors.append(f'CSV: {name}: {error}')
            return []

    def number(self, row: dict, key: str, label: str) -> int:
        value = row.get(key)
        try:
            if isinstance(value, bool) or str(value).strip() != str(int(value)):
                raise ValueError('integer required')
            return int(value)
        except (TypeError, ValueError, OverflowError):
            self.errors.append(f'NUMBER: {label}.{key}: integer required')
            return 0

    def evidence(self, item, label: str) -> Path | None:
        if not isinstance(item, dict):
            self.errors.append(f'EVIDENCE: {label}: file reference required')
            return None
        path = self.path(item.get('path', ''))
        if path is not None:
            self.need(item.get('sha256') == sha256(path), f'STALE: {label}: file hash mismatch')
        return path

    def reference_list(self, value, label: str) -> None:
        if not self.need(isinstance(value, list) and bool(value), f'EVIDENCE: {label}: nonempty evidence list required'):
            return
        for index, ref in enumerate(value):
            self.evidence(ref, f'{label}[{index}]')

    def fingerprints(self, project: dict) -> dict:
        files = {}
        inputs = project.get('inputs', {})
        if not isinstance(inputs, dict):
            self.errors.append('INPUTS: object required')
            inputs = {}
        for key in ('script', 'audio', 'assets'):
            path = self.path(inputs.get(key, ''))
            files[key] = sha256(path) if path else None
        cue_path = self.path('CUE_TIMELINE.csv')
        files['cues'] = sha256(cue_path) if cue_path else None
        config = {key: project.get(key) for key in ('schema_version', 'project_id', 'duration_ms', 'fps', 'width', 'height', 'producer_id', 'anchor_tolerance_ms', 'max_full_screen_effect_uses')}
        inputs_hash = digest_json({'files': files, 'config': config})
        plan = {}
        for name in PLAN_FILES:
            # G0 can run before visual planning exists.
            if (self.root / name).is_file():
                path = self.path(name)
                plan[name] = sha256(path) if path else None
        return {'input_fingerprint': inputs_hash, 'plan_fingerprint': digest_json({'inputs': inputs_hash, 'files': plan})}

    def validate(self, gate: str) -> dict:
        project = self.data('project.json')
        gates = self.data('GATES.json')
        self.need(project.get('schema_version') == 1 and gates.get('schema_version') == 1, 'SCHEMA: expected version 1')
        self.need(bool(project.get('producer_id')), 'PRODUCER: producer_id required')
        duration = self.number(project, 'duration_ms', 'project')
        fps = self.number(project, 'fps', 'project')
        valid_format = self.need(0 < duration <= 604800000 and 0 < fps <= 240, 'FORMAT: duration must be within 7 days and fps within 1..240')
        for key in ('width', 'height'):
            self.need(self.number(project, key, 'project') > 0, f'FORMAT: positive {key} required')
        fingerprints = self.fingerprints(project)
        self.project = project
        self.duration, self.fps = (duration, fps) if valid_format else (0, 1)
        cue_rows = self.table('CUE_TIMELINE.csv', ('cue_id', 'start_ms', 'end_ms', 'spoken_text', 'anchor_ms'))
        cues = {}
        previous_end = 0
        for row in cue_rows:
            cue = row['cue_id']
            start, end, anchor = (self.number(row, key, cue) for key in ('start_ms', 'end_ms', 'anchor_ms'))
            self.need(bool(cue) and cue not in cues, f'CUE: duplicate or empty ID {cue}')
            self.need(previous_end <= start < end <= duration and start <= anchor <= end, f'CUE_TIME: {cue}')
            self.need(bool(row['spoken_text'].strip()), f'CUE_TEXT: {cue}')
            previous_end = end
            cues[cue] = dict(row, start=start, end=end, anchor=anchor)
        assets = {}
        inputs = project.get('inputs', {}) if isinstance(project.get('inputs'), dict) else {}
        for row in self.table(inputs.get('assets', ''), ('asset_id', 'path', 'sha256', 'source', 'meaning', 'allowed_sections', 'allowed_start_ms', 'allowed_end_ms', 'max_uses', 'sensitive_handling'), allow_empty=True):
            asset = row['asset_id']
            self.need(bool(asset) and asset not in assets, f'ASSET: duplicate or empty ID {asset}')
            self.evidence(row, f'asset {asset}')
            start, end, uses = (self.number(row, key, asset) for key in ('allowed_start_ms', 'allowed_end_ms', 'max_uses'))
            self.need(0 <= start < end <= duration and uses >= 0, f'ASSET_TIME: {asset}')
            self.need(all(row[key].strip() for key in ('source', 'meaning', 'allowed_sections', 'sensitive_handling')), f'ASSET_ROLE: {asset}')
            assets[asset] = dict(row, start=start, end=end, uses=uses)
        self.cues, self.assets = cues, assets
        self.shots = {}
        selected = STAGES[:STAGES.index(gate) + 1]
        for stage in selected:
            record = gates.get(stage, {})
            if not isinstance(record, dict):
                self.errors.append(f'GATE: {stage}: object required')
                continue
            self.need(record.get('status') == 'pass', f'GATE: {stage}: status is not pass')
            self.need(record.get('input_fingerprint') == fingerprints['input_fingerprint'], f'STALE: {stage}: inputs changed')
            self.reference_list(record.get('evidence'), stage)
            if stage in ('G0', 'G1'):
                decision = record.get('decision', {})
                if not isinstance(decision, dict):
                    decision = {}
                self.need(decision.get('mode') in ('user', 'prior_user', 'delegated'), f'APPROVAL: {stage}: user decision or delegation required')
                self.evidence(decision.get('record'), f'{stage} decision')
            if stage != 'G0':
                self.need(record.get('plan_fingerprint') == fingerprints['plan_fingerprint'], f'STALE: {stage}: visual plan changed')
            if stage == 'G0':
                capability = record.get('review_capability', {})
                if not isinstance(capability, dict):
                    capability = {}
                self.need(capability.get('status') == 'pass' and capability.get('mode') in AV_MODES, 'CAPABILITY: synchronized AV review not verified')
                self.need(self.number(capability, 'sample_ms', 'capability') >= min(10000, duration), 'CAPABILITY: sample too short')
                self.evidence(capability.get('evidence'), 'G0 review capability')
            elif stage == 'G1':
                self.plan()
                self.reference_list(record.get('previews'), 'G1 previews')
            elif stage == 'G2':
                self.review_record(record.get('code_review'), 'G2 code review', project.get('producer_id'))
                self.evidence(record.get('sample_review'), 'G2 sample review')
                self.reference_list(record.get('code_snapshot'), 'G2 code snapshot')
                runtime = self.evidence(record.get('runtime_manifest'), 'G2 runtime manifest')
                usage = self.evidence(record.get('asset_usage'), 'G2 asset usage')
                if runtime and usage:
                    self.runtime(str(runtime.relative_to(self.root)), str(usage.relative_to(self.root)))
            elif stage == 'G3':
                self.final(record)
        return {'status': 'pass' if not self.errors else 'fail', 'gate': gate, **fingerprints, 'errors': self.errors, 'warnings': self.warnings, 'scope': 'record, hash, timing and reference checks; actual media and AV semantics need separate evidence'}

    def review_record(self, record, label: str, producer: str) -> None:
        if not isinstance(record, dict):
            record = {}
        self.need(record.get('status') == 'pass', f'REVIEW: {label}: not pass')
        self.need(record.get('independent') is True and bool(record.get('reviewer_id')) and record.get('reviewer_id') != producer, f'INDEPENDENCE: {label}')
        self.evidence(record.get('evidence'), label)

    def plan(self) -> None:
        self.path('STYLE_LOCK.md')
        rows = self.table('SHOT_SCRIPT.csv', ('cue_id', 'shot_id', 'section', 'start_ms', 'end_ms', 'visual_subject', 'visual_event', 'event_ms', 'read_hold_ms', 'asset_ids', 'effect_id', 'timing_note'))
        seen = Counter(row['cue_id'] for row in rows)
        self.need(set(seen) == set(self.cues) and all(count == 1 for count in seen.values()), 'COVERAGE: every semantic cue needs exactly one animation row')
        tolerance = self.project.get('anchor_tolerance_ms', 150)
        if not isinstance(tolerance, int) or isinstance(tolerance, bool) or tolerance < 0:
            self.errors.append('TIMING: nonnegative anchor_tolerance_ms required')
            tolerance = 150
        for row in rows:
            cue = row['cue_id']
            if cue not in self.cues:
                continue
            expected = self.cues[cue]
            start, end, event, hold = (self.number(row, key, cue) for key in ('start_ms', 'end_ms', 'event_ms', 'read_hold_ms'))
            self.need(start == expected['start'] and end == expected['end'] and start <= event <= end and 0 <= hold <= end - start, f'SHOT_TIME: {cue}')
            self.need(abs(event - expected['anchor']) <= tolerance or bool(row['timing_note'].strip()), f'ANCHOR: {cue}: offset needs justification')
            self.need(all(row[key].strip() for key in ('shot_id', 'section', 'visual_subject', 'visual_event')), f'ANIMATION: {cue}: subject and event required')
            self.need(row['visual_event'].strip().lower() not in ('none', 'noop', 'static', '纯文字换页'), f'ANIMATION: {cue}: no explanatory event')
            for asset in split(row['asset_ids']):
                self.asset_use(asset, row['section'], start, end, cue, intersection=True)
            self.shots[cue] = row
        adaptation = self.table('MOTION_ADAPTATION.csv', ('section', 'cue_ids', 'huashu_grammar', 'recommended_card', 'alternative_card', 'reference_demo', 'reason'))
        adapted = Counter()
        for row in adaptation:
            self.need(bool(row['huashu_grammar'].strip()) and bool(row['reason'].strip()), f'ADAPTATION: {row["section"]}: grammar and reason required')
            if row['recommended_card'].strip().lower() not in ('', 'none'):
                self.need(bool(row['reference_demo'].strip()), f'DEMO: {row["section"]}: accurate reference required')
            for cue in split(row['cue_ids']):
                adapted[cue] += 1
                self.need(cue in self.shots and self.shots[cue]['section'] == row['section'], f'ADAPTATION_SECTION: {cue}')
        self.need(set(adapted) == set(self.cues) and all(count == 1 for count in adapted.values()), 'ADAPTATION_COVERAGE: whole film must be mapped once')
        budget = self.table('MOTION_BUDGET.csv', ('section', 'max_major', 'notes'))
        self.budgets = {row['section']: self.number(row, 'max_major', row['section']) for row in budget}
        self.need(len(self.budgets) == len(budget) and all(n >= 0 for n in self.budgets.values()), 'BUDGET: unique sections and nonnegative limits required')
        self.need({row['section'] for row in rows}.issubset(self.budgets), 'BUDGET: missing chapter limit')

    def asset_use(self, asset: str, section: str, start: int, end: int, cue: str, frames: bool = False, intersection: bool = False) -> None:
        allowed = self.assets.get(asset)
        if not self.need(allowed is not None, f'ASSET_UNKNOWN: {cue}: {asset}'):
            return
        self.need(section in split(allowed['allowed_sections']), f'ASSET_SECTION: {cue}: {asset}')
        lower, upper = allowed['start'], allowed['end']
        if frames:
            lower = lower * self.fps // 1000
            upper = (upper * self.fps + 999) // 1000
        permitted = start < upper and lower < end if intersection else lower <= start and end <= upper
        self.need(permitted, f'ASSET_RANGE: {cue}: {asset}')

    def runtime(self, name: str, usage_name: str) -> None:
        rows = self.table(name, ('cue_id', 'start_frame', 'end_frame', 'asset_ids', 'effect_id', 'major_motion', 'full_screen'))
        counts = Counter(row['cue_id'] for row in rows)
        self.need(set(counts) == set(self.cues) and all(n == 1 for n in counts.values()), 'RUNTIME_COVERAGE: missing or duplicate cue')
        intervals, major, fullscreen = defaultdict(list), Counter(), Counter()
        runtime_cues = {}
        total_frames = (self.duration * self.fps + 999) // 1000
        for row in rows:
            cue = row['cue_id']
            if cue not in self.shots:
                continue
            shot = self.shots[cue]
            start, end = (self.number(row, key, cue) for key in ('start_frame', 'end_frame'))
            self.need(0 <= start < end <= total_frames, f'RUNTIME_TIME: {cue}')
            self.need(abs(start * 1000 - shot_int(shot['start_ms']) * self.fps) <= 1000 and abs(end * 1000 - shot_int(shot['end_ms']) * self.fps) <= 1000, f'RUNTIME_ANCHOR: {cue}')
            actual = set(split(row['asset_ids']))
            self.need(actual == set(split(shot['asset_ids'])) and row['effect_id'] == shot['effect_id'], f'RUNTIME_PLAN: {cue}: actual assets or effect differ')
            runtime_cues[cue] = (start, end, actual)
            self.need(row['major_motion'] in ('0', '1') and row['full_screen'] in ('0', '1'), f'RUNTIME_FLAG: {cue}: use 0 or 1')
            if row['major_motion'] == '1':
                major[shot['section']] += 1
            if row['full_screen'] == '1':
                self.need(bool(row['effect_id'].strip()), f'RUNTIME_EFFECT: {cue}: full screen requires effect ID')
                fullscreen[row['effect_id']] += 1
        actual_usage = defaultdict(set)
        for row in self.table(usage_name, ('cue_id', 'asset_id', 'start_frame', 'end_frame'), allow_empty=True):
            cue, asset = row['cue_id'], row['asset_id']
            if not self.need(cue in runtime_cues, f'USAGE_CUE: {cue}: not in runtime'):
                continue
            start, end = (self.number(row, key, cue) for key in ('start_frame', 'end_frame'))
            cue_start, cue_end, _ = runtime_cues[cue]
            self.need(0 <= start < end <= total_frames and start < cue_end and cue_start < end, f'USAGE_TIME: {cue}: {asset}')
            self.asset_use(asset, self.shots[cue]['section'], start, end, cue, frames=True)
            # A continuous background can span several cues and silent gaps.
            for visible_cue, (visible_start, visible_end, _) in runtime_cues.items():
                if start < visible_end and visible_start < end:
                    actual_usage[visible_cue].add(asset)
                    self.asset_use(asset, self.shots[visible_cue]['section'], start, end, visible_cue, frames=True)
            intervals[asset].append((start, end))
        for cue, (_, _, assets) in runtime_cues.items():
            self.need(actual_usage[cue] == assets, f'USAGE_COVERAGE: {cue}: actual visibility windows differ from runtime assets')
        for asset, spans in intervals.items():
            merged = []
            for start, end in sorted(spans):
                if merged and start <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
                else:
                    merged.append((start, end))
            if asset in self.assets:
                self.need(len(merged) <= self.assets[asset]['uses'], f'ASSET_USES: {asset}: {len(merged)} continuous appearances')
        for section, count in major.items():
            self.need(count <= self.budgets.get(section, -1), f'MOTION_BUDGET: {section}')
        limit = self.project.get('max_full_screen_effect_uses', 2)
        self.need(isinstance(limit, int) and not isinstance(limit, bool) and limit >= 0, 'BUDGET: full-screen repetition limit must be a nonnegative integer')
        if isinstance(limit, int):
            for effect, count in fullscreen.items():
                self.need(count <= limit, f'FULLSCREEN_REPETITION: {effect}')

    def final(self, gate: dict) -> None:
        video = self.evidence(gate.get('video'), 'G3 video')
        video_hash = sha256(video) if video else None
        for kind in ('semantic', 'technical', 'motion'):
            item = gate.get(kind, {})
            if not isinstance(item, dict):
                item = {}
            self.need(item.get('video_sha256') == video_hash and bool(video_hash), f'STALE: G3 {kind}: wrong video')
            path = self.evidence(item.get('report'), f'G3 {kind}')
            report = self.data(str(path.relative_to(self.root))) if path else {}
            if kind == 'motion':
                light = report.get('gate_light')
                self.need(light in ('green', 'yellow') and report.get('verdict') != 'red', 'MOTION_RED: original gate report is red or missing')
                if light == 'yellow':
                    self.need(bool(item.get('yellow_notes')), 'MOTION_YELLOW: segment explanations required')
                    self.warnings.append('MOTION_YELLOW: see segment explanations')
            else:
                self.need(report.get('status') == 'pass' and report.get('video_sha256') == video_hash, f'REPORT: {kind}: not pass or stale')
                self.reference_list(report.get('raw_evidence'), f'{kind} raw evidence')
                if kind == 'technical':
                    checks = report.get('checks', {})
                    self.need(isinstance(checks, dict) and all(checks.get(key) == 'pass' for key in TECH_CHECKS), 'TECHNICAL: required media checks missing')
                else:
                    self.need(report.get('mode') in AV_MODES, 'SEMANTIC_MODE: frames or transcripts cannot pass AV review')
                    self.need(report.get('independent') is True and bool(report.get('reviewer_id')) and report.get('reviewer_id') != self.project.get('producer_id'), 'INDEPENDENCE: semantic reviewer')
                    coverage = report.get('coverage_ms', [])
                    spans = []
                    if isinstance(coverage, list):
                        for interval in coverage:
                            if not isinstance(interval, list) or len(interval) != 2 or any(type(x) is not int for x in interval):
                                self.errors.append('SEMANTIC_COVERAGE: invalid interval')
                                continue
                            start, end = interval
                            self.need(0 <= start < end <= self.duration, 'SEMANTIC_COVERAGE: out of bounds')
                            spans.append((start, end))
                    covered = 0
                    for start, end in sorted(spans):
                        self.need(start <= covered, f'SEMANTIC_COVERAGE: gap at {covered} ms')
                        covered = max(covered, end)
                    self.need(bool(spans) and covered == self.duration, 'SEMANTIC_COVERAGE: entire film needs AV review')
        self.need(gate.get('open_issues') == [], 'BLOCKERS: unresolved or unrecorded issues')


def shot_int(value) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--gate', choices=STAGES, default='G3')
    parser.add_argument('--fingerprint', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    validator = Validator(args.project)
    if args.fingerprint:
        result = validator.fingerprints(validator.data('project.json'))
        result['errors'] = validator.errors
    else:
        result = validator.validate(args.gate)
    if args.report:
        report_path = args.report.resolve()
        if report_path.suffix != '.json' or not report_path.is_relative_to(validator.root) or report_path in validator.read_paths:
            parser.error('--report must be an unread JSON file inside the project, such as qa/release-check.json')
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result.get('errors') else 0


if __name__ == '__main__':
    raise SystemExit(main())
