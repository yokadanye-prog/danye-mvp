# Timeline schema

## Top-level shape

Use an object with metadata and a `pages` array:

```json
{
  "audioDuration": 284.238333,
  "clock": "audio.currentTime",
  "contentDensity": "rich",
  "pages": []
}
```

## Page object

Every page contains:

```json
{
  "id": "edit-from-voice",
  "pageNumber": 25,
  "section": "剪辑与发布",
  "subsection": "口播驱动剪辑",
  "start": 0,
  "end": 18.633,
  "cueStart": 1,
  "cueEnd": 9,
  "narration": "本页覆盖的连续口播文本",
  "screen": "页面核心信息",
  "visual": "页面视觉关系说明",
  "transition": "cut",
  "priority": "normal",
  "beats": []
}
```

Required invariants:

- The top level is an object, not a bare pages array.
- `clock` equals `audio.currentTime`.
- `contentDensity` equals `rich`, `concise`, or `custom`.
- First page `start` equals 0.
- Each page `end` equals the next page `start`.
- Last page `end` equals the exact MP3 duration.
- Page ids and page numbers are unique.
- `cueStart` and `cueEnd` map to valid SRT cue ids.
- `[PPT重点]` pages use `priority: "high"`.
- Page copy follows the approved `contentDensity` or documented custom density rule.

## Beat object

Every beat contains:

```json
{
  "id": "edit-from-voice-b1",
  "start": 0,
  "end": 4.2,
  "cueStart": 1,
  "cueEnd": 2,
  "action": "reveal-title"
}
```

Required invariants:

- Beat ids are unique within the page.
- Every page contains at least one beat.
- The first beat starts at the page start.
- Adjacent beats have no gap or overlap.
- The final beat ends at the page end.
- Beat start and end remain inside the page range.
- Beat order follows narration order.
- Beat timing comes from SRT cue boundaries or deliberate coverage of the initial silent segment.
- Do not create an independent timer for animation orchestration.

## Runtime selection

Select the active page with the current audio time:

```ts
const page = pages.find(
  (item, index) =>
    currentTime >= item.start &&
    (currentTime < item.end || index === pages.length - 1),
)
```

Select the active beat from the active page using the same `currentTime`. CSS transition duration must finish before the current beat or page ends.

## Runtime review contract

Expose deterministic review hooks in the generated page:

```html
<audio data-ppt-clock></audio>
<main data-page-id="..." data-beat-id="..."></main>
```

In `?review=1` mode, show or expose current page id, beat id, cue id, `audio.currentTime`, duration, paused state, ended state, muted state, and volume. Cue id is timing metadata. Never expose cue text as a visible subtitle. Browser Review must verify that visible state changes when `audio.currentTime` changes, remains stable while paused, and keeps the audio muted at volume 0.

## SRT timing gaps

SRT can contain pauses. Timeline pages must still cover those ranges. Keep the previous semantic visual active through a pause unless the narration requires a deliberate clean hold. Do not fill gaps with visible subtitle text.
