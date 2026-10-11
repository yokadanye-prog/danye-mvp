# Input material specification

Use this reference before content extraction or visual planning.

## Core rule

Validate and normalize the materials the user actually provides. MP3 and corrected SRT are required for this skill. Every other material type is optional. Do not request optional material simply to complete a checklist.

## Supported material

| Material | Preferred format | Acceptance rule |
| --- | --- | --- |
| Complete audio | MP3 | One complete, playable, non-DRM file readable by `ffprobe` |
| Corrected timing transcript | UTF-8 SRT | Valid sequence and timestamps; final cue does not exceed the MP3; used for timeline construction only and never rendered as visible captions |
| SOP or article | Markdown, TXT, DOCX, searchable PDF | Complete text and heading order can be extracted |
| Scanned document | PDF, PNG, JPG | OCR first, then verify page order, missing text, and confidence |
| Document screenshots | PNG or JPG | Clear text, complete reading order, preferably at least 1600 px wide |
| Evidence or data images | PNG, JPG, WebP | Original readable image stored at a stable local path |
| Narration | Markdown, TXT, DOCX | Text can be mapped to SRT ranges |
| Visual references | PNG, JPG, URL screenshot | Mark as reference-only unless the user approves direct display |

## Stable-path rule

Chat caches, temporary folders, clipboard paths, and messaging-app temporary folders can expire. Copy provided files into `inputs/original/` before relying on them. Preserve original filenames where practical and record a hash.

## Image roles

Assign one role to every provided image:

- `document-page`: read or OCR; do not place directly in the PPT by default
- `evidence-image`: displayable proof such as income, growth, or analytics
- `visual-reference`: informs style only
- `display-asset`: approved for direct composition

When the role is ambiguous, infer from content and record the assumption. Ask one focused question only when the role would materially change the result.

## Normalization outputs

Use this layout when applicable:

```text
inputs/
|-- original/
|-- normalized/
|   |-- article.md
|   |-- script.md
|   `-- captions.srt
`-- assets/
    |-- evidence/
    |-- display/
    `-- references/
```

Create `input-report.json` with read status, conversion status, and anomalies. Create `assets-manifest.json` with role, stable path, source path, dimensions, and intended page usage.

## Material gate

The gate passes when:

- MP3 and SRT are readable and mutually valid
- Every provided file needed by the approved plan has a stable readable copy
- Text-heavy source images have readable extracted text
- Provided image roles are recorded
- Critical OCR uncertainty is resolved or blocked

Missing optional material that was never provided does not fail the gate. If an optional item is unreadable and unused, record it as a warning and continue.
