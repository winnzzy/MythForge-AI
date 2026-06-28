# OpenMontage — Agent Analysis

## Overview

OpenMontage does not have traditional software agents (classes implementing an Agent interface). Instead, **"agents" are roles the AI assistant assumes** by reading Markdown skill files. Each skill file defines responsibilities, inputs, outputs, guidelines, and quality checklists for a specific role in the production pipeline.

The AI agent (Claude, GPT, Cursor) is the **single runtime agent** that reads skill documents and executes tool calls. Skills are the behavioral contracts.

---

## Agent Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AI AGENT (Claude/GPT/Cursor)              │
│                    (Single runtime process)                  │
└──────────────────────────┬──────────────────────────────────┘
                           │ reads
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    SKILL DOCUMENTS (Markdown)                │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Layer 1   │  │   Layer 2   │  │   Layer 3           │ │
│  │ AGENT_GUIDE │  │  PROJECT_   │  │ Skills (core/,      │ │
│  │    .md      │  │  CONTEXT.md │  │ creative/, meta/,   │ │
│  │             │  │             │  │ pipelines/)         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Layer 1** (`AGENT_GUIDE.md`): Core operating rules — always loaded. Defines how the agent should behave, when to ask questions, how to use tools.

**Layer 2** (`PROJECT_CONTEXT.md`): Project philosophy and context — loaded when the agent needs deeper understanding of design decisions.

**Layer 3** (Skills): Task-specific instructions — loaded on-demand based on the current pipeline stage.

---

## Executive Producer Agent

| Attribute | Value |
|-----------|-------|
| **File** | `skills/pipelines/explainer/executive-producer.md` (canonical), similar files in each pipeline directory |
| **Responsibilities** | Orchestrate entire pipeline serially, maintain cumulative state, enforce budget, review each stage output, manage revision loops |
| **Inputs** | User topic, pipeline definition, playbook |
| **Outputs** | Final rendered video + publish_log |
| **Dependencies** | All stage-director skills, all artifact schemas, playbook, tool registry |
| **Can Be Replaced?** | NO — This is the core orchestration logic |
| **Can Be Extended?** | YES — New pipelines can define their own EP variants |
| **Should Remain Untouched?** | YES for explainer EP; new pipelines should create their own |

**Key Behaviors**:
- Maintains `EP_STATE` object across all stages
- Carries `research_brief`, `selected_concept`, `production_plan`, `approved_budget_usd` forward
- Tracks `narration_durations`, `style_anchors`, `revision_counts`, `issues_log`
- Enforces approval gate at proposal stage
- Manages budget reallocation when early stages overspend
- Can send any stage back for revision without re-running everything
- Validates A/V sync before final render

---

## Stage Director Agents

Each pipeline stage has a corresponding "director" skill that the agent loads and follows.

### Research Director

| Attribute | Value |
|-----------|-------|
| **File** | `skills/pipelines/explainer/research-director.md` (and equivalents per pipeline) |
| **Responsibilities** | Web search for content landscape, gather data points, identify audience questions, discover unique angles |
| **Inputs** | User topic/idea |
| **Outputs** | `research_brief` artifact (validated against `schemas/research_brief.json`) |
| **Dependencies** | None (agent reasoning only) |
| **Cost** | $0.00 |
| **Can Be Replaced?** | YES — Could be extended with web scraping tools |
| **Can Be Extended?** | YES — Add competitor analysis, SEO keyword research |
| **Should Remain Untouched?** | Core logic safe to extend |

### Proposal Director

| Attribute | Value |
|-----------|-------|
| **File** | `skills/pipelines/explainer/proposal-director.md` |
| **Responsibilities** | Generate concept options, create production plan, select playbook, present cost/quality tradeoffs, lock render_runtime |
| **Inputs** | `research_brief` |
| **Outputs** | `proposal_packet` artifact (includes approval gate) |
| **Dependencies** | Playbook files, tool registry (for cost estimation) |
| **Cost** | $0.00 |
| **Can Be Replaced?** | NO — Contains critical decision logic (runtime locking, budget approval) |
| **Can Be Extended?** | YES — Add more concept templates, A/B testing hooks |
| **Should Remain Untouched?** | Approval gate logic should never be bypassed |

### Script Director

| Attribute | Value |
|-----------|-------|
| **File** | `skills/pipelines/explainer/script-director.md` |
| **Responsibilities** | Write narration script, add enhancement_cues, target word count, include speaker directions |
| **Inputs** | `proposal_packet`, `research_brief` |
| **Outputs** | `script` artifact |
| **Dependencies** | None (agent reasoning only) |
| **Cost** | $0.00 |
| **Can Be Replaced?** | YES — Could integrate with scriptwriting APIs |
| **Can Be Extended?** | YES — Add style templates, tone guides, brand voice |
| **Should Remain Untouched?** | Core structure safe to extend |

### Scene Director

| Attribute | Value |
|-----------|-------|
| **File** | `skills/pipelines/explainer/scene-director.md` |
| **Responsibilities** | Map script to visual scenes, assign scene types, define required_assets, ensure visual variety |
| **Inputs** | `script`, `proposal_packet` |
| **Outputs** | `scene_plan` artifact |
| **Dependencies** | Knowledge of available scene types (from Remotion components) |
| **Cost** | $0.00 |
| **Can Be Replaced?** | YES — Could add automated scene planning |
| **Can Be Extended?** | YES — Add new scene types, visual variety rules |
| **Should Remain Untouched?** | Scene type registry awareness is critical |

