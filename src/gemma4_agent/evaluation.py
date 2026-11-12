"""Paired, read-only localization evaluations for evidence-graph retrieval.

This is *not* Gemma inference, SWE-bench scoring, or evidence of correct patches.
Target labels are kept out of the retrieval query and index.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import random
from statistics import mean
from typing import Iterable

from gemma4_agent.evidence_graph import index_evidence_graph, select_context

METHODS = ("lexical", "structural", "file_graph", "evidence_graph")


@dataclass(frozen=True)
class Task:
    task_id: str
    repository: str
    issue: str
    target_files: tuple[str, ...]
    split: str


def load_tasks(manifest: str | Path) -> list[Task]:
    manifest = Path(manifest).resolve()
    rows: list[Task] = []
    ids: set[str] = set()
    for n, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            task_id = item["task_id"]
            issue = item["issue"]
            repo = Path(item["repository"])
            targets = tuple(item["target_files"])
            split = item["split"]
            if not all(isinstance(s, str) and s for s in (task_id, issue, split)):
                raise ValueError("task_id, issue and split must be nonempty strings")
            if task_id in ids:
                raise ValueError("duplicate task ID")
            if not targets or any(not isinstance(t, str) or Path(t).is_absolute() or ".." in Path(t).parts or not t.endswith(".py") for t in targets):
                raise ValueError("target_files must be nonempty repository-relative .py paths")
            location = (manifest.parent / repo).resolve() if not repo.is_absolute() else repo.resolve()
            if not location.is_dir():
                raise ValueError(f"repository missing: {location}")
            if not all((location / t).is_file() for t in targets):
                raise ValueError("target_files not present in repository")
            rows.append(Task(task_id, str(location), issue, targets, split))
            ids.add(task_id)
        except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Manifest line {n}: {exc}") from exc
    if not rows:
        raise ValueError("manifest contains no tasks")
    return rows


def _interval95(values: list[float], seed: int, draws: int) -> list[float]:
    if len(values) == 1:
        return [values[0], values[0]]
    rng = random.Random(seed)
    n = len(values)
    samples = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(draws))
    return [round(samples[int((draws - 1) * 0.025)], 4), round(samples[int((draws - 1) * 0.975)], 4)]


def evaluate(tasks: Iterable[Task], budgets: Iterable[int] = (500, 1500, 3000), seed: int = 13, bootstrap_draws: int = 1000) -> dict:
    task_list = list(tasks)
    if not task_list:
        raise ValueError("at least one task required")
    budgets = tuple(sorted(set(budgets)))
    if not budgets or min(budgets) <= 0 or bootstrap_draws < 100:
        raise ValueError("positive budgets and at least 100 bootstrap draws required")
    cache = {}
    details = []
    for task in task_list:
        index = cache.setdefault(task.repository, index_evidence_graph(task.repository)) if task.repository not in cache else cache[task.repository]
        for budget in budgets:
            for method in METHODS:
                pack = select_context(index, task.issue, method, budget_chars=budget)
                files = pack.files
                expected = set(task.target_files)
                hits = expected.intersection(files)
                ranks = [files.index(t) + 1 for t in hits]
                details.append({
                    "task_id": task.task_id,
                    "split": task.split,
                    "budget_chars": budget,
                    "method": method,
                    "any_file_recall": int(bool(hits)),
                    "all_file_recall": int(expected.issubset(files)),
                    "file_recall_fraction": round(len(hits) / len(expected), 4),
                    "reciprocal_rank": round(1 / min(ranks), 4) if ranks else 0,
                    "used_chars": pack.used_chars,
                    "retrieved_files": files,
                    "target_files": list(task.target_files),
                    "selected": [{"identifier": s.span.identifier, "score": s.score, "cost": s.span.cost, "evidence": list(s.evidence)} for s in pack.selections],
                    "warnings": pack.index_warnings,
                })
    groups = {}
    for budget in budgets:
        for method in METHODS:
            rows = [d for d in details if d["budget_chars"] == budget and d["method"] == method]
            groups[f"{budget}:{method}"] = {
                "tasks": len(rows),
                "any_file_recall": round(mean(d["any_file_recall"] for d in rows), 4),
                "all_file_recall": round(mean(d["all_file_recall"] for d in rows), 4),
                "file_recall_fraction": round(mean(d["file_recall_fraction"] for d in rows), 4),
                "mean_reciprocal_rank": round(mean(d["reciprocal_rank"] for d in rows), 4),
                "mean_context_chars": round(mean(d["used_chars"] for d in rows), 1),
            }
    contrasts = {}
    for budget in budgets:
        base = {d["task_id"]: d["any_file_recall"] for d in details if d["method"] == "lexical" and d["budget_chars"] == budget}
        for method in METHODS[1:]:
            condition = {d["task_id"]: d["any_file_recall"] for d in details if d["method"] == method and d["budget_chars"] == budget}
            changes = [condition[t.task_id] - base[t.task_id] for t in task_list]
            contrasts[f"{budget}:{method}-lexical"] = {
                "delta_any_file_recall": round(mean(changes), 4),
                "paired_bootstrap_95pct": _interval95(changes, seed, bootstrap_draws),
                "wins": sum(v > 0 for v in changes),
                "losses": sum(v < 0 for v in changes),
                "ties": sum(v == 0 for v in changes),
            }
    return {
        "experiment": "read_only_file_localization",
        "not_measured": ["Gemma model behavior", "patch generation", "verified task resolution", "SWE-bench score"],
        "methods": list(METHODS),
        "budgets_are": "source characters, not tokenizer tokens",
        "seed": seed,
        "bootstrap_draws": bootstrap_draws,
        "splits": sorted({t.split for t in task_list}),
        "task_count": len(task_list),
        "summary": groups,
        "paired_vs_lexical": contrasts,
        "task_details": details,
    }
