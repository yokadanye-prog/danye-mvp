---
name: video-depth-anything
description: Convert an existing local video into a temporally stable grayscale depth-reference video with Video Depth Anything. Use for depth-map extraction, motion-reference preparation, and Seedance or Wan replica-video workflows; do not use it as a text-to-video generator.
---

# Video Depth Anything

Use Video Depth Anything to extract relative grayscale depth from an existing video. Verify the source and output time axes; frame-rate conversion and segment encoding need measurement.

## Installation and runtime

- Install this complete skill folder, including `scripts` and `references`.
- Follow [runtime installation](references/installation.md) to prepare the official project, compatible Python packages, FFmpeg and the Small checkpoint. Skill installation does not install model weights.
- Configure `VIDEO_DEPTH_ANYTHING_HOME` or pass `-ToolRoot`. Use `VIDEO_DEPTH_ANYTHING_PYTHON` or `-PythonPath` only when Python is outside the tool's `.venv`.
- Model used by the supplied wrapper: Video-Depth-Anything-Small (`vits`, relative depth).
- Wrapper: `scripts/infer-depth.ps1`, with Windows PowerShell as the tested entry point.

Start with streaming inference, `vits`, input size 280 and max resolution 512, then check quality and memory on the user's hardware. These settings do not guarantee compatibility with every GPU. Check code and checkpoint licenses separately against the official project; model files are not included in this skill.

## Workflow

1. Inspect the input with `ffprobe` and detect intentional hard cuts. For a clip with outfit changes or scene cuts, split at those exact times so streaming state does not bleed across cuts.
2. Run the wrapper from PowerShell. Pass comma-separated cut times when known:

   ```powershell
   # Run from this skill folder and replace these example paths.
   & '.\scripts\infer-depth.ps1' `
     -ToolRoot 'C:\Tools\Video-Depth-Anything' `
     -InputVideo 'C:\Videos\input.mp4' `
     -OutputDir 'C:\Videos\depth-output' `
     -CutTimes '2.233,4.100,6.067'
   ```

3. Verify the output duration, dimensions, frame rate, and visual polarity. The wrapper produces near=light and far=dark relative depth, without audio.
4. Treat the depth result as a control reference, not the finished replica. For Seedance 2.5 or Wan 3.0 handoff, read [references/final-replica-workflow.md](references/final-replica-workflow.md).

## Operational constraints

- Keep 30 fps for fast hands, drinking water, and short animal reactions. Use 15 fps only for a quick preview.
- Default to `InputSize 280` and `MaxRes 512`. The wrapper retries at 252 and 224 after a failed GPU run.
- Ignore the Windows `No module named 'triton'` optimization notice when inference continues; it is not a failure.
- Do not call the result metric depth. The installed checkpoint is the relative-depth Small model.
- Do not promise exact geometry for transparent water, fine fingers, hair, or reflective metal. Inspect these regions before using the depth video as control.
- Do not install Base or Large without checking VRAM, disk space, intended commercial use, and model licensing.
- Missing Python, runner, weights or FFmpeg must stop the workflow with the concrete missing item. Do not automatically install environments or download weights.
- This skill extracts depth only. Paid image/video generation, candidate counts and retry policies belong to the parent workflow and require the user's decision.
