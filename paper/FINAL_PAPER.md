# Following the Evidence: When Repository Graphs Help and Hurt Code Retrieval

**Subtitle:** An auditable, budget-constrained comparison of lexical, structural, import-graph, and static-call retrieval for local coding agents

**Payton Gagne**  
Independent software engineering research | November 12, 2026  
**Code:** https://github.com/paytongagne/GEMMA4

## Abstract

A repository-level coding agent must find useful source code before it can reason about a defect, yet small local models face limited context and inference budgets. This paper introduces GEMMA4, an inspectable Python research framework for comparing four source-context retrieval strategies under equal character budgets: lexical relevance, AST-aware symbols, file-import adjacency, and a combined graph with conservative static-call links. Rather than assuming more structure always helps, we record why each source span was selected and how much budget it consumed. We evaluate seven constructed localization tasks and 15 manually curated questions about the project's own codebase, reporting paired results and failure cases. At 400 characters in the synthetic suite, import-graph and combined-graph retrieval located a target file in 7/7 tasks versus 6/7 for lexical retrieval; explicit call links produced no additional gain. On the self-audit at 700 characters, lexical retrieval reached 8/15 while the combined graph reached only 6/15. These observations illustrate that graph expansion can uncover dependencies but can also displace direct evidence when context is scarce. The findings are preliminary: no held-out public-issue benchmark, live Gemma 4 repair-rate experiment, or official competition score is reported. The contribution is an auditable evaluation resource and a concrete negative result about budget-sensitive graph retrieval.

## 1. Introduction

Software maintenance commonly requires understanding more than one function. A bug report may name the entry point, while the faulty behavior sits in an imported helper, a callee, or a class method. Repository-level completion and repair systems therefore retrieve evidence from multiple files instead of passing only the most obvious source to the model [1-3]. This creates a second problem: every apparently relevant dependency competes for a finite context budget.

Our research question is deliberately narrow: **under identical repository snapshots and source-character budgets, when does static relationship evidence improve or reduce target-file localization compared with simpler lexical retrieval?** We examine the context-selection stage, not the language model's ability to produce a correct patch. This separation matters because an agent can retrieve the correct file and still fail to repair the bug, or repair a bug through a valid file that a manually constructed oracle did not anticipate.

Our contributions are: (1) four deterministic retrieval variants sharing a single candidate index and selection rule; (2) recorded per-span selection evidence, source costs, and graph provenance; (3) a paired evaluation format with per-task outcomes, budget sweeps, and bootstrap uncertainty estimates; and (4) documented successes and regressions rather than a single best-case number. The implementation is public and intended as a small research resource, not a claim of a new general-purpose graph-reasoning algorithm.

## 2. Related work and positioning

SWE-bench evaluates whether systems can resolve real GitHub issues with executable tests rather than merely locate code [1]. RepoCoder demonstrates iterative retrieval for repository-level completion [2], while RepoGraph investigates repository-wide structural guidance for software engineering agents [3]. Agentless emphasizes that relatively simple localization, repair, and validation stages can be effective alternatives to elaborate autonomous control loops [4]. GEMMA4 builds on this literature but makes a narrower contribution: it isolates **the cost and provenance of source-context selection**, evaluates the same candidates under strictly bounded retrieval budgets, and explicitly publishes cases where graph signals degrade results. It does not claim to outperform any of these systems in verified bug resolution.

## 3. Method

### 3.1 Repository representation

GEMMA4 parses Python files with the standard-library `ast` module. The index records the repository-relative path, symbol name, inclusive line range, and source text for top-level functions, classes, and direct class methods. A syntax-invalid file remains searchable through a truncated fallback span. Generated outputs, virtual environments, caches, symlinks, and very large source files are excluded. This prototype is Python-specific.

Two relationship layers augment the source spans. First, resolvable local imports create undirected *file-adjacency* links. Second, conservative AST inspection records directed *symbol-call* links for same-module calls, imported aliases, and simple `self.method()` references. Because Python dispatch can be dynamic, these are syntactic hypotheses, not verified runtime dependencies. Edge confidence values are manually chosen scoring weights and must not be interpreted as calibrated probabilities.

### 3.2 Four controlled retrieval conditions

All conditions receive the same issue description, parsed repository, candidate spans, and budget:

