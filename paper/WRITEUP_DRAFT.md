# Following the Evidence: An Auditable, Budget-Constrained Repository Retrieval Testbed

**Subtitle:** A controlled comparison of lexical, structural, import-neighbor, and static-call evidence for local coding agents

**Status: preliminary resource paper; measured results are synthetic and curated-development localization, not Gemma 4 repair. The competition agent is a candidate configuration without official model/harness verification.**

## Abstract

Repository-level software repair requires selecting context from codebases that are often much larger than the prompt budget available to a local language model. Retrieving the function named in an issue may not be sufficient when the underlying problem involves a callee, a neighboring module, or a class method. We introduce an open-source, read-only research prototype for studying how progressively richer static code relationships change context selection under fixed source-character budgets. The prototype constructs a symbol-aware Python index, records import and direct-call relationships, and compares four deterministic retrieval conditions. It also produces per-selection evidence traces and paired, task-level localization reports. In a deliberately small, seven-task synthetic smoke test, import-neighbor retrieval increased any-target-file recall from 6/7 to 7/7 at budgets of 400 and 800 source characters, but a call-aware evidence graph yielded no further gain. We also evaluate fifteen manually curated questions against the project's own evolving Python repository. At a 700-character budget, lexical retrieval found the target file on 8/15 tasks versus 6/15 for the symbol-evidence graph; at 3,000 characters the pattern reversed to 12/15 versus 13/15. These contradictory results show that graph propagation has a real context cost and cannot be assumed helpful. The two evaluations establish operation and failure modes of the testbed, not generalization to independent repositories or improved Gemma 4 issue resolution. We also provide a candidate declarative Gemma 4 agent configuration with the official navigation tools, pending official harness evaluation.

## 1. Motivation and research question

A coding assistant cannot act on repository evidence it never sees. Even when a model has the reasoning capacity to propose a fix, its input context may omit the dependency responsible for the defect. This is especially important for local models that must manage a finite inference and interaction budget.

The immediate research question is: **with all other selection rules held constant, does adding static code-relationship evidence improve the chance that the correct source file is included in a bounded retrieval pack?** A second, harder question, which remains open, is whether that improvement translates into successful model-generated patches and verified fixes.

The focus here is not claiming a new general-purpose graph reasoner. Repository graph augmentation has precedent, including RepoGraph (Ouyang et al., 2025). Our proposed contribution is a small, inspectable experiment framework that makes each selected context segment, graph reason, budget cost, and regression visible. A retrieval policy that helps some tasks and hurts others should be evaluated as such, instead of summarized solely by a top-line success rate.

## 2. Method

### 2.1 Source indexing

We use Python's standard-library abstract syntax tree (AST) parser to identify top-level functions, classes, and direct class methods. The index stores a repository-relative path, symbol name, line interval, and source text for each candidate. Malformed Python is preserved as an unparsed fallback rather than crashing indexing. The implementation ignores typical build/cache directories and oversized Python files.

We also create (i) undirected file adjacency from resolvable local imports and (ii) directed, conservative static-call edges between symbols, including unambiguous same-module calls, imported-function aliases, and simple `self.method()` calls. The graph does not attempt runtime call resolution. Confidence annotations are heuristic metadata, **not** empirical probabilities.

### 2.2 Retrieval alternatives

We compare four methods with identical indexed candidates and budgets:

1. **Lexical:** query overlap with file paths and source code.
2. **Structural:** lexical features plus weighted symbol-name matches.
3. **File graph:** structural scores plus neighboring-file import evidence.
4. **Evidence graph:** file graph plus direct-call propagation from the highest-scoring anchor spans.

Every method uses the same deterministic budget-aware ranking rule (retrieval score divided by the square root of span length), the same rules for avoiding overlapping source spans, and the same source-character budget. This isolates differences in ranking signals, although it does not establish that the shared selector is optimal. The current budget unit is **source characters**, not tokens measured by Gemma's tokenizer; file paths and prompt wrapper overhead are excluded.

