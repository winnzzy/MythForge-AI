# Prompt Engine

## Overview

The Prompt Engine is MythForge's deterministic, versioned, cacheable prompt management system. It replaces ad-hoc string concatenation with a structured pipeline: **Template → Compose → Render → Deliver**.

Every prompt in the system flows through this engine, ensuring consistency, auditability, and reproducibility.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Prompt Engine                               │
│                                                                     │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐   │
│  │   Template    │   │   Variable   │   │   Template Registry  │   │
│  │   Models      │──▶│   Resolver   │◀──│   (versioned store)  │   │
│  └──────┬───────┘   └──────┬───────┘   └──────────────────────┘   │
│         │                   │                                       │
│         ▼                   ▼                                       │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐   │
│  │   Prompt      │   │   Prompt     │   │   In-Memory Cache    │   │
│  │   Composer    │──▶│   Validator  │──▶│   (hash → package)   │   │
│  └──────┬───────┘   └──────────────┘   └──────────────────────┘   │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐   ┌──────────────┐                               │
│  │   Prompt      │   │   Prompt     │                               │
│  │   Renderer    │──▶│   Hasher     │                               │
│  └──────┬───────┘   └──────────────┘                               │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────────────────────────┐                          │
│  │   Manifest Hooks (Engine integration)│                          │
│  └──────────────────────────────────────┘                          │
└─────────────────────────────────────────────────────────────────────┘
```

## Module Map

| Module | File | Purpose |
|--------|------|---------|
| Exceptions | `exceptions.py` | 8 specific exception types |
| Versioning | `versioning.py` | SemVer parsing, comparison, bumping |
| Hashing | `hashing.py` | SHA-256 content hashing for packages |
| Models | `models.py` | `PromptTemplate`, `PromptPackage`, `VariableSpec` dataclasses |
| Resolver | `resolver.py` | `{{var}}`, `{{var|default}}`, `{{>partial}}`, nested access |
| Templates | `templates.py` | `TemplateRegistry`, `TemplateLoader`, inheritance chain resolution |
| Validator | `validator.py` | Template & package integrity checks |
| Renderer | `renderer.py` | Output as chat messages, plain text, or dict |
| Composer | `composer.py` | High-level: template + variables + context → package |
| Cache | `cache.py` | `PromptCacheEntry`, `InMemoryPromptCache`, `PromptCacheProtocol` |
| Manifest Hooks | `manifest_hooks.py` | `get_prompt_engine_info()` for Engine manifest |

## Data Flow

```
1. Define Template (YAML/dict)
       │
       ▼
2. Register in TemplateRegistry (versioned, supports inheritance)
       │
       ▼
3. Composer.compose(template_name, variables, style_guides, knowledge)
       │
       ├─▶ Registry.get() → resolves inheritance chain
       ├─▶ Resolver.resolve() → fills {{variables}}
       ├─▶ Hasher.hash_package() → deterministic SHA-256
       ├─▶ Validator.validate_package() → integrity check
       │
       ▼
4. PromptPackage (immutable snapshot with hash)
       │
       ▼
5. Renderer.render_chat() / render_text() / render_dict()
       │
       ▼
6. Deliver to LLM provider
```

## Key Design Decisions

### 1. Immutability via Hashing
Every `PromptPackage` is content-hashed with SHA-256. If any field changes, the hash changes. This makes packages safe to cache, share, and audit.

### 2. Template Inheritance
Templates can `extend` other templates. Fields merge with child-overrides-parent semantics. Lists (like `negative_prompts`) concatenate.

### 3. Strict Variable Validation
The `VariableResolver` can operate in strict mode (throws on missing variables) or lenient mode (leaves `{{placeholders}}` intact). The `PromptValidator` also checks for unresolved variables.

### 4. Renderer Agnosticism
The `PromptRenderer` outputs in three formats:
- **Chat**: `[{role, content}]` for OpenAI/Gemini/Anthropic
- **Text**: Flat string for simple LLMs
- **Dict**: Structured for logging/inspection

### 5. Cache by Hash
The `PromptCacheProtocol` stores packages by their content hash. If the same template + variables + context produces the same hash, the cached result is returned.

## Usage Examples

### Basic Composition

```python
from mythforge.prompt_engine import PromptComposer, PromptTemplate, TemplateRegistry

registry = TemplateRegistry()
registry.register(PromptTemplate.from_dict({
    "name": "scene-writer",
    "version": "1.0.0",
    "system_prompt": "You are a cinematic scene writer in {{style}} style.",
    "user_prompt": "Write a scene in {{location}} with {{character}}.",
    "variables": [
        {"name": "style", "type": "string", "required": True},
        {"name": "location", "type": "string", "required": True},
        {"name": "character", "type": "string", "required": True},
    ],
}))

composer = PromptComposer(registry=registry)
package = composer.compose(
    "scene-writer",
    variables={"style": "noir", "location": "rainy alley", "character": "Detective Miles"},
    style_guides=["Use short sentences.", "Focus on shadows and light."],
)

# Package is immutable and hashed
print(package.hash)           # SHA-256
print(package.token_estimate) # ~token count

# Render for LLM
from mythforge.prompt_engine import PromptRenderer
renderer = PromptRenderer()
messages = renderer.render_chat(package)
# [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
```

### Template Inheritance

```python
registry.register(PromptTemplate.from_dict({
    "name": "base-writer",
    "version": "1.0.0",
    "system_prompt": "You are a professional writer.",
    "negative_prompts": ["No clichés"],
}))

registry.register(PromptTemplate.from_dict({
    "name": "dialogue-writer",
    "version": "1.0.0",
    "extends": "base-writer",
    "user_prompt": "Write dialogue between {{char_a}} and {{char_b}}.",
    "negative_prompts": ["No exposition dumps"],  # Appended to parent's list
}))

# Resolved template has both negative prompts
```

### Caching

```python
from mythforge.prompt_engine import InMemoryPromptCache, PromptCacheEntry

cache = InMemoryPromptCache(max_size=1000)

entry = PromptCacheEntry(hash=package.hash, package=package, ttl_seconds=3600)
await cache.put(entry)

cached = await cache.get(package.hash)
if cached:
    # Reuse cached package
    pass
```

## Variables

| Syntax | Example | Description |
|--------|---------|-------------|
| `{{name}}` | `Hello {{name}}` | Simple variable |
| `{{name\|default}}` | `Hello {{name\|stranger}}` | Variable with default value |
| `{{obj.key}}` | `{{character.name}}` | Nested object access |
| `{{>partial}}` | `{{>footer}}` | Partial insertion |

## Exceptions

| Exception | When |
|-----------|------|
| `PromptEngineError` | Base class for all prompt engine errors |
| `TemplateNotFoundError` | Template name not in registry |
| `CircularInheritanceError` | A extends B extends A |
| `MissingVariableError` | Required variable not provided (strict mode) |
| `VariableResolutionError` | General resolution failure |
| `CompositionError` | Composition pipeline failure |
| `VersionError` | Invalid version string |
| `CacheError` | Cache operation failure |

## Extension Points

- **Custom Renderers**: Implement a new renderer for non-standard LLM APIs
- **Custom Cache**: Implement `PromptCacheProtocol` for Redis/database caching
- **Template Loaders**: Extend `TemplateLoader` to load from databases, APIs, etc.
- **Custom Validators**: Add domain-specific validation rules

## Integration with Engine Manifest

The `manifest_hooks.py` module provides `get_prompt_engine_info()` which the Engine calls during manifest assembly. This exposes:
- Module name and version
- Available capabilities
- Health status