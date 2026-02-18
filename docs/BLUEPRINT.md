# BLUEPRINT

## 1) Pham vi va trang thai audit

- Runtime chinh: `run.bat` (Windows-only, single launcher).
- Core source: `src/agentforge` + `src/builtin_tools`.
- Test suite: `src/tests`.
- `adb-mcp` la optional integration, khong phu thuoc de chay runtime core.
- Audit baseline da duoc dong; file `docs/AUDIT_BASELINE.md` da xoa.

### Ket qua chuan hoa root

1. Bo launcher phu trong `scripts/`, giu 1 diem vao duy nhat: `run.bat`.
2. Gop toan bo tai lieu van hanh/kien truc/trien khai vao 2 file:
   - `docs/BLUEPRINT.md`
   - `docs/TUTORIAL.md`
3. Loai bo co/flag launcher du thua (`SHOW_BANNER`, `AUTO_SETUP`, `CHECK_ONLY`, `NO_PAUSE`).

## 2) Kien truc runtime

Agent-01 su dung vong lap tool-calling co cau truc tren endpoint Chat Completions-compatible:

1. Build request tu conversation state hien tai.
2. Gui `messages` + tool definitions (neu co).
3. Parse assistant output.
4. Neu co tool call, thuc thi tool.
5. Append `role=tool` result kem `tool_call_id`.
6. Lap lai cho den khi assistant tra text cuoi.

## 3) Chien luoc provider va compatibility

### Request contract chinh

- `model`
- `messages`
- token cap field:
  - `max_completion_tokens` cho OpenAI `o-series`
  - `max_tokens` cho model/provider khac
- `temperature`, `top_p`
- optional: `tools`, `tool_choice`, `parallel_tool_calls`, `response_format`
- optional reasoning control:
  - `reasoning_effort` (OpenAI-style)
  - `reasoning_format` (local/third-party)

### Fallback ladder (degrade co kiem soat)

Khi provider tu choi field, runtime retry theo thu tu:

1. `tools` + `tool_choice` (+ `parallel_tool_calls`)
2. `parallel_tool_calls`
3. `response_format`
4. token cap fallback (`max_completion_tokens` <-> `max_tokens`)
5. `reasoning_effort`
6. `reasoning_format`
7. `stream`
8. `grammar`
9. `stop`

## 4) Session va transcript

- Session schema version: `2`.
- Transcript cu duoc migrate + repair khi load.
- Pairing tool-call/tool-result duoc giu nhat quan trong runtime append path.

## 5) Module map (`src/agentforge`)

- `contracts.py`: dataclass contracts chia se.
- `llm_inference.py`: transport + compatibility fallback.
- `agent_core.py`: orchestration loop.
- `tool_loop.py`: guard va anti-loop logic.
- `tools.py`: registry + OpenAI-compatible schema export.
- `session.py` / `session_repair.py`: persistence + repair/migration.
- `prompting.py` / `schema_normalizer.py`: provider-safe payload shaping.
- `ui.py`: terminal UI stream/thinking/tool blocks.

## 6) Trien khai va CI blueprint

### Local quality gates

1. `python -m pytest -q`
2. `python -m compileall -q src`
3. `$env:PYTHONPATH='src'; python -m agentforge.cli --help`

### CI de xuat (Windows)

- Setup Python 3.10+
- Install deps deterministic tu `requirements.txt`
- Run lint/test/build checks
- Run CLI smoke command

## 7) Security va van hanh

- Khong commit secrets.
- API key duoc doc qua env name (`API_KEY_ENV`), vi du `OPENAI_API_KEY`.
- Workspace runtime tach rieng trong `workspace/`.
- `adb-mcp` giu optional, khong lam block startup.

## 8) Nguon tham chieu chinh

- PyPA `pyproject.toml`: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
- pip repeatable installs: https://pip.pypa.io/en/stable/topics/repeatable-installs/
- GitHub Actions Python: https://docs.github.com/en/actions/tutorials/build-and-test-code/python
- OpenAI migrate to Responses: https://platform.openai.com/docs/guides/migrate-to-responses
- OpenClaw concepts (duong dan dung):
  - https://docs.openclaw.ai/concepts/model-providers
  - https://docs.openclaw.ai/concepts/model-failover
