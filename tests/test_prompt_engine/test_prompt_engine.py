"""
Comprehensive tests for the Prompt Engine.

Tests cover:
- PromptVersion (parsing, comparison, bumping)
- PromptHasher (determinism, collision resistance)
- VariableResolver (simple, nested, defaults, partials, missing)
- PromptTemplate (from_dict, serialisation)
- PromptPackage (from_dict, serialisation, token estimation)
- TemplateRegistry (registration, lookup, inheritance, circular detection)
- PromptValidator (template validation, package validation)
- PromptRenderer (chat, text, dict)
- PromptComposer (end-to-end composition)
- InMemoryPromptCache (get, put, evict, expiry)
"""

from __future__ import annotations

import asyncio
import pytest

from mythforge.prompt_engine.versioning import PromptVersion
from mythforge.prompt_engine.hashing import PromptHasher
from mythforge.prompt_engine.resolver import VariableResolver
from mythforge.prompt_engine.models import PromptPackage, PromptTemplate, VariableSpec
from mythforge.prompt_engine.templates import TemplateRegistry, TemplateLoader
from mythforge.prompt_engine.validator import PromptValidator
from mythforge.prompt_engine.renderer import PromptRenderer
from mythforge.prompt_engine.composer import PromptComposer
from mythforge.prompt_engine.cache import InMemoryPromptCache, PromptCacheEntry
from mythforge.prompt_engine.exceptions import (
    CircularInheritanceError,
    CompositionError,
    MissingVariableError,
    TemplateNotFoundError,
    VariableResolutionError,
)


# =====================================================================
# PromptVersion
# =====================================================================

