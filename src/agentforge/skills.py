"""
AgentForge — SkillLoader for MMORPG-style skill system.

3-tier priority: workspace > user config > builtin
Dynamic activation/deactivation of skills and their tools.
Generates status panel for system prompt.
"""

import os
import re
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

try:
    import yaml
except ImportError:
    yaml = None

# Skill name validation: allow alphanumeric, spaces, hyphens, underscores
# Must NOT contain XML-dangerous chars (<, >, &, ", ')
_SKILL_NAME_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9 _-]*$')
_MAX_SKILL_NAME_LEN = 64
_MAX_SKILL_DESC_LEN = 1024


def _escape_xml(s: str) -> str:
    """Escape XML special characters (PicoClaw loader.go:324)."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


@dataclass
class SkillInfo:
    """Metadata about a discovered skill."""
    name: str
    description: str
    skill_file: str  # absolute path to SKILL_xxx.md
    folder: str  # skill folder name
    tools: List[str]  # tool names listed in frontmatter
    module: str = ""  # Python module path (e.g. "builtin_tools.file_ops")
    active: bool = False
    source: str = ""  # "workspace", "user", or "builtin"


class SkillLoader:
    """Discovers and manages skills with 3-tier priority."""

    def __init__(self, workspace_dir: str, user_config_dir: str = "", builtin_dir: str = ""):
        self._workspace_dir = Path(workspace_dir)
        self._user_config_dir = Path(user_config_dir) if user_config_dir else None
        self._builtin_dir = Path(builtin_dir) if builtin_dir else None
        self._skills: Dict[str, SkillInfo] = {}
        self._active_skills: set = set()

    def discover(self) -> Dict[str, SkillInfo]:
        """Discover all available skills from all tiers."""
        self._skills.clear()

        # Tier 3: builtin (lowest priority)
        if self._builtin_dir and self._builtin_dir.exists():
            self._scan_dir(self._builtin_dir, "builtin")

        # Tier 2: user config (overrides builtin)
        if self._user_config_dir and self._user_config_dir.exists():
            self._scan_dir(self._user_config_dir, "user")

        # Tier 1: workspace (highest priority)
        skills_dir = self._workspace_dir / "skills"
        if skills_dir.exists():
            self._scan_dir(skills_dir, "workspace")

        return self._skills

    def get_skill(self, name: str) -> Optional[SkillInfo]:
        """Get a skill by name (case-insensitive)."""
        name_lower = name.lower()
        for skill in self._skills.values():
            if skill.name.lower() == name_lower:
                return skill
        return None

    def activate(self, skill_name: str) -> Optional[SkillInfo]:
        """Mark a skill as active."""
        skill = self.get_skill(skill_name)
        if skill:
            skill.active = True
            self._active_skills.add(skill.name)
        return skill

    def deactivate(self, skill_name: str) -> Optional[SkillInfo]:
        """Mark a skill as inactive."""
        skill = self.get_skill(skill_name)
        if skill:
            skill.active = False
            self._active_skills.discard(skill.name)
        return skill

    def get_active_skills(self) -> List[SkillInfo]:
        """Get all active skills."""
        return [s for s in self._skills.values() if s.active]

    def get_all_skills(self) -> List[SkillInfo]:
        """Get all discovered skills."""
        return list(self._skills.values())

    def build_skills_xml(self) -> str:
        """Generate XML skills summary for system prompt (PicoClaw/OpenClaw pattern).
        
        IMPORTANT: Inactive skills do NOT list their tool names — this prevents
        the LLM from trying to call tools before activating the skill.
        """
        if not self._skills:
            return ""

        lines = ["<available_skills>"]

        for skill in self._skills.values():
            lines.append("  <skill>")
            lines.append(f"    <name>{_escape_xml(skill.name)}</name>")
            lines.append(f"    <description>{_escape_xml(skill.description)}</description>")
            lines.append(f"    <location>{_escape_xml(skill.skill_file)}</location>")
            if skill.active:
                lines.append(f"    <tools>{_escape_xml(', '.join(skill.tools))}</tools>")
                lines.append("    <status>ACTIVE</status>")
            else:
                lines.append(f"    <status>NOT ACTIVE — use read_file on the location to activate</status>")
            lines.append("  </skill>")

        lines.append("</available_skills>")
        return "\n".join(lines)

    def build_status_panel(self) -> str:
        """Backward-compatible alias for build_skills_xml()."""
        return self.build_skills_xml()

    def find_skill_by_file(self, file_path: str) -> Optional[SkillInfo]:
        """Find which skill a SKILL_xxx.md file belongs to."""
        file_path = str(Path(file_path).resolve())
        for skill in self._skills.values():
            if str(Path(skill.skill_file).resolve()) == file_path:
                return skill
        return None

    def _scan_dir(self, skills_dir: Path, source: str) -> None:
        """Scan a directory for skill folders containing SKILL_xxx.md files."""
        if not skills_dir.is_dir():
            return

        for child in skills_dir.iterdir():
            if not child.is_dir():
                continue

            # Look for SKILL_xxx.md files
            for f in child.iterdir():
                if f.is_file() and f.name.startswith("SKILL_") and f.name.endswith(".md"):
                    skill_info = self._parse_skill_file(f, child.name, source)
                    if skill_info:
                        # Higher priority source overrides lower
                        self._skills[skill_info.name] = skill_info

    def _parse_skill_file(self, path: Path, folder: str, source: str) -> Optional[SkillInfo]:
        """Parse a SKILL_xxx.md file to extract metadata."""
        if yaml is None:
            logger.warning("PyYAML is not installed; cannot parse skill metadata: %s", path)
            return None
        try:
            content = path.read_text(encoding="utf-8")

            # Extract YAML frontmatter
            match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
            if not match:
                return None

            frontmatter = yaml.safe_load(match.group(1))
            if not frontmatter or "name" not in frontmatter:
                return None

            name = str(frontmatter["name"])
            description = str(frontmatter.get("description", ""))
            tools = [str(t) for t in frontmatter.get("tools", []) if isinstance(t, str)]
            module = str(frontmatter.get("module", "")).strip()

            # Validate skill name (PicoClaw loader.go:14,33)
            if not _SKILL_NAME_RE.match(name):
                return None  # Invalid name format
            if len(name) > _MAX_SKILL_NAME_LEN:
                return None  # Name too long
            if len(description) > _MAX_SKILL_DESC_LEN:
                description = description[:_MAX_SKILL_DESC_LEN]  # Truncate

            return SkillInfo(
                name=name,
                description=description,
                skill_file=str(path.resolve()),
                folder=folder,
                tools=tools,
                module=module,
                source=source,
            )
        except (OSError, UnicodeDecodeError, ValueError, TypeError):
            return None
