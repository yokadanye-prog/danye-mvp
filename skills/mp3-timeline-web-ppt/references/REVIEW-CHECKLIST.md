# Review checklist

Run the functional gate on the simple skeleton, then run the complete checklist again after visual implementation. Record commands, outputs, failures, repairs, and reruns in `review-report.md`. Store machine-readable assertions in `review-results.json`.

## Severity

- P0 blocks visual development or completed delivery: unreadable MP3 or SRT, invalid timeline, wrong clock source, audible runtime audio, an unmute path, visible SRT subtitles, playback failure, launcher failure, build failure, resource failure, or full playback failure.
- P1 blocks completed delivery: wrong cover source, narration mismatch, wrong asset, missing required content, black frame, serious overflow, unreadable contrast, or console error.
- P2 allows delivery when documented: decorative refinement, limited layout variety, or simpler motion that does not reduce comprehension.

Correctness and readability take priority over decoration.

## Provided-input review

- Every provided file used by the plan exists at a stable project path.
- Temporary and messaging-cache paths are not used as runtime dependencies.
- `input-report.json` records read and conversion status.
- `assets-manifest.json` records image roles and intended usage.
- Text-heavy screenshots are treated as `document-page` unless explicitly approved for display.
- OCR text order and critical claims are checked against the source image.
- Missing optional material that the user never supplied is not reported as a blocking gap.

## Cover and content review

- When a full SOP or article exists, `cover-brief.md` reflects the complete document.
- Cover title, subtitle, steps, data, and outcomes have source references.
- A source-document screenshot is absent from the final cover unless explicitly approved.
- Every marked focus segment has a page or high-priority beat.
- Page count and page messages match the approved plan.
- Visible copy follows the approved `rich`, `concise`, or custom density rule.
- Visible copy contains no invented facts or fake precision.
- Every evidence image appears only in its approved role and location.

## Timeline and clock provenance

- MP3 duration comes from `ffprobe`.
- SRT cues parse successfully.
- Final SRT cue does not exceed audio duration.
- Timeline covers 0 through the exact audio duration.
- No page gaps or overlaps exist.
- Beats remain inside their pages and follow narration order.
- Timeline metadata says `clock: "audio.currentTime"`.
- Runtime page, beat, and progress selection use `audio.currentTime` only. SRT cue ids are timing metadata only.
- Source scan finds no timing use of `setTimeout`, `setInterval`, `Date.now`, `performance.now`, or an independent audio track.
- Review mode exposes page, beat, cue id, time, duration, paused, ended, muted state, and volume without displaying cue text.
- Visible state advances with audio time and remains stable while paused.

## Functional skeleton gate

Pass these checks before full visual development:

- Type check passes.
- Production build passes.
- Server, MP3, and timeline return HTTP 200. Validate the SRT locally; do not expose it as a runtime caption resource.
- Timeline validation passes.
- Space plays and pauses.
- Left and right move between timeline beats or pages according to the approved interaction.
- `?at=` and `?review=1` behave correctly.
- Native muted autoplay is attempted in `?auto=1` mode.
- The audio element remains muted and at volume 0 before, during, and after playback.
- Source scan finds no `muted = false`, positive volume assignment, `M` audio shortcut, sound button, volume control, or audible mode.
- The rendered page contains no subtitle or caption component, no text track, no visible SRT cue text, and no caption query parameter or control.
- A visible manual start control appears if autoplay is blocked.
- A dedicated Microsoft Edge run uses the same executable, isolated profile, URL, and autoplay arguments as the one-click launcher.
- After waiting at least one second in that Edge run, `currentTime` is greater than zero and `paused` is false.
- Accelerated full playback reaches `ended`, exact duration, last page, and last beat.
- No console errors occur.

Do not begin full visual implementation until all P0 checks pass.

## Screenshot Review

At 1920 x 1080 capture every page at:

1. Page start
2. Page midpoint
3. Immediately before page end

Check:

- Text overflow
- Empty or black scene
- Image stretching or unintended cropping
- Incomplete animation
- Residual elements from another page
- Text contrast and readability
- Stable safe margins
- Meaningful visual relationship
- Approved text density
- Correct asset role

Create start, middle, and end contact sheets when practical. Inspect dense pages at full resolution.

## Final playback Review

After visual implementation, rerun the entire functional suite and add:

- Normal-speed playback sample at the start
- Normal-speed samples across selected page and beat boundaries
- Normal-speed final segment
- Accelerated complete playback
- Final launcher test from a clean invocation
- Final console-error capture

The launcher must open the intended project and port. For reliable muted autoplay on Windows, prefer a dedicated Edge profile plus `--autoplay-policy=no-user-gesture-required`. Keep a manual start fallback because browser policy can still vary.

## Visual-selection compliance

- `visual-direction.md` records approval of one of five directions.
- Design dials and text density are recorded.
- One theme, accent, and shape system remain consistent.
- Page relationships vary with content.
- Consecutive pages avoid the same generic card grid.
- Motion communicates hierarchy, storytelling, feedback, or state change.

## Repair and release rule

Fix each failure and rerun the full affected suite. When a visual change could affect runtime, rerun the complete functional suite. Stop after three complete repair rounds for the same unresolved issue, record evidence in `BLOCKED.md`, and report the project as blocked or incomplete.

A completed delivery claim requires:

- No open P0 or P1 issue
- Functional skeleton gate passed before full visual work
- Final full regression passed
- Actual command output recorded
- `BLOCKED.md` contains `无`
