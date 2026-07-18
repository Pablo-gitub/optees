# Claude Cowork Manufacturing Study - 2026-07-18

This exploratory run tested whether Claude Desktop Cowork in local mode could
use the Optees MCP server to read a synthetic company workbook, formulate
versioned problems, execute solver capabilities, and create management reports.

## Results

| Task | Capability sequence | Reviewed result |
| --- | --- | --- |
| Direct production plan | `milp.linear` | A = 24, B = 3, objective = EUR 1,125 |
| Forecast-driven plan | `ml.regression.linear` twice, then `milp.linear` | forecasts A = 18 and B = 13.8; production A = 18 and B = 6; objective = EUR 1,050 |

Both tasks matched the private reference workbook. The reports correctly
separated solver mathematical status from independent validation status and
documented assumptions and limitations. Manual review awarded all 100 rubric
points. The direct report has one minor editorial defect: its final validation
table leaves a mostly empty third page.

## Reproducibility Status

This is evidence of a successful exploratory integration test, not yet a
publishable benchmark comparison. The exact Claude model identifier, token
usage, tool transcript, controlled unaided condition, and repeated trials were
not recorded. Those omissions are retained explicitly rather than guessed.

See the [scenario](../../scenarios/manufacturing-planning-001/README.md),
[agent service configuration guide](../../../../docs/AGENTS_SERVICE_CONFIG.md), and
`manifest.json` for the recorded metadata and file hashes.
