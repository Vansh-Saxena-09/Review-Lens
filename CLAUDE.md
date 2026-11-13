# Project guidance

- Preserve real functionality and use real trained model predictions only.
- Never fabricate evaluation metrics, analytics, extraction results, or model capabilities.
- Describe classifications as estimates: the source labels computer-generated vs original text, not verified fraud.
- Keep `PROJECT_STATUS.md` and `HANDOFF.md` current with actual verification and blockers.
- Keep model training and inference preprocessing consistent; prevent test-data leakage.
- Do not overwrite user data or committed artifacts without inspecting them.
