"""Lexical, AST-aware and import-graph context retrieval for Python repositories.

Research prototype: retrieves source excerpts only. Does not generate or validate patches.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
import re
from collections import defaultdict

STOP = {"a", "an", "the", "to", "of", "in", "and", "is", "it", "for", "on", "by", "with", "when", "from", "not", "be", "as"}


def tokens(s: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", s.lower().replace("_", " "))
    return set(words) - STOP


@dataclass(frozen=True)
class Span:
    path: str
    name: str
    start: int
    end: int
    text: str


@dataclass
class Index:
    spans: list[Span]
    neighbors: dict[str, set[str]]


def index_repository(root: str | Path) -> Index:
    """Index Python symbols and resolvable local imports, ignoring hidden folders."""
    root = Path(root)
    files = sorted(p for p in root.rglob("*.py") if not any(
        part.startswith(".") or part in {"__pycache__", "venv", ".venv"}
        for part in p.relative_to(root).parts
    ))
    modules = {}
    for p in files:
        rel = p.relative_to(root).as_posix()
        mod = rel[:-3].replace("/", ".")
        if mod.endswith(".__init__"):
            mod = mod[:-9]
        modules[mod] = rel
    spans: list[Span] = []
    graph: dict[str, set[str]] = defaultdict(set)
    for p in files:
        rel = p.relative_to(root).as_posix()
        source = p.read_text(encoding="utf-8", errors="replace")
        lines = source.splitlines(keepends=True)
        try:
            tree = ast.parse(source, filename=rel)
        except SyntaxError:
            # Preserve searchability for in-progress or malformed source files.
            spans.append(Span(rel, "<module>", 1, len(lines), source[:4000]))
            continue
        symbols = [node for node in ast.walk(tree) if isinstance(node, (
            ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef
        ))]
        if symbols:
            for node in symbols:
                begin, end = node.lineno, node.end_lineno or node.lineno
                spans.append(Span(rel, node.name, begin, end, "".join(lines[begin-1:end])))
        else:
            spans.append(Span(rel, "<module>", 1, len(lines), source[:4000]))
        current_mod = rel[:-3].replace("/", ".")
        package = current_mod.rsplit(".", 1)[0] if "." in current_mod else ""
        for node in ast.walk(tree):
            candidates = []
            if isinstance(node, ast.Import):
                candidates = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    parts = package.split(".") if package else []
                    prefix = ".".join(parts[:max(0, len(parts) - node.level + 1)])
                    base = ".".join(filter(None, [prefix, node.module or ""]))
                else:
                    base = node.module or ""
                candidates = [base] + [".".join(filter(None, [base, a.name])) for a in node.names]
            for candidate in candidates:
                target = modules.get(candidate)
                if target is None:
                    seg = candidate.split(".")
                    while len(seg) > 1 and target is None:
                        seg.pop()
                        target = modules.get(".".join(seg))
                if target is not None and target != rel:
                    graph[rel].add(target)
                    graph[target].add(rel)
    return Index(spans, dict(graph))


def retrieve(index: Index, issue: str, method: str = "lexical", max_chars: int = 4000) -> list[Span]:
    """Return deterministic spans under a character-budget proxy for tokens.

    Allowed methods: lexical, structural, graph. Graph uses one-hop undirected
    file imports; it is not a semantic call graph. No training, generation or tests.
    """
    if method not in {"lexical", "structural", "graph"}:
        raise ValueError("method must be lexical, structural, or graph")
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    q = tokens(issue)
    scored = []
    for span in index.spans:
        base = 2 * len(q & tokens(span.path)) + len(q & tokens(span.text))
        symbol = len(q & tokens(span.name))
        score = base + (3 * symbol if method in {"structural", "graph"} else 0)
        scored.append((score, span))
    if method == "graph":
        path_max = defaultdict(int)
        for score, span in scored:
            path_max[span.path] = max(path_max[span.path], score)
        scored = [(score + min(3, max((path_max[n] for n in index.neighbors.get(span.path, set())), default=0)), span)
                  for score, span in scored]
    ranked = sorted((pair for pair in scored if pair[0] > 0),
                    key=lambda pair: (-pair[0], pair[1].path, pair[1].start))
    selected, used = [], 0
    for _, span in ranked:
        cost = len(span.text)
        if cost and used + cost <= max_chars:
            selected.append(span)
            used += cost
    return selected
