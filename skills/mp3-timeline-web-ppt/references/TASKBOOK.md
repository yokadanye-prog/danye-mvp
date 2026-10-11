# MP3 时间轴动态 PPT 完整任务链

## Outcome

Convert a complete MP3 and corrected SRT into a silent 1920 x 1080 dynamic PPT website. Use any additional material the user provides, without requiring a complete asset package. The browser uses the muted MP3 as the only clock and selects pages and beats through `audio.currentTime`.

## Input policy

Required for this skill:

- Complete MP3
- Corrected SRT

Optional:

- Narration or full script
- SOP, article, PDF, Word, Markdown, text, or document screenshots
- Evidence images, data screenshots, brand assets, or visual references
- `[PPT重点]` markers
- A fixed page plan or selected source range

Inspect only material that was provided. Do not request optional assets merely to satisfy a template. If a requested page explicitly depends on a missing asset, block that page and continue unaffected work.

## Phase 0: Resume and inspect

1. Read `PROGRESS.md` and `BLOCKED.md` when they exist.
2. Read the companion skills and the references required for the current phase.
3. Record the current goal, completed phases, next gate, and largest risk in `PROGRESS.md`.

## Phase 1: Stabilize and classify provided material

Read `INPUT-SPEC.md`.

1. Verify every provided path exists and is readable.
2. Copy files from temporary, chat-cache, or expiring locations into `inputs/original/` without modifying the originals.
3. Record original path, stable path, type, size, hash, role, and read status.
4. Classify images as `document-page`, `evidence-image`, `visual-reference`, or `display-asset`.
5. Record missing or unreadable provided files in `BLOCKED.md`.

Outputs:

- `input-report.json`
- `assets-manifest.json`
- `PROGRESS.md`
- `BLOCKED.md`

## Phase 2: Normalize readable source material

Normalize only formats that were provided:

- Markdown and text to UTF-8 text
- DOCX and searchable PDF to structured Markdown
- Scanned PDF and document screenshots through OCR, followed by order and completeness checks
- SRT to an unchanged UTF-8 working copy

Preserve page references so claims can be traced to the source. Low-confidence OCR must be flagged. The generation workflow can continue when the affected material is optional and unused.

Suggested outputs when applicable:

```text
inputs/normalized/article.md
inputs/normalized/script.md
inputs/normalized/captions.srt
```

## Phase 3: Read the complete available source

When an SOP or article is provided, read it from beginning to end before planning the cover or pages. Build `source-map.md` containing:

- Core topic and audience
- User problem and promised outcome
- Procedure and step count
- Conclusions and action points
- Data, cases, evidence, and risks
- Misconceptions and constraints
- Mapping between source sections, narration, and SRT ranges

When no full source is provided, derive the map from the script and SRT and state that limitation.

## Phase 4: Create the cover brief and presentation plan

Create `cover-brief.md` with:

```text
Main title:
Subtitle:
Audience:
Core outcome:
Procedure or step count:
Strongest supported evidence:
Allowed cover assets:
Excluded cover assets:
Source references:
```

Cover rules:

- Derive the message from the complete available source.
- Keep every factual claim traceable.
- Use a document screenshot as reading input by default.
- Place a document screenshot on the final cover only when the user explicitly approves that treatment.
- Evidence images may appear as supporting proof when their role is approved.

Extract the presentation content by prioritizing focus markers, conclusions, procedures, data, cases, risks, misconceptions, summaries, and actions. Avoid filler and repeated transitions.

Suggested page count:

```text
round(audio duration in seconds / 25)
```

Semantic structure may adjust the result by two pages. A user-specified count overrides the formula.

Outputs:

- `cover-brief.md`
- `outline.md`
- `ppt-focus.md`

## Phase 5: Combined user checkpoint

Present all decisions in one review package:

1. Cover title and subtitle
2. PPT page structure
3. Core message for every page
4. Estimated page count
5. Placement and purpose of each provided evidence or display image
6. Exactly five same-content visual-direction previews
7. Design dials and avoid-list
8. Text-density choice
9. Blockers found in provided material

Text-density options:

- `rich`: Each page carries a conclusion plus explanation, procedure detail, data, or evidence. The PPT remains understandable when reviewed without audio.
- `concise`: Each page carries a title, key phrase, and one clear visual relationship. The narration carries most detail.
- `custom`: The user specifies a mixed rule, such as rich process pages and concise transition pages.

Do not turn unprovided optional material into a blocker or a material-gap request. Ask the user to approve the cover, structure, visual direction, design dials, text density, and planned use of provided assets.

Outputs:

