# M0 calibration status

Checked 2026-09-27: `TYPESAFE_API_KEY` is absent from the process environment and local `.env`. No vendor call was made. Entry-prior and placement/environment calibration are **unmeasured**. This is neither a passing gate nor evidence that the model fails Greek.

The thresholds remain those in the plan: entry agreement at least 15/16 distinct Greek items with p(top)>0.7; placement condition A at least 18/20 pairs with at most one Greek/ASCII flip over three repeats. No licensed/grammaticality question is authorized. Source explanations must stay out of probe prompts. No live model runs in pytest.

The parser, corpus judgments, coverage rates and validation operate without this service. Later decision hooks may ship only in stub mode until their individual gates are measured and passed.
