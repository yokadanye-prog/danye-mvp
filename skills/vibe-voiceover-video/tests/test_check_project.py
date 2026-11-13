"""Synthetic record tests. Media bytes in this suite are intentionally not videos."""
from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/check_project.py'
SPEC = importlib.util.spec_from_file_location('check_project', SCRIPT)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class Fixture:
    def __init__(self, root: Path):
        self.root = root
        self.write('inputs/script.txt', '音频推进页面。暂停后画面停止。')
        self.write('inputs/voice.mp3', b'synthetic voice bytes, not playable')
        self.write('assets/page.png', b'synthetic image bytes, not playable')
        self.write('qa/notes.md', 'Synthetic AV and approval record, only for validator tests.')
        self.write('src/main.js', '/* synthetic implementation snapshot */')
        self.write('qa/preview.mp4', b'synthetic preview bytes, not playable')
        self.write('out/final.mp4', b'synthetic video bytes, not playable')
        self.write('STYLE_LOCK.md', 'One shared page diagram and synchronized object actions.')
        self.project = {'schema_version': 1, 'project_id': 'synthetic-test', 'producer_id': 'maker',
                        'duration_ms': 20000, 'fps': 30, 'width': 1920, 'height': 1080,
                        'anchor_tolerance_ms': 150, 'max_full_screen_effect_uses': 2,
                        'inputs': {'script': 'inputs/script.txt', 'audio': 'inputs/voice.mp3', 'assets': 'ASSET_ROLES.csv'}}
        self.write_json('project.json', self.project)
        self.cues = [{'cue_id': 'c1', 'start_ms': 0, 'end_ms': 10000, 'spoken_text': '音频推进页面', 'anchor_ms': 3000},
                     {'cue_id': 'c2', 'start_ms': 10000, 'end_ms': 20000, 'spoken_text': '暂停后页面停止', 'anchor_ms': 13000}]
        self.assets = [{'asset_id': 'page', 'path': 'assets/page.png', 'sha256': self.ref('assets/page.png')['sha256'],
                        'source': 'synthetic', 'meaning': 'page object', 'allowed_sections': 'intro',
                        'allowed_start_ms': 0, 'allowed_end_ms': 20000, 'max_uses': 1, 'sensitive_handling': 'no real private data'}]
        self.shots = [dict(cue_id=c['cue_id'], shot_id='shared-scene', section='intro', start_ms=c['start_ms'], end_ms=c['end_ms'],
                           visual_subject='playhead and page', visual_event='page advances' if i == 0 else 'playhead and page freeze',
                           event_ms=c['anchor_ms'], read_hold_ms=500, asset_ids='page', effect_id='object-change', timing_note='')
                      for i, c in enumerate(self.cues)]
        self.adaptation = [{'section': 'intro', 'cue_ids': 'c1|c2', 'huashu_grammar': 'causal diagram',
                            'recommended_card': 'none', 'alternative_card': 'none', 'reference_demo': '', 'reason': 'keep causal object continuity'}]
        self.budget = [{'section': 'intro', 'max_major': 2, 'notes': 'two object events, no full-screen repetition'}]
        self.runtime = [{'cue_id': 'c1', 'start_frame': 0, 'end_frame': 300, 'asset_ids': 'page', 'effect_id': 'object-change', 'major_motion': '0', 'full_screen': '0'},
                        {'cue_id': 'c2', 'start_frame': 300, 'end_frame': 600, 'asset_ids': 'page', 'effect_id': 'object-change', 'major_motion': '0', 'full_screen': '0'}]
        self.usage = [{'cue_id': 'c1', 'asset_id': 'page', 'start_frame': 0, 'end_frame': 300},
                      {'cue_id': 'c2', 'asset_id': 'page', 'start_frame': 300, 'end_frame': 600}]
        self.save_tables()
        video_hash = self.ref('out/final.mp4')['sha256']
        self.semantic = {'status': 'pass', 'video_sha256': video_hash, 'mode': 'segmented_av', 'independent': True,
                         'reviewer_id': 'reviewer', 'coverage_ms': [[0, 10000], [10000, 20000]], 'raw_evidence': [self.ref('qa/notes.md')]}
        self.technical = {'status': 'pass', 'video_sha256': video_hash, 'checks': {key: 'pass' for key in module.TECH_CHECKS}, 'raw_evidence': [self.ref('qa/notes.md')]}
        self.motion = {'gate_light': 'green', 'verdict': 'pass'}
        for kind in ('semantic', 'technical', 'motion'):
            self.write_json(f'qa/{kind}.json', getattr(self, kind))
        self.gates = {'schema_version': 1}
        for stage in module.STAGES:
            self.gates[stage] = {'status': 'pass', 'evidence': [self.ref('qa/notes.md')]}
        for stage in ('G0', 'G1'):
            self.gates[stage]['decision'] = {'mode': 'prior_user', 'record': self.ref('qa/notes.md')}
        self.gates['G0']['review_capability'] = {'status': 'pass', 'mode': 'segmented_av', 'sample_ms': 10000, 'evidence': self.ref('qa/notes.md')}
        self.gates['G1']['previews'] = [self.ref('qa/preview.mp4')]
        self.gates['G2'].update(code_review={'status': 'pass', 'independent': True, 'reviewer_id': 'code-reviewer', 'evidence': self.ref('qa/notes.md')},
                                sample_review=self.ref('qa/notes.md'), code_snapshot=[self.ref('src/main.js')], runtime_manifest=self.ref('RENDER_MANIFEST.csv'), asset_usage=self.ref('ASSET_USAGE.csv'))
        self.gates['G3'].update(video=self.ref('out/final.mp4'), open_issues=[])
        for kind in ('semantic', 'technical', 'motion'):
            self.gates['G3'][kind] = {'video_sha256': video_hash, 'report': self.ref(f'qa/{kind}.json')}
        self.resign()

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(value, bytes):
            path.write_bytes(value)
        else:
            path.write_text(value, encoding='utf-8')

    def write_json(self, name, value):
        self.write(name, json.dumps(value, ensure_ascii=False, indent=2))

    def ref(self, name):
        return {'path': name, 'sha256': module.sha256(self.root / name)}

    def table(self, name, rows, fields=None):
        with (self.root / name).open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields or list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def save_tables(self):
        for name, rows in [('CUE_TIMELINE.csv', self.cues), ('ASSET_ROLES.csv', self.assets), ('SHOT_SCRIPT.csv', self.shots),
                           ('MOTION_ADAPTATION.csv', self.adaptation), ('MOTION_BUDGET.csv', self.budget), ('RENDER_MANIFEST.csv', self.runtime), ('ASSET_USAGE.csv', self.usage)]:
            self.table(name, rows)

    def save_gates(self):
        self.write_json('GATES.json', self.gates)

    def resign(self):
        fingerprints = module.Validator(self.root).fingerprints(self.project)
        for stage in module.STAGES:
            self.gates[stage]['input_fingerprint'] = fingerprints['input_fingerprint']
            if stage != 'G0':
                self.gates[stage]['plan_fingerprint'] = fingerprints['plan_fingerprint']
        self.save_gates()

    def update_report(self, kind):
        self.write_json(f'qa/{kind}.json', getattr(self, kind))
        self.gates['G3'][kind]['report'] = self.ref(f'qa/{kind}.json')
        self.save_gates()

    def check(self, stage='G3'):
        self.save_gates()
        return module.Validator(self.root).validate(stage)


