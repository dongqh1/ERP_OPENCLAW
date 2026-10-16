# PC Skills and Preferences Implementation Plan

> **For agentic workers:** Execute inline in the current authorized workspace. Keep the existing user changes intact; do not reset, stash, or commit unrelated files.

**Goal:** Load the two PC skills from their actual skill directories and persist PC-only user preferences in MongoDB, guarded so one-off task constraints are not saved as defaults.

**Architecture:** Point the PC main Agent and each PC subagent at the leaf directories containing `SKILL.md`. Add a small PC preference repository over a dedicated MongoDB collection, inject its values into the PC Agent context, and expose a schema-validated save tool that accepts updates only when the current user message explicitly expresses a durable preference.

**Tech Stack:** Python 3.11, LangChain tools/runtime, Pydantic, PyMongo, pytest, OpenSandbox skills.

## Global Constraints

- Keep automotive tools, skills, prompts, and preference namespace unchanged.
- Keep PC business data behind the existing PC MCP and Java service.
- Store durable PC preferences separately from conversational checkpoints and automotive memories.
- Do not save a one-time budget, requested component, or use case as a default.
- Run focused tests with `E:\anaconda\python.exe -m pytest`, adding the project `.venv\Lib\site-packages` and `src` directories to `PYTHONPATH` (the project venv does not include pytest).

---

### Task 1: Align PC skill declarations with the actual skill directories

**Files:**
- Modify: `src/agent/agents/pc_agent/agent.py`
- Modify: `src/agent/agents/pc_agent/prompt.yaml`
- Modify: `src/agent/agents/pc_agent/subagents/configs/pc_hardware_analyst.yaml`
- Modify: `src/agent/agents/pc_agent/subagents/configs/pc_build_planner.yaml`
- Test: `tests/test_pc_agent_setup.py`

**Interfaces:**
- Skill directories: `/skills/pc/analysis/pc-hardware-analysis/` and `/skills/pc/planning/pc-build-planning/`.
- The PC root policy remains `/skills/pc/AGENTS.md` and is loaded as memory, not declared as a skill directory.

- [x] **Step 1: Write a failing skill-path test.** Parse the Agent and subagent YAML declarations; assert every declared PC skill directory directly contains `SKILL.md` in the local skill tree.
- [x] **Step 2: Run the focused test and confirm it fails** because current declarations point at parent directories.
- [x] **Step 3: Change the main Agent and subagent declarations to the two leaf skill directories; update the prompt to name those paths.** Keep the relevant main skill-management directory only if it also directly contains `SKILL.md`.
- [x] **Step 4: Re-run the focused test and confirm it passes.**

### Task 2: Add validated, isolated PC preference persistence

**Files:**
- Create: `src/agent/agents/pc_agent/preferences.py`
- Modify: `src/agent/agents/pc_agent/agent.py`
- Modify: `src/agent/agents/pc_agent/prompt.yaml`
- Modify: `src/agent/config.py`
- Test: `tests/test_pc_preferences.py`

**Interfaces:**
- Collection: `langchain_db.pc_user_preferences`, uniquely keyed by `user_id`; the collection itself scopes records to the PC domain.
- Preference fields: default budget, preferred CPU/GPU brands, new/used preference, default use cases/resolution, preferred output/chart style, and confirmed owned components.
- Save tool: uses `ToolRuntime[ProcurementContext]` for the user identity; it does not accept a caller-supplied user ID.
- Durable-intent gate: a save is accepted only when the latest user message contains explicit persistence language such as “记住”“以后默认”“今后都”.

- [x] **Step 1: Write failing tests** for typed preference validation, user isolation, update merge behavior, and rejection of a one-time budget without durable-intent language.
- [x] **Step 2: Run the focused tests and confirm they fail** because the PC preference repository and tools did not yet exist.
- [x] **Step 3: Implement the repository** with a unique user index and `$set` updates; implement a read middleware and a save tool using runtime context. Use a dedicated collection and leave automotive storage untouched.
- [x] **Step 4: Register the PC-only middleware/tool and update the PC prompt** to apply loaded durable preferences, save only explicit long-term preferences, and keep ordinary task constraints in the current request.
- [x] **Step 5: Re-run focused tests and confirm they pass.**

### Task 3: Verify PC setup and existing regressions

**Files:**
- Test: `tests/test_pc_agent_setup.py`
- Test: `tests/test_pc_preferences.py`
- Existing regression suite: `tests/test_sandbox_lifecycle.py`, `tests/test_subagent_loader.py`, `tests/test_memory_update.py`

- [x] **Step 1: Run focused PC tests** for skill loading, preference validation, explicit-save intent, context injection, and user isolation.
- [x] **Step 2: Run related existing tests** for sandbox lifecycle, subagent loading, and generic memory updates.
- [x] **Step 3: Verify MongoDB create/read/update, user isolation, and cross-process persistence; remove the synthetic test record.**

**Verification results:** PC-focused suite: 9 passed; sandbox lifecycle: 10 passed; generic memory updates: 3 passed. PC Agent factory import succeeded with the project's `.env` loaded. A two-process MongoDB check confirmed preferences survive process restart and remain isolated by user. `tests/test_subagent_loader.py` has 2 unrelated failures in existing car/IT procurement assertions (`evaluate_it_equipment_procurement` tool mapping and an expected legacy system-prompt phrase); 2 other tests in that file passed.
