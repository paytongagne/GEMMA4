"""Build and statically validate a Kaggle Gemma 4 Developer Agent config archive.

Build output is a *candidate* archive. Official swegemma harness validation is
required before claiming Kaggle compatibility or a competition score.
"""
from __future__ import annotations

import argparse
import json
import re
import stat
import zipfile
from pathlib import Path

MODEL_IDS = {
    "gemma-4-31b-it-qat-w4a16-ct", "gemma-4-12b-it-qat-w4a16-ct",
    "gemma-4-e4b-it-qat-w4a16-ct", "gemma-4-e2b-it-qat-w4a16-ct",
}
TOOLS = {"run_command", "read_file", "edit_file", "write_file", "get_code_neighbors",
         "search_similar_code", "get_code_subgraph", "get_status", "submit_patch"}
EXTENSIONS = {".yaml", ".yml", ".md", ".txt", ".py", ".json", ".safetensors"}
REQUIRED = {"agent.yaml", "prompts/system.md", "configs/sampling.yaml"}
ROOT_DIR = Path(__file__).resolve().parents[1]


def collect(submission_dir: Path) -> dict[str, bytes]:
    submission_dir = submission_dir.resolve()
    if not submission_dir.is_dir():
        raise ValueError(f"Missing submission directory: {submission_dir}")
    entries: dict[str, bytes] = {}
    for item in sorted(submission_dir.rglob("*")):
        if item.is_symlink():
            raise ValueError(f"Symlink not allowed: {item}")
        if not item.is_file():
            continue
        name = item.relative_to(submission_dir).as_posix()
        if item.suffix not in EXTENSIONS or ".." in Path(name).parts:
            raise ValueError(f"Unsupported file: {name}")
        if len(entries) >= 10000:
            raise ValueError("Too many files")
        entries[name] = item.read_bytes()
    if not REQUIRED.issubset(entries):
        raise ValueError(f"Missing required files: {sorted(REQUIRED - entries.keys())}")
    if sum(map(len, entries.values())) >= 3 * 1024 ** 3:
        raise ValueError("Submission uncompressed size must be under 3 GiB")
    for name, raw in entries.items():
        if name.endswith((".yaml", ".yml", ".md", ".txt", ".py", ".json")):
            raw.decode("utf-8", errors="strict")
    return entries


def validate(entries: dict[str, bytes]) -> dict:
    root_files = {n for n in entries if n in {"agent.yaml", "agent.yml", "root_agent.yaml", "root_agent.yml"}}
    if len(root_files) != 1:
        raise ValueError("Exactly one root agent YAML is required")
    cfg = entries["agent.yaml"].decode("utf-8")
    model = re.search(r"(?m)^model:\s*(\S+)\s*$", cfg)
    if not model or model.group(1) not in MODEL_IDS:
        raise ValueError("Unexpected model, use a competition-supported Gemma 4 variant")
    names = set(re.findall(r"(?m)^\s*-\s*([a-z_]+)\s*$", cfg))
    if not names or names - TOOLS or "submit_patch" not in names:
        raise ValueError("Unsupported tools or missing submit_patch")
    for name, content in entries.items():
        if name.endswith((".yaml", ".yml")):
            for target in re.findall(r"!include\s+([^\s]+)", content.decode("utf-8")):
                rel = (Path(name).parent / target)
                if rel.is_absolute() or ".." in rel.parts or rel.as_posix() not in entries:
                    raise ValueError(f"Invalid YAML include in {name}: {target}")
    return {"model": model.group(1), "tools": sorted(names), "files": sorted(entries)}


def build(submission_dir: Path, output: Path) -> dict:
    entries = collect(submission_dir)
    details = validate(entries)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, raw in entries.items():
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, raw)
    with zipfile.ZipFile(output) as archive:
        if set(archive.namelist()) != set(entries) or archive.testzip() is not None:
            raise ValueError("Archive verification failed")
    return {"path": str(output), **details, "bytes": output.stat().st_size}


def make_kaggle_notebook(submission_dir: Path, output: Path) -> None:
    """Offline Kaggle cell embeds only the vetted submission files, no pip or git."""
    import base64
    entries = collect(submission_dir)
    validate(entries)
    encoded = {k: base64.b64encode(v).decode("ascii") for k, v in entries.items()}
    source = (
        "# Self-contained Kaggle offline builder generated from repository submission/ files.\\n"
        "import base64, pathlib, zipfile\\n"
        f"SOURCE = {repr(encoded)}\\n"
        "out = pathlib.Path('/kaggle/working/submission.zip') if pathlib.Path('/kaggle/working').is_dir() else pathlib.Path('submission.zip')\\n"
        "with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:\\n"
        "    for name, content in sorted(SOURCE.items()):\\n"
        "        z.writestr(name, base64.b64decode(content))\\n"
        "with zipfile.ZipFile(out) as z:\\n"
        "    assert 'agent.yaml' in z.namelist()\\n"
        "    assert z.testzip() is None\\n"
        "    print('Built', out, 'with', len(z.namelist()), 'configuration files:', z.namelist())\\n"
    )
    # Turn escaped newline markers into executable notebook source lines.
    source = source.replace("\\n", "\n")
    notebook = {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
        "cells": [
            {"cell_type": "markdown", "metadata": {}, "source": [
                "# GEMMA4 Kaggle Submission Builder\n",
                "Generated from the checked-in `submission/` directory. Works with Kaggle internet disabled. "
                "Run All and attach `/kaggle/working/submission.zip`. This builds the candidate archive, "
                "but does not run the official evaluation harness or measure accuracy.\n"]},
            {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": source.splitlines(True)}
        ]
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(notebook, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--submission-dir", type=Path, default=ROOT_DIR / "submission")
    ap.add_argument("--output", type=Path, default=ROOT_DIR / "artifacts" / "submission.zip")
    ap.add_argument("--notebook", type=Path, default=ROOT_DIR / "notebooks" / "kaggle_submit.ipynb")
    args = ap.parse_args()
    result = build(args.submission_dir, args.output)
    make_kaggle_notebook(args.submission_dir, args.notebook)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
