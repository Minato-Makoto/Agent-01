from agentforge.summarizer import Summarizer


def test_graceful_summarize_falls_back_when_llm_summary_raises():
    summarizer = Summarizer(max_tokens=128)
    messages = [
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "u2"},
        {"role": "assistant", "content": "a2"},
        {"role": "user", "content": "u3"},
        {"role": "assistant", "content": "a3"},
    ]

    def _boom(_: str) -> str:
        raise RuntimeError("llm unavailable")

    summary, remaining = summarizer.graceful_summarize(
        messages=messages,
        existing_summary="baseline",
        llm_fn=_boom,
    )

    assert "baseline" in summary
    assert "[Compressed" in summary
    assert len(remaining) == 4
