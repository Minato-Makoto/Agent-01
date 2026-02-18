from agentforge.memory import MemoryStore


def test_memory_store_long_term_read_write(tmp_path):
    store = MemoryStore(str(tmp_path))
    store.write_long_term("hello memory")
    assert store.read_long_term() == "hello memory"


def test_memory_store_append_today_keeps_header_and_appends(tmp_path):
    store = MemoryStore(str(tmp_path))
    store.append_today("line one")
    store.append_today("line two")

    today = store.read_today()
    assert today.startswith("# ")
    assert "line one" in today
    assert "line two" in today


def test_memory_store_recent_daily_notes_collects_existing_files(tmp_path):
    store = MemoryStore(str(tmp_path))
    store.append_today("today-note")

    recent = store.get_recent_daily_notes(3)
    assert "today-note" in recent


def test_memory_store_atomic_write_does_not_leave_tmp_file(tmp_path):
    store = MemoryStore(str(tmp_path))
    store.write_long_term("atomic content")

    memory_dir = tmp_path / "memory"
    tmp_files = list(memory_dir.rglob("*.tmp"))
    assert tmp_files == []
