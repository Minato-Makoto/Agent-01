# Agent-01 (AgentForge Runtime)

Windows-first AI agent runtime. Entry duy nhat cho user: `run.bat`.

v1.1.1 highlights:
- Skill manifests standardized to `workspace/skills/<skill_id>/SKILL.md`
- Skill ID is canonical by folder name
- Native desktop control tools (`desktop_*`) via `computer-use-agents` skill
- Strict loop args wiring from launcher (`MAX_ITERATIONS`, `MAX_REPEATS`, `AGENT_TIMEOUT`)

## Quick start

1. Cai Python 3.10+.
2. Mo terminal tai root repo.
3. Chay:

```bat
run.bat
```

`run.bat` la launcher 1-file: tu kiem tra/install dependency, nhan tham so qua env, va chay `agentforge.cli`.

## Provider modes

- `PROVIDER=local`:
  - can `SERVER_EXE` (llama-server.exe)
  - can `MODEL_PATH` (.gguf)
- `PROVIDER=openai_compatible`:
  - can `BASE_URL`, `MODEL_ID`, `API_KEY_ENV`

## Browser visibility

- Hien browser de user view:
  - `set AGENTFORGE_BROWSER_HEADLESS=0`

## Desktop control

- Bat/tat desktop tools:
  - `set AGENTFORGE_DESKTOP_CONTROL=1` (default on)

## Quality checks

```powershell
python -m pytest -q
python -m compileall -q src
$env:PYTHONPATH='src'; python -m agentforge.cli --help
```

## Docs

- [Blueprint (EN)](docs/BLUEPRINT_EN.md)
- [Blueprint (VI)](docs/BLUEPRINT_VI.md)
- [Tutorial (EN)](docs/TUTORIAL_EN.md)
- [Tutorial (VI)](docs/TUTORIAL_VI.md)
- [Changelog](CHANGELOG.md)

---

## Credits & Special Thanks

Agent-01 would not exist without the following tools, platforms, and AI systems that contributed to its development:

### Design Pattern References
- **PicoClaw** (Go) — Dual-output tool result pattern, web search provider pattern, skill loader validation, agent loop compression.
- **OpenClaw** (TypeScript) — Context window pruner pattern, transcript policy sanitization.

### AI Development Partners
- **Google Gemini 3 & 3.1** — Core codebase architecture, module design, and iterative development.
- **Anthropic Claude Opus 4.6** — Code review, security hardening, and documentation refinement.
- **OpenAI Codex 5.3** — Automated code generation, batch implementation, and upgrade auditing.

### Development Environment
- **Visual Studio Code** — Primary IDE.
- **Antigravity by Google DeepMind** — AI-assisted pair programming agent.
- **llama.cpp** — Local inference engine powering the `PROVIDER=local` mode.

### Third-Party Modules
- **adb-mcp** by Mike Chambers (MIT License) — Adobe Creative Suite MCP integration (Photoshop, Premiere Pro, After Effects, InDesign, Illustrator).

### Open-Source Community
- The broader open-source AI agent community whose collective research, experiments, and shared knowledge made projects like Agent-01 possible.

> Without these building blocks, there is no Agent-01.
