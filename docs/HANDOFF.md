# GEMMA4 Execution Handoff (Nov 12, 2026)

## Source of truth
https://github.com/paytongagne/GEMMA4

## What works
1. Research retrieval (`src/gemma4_agent/evidence_graph.py`) with local symbol/file graph hints.
2. Paired synthetic localization evaluation (`experiments/compare_retrieval.py`) and paper draft.
3. Standalone repair pipeline (`src/gemma4_agent/local_agent.py`) that accepts a compatible model endpoint, selects context, parses and safely applies a proposed patch to a scratch copy; focused tests run only by explicit opt-in.
4. Kaggle competition agent config (`submission/agent.yaml`) and prompt (`submission/prompts/system.md`), built using `tools/build_submission.py` into `artifacts/submission.zip`.
5. Offline Kaggle notebook (`notebooks/kaggle_submit.ipynb`) with embedded candidate config, no network dependency.

## Run checks
```
python -m unittest discover -s tests -v
python tools/build_submission.py
python experiments/pilot.py
python experiments/make_synthetic_suite.py
```

## Do not claim
The tests include a mock model and **do not prove real Gemma 4 repair success**. The generated ZIP is locally structurally validated but **not yet verified by the official Kaggle compiler/harness**. No Kaggle leaderboard submission has been made from this repository.

## Best next work
1. Use the official Kaggle starter environment and official sample submission to compile/validate the candidate agent ZIP.
2. Run public development tasks with Gemma 4. Record task IDs, inference config, success/failure traces and wall time.
3. Compare retrieval-first versus baseline prompts on the same tasks with equal tool-call/time budgets. Investigate costly exploration and unsuccessful patches.
4. Select measured model size and budget, freeze config, and submit through Kaggle before Dec 2, 2026.
5. Separately submit the Paper Track Kaggle Writeup before its November 12 deadline, if still possible.
