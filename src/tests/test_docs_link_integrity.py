from pathlib import Path


def _iter_markdown_files(root: Path):
    skip_prefixes = (
        "reference/",
        "adb-mcp/",
        "llama-",
    )
    for path in root.rglob("*.md"):
        rel = path.relative_to(root).as_posix()
        if any(rel.startswith(prefix) for prefix in skip_prefixes):
            continue
        yield path, rel


def test_openclaw_docs_routes_do_not_use_known_bad_paths():
    root = Path(__file__).resolve().parents[2]
    bad_routes = (
        "https://docs.openclaw.ai/platform/model-providers",
        "https://docs.openclaw.ai/ai-agents/model-failover",
    )

    offenders = []
    for path, rel in _iter_markdown_files(root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for route in bad_routes:
            if route in text:
                offenders.append((rel, route))

    assert offenders == []


def test_core_docs_use_current_openclaw_concepts_routes():
    root = Path(__file__).resolve().parents[2]
    model_compat = (root / "docs" / "MODEL_COMPATIBILITY.md").read_text(encoding="utf-8")

    assert "https://docs.openclaw.ai/concepts/model-providers" in model_compat
    assert "https://docs.openclaw.ai/concepts/model-failover" in model_compat
