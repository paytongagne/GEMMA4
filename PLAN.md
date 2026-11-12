# GEMMA4 — Execution Plan
**Repository:** https://github.com/paytongagne/GEMMA4  
**Status:** Planning. No implementation or results are claimed until verified.  
**Research working title:** Graph-Guided Context Selection for Efficient Repository-Level Code Repair with Gemma 4

## A. Submission gates (verify in Kaggle account)

- **Paper Track:** November 12, 2026 at **23:59 UTC** (17:59 CST). The Kaggle **Writeup** is the required paper submission, maximum **3,000 words**. Include title/subtitle, abstract, introduction, methods/experiments, and related work/citations. Explicitly submit; a GitHub repo alone does not submit the paper. A public Kaggle notebook or a public paper PDF can be attached if useful.  
  Source: https://www.kaggle.com/competitions/gemma-4-developer-agent-paper/overview/submission-requirements
- **Developer Agent Track:** Rules/entry acceptance by **November 25, 2026**, final submission **December 2, 2026** (23:59 UTC). Evaluate using the official harness and packaging constraints.  
  Source: https://www.kaggle.com/competitions/gemma-4-developer-agent/overview
- **Decision gate:** If the paper lacks original completed experiments, do **not** present a speculative or fabricated result as a completed study. A transparent pilot or a clearly labeled null result is acceptable scientifically, subject to competition rules.

## B. User-supplied Kaggle starter notebook

Reference: https://www.kaggle.com/kernels/fork-version/368805207  
Displayed title: “Gemma 4 Developer Agent Paper Starter Notebook”, v12; linked data: “Gemma 4 SWE-bench Telemetry & Verifier Audit”.

**Status of source inspection:** Notebook listing and data title are user supplied. Executable cells have **not** been inspected or independently executed. Do not attribute any unverified numerical result to it.

### Audit before reuse
1. Fork the notebook in your Kaggle account or export its `.ipynb` and commit a *reviewed* copy under `notebooks/reference/` if license permits; preserve author attribution.
2. Inventory imports, inputs, dataset schemas, columns, sample counts, compute requirements, outputs, and version/seed.
3. Run unchanged once and save stdout, environment, and resulting artifact manifest.
4. Identify whether the telemetry is **model-run traces**, **verifier outputs**, or **reference-derived labels**. Prevent gold patch or hidden verifier leakage into prompts.
5. Separate its descriptive analytics from **our** original experimental question; cite previous work and do not rebrand reused plots/results.
6. Use only components that are reproducible and allowed by competition rules.

## C. Core research question and experimental design

**Question:** With fixed Gemma 4 model, task list, input/output budgets, and retry policy, does code-structure or dependency-graph retrieval improve repository-level Python repair success relative to simple lexical retrieval?

**Conditions:**
- A: lexical search (e.g. BM25/keyword + identical budget)
- B: AST symbol/import search (structural)
- C: AST + dependency-neighbor expansion (graph aware)

**Primary outcome:** fraction of tasks resolved according to the official verifier.

**Secondary outcomes:** correct-file top-k recall; patch apply rate; test pass rate; tokens spent; input context tokens; wall time; wrong-file edits; no-op/timeout; patch size.

**Fairness:**
- Use identical issue descriptions, model checkpoint, prompt template except retrieval context, decoding settings, allowed tools, search budget, and maximum attempts.
- Freeze selected evaluation tasks before reviewing results. Keep development/pilot tasks separate.
- Do not use reference patches or verifier tests as model input. Use reference patches **only** for offline localization metrics if permissible.
- Track task-level paired outcomes for A/B/C; report confidence intervals, sample size, failures, and ambiguous cases. Explicitly distinguish localization from actual repair.
- If model execution is infeasible by paper deadline, focus a defensible experiment on **retrieval localization** and label agent repair evaluation as future work.

## D. Architecture

```
issue + repository snapshot
  -> repository indexer (Python AST, file inventory, imports, symbols)
  -> retriever A/B/C (equal context-token budget)
  -> prompt builder (source spans + paths + constraints)
  -> Gemma 4 model adapter (one allowed model, fixed inference parameters)
  -> patch parser + safe patch applicator
  -> isolated verification runner (timeouts, clean reset, tests)
  -> structured run log + experiment analysis
```

**Safety:** Treat repository content, issue descriptions, and model outputs as untrusted. Sandbox any execution, disallow network unless explicitly necessary, apply limits, use temporary worktrees, avoid running tests in the host workspace, and do not store secrets.

## E. Recommended repository structure

```text
GEMMA4/
  README.md
  PLAN.md
  pyproject.toml
  .gitignore
  configs/{paper_pilot,dev_eval,final_eval}.yaml
  src/gemma4_agent/
    __init__.py
    cli.py
    config.py
    indexer.py
    retrieval/{lexical,structural,graph}.py
    model.py
    patching.py
    verifier.py
    logging.py
  experiments/
    task_manifest.jsonl
    compare_retrievers.py
    summarize.py
  tests/
    test_indexer.py
    test_retrieval.py
    test_patching.py
    test_verifier.py
  notebooks/
    reference/README.md
    analysis.ipynb
  results/
    README.md
  paper/
    outline.md
    bibliography.md
    figures/
  submission/
    checklist.md
```