- `theme-shortlist.md`
- `visual-direction.md`
- Five candidate preview frames

## Phase 6: Audio and SRT timing preflight

1. Use `ffprobe` to obtain the exact MP3 duration.
2. Parse SRT cue id, start, end, and text.
3. Check ordering, overlaps, invalid timestamps, and final cue end.
4. Compare sampled SRT cue text with the script when available.
5. Record duration, cue count, and anomalies in `input-report.json`.

Resolve critical audio or SRT errors before timeline creation.

## Phase 7: Build and validate the two-layer timeline

Read `TIMELINE-SCHEMA.md`.

- Page changes follow complete semantic topics.
- A typical page lasts 18 to 32 seconds.
- Beats normally cover two to five consecutive SRT cues.
- Every page and beat is selected from `audio.currentTime`.
- Timeline content follows the approved text-density level.

Generate and validate `timeline.json` before website implementation.

## Phase 8: Build a simple playable skeleton

Build the full functional spine with intentionally simple visuals:

1. Fixed 1920 x 1080 stage
2. Hidden, permanently muted full MP3 at volume 0
3. Page, beat, and progress derived from `audio.currentTime`; SRT cue ids remain timing metadata only
4. All approved pages and beats represented
5. Space, left, right, `?auto=1`, `?at=`, and `?review=1`
6. Native autoplay attempt plus a visible manual start fallback
7. One-click Windows launcher that opens a dedicated Edge profile for reliable muted autoplay

Do not begin full visual refinement before the functional gate passes.

## Phase 9: Functional Review gate

Read `REVIEW-CHECKLIST.md` and run the P0 functional checks against the simple skeleton:

- Input and resource checks
- Timeline validation
- Clock provenance scan
- Type check and production build
- HTTP checks
- Manual controls
- Dedicated Edge autoplay
- Deep-link state checks
- Accelerated complete playback to exact duration
- Final page and final beat
- Console errors

Repair failures and rerun the affected complete suite. Save actual evidence.

## Phase 10: Full visual implementation

After the functional gate passes:

1. Apply the approved theme, design dials, text density, and asset roles.
2. Build the approved cover from `cover-brief.md`.
3. Use at least four content relationships across a longer deck: conclusion, process, comparison, data, case, checklist, or action.
4. Avoid repeated generic card grids.
5. Use motion for hierarchy, storytelling, feedback, or state change.
6. Keep visible page copy and recording-safe margins readable.

Decorative polish may be reduced to protect correctness and readability.

## Phase 11: Content and visual Review

Capture every page at its start, midpoint, and immediately before its end. Check full-resolution dense pages and create contact sheets when practical.

Verify cover-source accuracy, page-to-narration alignment, approved text density, asset-role correctness, factual support, overflow, collisions, black frames, stretching, unfinished motion, residual elements, contrast, and safe margins.

## Phase 12: Final full regression

Run the complete functional suite again against the final visual build. Include a normal-speed sample at the start, selected transitions, and the ending, plus accelerated full playback.

The final launcher must be tested with the same browser executable, profile isolation, URL, and autoplay arguments that the user will run.

## Phase 13: Evidence-backed delivery

Required project files:

```text
project/
|-- inputs/
|-- input-report.json
|-- assets-manifest.json
|-- source-map.md
|-- cover-brief.md
|-- article.md
|-- script.md
|-- outline.md
|-- ppt-focus.md
|-- theme-shortlist.md
|-- visual-direction.md
|-- timeline.json
|-- PROGRESS.md
|-- BLOCKED.md
|-- review-report.md
|-- review-results.json
|-- theme-preview/
|-- presentation/
|   |-- public/audio/
|   |-- public/data/timeline.json
|   |-- src/
|   |-- scripts/
|   `-- review-frames/
`-- 启动录制网页.cmd
```

Omit optional source-derived files only when that source type was not provided, and explain the omission.

## Completion conditions

- Provided materials are readable, stable, and classified.
- The user approved cover, structure, one of five visual directions, design dials, text density, and use of provided assets.
- Timeline covers 0 through the exact audio duration without gaps.
- All pages and beats are driven by muted MP3 `audio.currentTime`.
- The runtime contains no visible subtitle or caption rendering, no text track, and no caption control.
- The runtime contains no unmute path, sound control, volume control, or audible mode. The clock audio remains muted at volume 0.
- Every marked focus segment is represented.
- The functional skeleton passed before full visual implementation.
- The final visual build passed the complete regression.
- No P0 or P1 issue remains open.
- `review-report.md` contains actual commands and results.
- `BLOCKED.md` contains `无` when there are no blockers.
