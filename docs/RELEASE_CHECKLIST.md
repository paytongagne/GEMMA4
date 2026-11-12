# GEMMA4 Release Gates

## Completed locally (November 12, 2026)
- [x] Code retrieval: lexical, structural, file-graph, and symbol-evidence-graph options
- [x] Deterministic context packing and source-file evidence explanations
- [x] Synthetic paired localization experiment (clearly marked non-SWE benchmark)
- [x] Standalone model adapter for an OpenAI-compatible local Gemma serving endpoint
- [x] Patch extraction and source-path safety checks
- [x] Temporary workspace patch application using `git apply --check`
- [x] Focused test execution in opt-in **trusted-code-only** mode
- [x] Unmodified source workspace after repair experiment
- [x] Candidate competition `submission/agent.yaml` and prompt configuration
- [x] Build `submission.zip` with root `agent.yaml` and valid relative includes
- [x] Offline, standalone Kaggle notebook builder generated from the same config
- [x] Unit and mocked end-to-end tests pass locally

## Kaggle official acceptance gates (NOT yet satisfied)
- [ ] Confirm Kaggle account entered the Developer Agent competition before November 25
- [ ] Obtain official `HARNESS_README.md` and sample submission from Kaggle dataset; review versions
- [ ] Compile `submission.zip` using the **official** `adk-submission` validator
- [ ] Run a genuine Gemma 4 checkpoint and at least one official public development task
- [ ] Save a real task trace, result JSON, and verifier output
- [ ] Run comparative held-out tasks and compute actual repair resolution, not only localization
- [ ] Inspect failures and iterate on prompt, model size, and time budget
- [ ] Verify final notebook runs with Kaggle internet disabled and exact wheelhouse
- [ ] Submit artifact to Kaggle and confirm the resulting submission status/score
- [ ] Freeze evaluated commit + paper/agent artifact hashes

## Other release limitations
- Local test execution can run arbitrary code. Do not pass untrusted repositories to `--allow-local-tests`. Prefer the Kaggle harness or hardened container execution.
- Local HTTP model integration is implemented, but actual Gemma 4 inference has not been performed in this environment. No model weights/GPU were available here.
- The 12B model is a **config choice**, not a measured winner. Benchmark against E4B/31B before choosing a final submission.
- The research-paper track has a separate deadline and a separate Kaggle Writeup submission; placing a paper in GitHub is not equivalent to submitting it.
