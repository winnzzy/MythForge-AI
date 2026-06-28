# MythForge AI — Development Guide

## Overview

This guide provides engineers with everything needed to understand, extend, and maintain the MythForge AI codebase. It covers project setup, coding standards, extension patterns, testing strategies, and operational procedures.

---

## Project Structure

```
MythForge-AI/
├── mythforge/                          # MythForge extension code
│   ├── __init__.py
│   ├── cli.py                          # CLI entry point (mythforge command)
│   ├── config/
│   │   ├── default.yaml                # Default configuration
│   │   └── settings.py                 # Settings loader
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py                     # MythForgeAgent base class
│   │   ├── researcher.py              # MythForgeResearcher
│   │   ├── scriptwriter.py            # MythForgeScriptWriter
│   │   ├── scene_director.py          # MythForgeSceneDirector
│   │   ├── prompt_agent.py            # MythForgePromptAgent
│   │   ├── image_agent.py             # MythForgeImageAgent
│   │   ├── narrator.py                # MythForgeNarrator
│   │   ├── music_agent.py             # MythForgeMusicAgent
│   │   ├── sfx_agent.py               # MythForgeSfxAgent
│   │   ├── renderer.py                # MythForgeRenderer
│   │   ├── qa.py                       # MythForgeQA
│   │   └── publisher.py               # MythForgePublisher
│   ├── pipelines/
│   │   ├── __init__.py
│   │   └── production.py              # MythForgeProductionPipeline
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── knowledge_base.py          # Knowledge base search tool
│   │   ├── character_bible.py         # Character bible tool
│   │   ├── asset_cache.py             # Asset cache tool
│   │   ├── music_library.py           # Music library tool
│   │   ├── sfx_library.py             # SFX library tool
│   │   └── budget_tracker.py          # Budget tracking tool
│   ├── prompts/
│   │   ├── researcher.md              # Research agent prompt
│   │   ├── scriptwriter.md            # Script writing prompt
│   │   ├── scene_director.md          # Scene direction prompt
│   │   ├── image_prompt.md            # Image prompt engineering prompt
│   │   ├── image_quality_check.md     # Image quality validation prompt
│   │   ├── narration_ssml.md          # SSML template for narration
│   │   ├── music_selection.md         # Music selection prompt
│   │   ├── sfx_selection.md           # SFX selection prompt
│   │   ├── qa.md                       # Quality assurance prompt
│   │   ├── thumbnail.md               # Thumbnail generation prompt
│   │   └── metadata.md                # Metadata/SEO prompt
│   ├── knowledge/
│   │   ├── characters/                 # Character Bible entries
│   │   ├── kingdoms/                   # Kingdom definitions
│   │   ├── stories/                    # Story outlines
│   │   ├── cosmology/                  # Cosmology systems
│   │   ├── pronunciation/              # Pronunciation guides
│   │   ├── cultural_notes/             # Cultural sensitivity notes
│   │   └── index.json                  # Knowledge base index
│   └── playbooks/
│       ├── dark_fantasy.yaml           # Dark fantasy art style
│       ├── epic_realism.yaml           # Epic realism art style
│       └── classical.yaml              # Classical art style
├── openmontage/                        # OpenMontage framework (DO NOT MODIFY)
│   └── ...                             # Core framework code
├── extensions/
│   ├── remotion/                       # Remotion rendering extension
│   └── image_generation/               # Image generation extension
├── config/
│   └── providers/                      # Provider configurations
│       ├── openai.yaml
│       ├── elevenlabs.yaml
│       └── ...
├── tests/
│   ├── test_agents/
│   ├── test_pipelines/
│   ├── test_tools/
│   └── test_integration/
├── scripts/
│   ├── setup.sh                        # Initial setup
│   └── validate.sh                     # Validation checks
├── .env.example                        # Environment variable template
├── requirements.txt                    # Python dependencies
└── README.md
```

---

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+ (for Remotion)
- FFmpeg 6.0+
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/mythforge-ai.git
cd mythforge-ai

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows

# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies (for Remotion)
cd extensions/remotion
npm install
cd ../..

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# See Configuration Analysis for all required variables

# Validate setup
python -m mythforge.cli validate
```

### Directory Initialization

```bash
# Create MythForge working directories
mythforge init

