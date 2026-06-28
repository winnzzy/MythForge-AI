# OpenMontage — Risk Analysis

## Overview

This document identifies technical risks, coupling patterns, potential bottlenecks, dangerous files, safe files, and refactoring opportunities in the OpenMontage codebase. Risks are categorized by severity and likelihood.

---

## Risk Categories

| Category | Severity | Description |
|----------|----------|-------------|
| **CRITICAL** | 🔴 | Could halt production or cause data loss |
| **HIGH** | 🟠 | Significant impact on reliability or maintainability |
| **MEDIUM** | 🟡 | Moderate impact, workaround available |
| **LOW** | 🟢 | Minor inconvenience, easy to fix |

---

## Technical Debt

### TD-1: No Formal Agent Interface
- **Severity**: 🟠 HIGH
- **Location**: Framework-wide (no `Agent` class)
- **Description**: Agent behavior is defined entirely in Markdown skill files. There is no programmatic agent interface, no typed inputs/outputs, no runtime validation of agent behavior.
- **Impact**: Impossible to unit test agent logic. Behavior changes require editing prose, not code. No type safety.
- **Mitigation**: Accept Markdown-first design. Add JSON Schema validation for all artifact handoffs.

### TD-2: Tool Registry Discovery is Implicit
- **Severity**: 🟡 MEDIUM
- **Location**: `tool_registry.py`
- **Description**: Tools are discovered by scanning all Python files in `tools/`. There is no explicit registration, no manifest, no dependency declaration.
- **Impact**: Adding a broken tool file can crash the entire registry. No way to know which tools are available without running discovery.
- **Mitigation**: Add a `tools/manifest.json` or require explicit registration in `__init__.py` files.

### TD-3: No Dependency Version Pinning
- **Severity**: 🟠 HIGH
- **Location**: `requirements.txt`, `remotion-composer/package.json`
- **Description**: Python dependencies use `latest` (no pinned versions). No `requirements.lock` or `package-lock.json` verified in repo.
- **Impact**: Builds are not reproducible. A dependency update can break the entire toolchain without warning.
- **Mitigation**: Pin all dependencies to exact versions. Generate and commit lock files.

### TD-4: No Automated Test Coverage for Tools
- **Severity**: 🟠 HIGH
- **Location**: `tests/` directory
- **Description**: Test infrastructure exists (`pytest`, `tests/`) but coverage for individual tools is unclear. Most tools make external API calls that are difficult to mock.
- **Impact**: Changes to tools cannot be validated without running against live APIs (costly, slow, flaky).
- **Mitigation**: Add mock-based unit tests for all tools. Use VCR.py or responses library for HTTP mocking.

### TD-5: Dual Ecosystem Complexity
- **Severity**: 🟡 MEDIUM
- **Location**: Python tools + TypeScript Remotion
- **Description**: The framework spans Python and TypeScript/Node.js. Two build systems, two dependency trees, two runtime environments.
- **Impact**: Developers need expertise in both ecosystems. CI/CD must handle both. Debugging spans two languages.
- **Mitigation**: Document clear boundaries. Python handles tool execution, TypeScript handles rendering. No cross-language calls at runtime (only via CLI).

### TD-6: No Error Recovery in Pipeline Execution
- **Severity**: 🟡 MEDIUM
- **Location**: Pipeline execution (agent-driven)
- **Description**: If a tool fails mid-pipeline, recovery depends on the AI agent's judgment and checkpoint state. There is no automatic retry, no circuit breaker, no dead-letter queue.
- **Impact**: A transient API failure can waste an entire pipeline run. The agent may not know how to recover gracefully.
- **Mitigation**: Add retry logic to `BaseTool.run()`. Implement checkpoint-aware recovery in pipeline execution.

### TD-7: Cost Tracking is Post-Hoc
- **Severity**: 🟡 MEDIUM
- **Location**: `lib/cost_tracker.py`
- **Description**: Costs are tracked after tool execution via `ToolResult.cost_usd`. There is no pre-flight cost estimation, no real-time budget enforcement.
- **Impact**: Budget overruns are detected after the fact. A runaway tool can exceed the budget before the agent notices.
- **Mitigation**: Add pre-flight cost estimation. Implement hard budget caps in `BaseTool.run()`.

---

## Coupling Analysis

### Tight Coupling

