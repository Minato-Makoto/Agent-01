import json

from agentforge.session import SessionManager


def test_load_legacy_session_and_persist_migrated_schema(tmp_path):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    session_path = sessions_dir / "legacy123.json"

    legacy_payload = {
        "id": "legacy123",
        "created_at": 1,
        "updated_at": 2,
        "summary": "",
        "messages": [
            {"role": "user", "content": "open file"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call-1",
                        "function": {"name": "read_file", "arguments": {"path": "C:/a.txt"}},
                    }
                ],
            },
        ],
    }
    session_path.write_text(json.dumps(legacy_payload, ensure_ascii=False), encoding="utf-8")

    manager = SessionManager(str(sessions_dir))
    loaded = manager.load_session("legacy123")
    assert loaded is not None
    assert loaded.schema_version == 2
    assert loaded.id == "legacy123"
    assert any(m.role == "user" and m.content == "open file" for m in loaded.messages)
    assert any(
        m.role == "tool" and m.tool_call_id == "call-1" and m.synthetic is True
        for m in loaded.messages
    )

    # Ensure migrated payload was persisted back to disk.
    persisted = json.loads(session_path.read_text(encoding="utf-8"))
    assert persisted["schema_version"] == 2
    assert any(
        msg.get("role") == "tool" and msg.get("tool_call_id") == "call-1" and msg.get("synthetic")
        for msg in persisted["messages"]
    )