class TestPromptVersion:
    def test_parse_valid(self):
        v = PromptVersion.parse("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_str(self):
        v = PromptVersion(1, 2, 3)
        assert str(v) == "1.2.3"

    def test_comparison(self):
        assert PromptVersion(1, 0, 0) < PromptVersion(2, 0, 0)
        assert PromptVersion(1, 1, 0) > PromptVersion(1, 0, 0)
        assert PromptVersion(1, 0, 1) > PromptVersion(1, 0, 0)
        assert PromptVersion(1, 0, 0) == PromptVersion(1, 0, 0)

    def test_bump_major(self):
        v = PromptVersion(1, 2, 3).bump("major")
        assert str(v) == "2.0.0"

    def test_bump_minor(self):
        v = PromptVersion(1, 2, 3).bump("minor")
        assert str(v) == "1.3.0"

    def test_bump_patch(self):
        v = PromptVersion(1, 2, 3).bump("patch")
        assert str(v) == "1.2.4"

    def test_parse_invalid(self):
        with pytest.raises(Exception):
            PromptVersion.parse("invalid")


# =====================================================================
# PromptHasher
# =====================================================================

class TestPromptHasher:
    def test_determinism(self):
        hasher = PromptHasher()
        data = {"prompt": "Hello world", "version": "1.0.0"}
        h1 = hasher.hash_package(data)
        h2 = hasher.hash_package(data)
        assert h1 == h2

    def test_different_data_different_hash(self):
        hasher = PromptHasher()
        h1 = hasher.hash_package({"prompt": "Hello"})
        h2 = hasher.hash_package({"prompt": "World"})
        assert h1 != h2

    def test_hash_length(self):
        hasher = PromptHasher()
        h = hasher.hash_package({"test": "data"})
        assert len(h) == 64  # SHA-256 hex


# =====================================================================
# VariableResolver
# =====================================================================

class TestVariableResolver:
    def test_simple_variable(self):
        resolver = VariableResolver()
        result = resolver.resolve("Hello {{name}}", variables={"name": "World"})
        assert result == "Hello World"

    def test_variable_with_default(self):
        resolver = VariableResolver()
        result = resolver.resolve("Hello {{name|stranger}}", variables={})
        assert result == "Hello stranger"

    def test_default_not_used_when_variable_present(self):
        resolver = VariableResolver()
        result = resolver.resolve("Hello {{name|stranger}}", variables={"name": "Alice"})
        assert result == "Hello Alice"

    def test_nested_variable(self):
        resolver = VariableResolver()
        result = resolver.resolve(
            "{{character.name}} is {{character.age}}",
            variables={"character": {"name": "Alice", "age": 30}},
        )
        assert result == "Alice is 30"

    def test_partial_insertion(self):
        resolver = VariableResolver()
        result = resolver.resolve(
            "Header{{>footer}}",
            partials={"footer": "\n--- Footer ---"},
        )
        assert result == "Header\n--- Footer ---"

    def test_missing_variable_strict(self):
        resolver = VariableResolver(strict=True)
        with pytest.raises(MissingVariableError):
            resolver.resolve("Hello {{name}}", variables={})

    def test_missing_variable_not_strict(self):
        resolver = VariableResolver(strict=False)
        result = resolver.resolve("Hello {{name}}", variables={})
        assert result == "Hello {{name}}"

    def test_find_variables(self):
        resolver = VariableResolver()
        found = resolver.find_variables("{{a}} and {{b|default}}")
        assert ("a", None) in found
        assert ("b", "default") in found

    def test_find_missing(self):
        resolver = VariableResolver()
        missing = resolver.find_missing("{{a}} and {{b}}", variables={"a": 1})
        assert missing == ["b"]


# =====================================================================
# PromptTemplate
# =====================================================================

class TestPromptTemplate:
    def test_from_dict_minimal(self):
        data = {
            "name": "test",
            "version": "1.0.0",
            "system_prompt": "You are a helpful assistant.",
        }
        t = PromptTemplate.from_dict(data)
        assert t.name == "test"
        assert str(t.version) == "1.0.0"
        assert t.system_prompt == "You are a helpful assistant."

    def test_from_dict_with_variables(self):
        data = {
            "name": "test",
            "version": "1.0.0",
            "system_prompt": "You are {{role}}.",
            "variables": [{"name": "role", "type": "string", "required": True}],
        }
        t = PromptTemplate.from_dict(data)
        assert len(t.variables) == 1
        assert t.variables[0].name == "role"

    def test_to_dict_roundtrip(self):
        data = {
            "name": "test",
            "version": "1.0.0",
            "system_prompt": "Hello {{name}}.",
            "variables": [{"name": "name", "type": "string"}],
        }
        t = PromptTemplate.from_dict(data)
        d = t.to_dict()
        t2 = PromptTemplate.from_dict(d)
        assert t.name == t2.name
        assert t.system_prompt == t2.system_prompt

    def test_variable_names(self):
        t = PromptTemplate.from_dict({
            "name": "test",
            "version": "1.0.0",
            "system_prompt": "Test.",
            "variables": [
                {"name": "a", "type": "string"},
                {"name": "b", "type": "string"},
            ],
        })
        assert t.variable_names == {"a", "b"}


# =====================================================================
# PromptPackage
# =====================================================================

class TestPromptPackage:
    def test_from_dict_minimal(self):
        data = {
            "name": "test-pkg",
            "version": "1.0.0",
            "template_name": "test",
            "system_prompt": "You are helpful.",
        }
        pkg = PromptPackage.from_dict(data)
        assert pkg.template_name == "test"
        assert pkg.system_prompt == "You are helpful."

    def test_to_dict_roundtrip(self):
        data = {
            "name": "test-pkg",
            "version": "1.0.0",
            "template_name": "test",
            "system_prompt": "Hello.",
            "user_prompt": "Do something.",
            "variables": {"x": 1},
        }
        pkg = PromptPackage.from_dict(data)
        d = pkg.to_dict()
        pkg2 = PromptPackage.from_dict(d)
        assert pkg.template_name == pkg2.template_name
        assert pkg.system_prompt == pkg2.system_prompt
        assert pkg.variables == pkg2.variables

    def test_token_estimation(self):
        pkg = PromptPackage.from_dict({
            "name": "test",
            "version": "1.0.0",
            "template_name": "test",
            "system_prompt": "This is a test prompt for token estimation.",
        })
        assert pkg.token_estimate > 0
        assert pkg.estimated_tokens > 0


# =====================================================================
# TemplateRegistry
# =====================================================================

class TestTemplateRegistry:
    def test_register_and_get(self):
        reg = TemplateRegistry()
        t = PromptTemplate.from_dict({
            "name": "test",
            "version": "1.0.0",
            "system_prompt": "Hello.",
        })
        reg.register(t)
        got = reg.get("test")
        assert got.name == "test"

    def test_get_not_found(self):
        reg = TemplateRegistry()
        with pytest.raises(TemplateNotFoundError):
            reg.get("nonexistent")

    def test_latest_version(self):
        reg = TemplateRegistry()
        reg.register(PromptTemplate.from_dict({
            "name": "test", "version": "1.0.0", "system_prompt": "v1.",
        }))
        reg.register(PromptTemplate.from_dict({
            "name": "test", "version": "2.0.0", "system_prompt": "v2.",
        }))
        latest = reg.get("test")
        assert str(latest.version) == "2.0.0"

    def test_specific_version(self):
        reg = TemplateRegistry()
        reg.register(PromptTemplate.from_dict({
            "name": "test", "version": "1.0.0", "system_prompt": "v1.",
        }))
        reg.register(PromptTemplate.from_dict({
            "name": "test", "version": "2.0.0", "system_prompt": "v2.",
        }))
        v1 = reg.get("test", version="1.0.0")
        assert v1.system_prompt == "v1."

    def test_inheritance(self):
        reg = TemplateRegistry()
        reg.register(PromptTemplate.from_dict({
            "name": "base",
            "version": "1.0.0",
            "system_prompt": "Base system prompt.",
            "negative_prompts": ["Don't do X"],
        }))
        reg.register(PromptTemplate.from_dict({
            "name": "child",
            "version": "1.0.0",
            "extends": "base",
            "user_prompt": "Do something.",
        }))
        resolved = reg.resolve("child")
        assert resolved.system_prompt == "Base system prompt."
        assert resolved.user_prompt == "Do something."
        assert "Don't do X" in resolved.negative_prompts

    def test_circular_inheritance(self):
        reg = TemplateRegistry()
        reg.register(PromptTemplate.from_dict({
            "name": "a", "version": "1.0.0", "extends": "b", "system_prompt": "A.",
        }))
        reg.register(PromptTemplate.from_dict({
            "name": "b", "version": "1.0.0", "extends": "a", "system_prompt": "B.",
        }))
        with pytest.raises(CircularInheritanceError):
            reg.resolve("a")

    def test_list_templates(self):
        reg = TemplateRegistry()
        reg.register(PromptTemplate.from_dict({
            "name": "alpha", "version": "1.0.0", "system_prompt": "A.",
        }))
        reg.register(PromptTemplate.from_dict({
            "name": "beta", "version": "1.0.0", "system_prompt": "B.",
        }))
        names = reg.list_templates()
        assert "alpha" in names
        assert "beta" in names

    def test_register_many(self):
        reg = TemplateRegistry()
        templates = [
            PromptTemplate.from_dict({"name": f"t{i}", "version": "1.0.0", "system_prompt": f"T{i}."})
            for i in range(3)
        ]
        reg.register_many(templates)
        assert len(reg.list_templates()) == 3


# =====================================================================
# PromptValidator
# =====================================================================

class TestPromptValidator:
    def test_valid_template(self):
        validator = PromptValidator()
        t = PromptTemplate.from_dict({
            "name": "test",
            "version": "1.0.0",
            "system_prompt": "You are a helpful assistant.",
        })
        assert validator.is_valid_template(t)

    def test_empty_name(self):
        validator = PromptValidator()
        t = PromptTemplate.from_dict({
            "name": "",
            "version": "1.0.0",
            "system_prompt": "Hello.",
        })
        errors = validator.validate_template(t)
        assert len(errors) > 0

    def test_undefined_variable(self):
        validator = PromptValidator()
        t = PromptTemplate.from_dict({
            "name": "test",
            "version": "1.0.0",
            "system_prompt": "Hello {{name}}.",
        })
        errors = validator.validate_template(t)
        assert any("name" in e for e in errors)

    def test_valid_package(self):
        validator = PromptValidator()
        pkg = PromptPackage.from_dict({
            "name": "test",
            "version": "1.0.0",
            "template_name": "test",
            "system_prompt": "You are a helpful assistant.",
        })
        pkg.hash = "abc123"
        assert validator.is_valid_package(pkg)

    def test_package_no_hash(self):
        validator = PromptValidator()
        pkg = PromptPackage.from_dict({
            "name": "test",
            "version": "1.0.0",
            "template_name": "test",
            "system_prompt": "You are a helpful assistant.",
        })
        errors = validator.validate_package(pkg)
        assert any("hash" in e.lower() for e in errors)

    def test_unresolved_variable_in_package(self):
        validator = PromptValidator()
        pkg = PromptPackage.from_dict({
            "name": "test",
            "version": "1.0.0",
            "template_name": "test",
            "system_prompt": "Hello {{name}}.",
        })
        pkg.hash = "abc"
        errors = validator.validate_package(pkg)
        assert any("unresolved" in e.lower() or "name" in e for e in errors)


# =====================================================================
# PromptRenderer
# =====================================================================

class TestPromptRenderer:
    def test_render_chat(self):
        renderer = PromptRenderer()
        pkg = PromptPackage.from_dict({
            "name": "test",
            "version": "1.0.0",
            "template_name": "test",
            "system_prompt": "You are helpful.",
            "user_prompt": "Hello.",
        })
        messages = renderer.render_chat(pkg)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_render_text(self):
        renderer = PromptRenderer()
        pkg = PromptPackage.from_dict({
            "name": "test",
            "version": "1.0.0",
            "template_name": "test",
            "system_prompt": "You are helpful.",
            "user_prompt": "Hello.",
        })
        text = renderer.render_text(pkg)
        assert "[SYSTEM]" in text
        assert "[USER]" in text

    def test_render_dict(self):
        renderer = PromptRenderer()
        pkg = PromptPackage.from_dict({
            "name": "test",
            "version": "1.0.0",
            "template_name": "test",
            "system_prompt": "You are helpful.",
        })
        d = renderer.render_dict(pkg)
        assert d["template_name"] == "test"
        assert "system_prompt" in d

    def test_render_with_negative_prompts(self):
        renderer = PromptRenderer()
        pkg = PromptPackage.from_dict({
            "name": "test",
            "version": "1.0.0",
            "template_name": "test",
            "system_prompt": "You are helpful.",
            "user_prompt": "Hello.",
            "negative_prompts": ["Don't be rude"],
        })
        messages = renderer.render_chat(pkg)
        user_msg = [m for m in messages if m["role"] == "user"][0]
        assert "Don't be rude" in user_msg["content"]


# =====================================================================
# PromptComposer
# =====================================================================

class TestPromptComposer:
    def test_compose_basic(self):
        registry = TemplateRegistry()
        registry.register(PromptTemplate.from_dict({
            "name": "greeting",
            "version": "1.0.0",
            "system_prompt": "You are a {{role}} assistant.",
            "user_prompt": "Say hello to {{name}}.",
            "variables": [
                {"name": "role", "type": "string", "required": True},
                {"name": "name", "type": "string", "required": True},
            ],
        }))
        composer = PromptComposer(registry=registry)
        pkg = composer.compose(
            "greeting",
            variables={"role": "helpful", "name": "Alice"},
        )
        assert "helpful" in pkg.system_prompt
        assert "Alice" in pkg.user_prompt
        assert pkg.hash  # Hash was computed

    def test_compose_with_style_guides(self):
        registry = TemplateRegistry()
        registry.register(PromptTemplate.from_dict({
            "name": "test",
            "version": "1.0.0",
            "system_prompt": "You are helpful.",
            "user_prompt": "Write a scene.",
        }))
        composer = PromptComposer(registry=registry)
        pkg = composer.compose(
            "test",
            style_guides=["Use vivid language."],
        )
        assert "vivid language" in pkg.system_prompt

    def test_compose_with_knowledge_references(self):
        registry = TemplateRegistry()
        registry.register(PromptTemplate.from_dict({
            "name": "test",
            "version": "1.0.0",
            "system_prompt": "You are helpful.",
            "user_prompt": "Write.",
        }))
        composer = PromptComposer(registry=registry)
        pkg = composer.compose(
            "test",
            knowledge_references=["The hero is a dragon rider."],
        )
        assert "dragon rider" in pkg.system_prompt

    def test_compose_inheritance(self):
        registry = TemplateRegistry()
        registry.register(PromptTemplate.from_dict({
            "name": "base",
            "version": "1.0.0",
            "system_prompt": "Base prompt.",
        }))
        registry.register(PromptTemplate.from_dict({
            "name": "specialised",
            "version": "1.0.0",
            "extends": "base",
            "user_prompt": "Do the thing.",
        }))
        composer = PromptComposer(registry=registry)
        pkg = composer.compose("specialised")
        assert pkg.system_prompt == "Base prompt."
        assert pkg.user_prompt == "Do the thing."

    def test_compose_and_render_chat(self):
        registry = TemplateRegistry()
        registry.register(PromptTemplate.from_dict({
            "name": "test",
            "version": "1.0.0",
            "system_prompt": "You are helpful.",
            "user_prompt": "Hello.",
        }))
        composer = PromptComposer(registry=registry)
        messages = composer.compose_and_render("test", format="chat")
        assert isinstance(messages, list)
        assert messages[0]["role"] == "system"

    def test_compose_and_render_text(self):
        registry = TemplateRegistry()
        registry.register(PromptTemplate.from_dict({
            "name": "test",
            "version": "1.0.0",
            "system_prompt": "You are helpful.",
            "user_prompt": "Hello.",
        }))
        composer = PromptComposer(registry=registry)
        text = composer.compose_and_render("test", format="text")
        assert isinstance(text, str)
        assert "[SYSTEM]" in text

    def test_compose_not_found(self):
        registry = TemplateRegistry()
        composer = PromptComposer(registry=registry, validate_output=False)
        with pytest.raises(Exception):
            composer.compose("nonexistent")


# =====================================================================
# InMemoryPromptCache
# =====================================================================

class TestInMemoryPromptCache:
    def test_put_and_get(self):
        cache = InMemoryPromptCache()
        pkg = PromptPackage.from_dict({
            "name": "test",
            "version": "1.0.0",
            "template_name": "test",
            "system_prompt": "Hello.",
        })
        entry = PromptCacheEntry(hash="abc123", package=pkg)
        asyncio.get_event_loop().run_until_complete(cache.put(entry))
        result = asyncio.get_event_loop().run_until_complete(cache.get("abc123"))
        assert result is not None
        assert result.hash == "abc123"
        assert result.hit_count == 1

    def test_get_nonexistent(self):
        cache = InMemoryPromptCache()
        result = asyncio.get_event_loop().run_until_complete(cache.get("nope"))
        assert result is None

    def test_evict(self):
        cache = InMemoryPromptCache()
        pkg = PromptPackage.from_dict({
            "name": "test",
            "version": "1.0.0",
            "template_name": "test",
            "system_prompt": "Hello.",
        })
        entry = PromptCacheEntry(hash="abc123", package=pkg)
        asyncio.get_event_loop().run_until_complete(cache.put(entry))
        evicted = asyncio.get_event_loop().run_until_complete(cache.evict("abc123"))
        assert evicted is True
        result = asyncio.get_event_loop().run_until_complete(cache.get("abc123"))
        assert result is None

    def test_clear(self):
        cache = InMemoryPromptCache()
        pkg = PromptPackage.from_dict({
            "name": "test",
            "version": "1.0.0",
            "template_name": "test",
            "system_prompt": "Hello.",
        })
        asyncio.get_event_loop().run_until_complete(
            cache.put(PromptCacheEntry(hash="a", package=pkg))
        )
        asyncio.get_event_loop().run_until_complete(
            cache.put(PromptCacheEntry(hash="b", package=pkg))
        )
        count = asyncio.get_event_loop().run_until_complete(cache.clear())
        assert count == 2

    def test_stats(self):
        cache = InMemoryPromptCache()
        stats = asyncio.get_event_loop().run_until_complete(cache.stats())
        assert "total_entries" in stats
        assert "total_hits" in stats

    def test_entry_serialisation(self):
        pkg = PromptPackage.from_dict({
            "name": "test",
            "version": "1.0.0",
            "template_name": "test",
            "system_prompt": "Hello.",
        })
        entry = PromptCacheEntry(hash="abc", package=pkg, ttl_seconds=3600)
        d = entry.to_dict()
        entry2 = PromptCacheEntry.from_dict(d)
        assert entry2.hash == "abc"
        assert entry2.ttl_seconds == 3600


# =====================================================================
# End-to-end
# =====================================================================

class TestEndToEnd:
    """Full pipeline test: template → registry → compose → render → validate."""

    def test_full_pipeline(self):
        # 1. Create templates
        base = PromptTemplate.from_dict({
            "name": "scene-base",
            "version": "1.0.0",
            "system_prompt": (
                "You are a cinematic scene writer. "
                "Write in a {{style|cinematic}} style."
            ),
            "negative_prompts": ["No clichés", "No purple prose"],
        })

        action = PromptTemplate.from_dict({
            "name": "scene-action",
            "version": "1.0.0",
            "extends": "scene-base",
            "user_prompt": (
                "Write an action scene in {{location}} "
                "featuring {{character}}."
            ),
            "variables": [
                {"name": "location", "type": "string", "required": True},
                {"name": "character", "type": "string", "required": True},
            ],
            "output_schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "narration": {"type": "string"},
                    "duration_seconds": {"type": "number"},
                },
            },
        })

        # 2. Register
        registry = TemplateRegistry()
        registry.register(base)
        registry.register(action)

        # 3. Validate
        validator = PromptValidator()
        assert validator.is_valid_template(base)
        assert validator.is_valid_template(action)

        # 4. Compose
        composer = PromptComposer(registry=registry)
        pkg = composer.compose(
            "scene-action",
            variables={
                "location": "a crumbling fortress",
                "character": "Kael the Dragonrider",
                "style": "epic fantasy",
            },
            style_guides=["Use short, punchy sentences.", "Focus on sensory details."],
        )

        # 5. Verify
        assert "epic fantasy" in pkg.system_prompt
        assert "Kael the Dragonrider" in pkg.user_prompt
        assert "crumbling fortress" in pkg.user_prompt
        assert "No clichés" in pkg.negative_prompts
        assert pkg.output_schema is not None
        assert pkg.hash
        assert pkg.token_estimate > 0

        # 6. Render
        renderer = PromptRenderer()
        messages = renderer.render_chat(pkg)
        assert len(messages) >= 2
        assert messages[0]["role"] == "system"

        text = renderer.render_text(pkg)
        assert "[SYSTEM]" in text

        # 7. Validate package
        assert validator.is_valid_package(pkg)

        # 8. Cache
        cache = InMemoryPromptCache()
        entry = PromptCacheEntry(hash=pkg.hash, package=pkg, ttl_seconds=3600)
        asyncio.get_event_loop().run_until_complete(cache.put(entry))
        cached = asyncio.get_event_loop().run_until_complete(cache.get(pkg.hash))
        assert cached is not None
        assert cached.package.template_name == "scene-action"