### 2.3 Auditable evidence trails

Each result records its path, source span, cost, score, lexical contribution, graph contribution, and graph-edge rationale. This allows a reviewer to determine whether a dependency was retrieved because the issue named it, because it was imported, or because an indexed function referred to it. The explicit record also reveals false connections and irrelevant budget consumption.

## 3. Evaluation protocol

The evaluation tool reads JSONL manifests containing task IDs, repository checkout directories, issue descriptions, target files, and split labels. Gold target files are used **only after retrieval** to compute metrics; they are not concatenated into prompts or passed to the selection algorithm.

At each budget, we report any-target-file recall, all-target-file recall, fraction of reference files recovered, mean reciprocal rank, and average source characters selected. We compare each alternative against lexical on identical tasks, record paired wins/losses/ties, and calculate fixed-seed paired bootstrap intervals over task-level recall differences. These intervals are descriptive and unreliable with tiny test sets; we do not treat them as proof of statistical significance.

For the next evaluation, we would freeze exact repository commits, tune only on development tasks, and assess held-out tasks without changing weights. Crucially, **localization accuracy is not a measure of patch correctness**. Real repair evaluation requires a Gemma model, patch application, independent verifier execution, latency/token accounting, and a safe isolated environment. None are part of this result.

## 4. Preliminary implementation check

A deliberately small, seven-task synthetic suite includes imported aliases, cross-file calls, an ambiguous duplicated handler name, self-method relationships, and a malformed Python file. The oracle target files were manually specified when constructing the examples. The cases are intended to exercise the software, and their naming conventions may favor some methods.

| Source-character budget | Lexical: any-file recall | Structural | File graph | Evidence graph |
|---|---:|---:|---:|---:|
| 200 | 6/7 | 6/7 | 6/7 | 6/7 |
| 400 | 6/7 | 6/7 | 7/7 | 7/7 |
| 800 | 6/7 | 6/7 | 7/7 | 7/7 |

These figures come from the local synthetic generator and evaluator and can be reproduced with the commands in `README.md`. The 400-character graph-versus-lexical difference was only one task out of seven; the paired bootstrap interval includes zero. The additional call-site evidence did **not** improve recall over import adjacency on these tasks. This is a meaningful limitation of the current fixture and a reason to evaluate varied real-world defects rather than selectively report successes.

### 4.1 Curated development queries on a non-synthetic repository

A secondary diagnostic uses **15 manually formulated queries** about the implementation files in this same evolving GitHub project. Each query names an actual API behavior; its expected file was chosen by the developers. These queries are **not held out**, the repository is **not frozen**, and the author knows where the answers are. They are not an unbiased sample of public issues, and the labels must not be used to claim external validity.

| Source-character budget | Lexical: any-file recall | Structural | File graph | Evidence graph |
|---|---:|---:|---:|---:|
| 700 | 8/15 | 4/15 | 4/15 | 6/15 |
| 1,500 | 12/15 | 9/15 | 9/15 | 12/15 |
| 3,000 | 12/15 | 12/15 | 12/15 | 13/15 |

The tight-budget regression is particularly instructive: on some queries, graph bonuses elevate connected but less relevant code or test helpers above the expected source. A different failure mode occurs when an oversized function occupies most of the budget. We found and corrected an indexing contamination bug that included generated `runs/` artifacts; the revised index excludes such outputs. The self-audit data remains exploratory because future code changes will change the candidate pool and potentially the values reported here. The recorded queries and per-task output allow exact reruns against the corresponding source snapshot.

### 4.2 Engineering tests and candidate agent integration

The project passed **32 local tests** covering AST import/call analysis, safe context budgets, paired evaluator reporting, ZIP packaging, notebook reconstruction, and a scripted-model patch that passes a focused unit test in a temporary workspace. This integration test uses an explicitly **mocked model**, not Gemma 4. A self-contained Kaggle notebook can emit a candidate `submission.zip` with the required root `agent.yaml`, model declaration, system prompt, and supported tools. Only the official ADK compiler and a real Gemma 4 public development task can establish competition acceptance and actual software-repair accuracy. The local tests validate software behavior, **not** model performance.

