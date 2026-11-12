# Research design: explainable, budget-aware graph context for coding agents

**Status: executable method + toy harness; empirical claims on real tasks and Gemma 4 are pending.**

## Contribution we are trying to validate

When a model has a bounded context window or inference budget, a larger retrieved snippet is not necessarily a better one. Many apparent failures in repo-level repair may be *evidence selection* failures: a function mentioned in an issue is relevant, but the defect occurs in a callee, imported module, or validation helper. A simple keyword retrieval may miss this relationship; an indiscriminate graph expansion may waste precious tokens on irrelevant neighbors.

We propose **EGR: Evidence-Graph Retrieval**, an inspectable selection mechanism combining (1) literal issue-to-code matches, (2) static symbol names, (3) neighboring import relationships, and (4) call-site edges with explicitly recorded provenance. Code evidence is selected under the same source-character budget for each alternative, and the decision log exposes why a span was selected. It is an engineering hypothesis rather than a demonstrated improvement.

### Claim boundary

- *Supported now:* Python AST static indexes; import adjacency; direct top-level and self-method call associations in simple Python; deterministic retrieval; provenance records; offline paired localization evaluation; unit tests.
- *Not supported now:* model-in-the-loop issue resolution; code patch validity; verifier passing rate; statistical superiority on real repositories; precise Gemma tokenizer costs; model compute/hardware comparisons.
- *Important caveat:* a static call edge is **not** a runtime causal relationship. Python dynamic dispatch, decorators, closures, monkey patching, re-exports, and `getattr` create false negatives/positives.

## Controlled experiment

**Independent variable:** retrieval method. Four ablations use the same index corpus and budgets.

| Condition | Ranking signals |
|---|---|
| A: Lexical | query word overlap with source and file path |
| B: Structural | A + symbol name overlap |
| C: File graph | B + import-adjacent file expansion |
| D: Evidence graph | C + call-site propagation from the strongest matched code spans |

**Controls:** the same repository checkout, exact issue text, source span inventory, fixed budget set, seed count, deterministic tie-breaking, and labels sequestered within the evaluation module. All methods use a shared greedy score / sqrt(source length) selector and the same overlap de-duplication rule.

**Read-only localization outcomes:** any-target-file recall, all-target-file recall, target-file fraction, mean reciprocal rank (MRR), used source characters, and per-task evidence provenance. The paired delta in recall versus A uses resampling **tasks** with a fixed seed, yielding a bootstrap interval; not a formal significance claim with tiny data. We report win/loss/tie counts to make regressions visible.

**Later downstream outcomes:** cleanly-applied patch rate, resolution by provided verifier (the primary agent metric), inference/model prompt tokens, runtime, retry count, and failure mode taxonomy. This requires an official harness and Gemma inference; no localization figure should be relabeled as repair success.

## Data, leakage and reproducibility

1. **Toy fixture:** only validates behavior, not generalization. It includes intentionally named functions and manually chosen targets; it can favor structural methods. Report explicitly as a smoke test.
2. **Development tasks:** preselect publicly authorized repository issue tasks. Clone exact commit; record target files offline from developer-visible changes where permitted. Never expose target paths to the retriever, prompts, or repair agent.
3. **Held-out tasks:** freeze before tuning ranking weights; do not inspect gold changes or adjust retrieval hyperparameters on this split. Public data only; follow competition data-use restrictions.
4. **Model-conditioned evaluation:** if run, use only the required Gemma 4 checkpoint and official tools allowed by the coding competition. The paper track permits different research methods, but never imply a model run unless logs prove it.
5. **Provenance:** preserve source commit SHAs, dataset version, code commit, model ID (if any), run seeds, configuration, measured context budget, task-level outputs and clean reproductions.

## Pre-registered hypotheses

- **H1:** D improves target-file recall over A under tight budgets (test as paired difference, with interval).
- **H2:** D provides more benefit on issues that mention callers while the defect sits in a distinct callee file than on direct single-function issues.
- **H3:** As retrieval budget increases, A/B/C/D converge, because enough source can be selected by all methods.
- **H4:** Additional graph expansion can also hurt by surfacing irrelevant neighbors; report counterexamples and costs.

## The paper we could honestly submit

- **Title:** *Following the Evidence: Budget-Constrained Graph Context Selection for Local Coding Agents*
- **Subtitle:** *A transparent testbed for repository localization under limited inference budgets*
- **Abstract:** A substantive paper must state *measured* task counts, datasets, methods, results, and limitations. Until real experiments finish, omit outcome claims and label the work as a tool/resource proposal.
- **Introduction:** local-model context efficiency, why dependencies matter, research gap in auditability.
- **Method:** four controlled ablations, AST indexing, confidence-weighted syntax edges, bounded selection, deterministic diagnostics.
- **Evaluation:** task sets + exact git revisions, independent oracle labels, budget curves, paired contrasts, failure cases, held-out generalization.
- **Limitations:** approximate syntax graph; Python-only; source-character rather than token budgets; static analysis misses dynamic behavior; gold-file labels measure localization, not successful repair.
- **Conclusion:** only make evidence-backed statements.

## Criterion-oriented priorities (Paper Track)

Kaggle evaluates novelty, quality, relevance, verifiability, and clarity equally. Our most credible *current* contribution is a **new, inspectable research resource** for studying retrieval failure modes and budget tradeoffs. A new algorithm alone is not a novelty guarantee; we must compare to prior methods and test generalization before making that claim.

Reference: [Gemma 4 Developer Agent Paper Track](https://www.kaggle.com/competitions/gemma-4-developer-agent-paper) and [Developer Agent competition](https://www.kaggle.com/competitions/gemma-4-developer-agent).
