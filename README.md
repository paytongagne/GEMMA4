# GEMMA4 | Evidence-Guided Coding Agent & Research Framework

An experimental **Gemma 4 developer agent** for repository-level Python software repair, with an auditable retrieval testbed and a self-contained **Kaggle competition config**. The goal is to test whether graph-aware context selection produces more correct source patches at a fixed time and context budget.

> **Evidence boundary:** All successful repair tests in this repository currently use a scripted **mock model** on trusted toy repositories. The Kaggle submission package has been generated locally, but has **not been accepted or scored by the official competition harness**. No original Gemma 4/SWE-bench pass rate is claimed.

## Architecture

```
Issue / repository
  |-- Research pipeline: AST index -> lexical/structural/file-graph/evidence-graph -> context pack
  |       -> local Gemma-compatible API adapter -> unified patch -> scratch workspace -> optional trusted test -> trace
  |
  +-- Kaggle pipeline: submission/agent.yaml -> official ADK compiler -> Gemma 4 + 9 harness tools
          -> code search, graph reasoning, minimal edits, targeted tests -> submit_patch
```

**The Kaggle agent is separate from the standalone Python repair loop.** Kaggle's official harness reads a declarative YAML archive, not the local `src/` package. The agent prompt uses the harness's native graph and file tools. The Python retrieval code supports independently reproducible analysis, but its code is not automatically loaded into the competition agent.

## Quick start (Python 3.11+)

```
python -m unittest discover -s tests -v
python experiments/pilot.py
python experiments/make_synthetic_suite.py
python experiments/compare_retrieval.py --help
python tools/build_submission.py
```

The builder produces:

- `artifacts/submission.zip`, with **agent.yaml at the ZIP root** (never `submission/agent.yaml`).
- `notebooks/kaggle_submit.ipynb`, a self-contained, internet-off Kaggle notebook that reconstructs the same configuration archive.

### Kaggle submission workflow

1. Open the **Developer Agent Competition** on Kaggle and accept its rules before the entry deadline.
2. Open `notebooks/kaggle_submit.ipynb` as a new **Kaggle notebook** with the official competition data attached.
3. Disable internet, run all cells, verify `/kaggle/working/submission.zip` exists and `agent.yaml` is at its root.
4. **Before final submission**, test the resulting zip using the official Kaggle **swegemma** / ADK compiler and one public task. Our static builder alone is not enough to guarantee harness acceptance.
5. Submit the generated archive according to the current Kaggle competition instructions and confirm the result/score.

**Chosen candidate:** `gemma-4-12b-it-qat-w4a16-ct`, single agent, no LoRA. This is an initial compute/quality tradeoff, not a measured optimum. The main track also permits other Gemma 4 variants; compare them on public tasks before selecting a final one.

### Optional standalone API repair CLI

This path is only for controlled development and works with any locally served **OpenAI-compatible** text-completions endpoint. Launch an appropriate local server separately, then:

```
PYTHONPATH=src python -m gemma4_agent.local_agent \
  --repo ./some-trusted-python-project \
  --issue "The parser crashes when its input is empty" \
  --endpoint http://127.0.0.1:8000/v1/chat/completions \
  --model gemma-4-12b-it-qat-w4a16-ct \
  --out repair_report.json
```

It generates a proposed unified patch and applies it only inside a **temporary copy**. It does **not** execute tests by default. For trusted development fixtures only, add `--allow-local-tests --test-command 'python -m unittest discover -s tests -q'` to execute a test runner; untrusted code requires an external sandbox. Results are recorded as JSON; the original repository is unchanged.

## Files

| Location | Purpose |
|---|---|
| `submission/` | Competition agent.yaml, system prompt, model sampling and time budget |
| `tools/build_submission.py` | Static preflight + reproducible ZIP / Kaggle notebook builder |
| `notebooks/kaggle_submit.ipynb` | Self-contained Kaggle internet-off archive generator |
| `src/gemma4_agent/evidence_graph.py` | Repository index, local AST and static call evidence |
| `src/gemma4_agent/local_agent.py` | Development-only model/patch/test orchestrator |
| `src/gemma4_agent/evaluation.py` | Paired, auditable read-only context-localization metrics |
| `experiments/` | Synthetic fixtures and retriever comparisons |
| `tests/` | Unit, artifact, and scripted-model integration tests |
| `paper/` | Research methodology and work-in-progress writeup |
| `docs/` | Release checklist, handoff, security limitations |

## Scientific integrity

Experiments to date use **synthetic localization cases**, not an independently held-out SWE-bench test set. A correct-file retrieval result is not a resolved bug. Real claims require actual Gemma 4 inference, a verifier, paired tasks, identical budgets, and independently reproducible logs. Do not use gold patches or hidden verifier information as prompt input.

See [release gates](docs/RELEASE_CHECKLIST.md), [handoff](docs/HANDOFF.md), and [security model](docs/SECURITY.md).

## Sources

- [Official Gemma 4 Developer Agent Competition](https://www.kaggle.com/competitions/gemma-4-developer-agent/overview)
- [Official Paper Track](https://www.kaggle.com/competitions/gemma-4-developer-agent-paper/overview/submission-requirements)
- [Existing research design](paper/RESEARCH_DESIGN.md)

## Official public-task evaluation (requires Kaggle environment)

This runs **only** where the competition's official `swegemma` CLI, permitted model checkpoint, task snapshots and Docker are present. It does not run in an ordinary CPU-only environment.

```
# First inspect the command without executing anything:
python tools/official_eval.py \
  --tasks /path/to/tasks.jsonl \
  --snapshots-dir /path/to/snapshots \
  --task-id YOUR_PUBLIC_DEV_TASK_ID

# After reviewing paths and selecting an allowed public development task:
python tools/official_eval.py \
  --tasks /path/to/tasks.jsonl \
  --snapshots-dir /path/to/snapshots \
  --task-id YOUR_PUBLIC_DEV_TASK_ID --execute

python tools/report_official_eval.py --results-dir runs/official
```

This wrapper never downloads private datasets, changes competition rules, or fabricates scores. Follow the official harness for exact model-server setup; retain its raw task logs and traces. The reporting tool labels incomplete task outcomes as **unknown**, not failed or passed.
