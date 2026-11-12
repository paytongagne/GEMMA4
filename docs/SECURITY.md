# Security model and limitations

The repository is partly a research prototype. It must not be used as a general secure executor for arbitrary repositories without additional isolation.

- Repository code, issue reports, and language-model output are untrusted. The standalone client only treats model output as a unified diff. It never evaluates returned Python code or treats LLM text as a shell command.
- Source patches are restricted to existing Python files, with no `../` traversal, symlinks, test-file rewrites, binary patches, or new files; then `git apply --check` is performed on a **temporary copy**.
- Actual `python -m pytest` and other test commands can execute arbitrary code. The local agent **does not run them by default**. The opt-in `--allow-local-tests` flag is for trusted local projects only. The Kaggle harness handles its own sandboxed execution.
- An OpenAI-compatible model endpoint defaults to localhost. Remote endpoints require explicit opt-in and HTTPS; user-supplied repository source may leave the host when enabled. Do not commit API keys; use environment variables.
- Prompts attempt to prevent instruction following from code comments and issue text, but prompts alone are not a security boundary.
- The package builder disallows symlinks, path traversal in YAML `!include`, and unsupported file extensions. It provides a static preflight only, not a substitute for the official contest compiler.