| Coupling | Between | Risk | Mitigation |
|----------|---------|------|------------|
| Compose Director ↔ Render Runtimes | `compose-director.md` ↔ `video_compose.py`, `hyperframes_compose.py` | HIGH — Adding new runtime requires updating skill | Define runtime interface contract |
| Asset Director ↔ All Tools | `asset-director.md` ↔ 40+ tools | HIGH — Skill must know all tool names | Use tool categories, not names |
| Pipeline YAML ↔ Skill Paths | `pipeline_defs/*.yaml` ↔ `skills/*.md` | MEDIUM — Moving skills breaks pipelines | Use relative paths, validate at load |
| Scene Plan ↔ Remotion Components | `scene_plan.json` ↔ `src/scenes/*.tsx` | MEDIUM — Adding scene type requires both sides | Define scene type registry |
| Playbook ↔ Scene Components | `playbooks/*.json` ↔ `src/scenes/*.tsx` | LOW — Playbook is consumed by agent | Document expected fields |

### Loose Coupling (Good)

| Coupling | Between | Benefit |
|----------|---------|---------|
| Tools ↔ Skills | Tools are invoked by name, skills define when | Tools can be replaced independently |
| Pipelines ↔ Tools | Pipeline YAML references tools, doesn't import them | New tools auto-discovered |
| Playbooks ↔ Code | Playbooks are JSON, consumed by agent reasoning | Visual style changes don't touch code |
| Knowledge ↔ Skills | Knowledge files are loaded on-demand | Domain expertise is modular |

---

## Potential Bottlenecks

### BOTTLENECK-1: WhisperX Transcription
- **Location**: `tools/analysis/transcriber.py`
- **Issue**: WhisperX requires GPU for real-time transcription. CPU-only mode is 10-50x slower.
- **Impact**: Long videos (>10 min) can take 30+ minutes to transcribe on CPU.
- **Mitigation**: Use cloud transcription API (Google Speech-to-Text, AssemblyAI) as fallback.

### BOTTLENECK-2: Remotion Rendering
- **Location**: `remotion-composer/`
- **Issue**: Remotion renders frame-by-frame. Complex scenes with many layers are slow.
- **Impact**: A 60-second video at 30fps = 1,800 frames. Complex scenes can take 5-15 minutes.
- **Mitigation**: Use Remotion's `--concurrency` flag. Simplify scene components. Consider FFmpeg for simple compositions.

### BOTTLENECK-3: API Rate Limits
- **Location**: All external API tools
- **Issue**: Image/video generation APIs have rate limits (typically 10-100 requests/minute).
- **Impact**: Generating 20+ images for a single video can hit rate limits.
- **Mitigation**: Add rate limiting to `BaseTool.run()`. Implement exponential backoff. Use multiple API keys.

### BOTTLENECK-4: Asset Storage
- **Location**: `projects/<name>/assets/`
- **Issue**: All assets are stored locally. No CDN, no cloud storage integration.
- **Impact**: Large projects (100+ assets) consume significant disk space. No sharing between machines.
- **Mitigation**: Add S3/GCS storage option. Implement asset cleanup after render.

### BOTTLENECK-5: AI Agent Context Window
- **Location**: Skill documents
- **Issue**: The AI agent has a finite context window. Loading multiple skill files + artifacts can exceed it.
- **Impact**: Complex pipelines with many stages may hit context limits, causing the agent to lose track of earlier decisions.
- **Mitigation**: Use checkpoint state to offload context. Minimize skill file verbosity. Use artifact references instead of inline data.

---

## Dangerous Files

Files that should be modified with extreme caution or never modified:

| File | Risk | Reason |
|------|------|--------|
| `AGENT_GUIDE.md` | 🔴 CRITICAL | Defines all agent behavior. Changes affect every pipeline. |
| `tools/base_tool.py` | 🔴 CRITICAL | Base class for all tools. Breaking change breaks everything. |
| `tools/tool_registry.py` | 🔴 CRITICAL | Tool discovery mechanism. Failure here = no tools available. |
| `lib/pipeline.py` | 🟠 HIGH | Pipeline loading and execution. Changes affect all pipelines. |
| `lib/artifact_manager.py` | 🟠 HIGH | Artifact save/load. Data loss risk if broken. |
| `lib/cost_tracker.py` | 🟠 HIGH | Budget enforcement. Failure = unlimited spending. |
| `remotion-composer/src/Root.tsx` | 🟠 HIGH | Composition registry. Breaking change = no rendering. |
| `pipeline_defs/animated-explainer.yaml` | 🟡 MEDIUM | Primary pipeline definition. Changes affect default behavior. |
| `skills/pipelines/explainer/executive-producer.md` | 🟡 MEDIUM | Core orchestration logic. Changes affect pipeline flow. |