Never commit private Kaggle datasets, model weights without permission, credentials, or huge run artifacts.

## F. Milestones and acceptance criteria

### M0 — Scope and submission compliance
- [ ] Join both competition tracks if participating in both; review current rules.
- [ ] Confirm model eligibility, notebook dataset permissions, exact UTC deadline.
- [ ] Establish paper question, hypotheses, primary metric, and 3 conditions.
- **Exit:** research specification and submission checklist are checked in.

### M1 — Baseline repository
- [ ] Python package, pinned dependencies, README, CI and local test command.
- [ ] Dataset loader validates schema and missing/invalid tasks.
- [ ] CLI `index`, `retrieve`, `evaluate`, `report` skeleton.
- **Exit:** reproducible setup works from clean clone; unit tests pass.

### M2 — AST + graph extraction
- [ ] Parse Python AST; index file path, classes, functions, imports, call references when resolvable.
- [ ] Use conservative fallbacks on syntax errors, dynamic imports and unresolved calls.
- [ ] Graph edges record provenance and confidence.
- **Exit:** synthetic fixtures and real-repository smoke tests pass; no exceptions on supported cases.

### M3 — Retrieval baselines
- [ ] A lexical retriever.
- [ ] B AST-aware retriever.
- [ ] C one-hop graph-aware expansion, with fixed token budget and deterministic ranking.
- [ ] Log chosen source spans and retrieval timing.
- **Exit:** all methods return comparable context packs; no oracle patch leakage.

### M4 — Model / patch / execution loop
- [ ] Fixed Gemma 4 checkpoint and decoding config.
- [ ] Structured patch generation with validation of paths, allowed edits and diff.
- [ ] Isolated worktree per task, test invocation and timeout handling.
- [ ] Trace every tool action, tokens, elapsed time, exit code and failure reason.
- **Exit:** one end-to-end known toy issue repaired and verified without manual intervention.

### M5 — Evaluation
- [ ] Preselect development and held-out task IDs.
- [ ] Complete pilot on a small subset; fix harness bugs on dev set only.
- [ ] Run three retrieval conditions on same held-out set.
- [ ] Report paired comparisons and limitations; rerun seeds if resources permit.
- **Exit:** raw logs, aggregate CSV, analysis script and figures reproduce same conclusions.

### M6 — Paper
Structure: Title/subtitle, abstract, introduction, prior work, hypothesis, dataset and methods, controls, results, error analysis, limitations/ethics, conclusion, citations. **<=3,000 words**.
- [ ] Every result in prose traces to a run log or reproducible table.
- [ ] Properly cite original notebook and prior research, if used.
- [ ] State resource constraints, unsuccessful cases and no-leakage safeguards.
- **Exit:** reviewed research report plus public project link, submitted in Kaggle.

### M7 — Coding competition extension
- [ ] Integrate official harness and ensure allowed models, tools, archive layout and limits.
- [ ] Optimize task budget, early exits, graph retrieval fallback, patch validation and safe retries.
- [ ] Test Kaggle internet-off runtime and final zip size under official constraints.
- [ ] Accept entry rules by November 25; upload valid final zip by December 2.
- **Exit:** acceptance / scoring status confirmed, artifact hashed and tagged.

## G. Paper Track triage for November 12

Priority 1: Inspect the notebook/dataset (not enough to rely on a description).  
Priority 2: Run a **narrow original retrieval benchmark**, e.g. lexical vs AST vs graph on a preselected task subset.  
Priority 3: Re-run analysis from a fresh kernel; generate a small results table and error cases.  
Priority 4: Write the Kaggle paper, citing everything and stating limits.  
Priority 5: Ensure the actual Kaggle Writeup is submitted before 23:59 UTC.

**Scope guard:** Training a new model, serving a large 31B model, implementing an entire production-grade agent and a full SWE-bench evaluation are deferred until after the paper deadline. Do not claim them complete.

## H. Execution conventions

- One change per milestone / meaningful commit.
- `main` protected logically by small PRs where feasible.
- All tests must run offline or with mocked inference.
- Keep machine-readable experiment provenance: `run_id`, Git SHA, model ID, dataset version, condition, seed, token/time budgets, task id, context selected, patch hash, verifier outcome.
- Create tagged reproducible states: `paper-submission-2026-11-12`, `agent-final-2026-12-02`.
- Do not overclaim outcomes in résumé until the work is actually implemented and measured.

## I. First next actions

1. Export/share the starter `.ipynb` or the public notebook's exact `/code/<author>/<slug>` URL so its source cells can be audited.
2. Verify the user's Kaggle competition participation and data access.
3. Build a small, independently testable `indexer.py` and lexical retrieval baseline; compare against an AST variant.
4. Keep experimental output under `results/` with a manifest and derive the writeup only from observed results.
