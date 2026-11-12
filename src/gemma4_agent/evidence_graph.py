"""Static code evidence graph and budget-controlled context selection.

Research-only prototype: no model execution and no assertion of repair success.
Edges are syntactic hints, not proof of runtime call behavior.
"""
from __future__ import annotations

import ast
from collections import Counter, defaultdict
from dataclasses import dataclass
from math import log, sqrt
from pathlib import Path
import re
from typing import Literal

STOP = {"a", "an", "and", "are", "as", "be", "by", "for", "from", "in", "is", "it", "of", "on", "or", "the", "to", "was", "when", "with", "not", "this", "should"}
METHOD = Literal["lexical", "structural", "file_graph", "evidence_graph"]
EXCLUDED = {".git", ".venv", "venv", "__pycache__", "node_modules", "build", "dist", ".tox", ".mypy_cache", "runs", "artifacts"}


def tokenize(value: str) -> set[str]:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return set(re.findall(r"[a-z0-9]+", value.lower().replace("_", " "))) - STOP


@dataclass(frozen=True)
class CodeSpan:
    identifier: str
    path: str
    symbol: str
    start: int
    end: int
    text: str

    @property
    def cost(self) -> int:
        return len(self.text)


@dataclass(frozen=True)
class EvidenceEdge:
    source: str
    destination: str
    kind: str
    confidence: float


@dataclass
class EvidenceIndex:
    spans: list[CodeSpan]
    edges: list[EvidenceEdge]
    file_neighbors: dict[str, set[str]]
    warnings: list[str]


@dataclass(frozen=True)
class Selection:
    span: CodeSpan
    score: float
    lexical_score: float
    graph_bonus: float
    evidence: tuple[str, ...]


@dataclass
class ContextPack:
    method: str
    budget_chars: int
    used_chars: int
    selections: list[Selection]
    index_warnings: list[str]

    @property
    def files(self) -> list[str]:
        return list(dict.fromkeys(s.span.path for s in self.selections))


def _module(path: str) -> str:
    mod = path[:-3].replace("/", ".")
    return mod[:-9] if mod.endswith(".__init__") else mod


def _qualified_import(node: ast.ImportFrom, module: str, is_package: bool) -> str:
    if not node.level:
        return node.module or ""
    package = module if is_package else module.rpartition(".")[0]
    parts = package.split(".") if package else []
    ascents = node.level - 1
    if ascents > len(parts):
        return ""
    prefix = parts[:len(parts)-ascents] if ascents else parts
    return ".".join([*prefix, *([node.module] if node.module else [])])


def _symbols(tree: ast.Module) -> list[tuple[str, ast.AST, str | None]]:
    result = []
    for item in tree.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result.append((item.name, item, None))
        elif isinstance(item, ast.ClassDef):
            result.append((item.name, item, None))
            for member in item.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    result.append((f"{item.name}.{member.name}", member, item.name))
    return result


def index_evidence_graph(root: str | Path, max_file_bytes: int = 2_000_000) -> EvidenceIndex:
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError(f"No repository directory: {root}")
    paths = sorted(
        p for p in root.rglob("*.py")
        if p.is_file() and not any(part.startswith(".") or part in EXCLUDED for part in p.relative_to(root).parts)
        and not p.is_symlink() and p.stat().st_size <= max_file_bytes
    )
    modules = {_module(p.relative_to(root).as_posix()): p.relative_to(root).as_posix() for p in paths}
    spans: list[CodeSpan] = []
    entries: list[tuple[str, str, ast.AST, str | None, dict[str, str]]] = []
    warnings: list[str] = []
    file_neighbors: dict[str, set[str]] = defaultdict(set)
    for path in paths:
        rel = path.relative_to(root).as_posix()
        code = path.read_text(encoding="utf-8", errors="replace")
        lines = code.splitlines(keepends=True)
        mod = _module(rel)
        try:
            tree = ast.parse(code, filename=rel)
        except SyntaxError as exc:
            warnings.append(f"{rel}: syntax error at line {exc.lineno}")
            spans.append(CodeSpan(f"{rel}:1:<unparsed>", rel, "<unparsed>", 1, max(1, len(lines)), code[:4000]))
            continue
        aliases: dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    aliases[a.asname or a.name.split(".")[0]] = a.name if a.asname else a.name.split(".")[0]
                    target = modules.get(a.name)
                    if target and target != rel:
                        file_neighbors[rel].add(target)
                        file_neighbors[target].add(rel)
            elif isinstance(node, ast.ImportFrom):
                base = _qualified_import(node, mod, path.name == "__init__.py")
                if base in modules and modules[base] != rel:
                    target = modules[base]
                    file_neighbors[rel].add(target)
                    file_neighbors[target].add(rel)
                for a in node.names:
                    if a.name == "*":
                        continue
                    aliases[a.asname or a.name] = f"{base}.{a.name}" if base else a.name
                    sub = f"{base}.{a.name}" if base else a.name
                    if sub in modules and modules[sub] != rel:
                        target = modules[sub]
                        file_neighbors[rel].add(target)
                        file_neighbors[target].add(rel)
        found = _symbols(tree)
        if not found:
            spans.append(CodeSpan(f"{rel}:1:<module>", rel, "<module>", 1, max(1, len(lines)), code[:4000]))
        for name, node, enclosing in found:
            start = min([node.lineno, *(d.lineno for d in getattr(node, "decorator_list", []) if hasattr(d, "lineno"))])
            end = node.end_lineno or node.lineno
            identifier = f"{rel}:{start}:{name}"
            spans.append(CodeSpan(identifier, rel, name, start, end, "".join(lines[start-1:end])))
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                entries.append((identifier, mod, node, enclosing, aliases))
    symbol_map = {f"{_module(s.path)}.{s.symbol}": s.identifier for s in spans}
    edges: list[EvidenceEdge] = []
    recorded: set[tuple[str, str]] = set()
    for src, mod, node, enclosing, aliases in entries:
        # ast.walk includes nested-function calls; approximate conservative static edges.
        for call in (n for n in ast.walk(node) if isinstance(n, ast.Call)):
            target_name = None
            kind = "local_call"
            func = call.func
            if isinstance(func, ast.Name):
                target_name = aliases.get(func.id, f"{mod}.{func.id}")
                kind = "imported_call" if func.id in aliases else "local_call"
            elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                owner = func.value.id
                if owner in {"self", "cls"} and enclosing:
                    target_name = f"{mod}.{enclosing}.{func.attr}"
                    kind = "self_method"
                elif owner in aliases:
                    target_name = f"{aliases[owner]}.{func.attr}"
                    kind = "imported_call"
            dst = symbol_map.get(target_name or "")
            if dst and dst != src and (src, dst) not in recorded:
                recorded.add((src, dst))
                edges.append(EvidenceEdge(src, dst, kind, {"local_call": 0.90, "imported_call": 0.85, "self_method": 0.90}[kind]))
    edges.sort(key=lambda e: (e.source, e.destination, e.kind))
    return EvidenceIndex(spans, edges, dict(file_neighbors), warnings)