# This creates:
# .mythforge/
# .mythforge/projects/
# .mythforge/cache/
# .mythforge/cache/images/
# .mythforge/cache/narration/
# .mythforge/cache/music/
# .mythforge/cache/sfx/
```

---

## Coding Standards

### Python Style

- **PEP 8** compliance (enforced by flake8)
- **Type hints** on all function signatures
- **Docstrings** on all classes and public methods (Google style)
- **Maximum line length**: 100 characters
- **Imports**: Grouped (stdlib, third-party, local), sorted alphabetically

### File Naming

- Agent files: `snake_case.py` (e.g., `researcher.py`, `prompt_agent.py`)
- Tool files: `snake_case.py` (e.g., `knowledge_base.py`, `asset_cache.py`)
- Prompt files: `snake_case.md` (e.g., `image_prompt.md`)
- Knowledge entries: `snake_case.json` (e.g., `shango.json`, `oyo.json`)
- Config files: `snake_case.yaml` (e.g., `dark_fantasy.yaml`)

### Naming Conventions

- Classes: `PascalCase` (e.g., `MythForgeResearcher`)
- Functions/methods: `snake_case` (e.g., `generate_image`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`)
- Private methods: `_snake_case` with leading underscore (e.g., `_validate_image`)

---

## Extension Patterns

### Adding a New Agent

1. Create `mythforge/agents/{agent_name}.py`
2. Inherit from `MythForgeAgent`
3. Implement required methods:

```python
from mythforge.agents.base import MythForgeAgent

class MythForgeNewAgent(MythForgeAgent):
    """Agent that does X."""
    
    agent_id = "mythforge_new_agent"
    stage_id = "new_stage"
    
    def get_prompt_template(self) -> str:
        """Return the path to the prompt template file."""
        return "mythforge/prompts/new_agent.md"
    
    def get_llm_model(self) -> str:
        """Return the LLM model to use."""
        return "gpt-4o-mini"
    
    def get_temperature(self) -> float:
        """Return the temperature for LLM calls."""
        return 0.5
    
    def execute(self, context: dict) -> dict:
        """Execute the agent's primary task."""
        # 1. Load inputs from context
        # 2. Call LLM or provider
        # 3. Process results
        # 4. Save artifacts
        # 5. Return output metadata
        pass
```

4. Register in `mythforge/pipelines/production.py`
5. Add prompt template at `mythforge/prompts/{agent_name}.md`
6. Write tests at `tests/test_agents/test_{agent_name}.py`

### Adding a New Tool

1. Create `mythforge/tools/{tool_name}.py`
2. Inherit from OpenMontage `BaseTool`
3. Register in the agent that uses it

```python
from openmontage.tools.base import BaseTool

class MythForgeNewTool(BaseTool):
    """Tool that provides X capability."""
    
    name = "new_tool"
    description = "Provides X capability for agents"
    
    def get_schema(self) -> dict:
        """Return the tool's input schema."""
        return {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "..."},
            },
            "required": ["param1"]
        }
    
    def execute(self, params: dict) -> dict:
        """Execute the tool."""
        pass
```

### Adding a New Provider

1. Create provider class inheriting from OpenMontage provider base
2. Implement `generate()` method
3. Register in `config/providers/{provider}.yaml`
4. Update agent provider selection logic

### Adding a New Playbook

1. Create `mythforge/playbooks/{style_name}.yaml`
2. Follow the playbook schema:

```yaml
name: "New Art Style"
description: "Description of the visual style"
style_anchor: "Cinematic [style] art, [characteristics], highly detailed, 8K quality"
negative_anchor: "[things to avoid]"
image_settings:
  aspect_ratio: "16:9"
  guidance_scale: 7.5
  steps: 30
scene_templates:
  title_card:
    camera_movement: "slow_zoom_in"
    movement_intensity: 2
  narration:
    camera_movement: "slow_pan_right"
    movement_intensity: 3
transitions:
  default: "cross_dissolve"
  dramatic: "fade_to_black"
  action: "quick_cut"
audio:
  music_volume: -18
  sfx_volume: -14
  narration_volume: -1
```

### Adding Knowledge Base Content

1. Create JSON entry following the schema in `07_KNOWLEDGE_BASE.md`
2. Place in appropriate subdirectory under `mythforge/knowledge/`
3. Update `mythforge/knowledge/index.json`
4. Validate against schema
5. Run knowledge base integrity check: `mythforge knowledge validate`

