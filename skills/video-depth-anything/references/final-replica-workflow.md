# Depth reference handoff

This skill produces relative grayscale depth. A separate generator handles finished images and videos. The parent workflow controls paid submissions, candidate counts and retries.

## Align the references

1. Measure the original duration, frame rate and hard cuts before extraction.
2. Keep source and depth clips on the same timeline. Cut the corresponding intervals together.
3. Label original video, depth video, character identity, wardrobe and scene references separately.
4. Check the selected generator and current MCP schema for file count, duration and resolution constraints.
5. Confirm the depth output with the user before handing it to a paid generator.

## Parent workflow contract

When video-replica-jiangling calls this skill, extract depth only. Do not generate multiple paid candidates or retry paid generation because of this handoff document. Preserve the parent task ID and wait for the user's decision when generation fails.

For the parent's Wan3 workflow, the original and depth reference clips have a combined limit of fifteen seconds under its current rules. A six-second source segment and its six-second depth counterpart fit within that reference budget. This is an example of planning, not a completed generation test.

## Inspect the actual output

Compare duration and frame rate, inspect silhouettes and near/far polarity, and look at hands, hair, transparent surfaces and occlusion boundaries. Report timing drift or depth artifacts before proceeding. Relative depth is a control reference; it does not guarantee identical geometry or final motion.