1. **Lexical:** inverse-document-frequency-weighted matches between issue terms and source text or paths.
2. **Structural:** lexical scoring plus a symbol-name match bonus.
3. **File graph:** structural scoring plus limited propagation from high-ranking spans to directly import-adjacent files.
4. **Evidence graph:** file-graph signals plus propagation along direct static-call edges.

The index uses normalized identifier tokens, including underscore and CamelCase splitting. For graph variants, a small number of high-scoring seeds is selected before propagation. All methods rank spans by relevance divided by the square root of span length, then greedily fill an equal maximum **source-character** budget without double-counting overlapping class and method spans. This budget is a convenient retrieval proxy, **not a measurement of Gemma tokenizer tokens**; path labels and prompt wrapping are excluded. Scores, selected paths, costs, lexical components, graph bonuses, and reasons for selection are logged to enable inspection.

### 3.3 What the system does and does not do

The broader repository also contains a model-compatible local patch pipeline, isolated temporary-workspace editing, restricted test execution, and candidate Kaggle agent configuration. These components have automated tests, including a scripted-model patch that passes a focused unit test. **That model is mocked.** The current empirical study measures retrieval localization only: it does not measure patch generation, end-to-end issue resolution, GPU utilization, inference latency, or real Gemma 4 performance.

## 4. Evaluation protocol

Each task is specified by a JSONL record containing a task ID, repository checkout, issue text, target file(s), and split label. The evaluator gives **only the issue and repository** to retrieval; oracle target-file labels are used afterward to compute outcomes. Every strategy is run against identical tasks and budgets. Metrics include any-target-file recall (whether at least one target appears), all-target-file recall, fraction of target files retrieved, reciprocal rank, average source characters consumed, and paired wins/losses versus lexical.

We use two development-oriented datasets. **Synthetic suite:** seven hand-constructed tasks covering imported functions, duplicated names, method relationships, and malformed source. Labels were authored with the fixtures; a split named `heldout_toy` is not a genuinely independent held-out benchmark. **Project self-audit:** 15 manually written queries about code in GEMMA4 itself; targets are known to the author and the repository is evolving. These tasks expose engineering regressions but cannot support generalization to independent projects.

The evaluation scripts use deterministic selections and paired bootstrap resampling with seed 13 and 1,000 draws. With samples this small and curated, the intervals characterize instability of the observed samples, not robust population-level statistical significance.

## 5. Results

### 5.1 Synthetic localization: seven tasks

| Budget (source characters) | Lexical | Structural | File graph | Evidence graph |
|:--|--:|--:|--:|--:|
| 200 | 6/7 | 6/7 | 6/7 | 6/7 |
| 400 | 6/7 | 6/7 | **7/7** | **7/7** |
| 800 | 6/7 | 6/7 | **7/7** | **7/7** |

At 400 characters, the graph methods recovered `app/storage.py` for an issue describing a crash in `handle_profile`. Lexical selection instead preferred the two files containing similarly named handlers. Import adjacency supplied a useful pointer from a handler to the underlying storage helper. Crucially, the richer static-call variant offered **no further improvement** beyond the simpler import graph. The evidence-graph versus lexical paired difference was 1/7, or 14.3 percentage points, with a bootstrap interval of **0 to 42.9 points**. This is a smoke test, not an effect-size estimate for real coding issues.

### 5.2 Curated self-audit: 15 repository questions

| Budget (source characters) | Lexical | Structural | File graph | Evidence graph |
|:--|--:|--:|--:|--:|
| 700 | **8/15** | 4/15 | 4/15 | 6/15 |
| 1,500 | 12/15 | 9/15 | 9/15 | 12/15 |
| 3,000 | 12/15 | 12/15 | 12/15 | **13/15** |

The pattern reverses under pressure. At 700 characters, the evidence graph loses two tasks that lexical retrieval gets right. For a query about applying a patch in a temporary workspace, the graph selects only a related test file, displacing the expected implementation module `src/gemma4_agent/local_agent.py`. For a synthetic-suite generation query, graph propagation favors a test and evaluator over `experiments/make_synthetic_suite.py`. These are concrete **context-crowding failures**. At 1,500 characters the combined graph ties lexical; at 3,000 it wins one extra task. The respective graph-minus-lexical paired differences are -13.3, 0, and +6.7 percentage points, all based on this tiny in-development set.