## 5. Error analysis and threats to validity

- **Synthetic and researcher-curated data:** task wording and targets do not represent the distribution of independent GitHub issues. The self-audit is known to the authors and is not held out.
- **Static Python limitations:** dynamically resolved names, monkey patching, re-exports, decorators, and runtime reflection can invalidate an inferred dependency graph.
- **Selection bias:** source length, identifier choice, and default retrieval weights may influence outcomes. Hyperparameters must be frozen before held-out evaluation.
- **Proxy budget:** character count excludes metadata and is not equivalent to model tokens or runtime cost.
- **Oracle ambiguity:** a patch can repair an issue by changing a file not listed in a reference patch; gold-file recall is imperfect.
- **No Gemma model experiment:** a mocked patch-validation integration test confirms plumbing only; the paper cannot infer Gemma 4 patch success, model reasoning ability, or GPU serving efficiency.
- **No novelty guarantee:** code graphs and retrieval-augmented coding are established techniques. The proposed testbed should be judged on reproducibility and diagnostic utility, pending realistic experiments.

## 6. Proposed next experiment

The most informative follow-up is a pre-registered, paired real-repository evaluation with frozen task selection and a small set of fixed budgets. The next stage should stratify tasks by whether their described symptom is located in a caller, a callee, or an unrelated file. That would directly test whether graph propagation helps on cross-file symptoms while harming or wasting context on direct, single-file bugs. The current submission candidate is a single Gemma 4 12B agent whose instructions use the official harness's graph, file, editing, testing, and patch-submission tools. Paired, structurally identical lexical-navigation and graph-navigation candidates are generated with fixed models and budgets, alongside 4B and 31B configurations for later model-size comparisons. None of these candidates has been scored. The next experiment must run the official public development harness with frozen issue IDs and a live supported Gemma 4 checkpoint, then capture per-task traces, patch-apply outcomes, true test success, and runtime. Until those runs exist, no repair-rate conclusion is justified.

## 7. Conclusion

We release an inspectable prototype for comparing repository context-selection strategies with paired, bounded-budget evaluation. The preliminary toy check demonstrates reproducibility and exposes a negative result: deeper graph propagation was not better than simple import adjacency in this tiny suite. The development self-audit also shows that evidence graphs can decrease retrieval recall when the context budget is very small, underscoring the importance of publishing negative ablations. The principal value of the work is a framework for measuring and explaining context-selection decisions, accompanied by a reproducible candidate-agent artifact. Claims about actual software repair remain contingent on independent real-task and model-in-the-loop evaluation.

## References

1. Jimenez, C. E., et al. (2024). **SWE-bench: Can Language Models Resolve Real-world GitHub Issues?** ICLR. https://proceedings.iclr.cc/paper_files/paper/2024/hash/edac78c3e300629acfe6cbe9ca88fb84-Abstract-Conference.html
2. Zhang, F., et al. (2023). **RepoCoder: Repository-Level Code Completion Through Iterative Retrieval and Generation.** EMNLP, 2471–2484. https://aclanthology.org/2023.emnlp-main.151/
3. Ouyang, S., et al. (2025). **RepoGraph: Enhancing AI Software Engineering with Repository-level Code Graph.** ICLR. https://proceedings.iclr.cc/paper_files/paper/2025/hash/4a4a3c197deac042461c677219efd36c-Abstract-Conference.html
4. Xia, C. S., et al. (2025). **Demystifying LLM-based Software Engineering Agents.** FSE. https://doi.org/10.1145/3715754
5. Google DeepMind (2026). **Gemma 4 Developer Agent Paper Track.** Kaggle. https://www.kaggle.com/competitions/gemma-4-developer-agent-paper