### Asset Director

| Attribute | Value |
|-----------|-------|
| **File** | `skills/pipelines/explainer/asset-director.md` |
| **Responsibilities** | Generate TTS audio, source/generate images and videos, generate diagrams/code/math, generate music, track costs |
| **Inputs** | `scene_plan`, `script`, `proposal_packet` |
| **Outputs** | `asset_manifest` artifact |
| **Dependencies** | TTS tools, image tools, video tools, music tools, diagram tools |
| **Cost** | Varies ($0.10 - $5.00+) |
| **Can Be Replaced?** | Partially — tool invocations are hard-coded in skill |
| **Can Be Extended?** | YES — Add new asset types, caching strategies |
| **Should Remain Untouched?** | Tool selection logic tied to production_plan |

### Edit Director

| Attribute | Value |
|-----------|-------|
| **File** | `skills/pipelines/explainer/edit-director.md` |
| **Responsibilities** | Create timeline cuts, configure subtitles, set music ducking, verify no gaps/overlaps |
| **Inputs** | `scene_plan`, `asset_manifest` |
| **Outputs** | `edit_decisions` artifact |
| **Dependencies** | Knowledge of rendering runtime capabilities |
| **Cost** | $0.00 |
| **Can Be Replaced?** | YES — Could add automated timeline generation |
| **Can Be Extended?** | YES — Add transition effects, multi-track audio |
| **Should Remain Untouched?** | Runtime locking logic is critical |

### Compose Director

| Attribute | Value |
|-----------|-------|
| **File** | `skills/pipelines/explainer/compose-director.md` |
| **Responsibilities** | Route to correct render runtime, generate props JSON, invoke rendering, run final_review |
| **Inputs** | `edit_decisions`, `asset_manifest`, audio files |
| **Outputs** | `render_report` artifact |
| **Dependencies** | `video_compose` tool, `hyperframes_compose` tool, FFmpeg |
| **Cost** | $0.00 (compute only) |
| **Can Be Replaced?** | NO — Tightly coupled to rendering backends |
| **Can Be Extended?** | YES — Add new render runtimes |
| **Should Remain Untouched?** | Runtime routing logic is critical |

### Publish Director

| Attribute | Value |
|-----------|-------|
| **File** | `skills/pipelines/explainer/publish-director.md` |
| **Responsibilities** | Generate SEO metadata, chapter markers, export package, thumbnail concept |
| **Inputs** | `render_report`, `final_review` |
| **Outputs** | `publish_log` artifact |
| **Dependencies** | None (agent reasoning only) |
| **Cost** | $0.00 |
| **Can Be Replaced?** | YES — Could integrate with YouTube/LinkedIn APIs |
| **Can Be Extended?** | YES — Add platform-specific formatting |
| **Should Remain Untouched?** | Safe to extend or replace entirely |

---

## Meta-Skills (Cross-Cutting Agents)

| Skill | File | Purpose | Risk |
|-------|------|---------|------|
| **Reviewer** | `skills/meta/reviewer.md` | Quality review checklist for stage outputs | LOW |
| **Checkpoint Protocol** | `skills/meta/checkpoint-protocol.md` | Pipeline state persistence and resume | MEDIUM |
| **Onboarding** | `skills/meta/onboarding.md` | New project initialization | LOW |
| **Skill Creator** | `skills/meta/skill-creator.md` | Guide for creating new skill files | LOW |
| **Capability Extension** | `skills/meta/capability-extension.md` | Guide for adding new tools/capabilities | LOW |
| **Creative Intake** | `skills/meta/creative-intake.md` | Structured creative brief gathering | LOW |
| **Animation Runtime Selector** | `skills/meta/animation-runtime-selector.md` | Help choose between Remotion/HyperFrames/FFmpeg | MEDIUM |
| **Bespoke Composition** | `skills/meta/bespoke-composition.md` | Guide for hand-authored Remotion compositions | MEDIUM |
| **Video Reference Analyst** | `skills/meta/video-reference-analyst.md` | Analyze reference videos for style extraction | LOW |

---

## Agent Extension Strategy

To add a new agent role in MythForge AI:

1. **Create a new Markdown skill file** in the appropriate `skills/` subdirectory
2. **Define the skill's**: responsibilities, inputs, outputs, guidelines, quality checklists
3. **Reference the skill** in the pipeline YAML definition
4. **No code changes required** — the AI agent will load and follow the new skill

To add a new pipeline:

1. **Create a YAML pipeline definition** in `pipeline_defs/`
2. **Create pipeline-specific director skills** in `skills/pipelines/<name>/`
3. **Reference existing or new tools** in the skill files
4. **Create schemas** for new artifact types if needed

---

## Key Observations

1. **No traditional agent classes exist** — all agent behavior is defined in Markdown
2. **The AI runtime is the single agent** — it role-switches based on loaded skill
3. **Skills are composable** — a pipeline references multiple skills in sequence
4. **Skills are versionable** — they live in git and can be branched/forked
5. **Skills are testable** — the `meta/reviewer.md` skill provides quality checklists
6. **Skills are the primary extension point** — new capabilities are added by writing Markdown, not code