# Objective
Upgrade the system to Version 1.1 with the following enhancements:
1. **Intelligent Session Continuation**: When context limits are reached, `Graceful Summarization` will create a new session, link it to the old session ID, and include a clear, revised prompt to the LLM so it knows it is continuing a previous session based on a summary. The JSON payload will include `previous_session_id`.
2. **Context Hydration**: Fix the bug where old sessions loaded from the disk do not populate the LLM's prompt context on startup.
3. **Tool Cleanup**: Remove the `calculator` and `message` tools from the codebase.
4. **Documentation**: Update the necessary docs (`docs/` and `workspace/`) to reflect these changes.

## Proposed Changes

---

### Core Architecture (`src/agentforge/`)

#### [MODIFY] [agent_core.py](file:///d:/Personal/MinatoZeroFace/AI%20Agent/Agent-01/src/agentforge/agent_core.py)
- **Session Loading Fix**: In `__init__` or `reset`, if `self.session_mgr.session` exists and has messages, iterate over `session.messages` and append them to `self.prompt.messages` so the LLM regains its memory when an old session is loaded.
- **Graceful Summarization LLM Hook**: In `_maybe_summarize_prompt_history`, pass an `llm_fn` (a wrapper around `self.llm.generate`) to `self.summarizer.graceful_summarize` so it actually uses the AI to summarize instead of the fallback text concat.
- **Session Branching**: When `graceful_summarize` returns a new summary, call a new method on `session_mgr` (e.g., `branch_session(summary)`) to start a new JSON file linked to the old one.

#### [MODIFY] [session.py](file:///d:/Personal/MinatoZeroFace/AI%20Agent/Agent-01/src/agentforge/session.py)
- **Schema Update**: Add an optional `previous_session_id: str = ""` field to `SessionData` to track the lineage.
- **Branching Logic**: Add a method `branch_session(self, summary: str, old_id: str)`. This will create a new session, set its `previous_session_id` to `old_id`, insert a system injection message ("This is a continuation of session X. Summary: Y"), and save it.

#### [MODIFY] [summarizer.py](file:///d:/Personal/MinatoZeroFace/AI%20Agent/Agent-01/src/agentforge/summarizer.py)
- **Prompt Revision**: Rewrite the LLM prompt inside `graceful_summarize` to explicitly state: "You are Agent-01. Context limit reached. Write a highly detailed summary... The new session will use this. To view the exact old history, the LLM can read the old session JSON file..."

---

### Built-in Tools (`src/builtin_tools/`)

#### [DELETE] [calculator.py](file:///d:/Personal/MinatoZeroFace/AI%20Agent/Agent-01/src/builtin_tools/calculator.py)
- Remove the calculator tool file entirely.

#### [DELETE] [send_message.py](file:///d:/Personal/MinatoZeroFace/AI%20Agent/Agent-01/src/builtin_tools/send_message.py)
- Remove the message tool file entirely. (Assuming the file is named something like `send_message.py` or similar in that directory).
- *Note: I will double-check the exact filenames of these tools before deletion.*

---

### Documentation (`docs/` & `workspace/`)

#### [MODIFY] [BLUEPRINT_EN.md](file:///d:/Personal/MinatoZeroFace/AI%20Agent/Agent-01/docs/BLUEPRINT_EN.md) & [BLUEPRINT_VI.md](file:///d:/Personal/MinatoZeroFace/AI%20Agent/Agent-01/docs/BLUEPRINT_VI.md)
- Update the **Context Management** section to describe the new v1.1 behavior: "Tier 1: Graceful Summarization now branches into a new session file, injecting the `previous_session_id` for traceability and seamless continuation."
- Remove references to the Calculator and Message tools.

## Verification Plan

### Automated/Manual Tests
1. **Context Hydration**: Run `run.bat --session <old_id>`, type a query referring to past context, and verify the model knows the context without looking it up.
2. **Graceful Summarization Branching**: Use the simulated script or lower the token limit drastically to force a Tier 1 compression. Verify in the `workspace/sessions/` folder that a *new* session ID is created, and its JSON contains `previous_session_id`.
3. **Tool Deletion**: Run the UI and check the active tools list; ensure `calculator` and `message` are gone and no import errors occur.