---

## Safe Files

Files that can be modified freely:

| File | Risk | Reason |
|------|------|--------|
| `knowledge/*.md` | 🟢 LOW | Knowledge files are additive, no code impact |
| `playbooks/*.json` | 🟢 LOW | Style definitions, consumed by agent reasoning |
| `skills/meta/*.md` | 🟢 LOW | Meta skills are optional enhancements |
| `.env.example` | 🟢 LOW | Template file, no runtime impact |
| `tests/*.py` | 🟢 LOW | Test files don't affect production |
| `docs/*.md` | 🟢 LOW | Documentation only |
| `demo/` | 🟢 LOW | Demo assets and scripts |
| New files in `tools/` | 🟢 LOW | Auto-discovered, additive only |
| New files in `skills/` | 🟢 LOW | Referenced by pipeline YAML, additive |
| New files in `pipeline_defs/` | 🟢 LOW | New pipeline definitions, don't affect existing |

---

## Refactoring Opportunities

### REFACTOR-1: Extract Tool Interface
- **Current**: Each tool extends `BaseTool` with informal `run()` signature
- **Proposed**: Define formal `ToolInterface` with typed inputs/outputs
- **Benefit**: Type safety, auto-documentation, easier testing
- **Risk**: LOW — additive change, doesn't break existing tools

### REFACTOR-2: Add Configuration Manager
- **Current**: Configuration spread across YAML, env, JSON
- **Proposed**: Single `ConfigManager` class that merges all sources
- **Benefit**: Validation, defaults, environment profiles
- **Risk**: MEDIUM — requires updating config access patterns

### REFACTOR-3: Implement Asset Cache
- **Current**: Every tool invocation generates new assets
- **Proposed**: Content-addressed cache with TTL
- **Benefit**: Cost reduction, faster iteration, offline capability
- **Risk**: LOW — additive layer, doesn't change existing behavior

### REFACTOR-4: Add Provider Health Checks
- **Current**: Providers fail at invocation time
- **Proposed**: Pre-flight health check for all configured providers
- **Benefit**: Fail fast, better error messages, provider status dashboard
- **Risk**: LOW — additive check, doesn't change existing behavior

### REFACTOR-5: Standardize Artifact Schema
- **Current**: Artifacts are validated by JSON Schema (some by Pydantic)
- **Proposed**: Unified validation using Pydantic models for all artifacts
- **Benefit**: Type safety, better error messages, auto-documentation
- **Risk**: MEDIUM — requires updating validation logic

### REFACTOR-6: Add Pipeline State Machine
- **Current**: Pipeline state managed by agent reasoning + checkpoint files
- **Proposed**: Formal state machine with defined transitions
- **Benefit**: Predictable behavior, easier debugging, resume guarantees
- **Risk**: MEDIUM — requires careful migration from agent-driven to code-driven state

### REFACTOR-7: Extract Render Runtime Interface
- **Current**: Each runtime (Remotion, HyperFrames, FFmpeg) has different invocation
- **Proposed**: Common `RenderRuntime` interface with standard methods
- **Benefit**: Easier to add new runtimes, consistent error handling
- **Risk**: MEDIUM — requires updating compose-director and all runtime tools

---

## Risk Heat Map

```
                    LOW IMPACT          HIGH IMPACT
                ┌───────────────────┬───────────────────┐
   HIGH         │                   │ TD-3: No version  │
   LIKELIHOOD   │  B-4: Asset       │ pinning            │
                │  storage          │ B-5: Context       │
                │                   │ window limits      │
                ├───────────────────┼───────────────────┤
   LOW          │ TD-2: Implicit    │ TD-1: No agent     │
   LIKELIHOOD   │ registry          │ interface           │
                │ TD-5: Dual        │ TD-4: No tool      │
                │ ecosystem         │ tests              │
                │                   │ B-1: WhisperX      │
                │                   │ B-2: Remotion      │
                └───────────────────┴───────────────────┘
```

---

## Key Observations

1. **Highest risk area**: Dependency management — no version pinning creates build fragility
2. **Biggest bottleneck**: Remotion rendering for complex scenes
3. **Best mitigation**: The provider fallback system is excellent — no single point of failure
4. **Safest extension**: Adding new knowledge files, playbooks, and tools
5. **Most dangerous modification**: Changing `AGENT_GUIDE.md` or `base_tool.py`
6. **Immediate priority**: Pin dependency versions and add tool unit tests