### 5.3 Software verification

We independently reran the source release in a clean extracted directory on November 12, 2026. The suite completed **32/32 local Python unit tests** successfully, including index construction, parsing failures, graph links, budget enforcement, evaluator outputs, mock patch verification, and packaging checks. Both experiment scripts reproduced the counts above. This verifies the software's reported local behavior, not external scientific validity or acceptance by Kaggle's official evaluation harness.

## 6. Interpretation and limitations

**Graph expansion has a measurable opportunity cost.** Linking a caller to its callee can recover evidence missing from the original issue wording, as the synthetic handler/storage case illustrates. Yet the same propagation can raise auxiliary tests or connected utility functions above the implementation actually needed. A useful research extension would detect graph-beneficial task types and apply propagation only when its expected value exceeds its context cost.

The findings face substantial limitations. The samples are small, intentionally constructed or developer-curated, and subject to both issue-wording bias and oracle-label ambiguity. The self-audit is not frozen, and all hyperparameters were developed on the same project rather than tuned on a separate development set. Static links omit dynamic dispatch, monkey-patching, re-exports, reflection, and some higher-order relationships. Character budgets are not actual token budgets, and no inference or verification tests with Gemma 4 were executed. Therefore, the paper **does not show that graph retrieval improves real-world repair rates**. Results on larger independent repositories could reverse every observed ordering.

Our next experiment is a preregistered paired comparison on frozen, publicly available issue tasks. It should use independent development and evaluation splits, identical model checkpoints and decoding parameters, tokenizer-measured input budgets, a safe verifier, measured latency and token counts, and explicit patch success/failure traces. Task strata should separate direct single-file symptoms from cross-file caller/callee problems. This is proposed work, not a completed result.

## 7. Conclusion

GEMMA4 provides an auditable framework for examining what a coding agent retrieves and why. On a seven-case toy suite, file graph expansion recovered one additional target file, while more elaborate static-call evidence did not improve on basic imports. On 15 development queries, graph retrieval **hurt** tight-budget localization and recovered only a slight advantage when additional context was available. The contribution is a reproducible resource and a testable caution: **richer repository context is not automatically better context**. Verified downstream Gemma 4 software-repair performance remains an open evaluation task.

## References

[1] Jimenez, C. E., et al. (2024). *SWE-bench: Can Language Models Resolve Real-World GitHub Issues?* International Conference on Learning Representations. https://proceedings.iclr.cc/paper_files/paper/2024/hash/edac78c3e300629acfe6cbe9ca88fb84-Abstract-Conference.html

[2] Zhang, F., et al. (2023). *RepoCoder: Repository-Level Code Completion Through Iterative Retrieval and Generation.* EMNLP, 2471-2484. https://aclanthology.org/2023.emnlp-main.151/

[3] Ouyang, S., et al. (2025). *RepoGraph: Enhancing AI Software Engineering with Repository-level Code Graph.* International Conference on Learning Representations. https://proceedings.iclr.cc/paper_files/paper/2025/hash/4a4a3c197deac042461c677219efd36c-Abstract-Conference.html

[4] Xia, C. S., Deng, Y., Dunn, S., & Zhang, L. (2025). *Demystifying LLM-Based Software Engineering Agents.* Proceedings of the ACM on Software Engineering, FSE. https://doi.org/10.1145/3715754

[5] Google DeepMind. (2026). *The Gemma 4 Developer Agent Paper Track: Evaluation and submission requirements.* Kaggle. https://www.kaggle.com/competitions/gemma-4-developer-agent-paper/overview/submission-requirements

## Reproducibility note

Public repository: https://github.com/paytongagne/GEMMA4 . To reproduce the numbers from the November 12 development release, use Python 3.10+:

```bash
python -m unittest discover -s tests -v
python experiments/make_synthetic_suite.py --output-dir runs/toy_suite
python experiments/compare_retrieval.py runs/toy_suite/toy_tasks.jsonl --budgets 200 400 800 --output runs/toy_results.json
python experiments/self_audit.py --output runs/self_audit_results.json
```

Expected outputs: 32 passing tests; the two recall tables in Section 5. No private Kaggle data, model weights, or official Gemma 4 evaluation result is required to reproduce these local findings.