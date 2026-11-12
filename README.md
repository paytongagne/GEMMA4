# GEMMA4: Repository-Aware Code Retrieval Research

Research prototype for comparing lexical, AST-based and import-graph-assisted source retrieval as possible context selection methods for Gemma 4 coding agents.

**Current status:** Retrieval prototype only. No Gemma 4 inference, patch generation, SWE-bench scoring, or original real-world performance results have been implemented or established.

## What is implemented

- Read-only Python repository indexing using the standard-library AST parser.
- Lexical retrieval and structural symbol weighting.
- Graph method using **one-hop local import adjacency**, not a full function call graph.
- Deterministic source excerpt selection with a **character budget** (a proxy, not a tokenizer-measured token budget).
- Unit tests and a small **synthetic smoke test** to verify the software works.

## Run locally

Requires Python 3.10+; no external Python dependencies for the prototype.

```bash
python -m unittest discover -s tests -v
python experiments/pilot.py
```

## Experimental integrity

The 3-case pilot uses hand-written fixtures and **must not be presented as scientific evidence** of an improvement. Actual comparative research requires preselected public repair tasks, fixed model/runtime/token budgets, multiple seeds or paired task runs, and a task verifier that measures **successful repairs**, not just retrieved-file relevance.

- The existing `GEMMA4.ipynb` was exported from Colab; it currently contains setup cells, not agent implementation.
- The earlier Kaggle starter notebook is a separate reference. It contains a paper-style hardware/telemetry analysis with embedded example tables and should not be treated as our original measured results without independent verification and proper attribution.
- `PLAN.md` contains the longer research and competition execution roadmap.

## Next steps

1. Validate actual Kaggle dataset schema and licenses in the Kaggle runtime.
2. Create a held-out task manifest and baseline localization labels without leaking reference patches into the model prompt.
3. Integrate official Gemma 4 model serving and fixed-context prompts.
4. Add sandboxed patch application and verification with clean worktrees.
5. Execute paired retrieval/repair benchmarks, publish raw results and limitations.
