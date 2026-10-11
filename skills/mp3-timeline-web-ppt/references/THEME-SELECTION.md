# Theme and content-density selection

Use this reference before full visual implementation.

## Read themes dynamically

Inspect every `theme.json` under:

```text
C:\Users\ASUS\.codex\skills\web-video-presentation\themes
```

Match `nameZh`, `descriptionZh`, `mood`, `bestFor`, and `preview` against the complete available source, audience, and recording readability. Do not maintain a hardcoded theme list.

## Design Read

Before previews, state:

- Presentation type
- Audience
- Tone
- Preferred aesthetic family

Then set and explain:

- `DESIGN_VARIANCE`: 1 to 10
- `MOTION_INTENSITY`: 1 to 10
- `VISUAL_DENSITY`: 1 to 10

## Five-direction shortlist

Recommend exactly five visual directions unless the user explicitly requests another count. Each direction must include:

- Theme id and Chinese name
- Why it matches the content and audience
- Design signature
- Recording-readability strength
- Readability or repetition risk
- Best page relationships
- Author preview link when available

The five choices should be meaningfully distinct. Avoid five cosmetic variations of one layout.

## Same-content preview rule

Use the same real content, information quantity, semantic time point, and asset role in all five 1920 x 1080 previews. Each preview contains:

- Short title
- Concise explanation
- One process, comparison, or data relationship
- Completed beat state

Generate a final static state only. Do not wire the MP3 or build the full deck during selection.

## Text-density checkpoint

Ask the user to approve one:

- `rich`: conclusion plus explanatory details, process notes, data, or evidence on each applicable page
- `concise`: title, key phrase, and one visual relationship; narration carries most details
- `custom`: user-defined mixed rule

Do not silently infer this choice when the user is reviewing the combined checkpoint. If the user delegates the choice, recommend one based on viewing context and record the reason.

## Approval record

Write `visual-direction.md`:

```text
Approved theme id:
Theme name:
Light or dark:
DESIGN_VARIANCE:
MOTION_INTENSITY:
VISUAL_DENSITY:
Text density: rich | concise | custom
Custom density rule:
Preferred page relationships:
Provided asset usage:
Avoid list:
Approved preview:
Approval date:
```

Full visual implementation may start after this record is complete. Explicit choices in the user's request may populate the record directly.

## Theme and layout distinction

Theme tokens control color, typography, spacing character, rules, radii, number style, shadow, texture, and baseline mood. Layout remains content-driven. Keep one theme while choosing relationships from the narration and approved text density.
