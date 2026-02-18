"""
AgentForge — MemoryStore for persistent agent memory.

Manages:
- Long-term memory: workspace/memory/MEMORY.md
- Daily notes: workspace/memory/YYYYMM/YYYYMMDD.md
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class MemoryStore:
    """Manages persistent memory for the agent."""

    def __init__(self, workspace: str):
        self._workspace = Path(workspace).resolve()
        self._memory_dir = self._workspace / "memory"
        self._memory_file = self._memory_dir / "MEMORY.md"
        self._memory_dir.mkdir(parents=True, exist_ok=True)

    def read_long_term(self) -> str:
        """Read the long-term memory (MEMORY.md)."""
        if self._memory_file.exists() and self._memory_file.is_file():
            return self._safe_read(self._memory_file)
        return ""

    def write_long_term(self, content: str) -> None:
        """Write content to the long-term memory file."""
        self._atomic_write(self._memory_file, content)

    def read_today(self) -> str:
        """Read today's daily note."""
        today_file = self._get_today_file()
        if today_file.exists() and today_file.is_file():
            return self._safe_read(today_file)
        return ""

    def append_today(self, content: str) -> None:
        """Append content to today's daily note."""
        today_file = self._get_today_file()
        today_file.parent.mkdir(parents=True, exist_ok=True)

        if today_file.exists():
            existing = self._safe_read(today_file)
            new_content = existing + "\n" + content
        else:
            header = f"# {datetime.now().strftime('%Y-%m-%d')}\n\n"
            new_content = header + content

        self._atomic_write(today_file, new_content)

    def get_recent_daily_notes(self, days: int = 3) -> str:
        """Get daily notes from the last N days."""
        notes = []
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime("%Y%m%d")
            month_dir = date_str[:6]
            file_path = self._memory_dir / month_dir / f"{date_str}.md"
            if file_path.exists() and file_path.is_file():
                notes.append(self._safe_read(file_path))

        if not notes:
            return ""
        return "\n\n---\n\n".join(notes)

    def get_memory_context(self) -> str:
        """Get formatted memory context for the system prompt."""
        parts = []

        long_term = self.read_long_term()
        if long_term and long_term.strip() != "# Long-term Memory":
            parts.append("## Long-term Memory\n\n" + long_term)

        recent = self.get_recent_daily_notes(3)
        if recent:
            parts.append("## Recent Daily Notes\n\n" + recent)

        if not parts:
            return ""

        return "\n\n---\n\n".join(parts)

    def _get_today_file(self) -> Path:
        """Get the path to today's daily note file."""
        today = datetime.now().strftime("%Y%m%d")
        month_dir = today[:6]
        return self._memory_dir / month_dir / f"{today}.md"

    def _safe_read(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning("Failed to read memory file '%s': %s", path, exc)
            return ""

    def _atomic_write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)
