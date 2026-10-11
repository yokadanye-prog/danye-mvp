---
name: mp3-timeline-web-ppt
description: Create a silent, recordable 1920x1080 dynamic PPT website whose pages, beats, and progress are driven by a complete muted MP3, with corrected SRT used only as a timing map. Use when source documents may need normalization, the cover must be derived from the full source, the user must choose among five visual directions and a text-density level, and playback correctness requires evidence-backed review. Do not use for visible captions, audible playback, TTS generation, or direct MP4 export.
---

# MP3 Timeline Web PPT

Create a silent, recordable dynamic PPT website. The complete MP3 is the only playback clock. Use SRT only to derive semantic timing boundaries. Treat every source input as read-only.

## Required companion skills

Before task actions, read these installed skills completely:

1. `C:\Users\ASUS\.codex\skills\web-video-presentation\SKILL.md`
2. `C:\Users\ASUS\.codex\skills\taste-skill\SKILL.md`

Use `web-video-presentation` only for the 16:9 presentation system, theme tokens, chapter craft, and visual recording patterns. Do not inherit its TTS, audible playback, audio toggle, caption, or subtitle behavior. This skill's silent output rules take precedence. Use `design-taste-frontend` for the Design Read, three design dials, layout variety, and anti-slop review.

## Non-negotiable invariants

- The full MP3 is hidden, permanently muted, set to volume 0, and the only playback clock.
- Derive page, beat, and progress state from `audio.currentTime`. Use SRT cue boundaries only to build and review the timeline.
- Never render SRT text in the webpage. Do not create caption or subtitle components, text tracks, subtitle overlays, caption query parameters, or caption controls.
- Never provide an unmute path. Do not add an `M` shortcut, sound button, volume control, audible mode, or code that can set `muted` to false or `volume` above 0.
- Do not use `setTimeout`, `setInterval`, wall-clock time, or another audio track to drive presentation timing.
- Do not synthesize TTS, modify source audio or captions, or export MP4.
- Keep MP3, SRT, narration, PDF, Word, images, and linked source documents read-only.
- Build a fixed 1920 x 1080 stage with Vite, React, and TypeScript.
- Inspect and normalize only the materials the user actually provides. Missing optional material does not block the project.
- Treat text-heavy screenshots as document pages by default. Read and extract their content before deciding how the content appears in the PPT.
- When a full SOP or article is provided, derive the cover from the complete document. Do not use a source-document screenshot as the finished cover unless the user explicitly asks for that treatment.
- Build and pass a simple end-to-end playable skeleton before investing in full visual polish.
- Functional correctness, content correctness, and readability take priority over decorative refinement.
- Keep every runtime and recording path silent so the source MP3 and SRT can be added separately in the editor.

## Workflow router

1. Before content work, read [references/INPUT-SPEC.md](references/INPUT-SPEC.md). Normalize and classify the materials that were provided.
2. Read [references/TASKBOOK.md](references/TASKBOOK.md) for the complete workflow, checkpoints, and deliverables.
3. During visual selection, read [references/THEME-SELECTION.md](references/THEME-SELECTION.md). Dynamically inspect installed theme JSON files.
4. Before creating `timeline.json`, read [references/TIMELINE-SCHEMA.md](references/TIMELINE-SCHEMA.md).
5. Before visual implementation and again before delivery, read and execute [references/REVIEW-CHECKLIST.md](references/REVIEW-CHECKLIST.md).

## Required plan checkpoint

Before full visual implementation, present one combined checkpoint containing:

- Cover copy derived from the complete available source
- PPT structure, core message per page, and estimated page count
- Placement and role of each provided image or asset
- Exactly five visual-direction previews using the same real content
- `DESIGN_VARIANCE`, `MOTION_INTENSITY`, and `VISUAL_DENSITY`
- A text-density choice: `rich`, `concise`, or a user-defined custom level
- Any blocker found in provided material

Ask the user to approve the cover, structure, visual direction, design dials, text density, and asset usage together. Do not require optional materials the user did not provide.

## Execution discipline

- At session start, read existing `PROGRESS.md` and `BLOCKED.md` if present.
- Update `PROGRESS.md` after every completed phase.
- Put uncertain provided inputs in `BLOCKED.md` and continue unaffected work.
- Treat user-specified page counts, source ranges, and asset placements as hard constraints.
- When no `[PPT重点]` markers exist, extract core conclusions, procedures, data, cases, risks, misconceptions, and actions from the available source.
- Use page-level semantic scenes and intra-page beats. Prefer a beat reveal when it preserves continuity better than a page switch.
- Run deterministic scripts when available.
- Record actual commands, results, failures, repairs, and reruns in `review-report.md`.
- A P0 or P1 Review failure blocks a completed delivery claim. After three full repair rounds for the same failure, record it in `BLOCKED.md` and report the project as blocked or incomplete.

## Bundled scripts

```powershell
node scripts\parse-srt.mjs <captions.srt> --audio-duration <seconds>
node scripts\list-themes.mjs C:\Users\ASUS\.codex\skills\web-video-presentation\themes
node scripts\validate-timeline.mjs <timeline.json> --duration <seconds> --srt <captions.srt>
node scripts\validate-silent-runtime.mjs <presentation-src>
```

Copy the scripts into the output project when repeatable local validation is useful. Create a project-specific browser playback test that follows the Review contract.

## Required delivery

Deliver `input-report.json`, `assets-manifest.json`, `source-map.md`, `cover-brief.md`, `timeline.json`, `outline.md`, `ppt-focus.md`, `visual-direction.md`, `review-report.md`, `review-results.json`, `PROGRESS.md`, `BLOCKED.md`, source code, review frames, a fixed recording URL, and a one-click Windows launcher. Omit source-derived files only when their corresponding optional input was not provided, and explain the omission.

Report actual evidence for duration, input validation, timeline validation, clock provenance, type checking, production build, HTTP checks, screenshot Review, controls, dedicated-browser autoplay, and full playback Review.