class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.f = Fixture(Path(self.temp.name))

    def fails(self, code, stage='G3'):
        result = self.f.check(stage)
        self.assertEqual(result['status'], 'fail')
        self.assertTrue(any(code in error for error in result['errors']), result)

    def test_valid_all_gates_and_continuous_asset_use(self):
        self.assertEqual(self.f.check()['errors'], [])

    def test_missing_choice_cannot_pass(self):
        self.f.gates['G1']['decision'] = {}
        self.fails('APPROVAL', 'G1')

    def test_explicit_delegation_is_accepted(self):
        for stage in ('G0', 'G1'):
            self.f.gates[stage]['decision']['mode'] = 'delegated'
        self.assertEqual(self.f.check()['errors'], [])

    def test_missing_sentence(self):
        self.f.table('SHOT_SCRIPT.csv', self.f.shots[:1])
        self.f.resign()
        self.fails('COVERAGE', 'G1')

    def test_text_page_is_not_an_animation(self):
        self.f.shots[0]['visual_event'] = '纯文字换页'
        self.f.table('SHOT_SCRIPT.csv', self.f.shots)
        self.f.resign()
        self.fails('ANIMATION', 'G1')

    def test_whole_film_adaptation_required(self):
        self.f.adaptation[0]['cue_ids'] = 'c1'
        self.f.table('MOTION_ADAPTATION.csv', self.f.adaptation)
        self.f.resign()
        self.fails('ADAPTATION_COVERAGE', 'G1')

    def test_wrong_asset_section(self):
        self.f.assets[0]['allowed_sections'] = 'other'
        self.f.table('ASSET_ROLES.csv', self.f.assets)
        self.f.resign()
        self.fails('ASSET_SECTION', 'G1')

    def test_replaced_audio_invalidates_old_gate(self):
        self.f.write('inputs/voice.mp3', b'replaced audio bytes')
        self.fails('STALE', 'G0')

    def test_changed_plan_invalidates_selection(self):
        self.f.write('STYLE_LOCK.md', 'different style')
        self.fails('STALE', 'G1')

    def test_changed_code_invalidates_code_review(self):
        self.f.write('src/main.js', 'changed code after review')
        self.fails('STALE', 'G2')

    def test_new_video_cannot_reuse_old_reports(self):
        self.f.write('out/final.mp4', b'new final candidate bytes')
        self.f.gates['G3']['video'] = self.f.ref('out/final.mp4')
        self.fails('wrong video')

    def test_original_red_cannot_be_overridden(self):
        self.f.motion.update(gate_light='red', verdict='red')
        self.f.gates['G3']['motion']['status'] = 'pass'
        self.f.update_report('motion')
        self.fails('MOTION_RED')

    def test_frames_only_cannot_claim_semantic_pass(self):
        self.f.semantic['mode'] = 'frames_only'
        self.f.update_report('semantic')
        self.fails('SEMANTIC_MODE')

    def test_gap_in_semantic_coverage(self):
        self.f.semantic['coverage_ms'] = [[0, 9000], [10000, 20000]]
        self.f.update_report('semantic')
        self.fails('SEMANTIC_COVERAGE')

    def test_self_review_cannot_be_independent(self):
        self.f.semantic['reviewer_id'] = 'maker'
        self.f.update_report('semantic')
        self.fails('INDEPENDENCE')

    def test_missing_actual_evidence(self):
        self.f.technical['raw_evidence'] = []
        self.f.update_report('technical')
        self.fails('EVIDENCE')

    def test_pending_media_check_cannot_pass(self):
        self.f.technical['checks']['full_decode'] = 'pending'
        self.f.update_report('technical')
        self.fails('TECHNICAL')

    def test_changed_evidence_is_stale(self):
        self.f.write('qa/notes.md', 'changed review evidence')
        self.fails('STALE')

    def test_runtime_cannot_hide_unapproved_asset(self):
        self.f.runtime[0]['asset_ids'] = 'other'
        self.f.table('RENDER_MANIFEST.csv', self.f.runtime)
        self.f.gates['G2']['runtime_manifest'] = self.f.ref('RENDER_MANIFEST.csv')
        self.fails('RUNTIME_PLAN', 'G2')

    def test_yellow_needs_notes(self):
        self.f.motion['gate_light'] = 'yellow'
        self.f.update_report('motion')
        self.fails('MOTION_YELLOW')
        self.f.gates['G3']['motion']['yellow_notes'] = ['opening: readable held state']
        self.assertEqual(self.f.check()['errors'], [])

    def test_unverified_review_capability(self):
        self.f.gates['G0']['review_capability']['mode'] = 'frames_only'
        self.fails('CAPABILITY', 'G0')

    def test_malformed_number_does_not_crash(self):
        self.f.shots[0]['event_ms'] = 'not-a-time'
        self.f.table('SHOT_SCRIPT.csv', self.f.shots)
        self.f.resign()
        self.fails('NUMBER', 'G1')

    def test_diagram_only_project_needs_no_external_asset(self):
        self.f.table('ASSET_ROLES.csv', [], list(self.f.assets[0]))
        for row in self.f.shots + self.f.runtime:
            row['asset_ids'] = ''
        self.f.table('SHOT_SCRIPT.csv', self.f.shots)
        self.f.table('RENDER_MANIFEST.csv', self.f.runtime)
        self.f.table('ASSET_USAGE.csv', [], list(self.f.usage[0]))
        self.f.gates['G2']['asset_usage'] = self.f.ref('ASSET_USAGE.csv')
        self.f.gates['G2']['runtime_manifest'] = self.f.ref('RENDER_MANIFEST.csv')
        self.f.resign()
        self.assertEqual(self.f.check()['errors'], [])

    def test_one_frame_disappearance_counts_as_second_use(self):
        self.f.usage[0]['end_frame'] = 299
        self.f.table('ASSET_USAGE.csv', self.f.usage)
        self.f.gates['G2']['asset_usage'] = self.f.ref('ASSET_USAGE.csv')
        self.fails('ASSET_USES', 'G2')

    def test_partial_sentence_visibility_is_allowed(self):
        self.f.assets[0].update(allowed_start_ms=4000, allowed_end_ms=6000)
        self.f.shots[1]['asset_ids'] = ''
        self.f.runtime[1]['asset_ids'] = ''
        self.f.usage = [{'cue_id': 'c1', 'asset_id': 'page', 'start_frame': 120, 'end_frame': 180}]
        self.f.save_tables()
        self.f.gates['G2']['runtime_manifest'] = self.f.ref('RENDER_MANIFEST.csv')
        self.f.gates['G2']['asset_usage'] = self.f.ref('ASSET_USAGE.csv')
        self.f.resign()
        self.assertEqual(self.f.check()['errors'], [])

    def test_huge_duration_returns_structured_failure(self):
        self.f.project['duration_ms'] = 10 ** 400
        self.f.write_json('project.json', self.f.project)
        self.f.resign()
        self.fails('FORMAT', 'G2')

    def test_missing_visibility_window_fails(self):
        self.f.table('ASSET_USAGE.csv', self.f.usage[:1])
        self.f.gates['G2']['asset_usage'] = self.f.ref('ASSET_USAGE.csv')
        self.fails('USAGE_COVERAGE', 'G2')

    def test_continuous_asset_can_span_silent_gap(self):
        self.f.cues[0]['end_ms'] = 5000
        self.f.shots[0]['end_ms'] = 5000
        self.f.runtime[0]['end_frame'] = 150
        self.f.usage = [{'cue_id': 'c1', 'asset_id': 'page', 'start_frame': 0, 'end_frame': 600}]
        self.f.save_tables()
        self.f.gates['G2']['runtime_manifest'] = self.f.ref('RENDER_MANIFEST.csv')
        self.f.gates['G2']['asset_usage'] = self.f.ref('ASSET_USAGE.csv')
        self.f.resign()
        self.assertEqual(self.f.check()['errors'], [])

    def test_cross_cue_window_cannot_hide_forbidden_section(self):
        self.f.shots[1]['section'] = 'body'
        self.f.adaptation = [dict(self.f.adaptation[0], cue_ids='c1'), dict(self.f.adaptation[0], section='body', cue_ids='c2')]
        self.f.budget.append(dict(self.f.budget[0], section='body'))
        self.f.usage = [{'cue_id': 'c1', 'asset_id': 'page', 'start_frame': 0, 'end_frame': 600}]
        self.f.save_tables()
        self.f.gates['G2']['runtime_manifest'] = self.f.ref('RENDER_MANIFEST.csv')
        self.f.gates['G2']['asset_usage'] = self.f.ref('ASSET_USAGE.csv')
        self.f.resign()
        self.fails('ASSET_SECTION', 'G2')

    def test_unsafe_report_destination_does_not_overwrite_inputs(self):
        self.f.save_gates()
        before = (self.f.root / 'GATES.json').read_bytes()
        process = subprocess.run([sys.executable, str(SCRIPT), '--project', str(self.f.root), '--report', str(self.f.root / 'GATES.json')], capture_output=True)
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(before, (self.f.root / 'GATES.json').read_bytes())


if __name__ == '__main__':
    unittest.main()