def select_context(index: EvidenceIndex, issue: str, method: METHOD = "lexical", budget_chars: int = 4000, seed_count: int = 3) -> ContextPack:
    if method not in {"lexical", "structural", "file_graph", "evidence_graph"}:
        raise ValueError("unknown retrieval method")
    if budget_chars <= 0 or seed_count <= 0:
        raise ValueError("budget_chars and seed_count must be positive")
    q = tokenize(issue)
    if not q:
        return ContextPack(method, budget_chars, 0, [], index.warnings.copy())
    docs = [tokenize(s.text) | tokenize(s.path) | tokenize(s.symbol) for s in index.spans]
    counts = Counter(term for d in docs for term in d)
    num_docs = max(1, len(docs))
    idf = {t: log(1 + (num_docs + 1) / (counts[t] + 1)) for t in q}
    weighted = {}
    lexical = {}
    for span, terms in zip(index.spans, docs):
        matching = q & terms
        body = sum(idf[t] for t in matching if t in tokenize(span.text))
        path = sum(idf[t] for t in matching if t in tokenize(span.path))
        symbol = sum(idf[t] for t in matching if t in tokenize(span.symbol))
        lex = body + 1.5 * path
        lexical[span.identifier] = lex
        weighted[span.identifier] = lex + (2.2 * symbol if method != "lexical" else 0)
    seeds = sorted(index.spans, key=lambda s: (-weighted[s.identifier], s.path, s.start))
    seeds = [s for s in seeds if weighted[s.identifier] > 0][:seed_count]
    bonus: dict[str, float] = defaultdict(float)
    evidence: dict[str, list[str]] = defaultdict(list)
    if method in {"file_graph", "evidence_graph"}:
        for seed in seeds:
            for neighbor_file in sorted(index.file_neighbors.get(seed.path, ())):
                for dest in index.spans:
                    if dest.path == neighbor_file and dest.identifier != seed.identifier:
                        increase = min(2.0, weighted[seed.identifier] * 0.12)
                        if increase > bonus[dest.identifier]:
                            bonus[dest.identifier] = increase
                            evidence[dest.identifier] = [f"import-adjacent to {seed.path}"]
    if method == "evidence_graph":
        for seed in seeds:
            for edge in index.edges:
                if seed.identifier == edge.source:
                    dst = edge.destination
                elif seed.identifier == edge.destination:
                    dst = edge.source
                else:
                    continue
                increase = min(7.0, weighted[seed.identifier] * 0.85 * edge.confidence)
                if increase > bonus[dst]:
                    bonus[dst] = increase
                    evidence[dst] = [f"{edge.kind}: {edge.source} -> {edge.destination} (confidence {edge.confidence:.2f})"]
    candidates = []
    for span in index.spans:
        score = weighted[span.identifier] + bonus[span.identifier]
        if score <= 0 or not span.text:
            continue
        candidates.append((score / sqrt(max(1, span.cost)), score, span))
    candidates.sort(key=lambda x: (-x[0], -x[1], x[2].path, x[2].start, x[2].symbol))
    used = 0
    selected: list[Selection] = []
    occupied: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for _, score, span in candidates:
        if used + span.cost > budget_chars:
            continue
        # Avoid selecting overlapping class and method definitions, so budget is not double-counted.
        if any(not (span.end < lo or span.start > hi) for lo, hi in occupied[span.path]):
            continue
        reasons = ["issue-to-code lexical match"] if lexical[span.identifier] > 0 else []
        if method != "lexical" and score - bonus[span.identifier] > lexical[span.identifier]:
            reasons.append("function/class name match")
        reasons.extend(evidence[span.identifier])
        selected.append(Selection(span, round(score, 4), round(lexical[span.identifier], 4), round(bonus[span.identifier], 4), tuple(reasons)))
        used += span.cost
        occupied[span.path].append((span.start, span.end))
    return ContextPack(method, budget_chars, used, selected, index.warnings.copy())