---

## Testing Strategy

### Test Categories

| Category | Directory | Purpose | Run Command |
|----------|-----------|---------|-------------|
| Unit | `tests/test_agents/` | Test individual agent logic | `pytest tests/test_agents/` |
| Unit | `tests/test_tools/` | Test tool implementations | `pytest tests/test_tools/` |
| Integration | `tests/test_integration/` | Test pipeline end-to-end | `pytest tests/test_integration/` |
| Prompt | `tests/test_prompts/` | Validate prompt templates | `pytest tests/test_prompts/` |
| Knowledge | `tests/test_knowledge/` | Validate KB entries | `pytest tests/test_knowledge/` |

### Test Patterns

```python
# Agent test example
import pytest
from mythforge.agents.researcher import MythForgeResearcher

class TestMythForgeResearcher:
    def test_research_with_known_character(self):
        """Researcher should find Shango in the Knowledge Base."""
        agent = MythForgeResearcher()
        result = agent.execute({"title": "The Legend of Shango"})
        assert result["characters"][0]["id"] == "shango"
        assert result["mythology_origin"] == "yoruba"
    
    def test_research_with_unknown_topic(self):
        """Researcher should fall back to web research for unknown topics."""
        agent = MythForgeResearcher()
        result = agent.execute({"title": "The Legend of Unknown Deity"})
        assert result["sources"]  # Should have web sources
        assert result["confidence"] < 0.8  # Lower confidence
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific category
pytest tests/test_agents/

# Run with coverage
pytest --cov=mythforge --cov-report=html

# Run integration tests (requires API keys)
pytest tests/test_integration/ --run-integration

# Validate knowledge base
pytest tests/test_knowledge/
```

---

## Operational Procedures

### Running a Production Pipeline

```bash
# Basic run
mythforge produce "The Legend of Shango, God of Thunder"

# With specific playbook
mythforge produce "The Legend of Shango" --playbook dark_fantasy

# With custom output directory
mythforge produce "The Legend of Shango" --output ./my_videos/

# Resume from checkpoint
mythforge produce --resume shango_thunder_20260628

# Dry run (validate without executing)
mythforge produce "The Legend of Shango" --dry-run
```

### Monitoring a Pipeline

```bash
# View pipeline status
mythforge status shango_thunder_20260628

# View real-time logs
mythforge logs shango_thunder_20260628 --follow

# View cost report
mythforge cost shango_thunder_20260628
```

### Debugging

```bash
# Run with verbose logging
mythforge produce "The Legend of Shango" --log-level DEBUG

# Run single stage
mythforge stage run shango_thunder_20260628 research

# Inspect artifacts
mythforge inspect shango_thunder_20260628 artifacts/research.json

# Regenerate specific stage
mythforge stage rerun shango_thunder_20260628 image_generation
```

---

## Common Tasks

### Updating a Prompt Template

1. Open the prompt file in `mythforge/prompts/`
2. Edit the prompt text
3. Test with a dry run: `mythforge produce "Test Title" --dry-run`
4. Run a full production and compare output quality
5. Commit with descriptive message: `git commit -m "Improve image prompt template for better character consistency"`

### Adding a New Mythology Domain

1. Research the mythology thoroughly
2. Create Knowledge Base entries (characters, kingdoms, stories, pronunciation, cultural notes)
3. Create a Character Bible for each character
4. Create style anchors for the mythology origin
5. Test with a sample production
6. Document cultural sensitivity considerations

### Updating a Provider

1. Edit the provider config in `config/providers/`
2. Test with: `mythforge provider test {provider_name}`
3. Run a single stage that uses the provider
4. Compare output quality with previous provider version
5. Update provider version in `requirements.txt` if needed

---

## What NOT to Modify

| Component | Reason |
|-----------|--------|
| `openmontage/` directory | Core framework — changes break the foundation |
| OpenMontage base classes | All agents depend on these interfaces |
| OpenMontage tool interfaces | Provider abstraction depends on these |
| OpenMontage configuration loading | May break all provider configurations |
| Existing published Character Bible entries | Breaks visual consistency with published videos |

If you need to change something in OpenMontage, propose it as an upstream contribution instead of forking.