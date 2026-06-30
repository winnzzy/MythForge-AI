"""
Comprehensive tests for the MythForge Artifact System.

Covers:
- All 11 concrete artifact types
- Serialization (JSON, YAML, Dict)
- Hashing (deterministic SHA-256)
- Versioning
- Validation
- Registry (register, lookup, migration)
- Factory (from JSON, Dict, YAML)
- Exports (JSON, Markdown, Dict)
- Metadata and Provenance
"""

from __future__ import annotations

import json
import pytest
from datetime import datetime, timezone

from mythforge.artifacts import (
    # Infrastructure
    ArtifactHasher,
    ArtifactVersion,
    ArtifactMetadata,
    ArtifactProvenance,
    BaseArtifact,
    ArtifactSerializer,
    ArtifactValidator,
    ArtifactRegistry,
    ArtifactFactory,
    ArtifactExporter,
    get_registry,
    # Exceptions
    ArtifactError,
    ArtifactValidationError,
    ArtifactSerializationError,
    ArtifactAlreadyRegisteredError,
    ArtifactNotRegisteredError,
    ArtifactFactoryError,
    InvalidArtifactVersionError,
    # Concrete artifacts
    ResearchArtifact,
    ScriptArtifact,
    SceneArtifact,
    ImageArtifact,
    NarrationArtifact,
    MusicArtifact,
    SFXArtifact,
    TimelineArtifact,
    ThumbnailArtifact,
    MetadataArtifact,
    VideoArtifact,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def provenance():
    return ArtifactProvenance(
        provider="test-provider",
        model="test-model",
        workflow_stage="research",
        prompt_hash="abc123",
        cost_usd=0.05,
        duration_s=1.5,
        software_version="1.0.0",
        manifest_id="manifest-001",
    )


@pytest.fixture
def metadata():
    return ArtifactMetadata(
        name="Test Artifact",
        description="A test artifact",
        tags=["test", "demo"],
        author="test-suite",
    )


# ============================================================================
# Model Tests
# ============================================================================

class TestArtifactMetadata:
    def test_defaults(self):
        m = ArtifactMetadata()
        assert m.name == ""
        assert m.tags == []
        assert m.author == ""

    def test_to_dict_roundtrip(self):
        m = ArtifactMetadata(name="foo", tags=["a", "b"], author="me")
        d = m.to_dict()
        m2 = ArtifactMetadata.from_dict(d)
        assert m2.name == "foo"
        assert m2.tags == ["a", "b"]
        assert m2.author == "me"


class TestArtifactProvenance:
    def test_defaults(self):
        p = ArtifactProvenance()
        assert p.provider == ""
        assert p.cost_usd == 0.0
        assert p.timestamp  # auto-set

    def test_to_dict_roundtrip(self):
        p = ArtifactProvenance(provider="openai", model="gpt-4", cost_usd=0.10)
        d = p.to_dict()
        p2 = ArtifactProvenance.from_dict(d)
        assert p2.provider == "openai"
        assert p2.model == "gpt-4"
        assert p2.cost_usd == 0.10

    def test_artifact_id_generation(self):
        p = ArtifactProvenance()
        assert p.artifact_id  # auto-generated


# ============================================================================
# Hashing Tests
# ============================================================================

class TestArtifactHasher:
    def test_deterministic(self):
        hasher = ArtifactHasher()
        data = {"key": "value", "number": 42}
        h1 = hasher.hash_content(data)
        h2 = hasher.hash_content(data)
        assert h1 == h2

    def test_different_data_different_hash(self):
        hasher = ArtifactHasher()
        h1 = hasher.hash_content({"a": 1})
        h2 = hasher.hash_content({"a": 2})
        assert h1 != h2

    def test_sha256_format(self):
        hasher = ArtifactHasher()
        h = hasher.hash_content({"x": 1})
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_order_independent(self):
        hasher = ArtifactHasher()
        h1 = hasher.hash_content({"b": 2, "a": 1})
        h2 = hasher.hash_content({"a": 1, "b": 2})
        assert h1 == h2


# ============================================================================
# Versioning Tests
# ============================================================================

class TestArtifactVersion:
    def test_parse_valid(self):
        v = ArtifactVersion.parse("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_str(self):
        v = ArtifactVersion(major=2, minor=0, patch=1)
        assert str(v) == "2.0.1"

    def test_initial(self):
        v = ArtifactVersion.initial()
        assert str(v) == "0.1.0"

    def test_parse_invalid(self):
        with pytest.raises(InvalidArtifactVersionError):
            ArtifactVersion.parse("not-a-version")

    def test_comparison(self):
        v1 = ArtifactVersion.parse("1.0.0")
        v2 = ArtifactVersion.parse("2.0.0")
        assert v1 < v2

    def test_equality(self):
        v1 = ArtifactVersion.parse("1.0.0")
        v2 = ArtifactVersion(major=1, minor=0, patch=0)
        assert v1 == v2


# ============================================================================
# Concrete Artifact Tests (all 11 types)
# ============================================================================

class TestResearchArtifact:
    def test_create_valid(self, metadata, provenance):
        a = ResearchArtifact(
            topic="AI Filmmaking",
            summary="Research on AI video generation",
            findings=["Finding 1", "Finding 2"],
            keywords=["ai", "video"],
            metadata=metadata,
            provenance=provenance,
        )
        assert a.artifact_type() == "ResearchArtifact"
        assert a.is_valid()

    def test_validation_requires_topic(self):
        a = ResearchArtifact(summary="no topic")
        errors = a.validate()
        assert any("topic" in e for e in errors)

    def test_validation_requires_summary(self):
        a = ResearchArtifact(topic="t")
        errors = a.validate()
        assert any("summary" in e for e in errors)

    def test_json_roundtrip(self):
        a = ResearchArtifact(topic="T", summary="S", findings=["F1"])
        a.compute_hash()
        j = a.to_json()
        b = ResearchArtifact.from_json(j)
        assert b.topic == "T"
        assert b.summary == "S"
        assert b.findings == ["F1"]
        assert b.content_hash == a.content_hash

    def test_markdown_export(self):
        a = ResearchArtifact(topic="T", summary="S", findings=["F1"], keywords=["k1"])
        md = a.to_markdown()
        assert "## Research: T" in md
        assert "S" in md
        assert "F1" in md
        assert "k1" in md

    def test_dict_roundtrip(self):
        a = ResearchArtifact(topic="T", summary="S")
        d = a.to_dict()
        assert d["artifact_type"] == "ResearchArtifact"
        b = ResearchArtifact.from_dict(d)
        assert b.topic == "T"


class TestScriptArtifact:
    def test_create_valid(self):
        a = ScriptArtifact(
            title="My Film",
            genre="Drama",
            raw_text="FADE IN:\nINT. HOUSE - DAY",
            characters=[{"name": "Alice", "description": "protagonist"}],
        )
        assert a.artifact_type() == "ScriptArtifact"
        assert a.is_valid()

    def test_validation_requires_title(self):
        a = ScriptArtifact(raw_text="text")
        errors = a.validate()
        assert any("title" in e for e in errors)

    def test_validation_requires_content(self):
        a = ScriptArtifact(title="T")
        errors = a.validate()
        assert any("raw_text" in e or "scenes" in e for e in errors)

    def test_json_roundtrip(self):
        a = ScriptArtifact(title="T", raw_text="text", genre="Horror")
        a.compute_hash()
        j = a.to_json()
        b = ScriptArtifact.from_json(j)
        assert b.title == "T"
        assert b.genre == "Horror"

    def test_markdown_with_scenes(self):
        a = ScriptArtifact(
            title="T",
            scenes=[{"heading": "INT. OFFICE", "action": "Bob sits.", "dialogue": [{"character": "Bob", "line": "Hello"}]}],
        )
        md = a.to_markdown()
        assert "INT. OFFICE" in md
        assert "Hello" in md


class TestSceneArtifact:
    def test_create_valid(self):
        a = SceneArtifact(
            scene_id="s1",
            heading="INT. CASTLE - NIGHT",
            action="The hero enters.",
            mood="dark",
            location="Castle",
        )
        assert a.artifact_type() == "SceneArtifact"
        assert a.is_valid()

    def test_validation_requires_heading(self):
        a = SceneArtifact(action="something")
        errors = a.validate()
        assert any("heading" in e for e in errors)

    def test_json_roundtrip(self):
        a = SceneArtifact(heading="H", action="A", mood="m")
        a.compute_hash()
        j = a.to_json()
        b = SceneArtifact.from_json(j)
        assert b.heading == "H"
        assert b.mood == "m"


class TestImageArtifact:
    def test_create_valid(self):
        a = ImageArtifact(
            prompt="A dragon flying over mountains",
            file_path="/output/dragon.png",
            width=1920,
            height=1080,
            seed=42,
        )
        assert a.artifact_type() == "ImageArtifact"
        assert a.is_valid()

    def test_validation_requires_prompt(self):
        a = ImageArtifact(file_path="/f.png")
        errors = a.validate()
        assert any("prompt" in e for e in errors)

    def test_validation_requires_file_or_url(self):
        a = ImageArtifact(prompt="p")
        errors = a.validate()
        assert any("file_path" in e or "url" in e for e in errors)

    def test_json_roundtrip(self):
        a = ImageArtifact(prompt="p", file_path="/f.png", width=100, height=100, seed=7)
        a.compute_hash()
        j = a.to_json()
        b = ImageArtifact.from_json(j)
        assert b.prompt == "p"
        assert b.seed == 7


class TestNarrationArtifact:
    def test_create_valid(self):
        a = NarrationArtifact(
            text="Once upon a time...",
            voice="en-US-Neural2-F",
            duration_s=30.5,
            segments=[{"start": 0.0, "end": 5.0, "text": "Once upon a time..."}],
        )
        assert a.artifact_type() == "NarrationArtifact"
        assert a.is_valid()

    def test_validation_requires_text(self):
        a = NarrationArtifact(voice="v")
        errors = a.validate()
        assert any("text" in e for e in errors)

    def test_validation_requires_voice(self):
        a = NarrationArtifact(text="t")
        errors = a.validate()
        assert any("voice" in e for e in errors)

    def test_json_roundtrip(self):
        a = NarrationArtifact(text="t", voice="v", duration_s=10.0)
        a.compute_hash()
        j = a.to_json()
        b = NarrationArtifact.from_json(j)
        assert b.text == "t"
        assert b.duration_s == 10.0


class TestMusicArtifact:
    def test_create_valid(self):
        a = MusicArtifact(
            title="Epic Battle",
            mood="intense",
            tempo_bpm=140,
            key="D minor",
            duration_s=180.0,
            genre="orchestral",
        )
        assert a.artifact_type() == "MusicArtifact"
        assert a.is_valid()

    def test_validation_requires_title(self):
        a = MusicArtifact(mood="m")
        errors = a.validate()
        assert any("title" in e for e in errors)

    def test_validation_requires_mood(self):
        a = MusicArtifact(title="t")
        errors = a.validate()
        assert any("mood" in e for e in errors)

    def test_json_roundtrip(self):
        a = MusicArtifact(title="t", mood="m", tempo_bpm=120)
        a.compute_hash()
        j = a.to_json()
        b = MusicArtifact.from_json(j)
        assert b.title == "t"
        assert b.tempo_bpm == 120


class TestSFXArtifact:
    def test_create_valid(self):
        a = SFXArtifact(
            name="Thunder Crack",
            category="nature",
            trigger="lightning",
            file_path="/sfx/thunder.wav",
            duration_s=3.0,
        )
        assert a.artifact_type() == "SFXArtifact"
        assert a.is_valid()

    def test_validation_requires_name(self):
        a = SFXArtifact(file_path="/f.wav")
        errors = a.validate()
        assert any("name" in e for e in errors)

    def test_validation_requires_file(self):
        a = SFXArtifact(name="n")
        errors = a.validate()
        assert any("file_path" in e for e in errors)

    def test_json_roundtrip(self):
        a = SFXArtifact(name="n", file_path="/f.wav", volume=0.8)
        a.compute_hash()
        j = a.to_json()
        b = SFXArtifact.from_json(j)
        assert b.name == "n"
        assert b.volume == 0.8


class TestTimelineArtifact:
    def test_create_valid(self):
        a = TimelineArtifact(
            duration_s=120.0,
            fps=30.0,
            resolution={"width": 3840, "height": 2160},
            tracks=[{"name": "Video 1", "type": "video", "clips": []}],
        )
        assert a.artifact_type() == "TimelineArtifact"
        assert a.is_valid()

    def test_validation_requires_positive_duration(self):
        a = TimelineArtifact(duration_s=0)
        errors = a.validate()
        assert any("duration" in e for e in errors)

    def test_json_roundtrip(self):
        a = TimelineArtifact(duration_s=60.0, fps=24.0)
        a.compute_hash()
        j = a.to_json()
        b = TimelineArtifact.from_json(j)
        assert b.duration_s == 60.0
        assert b.fps == 24.0


class TestThumbnailArtifact:
    def test_create_valid(self):
        a = ThumbnailArtifact(
            title="My Video Thumb",
            file_path="/thumb.png",
            width=1280,
            height=720,
            overlay_text="WATCH NOW",
        )
        assert a.artifact_type() == "ThumbnailArtifact"
        assert a.is_valid()

    def test_validation_requires_file_or_url(self):
        a = ThumbnailArtifact()
        errors = a.validate()
        assert any("file_path" in e or "url" in e for e in errors)

    def test_json_roundtrip(self):
        a = ThumbnailArtifact(file_path="/t.png", style="cinematic")
        a.compute_hash()
        j = a.to_json()
        b = ThumbnailArtifact.from_json(j)
        assert b.style == "cinematic"


class TestMetadataArtifact:
    def test_create_valid(self):
        a = MetadataArtifact(
            title="My Video",
            description="An AI-generated short film",
            tags=["ai", "film"],
            category="Entertainment",
            platform="YouTube",
        )
        assert a.artifact_type() == "MetadataArtifact"
        assert a.is_valid()

    def test_validation_requires_title(self):
        a = MetadataArtifact()
        errors = a.validate()
        assert any("title" in e for e in errors)

    def test_json_roundtrip(self):
        a = MetadataArtifact(title="T", tags=["a"], visibility="public")
        a.compute_hash()
        j = a.to_json()
        b = MetadataArtifact.from_json(j)
        assert b.title == "T"
        assert b.visibility == "public"


class TestVideoArtifact:
    def test_create_valid(self):
        a = VideoArtifact(
            title="Final Render",
            file_path="/output/final.mp4",
            width=1920,
            height=1080,
            fps=24.0,
            duration_s=300.0,
            codec="h264",
        )
        assert a.artifact_type() == "VideoArtifact"
        assert a.is_valid()

    def test_validation_requires_title(self):
        a = VideoArtifact(file_path="/f.mp4")
        errors = a.validate()
        assert any("title" in e for e in errors)

    def test_validation_requires_file_or_url(self):
        a = VideoArtifact(title="T")
        errors = a.validate()
        assert any("file_path" in e or "url" in e for e in errors)

    def test_json_roundtrip(self):
        a = VideoArtifact(title="T", file_path="/f.mp4", duration_s=60.0, scene_ids=["s1", "s2"])
        a.compute_hash()
        j = a.to_json()
        b = VideoArtifact.from_json(j)
        assert b.title == "T"
        assert b.scene_ids == ["s1", "s2"]


# ============================================================================
# Serialization Tests
# ============================================================================

class TestSerialization:
    def test_json_roundtrip_all_types(self):
        """Every artifact type survives JSON serialization."""
        artifacts = [
            ResearchArtifact(topic="T", summary="S"),
            ScriptArtifact(title="T", raw_text="R"),
            SceneArtifact(heading="H", action="A"),
            ImageArtifact(prompt="P", file_path="/f.png"),
            NarrationArtifact(text="T", voice="V"),
            MusicArtifact(title="T", mood="M"),
            SFXArtifact(name="N", file_path="/f.wav"),
            TimelineArtifact(duration_s=60.0),
            ThumbnailArtifact(file_path="/f.png"),
            MetadataArtifact(title="T"),
            VideoArtifact(title="T", file_path="/f.mp4"),
        ]
        for a in artifacts:
            a.compute_hash()
            j = a.to_json()
            b = type(a).from_json(j)
            assert b.content_hash == a.content_hash
            assert b.artifact_type() == a.artifact_type()

    def test_dict_roundtrip_all_types(self):
        """Every artifact type survives dict serialization."""
        artifacts = [
            ResearchArtifact(topic="T", summary="S"),
            ScriptArtifact(title="T", raw_text="R"),
            SceneArtifact(heading="H", action="A"),
            ImageArtifact(prompt="P", file_path="/f.png"),
            NarrationArtifact(text="T", voice="V"),
            MusicArtifact(title="T", mood="M"),
            SFXArtifact(name="N", file_path="/f.wav"),
            TimelineArtifact(duration_s=60.0),
            ThumbnailArtifact(file_path="/f.png"),
            MetadataArtifact(title="T"),
            VideoArtifact(title="T", file_path="/f.mp4"),
        ]
        for a in artifacts:
            d = a.to_dict()
            b = type(a).from_dict(d)
            assert b.artifact_type() == a.artifact_type()

    def test_to_json_is_valid_json(self):
        a = ScriptArtifact(title="T", raw_text="R")
        j = a.to_json()
        parsed = json.loads(j)
        assert parsed["artifact_type"] == "ScriptArtifact"
        assert "content" in parsed
        assert "metadata" in parsed
        assert "provenance" in parsed

    def test_yaml_roundtrip(self):
        a = ResearchArtifact(topic="T", summary="S")
        a.compute_hash()
        y = a.to_yaml()
        b = ResearchArtifact.from_yaml(y)
        assert b.topic == "T"
        assert b.content_hash == a.content_hash

    def test_serializer_class(self):
        a = ScriptArtifact(title="T", raw_text="R")
        j = ArtifactSerializer.to_json(a)
        b = ArtifactSerializer.from_json(j, ScriptArtifact)
        assert b.title == "T"


# ============================================================================
# Validation Tests
# ============================================================================

class TestValidation:
    def test_valid_artifact(self):
        a = ResearchArtifact(topic="T", summary="S")
        assert a.is_valid()
        assert a.validate() == []

    def test_invalid_artifact(self):
        a = ResearchArtifact()
        assert not a.is_valid()
        errors = a.validate()
        assert len(errors) >= 2

    def test_validator_class(self):
        validator = ArtifactValidator()
        a = ScriptArtifact(title="T", raw_text="R")
        assert validator.is_valid(a)
        assert validator.validate(a) == []

    def test_validator_catches_errors(self):
        validator = ArtifactValidator()
        a = ImageArtifact()
        errors = validator.validate(a)
        assert len(errors) > 0

    def test_hash_validation(self):
        validator = ArtifactValidator()
        a = ResearchArtifact(topic="T", summary="S")
        a.compute_hash()
        assert validator.validate_hash(a)

    def test_hash_validation_fails_on_tamper(self):
        validator = ArtifactValidator()
        a = ResearchArtifact(topic="T", summary="S")
        a.compute_hash()
        a.topic = "CHANGED"
        assert not validator.validate_hash(a)


# ============================================================================
# Registry Tests
# ============================================================================

class TestRegistry:
    def test_global_registry_has_all_types(self):
        reg = get_registry()
        expected = [
            "ResearchArtifact", "ScriptArtifact", "SceneArtifact",
            "ImageArtifact", "NarrationArtifact", "MusicArtifact",
            "SFXArtifact", "TimelineArtifact", "ThumbnailArtifact",
            "MetadataArtifact", "VideoArtifact",
        ]
        for name in expected:
            assert reg.has(name), f"Missing: {name}"

    def test_lookup_by_name(self):
        reg = get_registry()
        cls = reg.get("ScriptArtifact")
        assert cls is ScriptArtifact

    def test_names_list(self):
        reg = get_registry()
        names = reg.names()
        assert len(names) >= 11

    def test_register_duplicate_raises(self):
        reg = ArtifactRegistry()
        reg.register(ResearchArtifact)
        with pytest.raises(ArtifactAlreadyRegisteredError):
            reg.register(ResearchArtifact)

    def test_lookup_missing_raises(self):
        reg = ArtifactRegistry()
        with pytest.raises(ArtifactNotRegisteredError):
            reg.get("NonExistent")

    def test_unregister(self):
        reg = ArtifactRegistry()
        reg.register(ResearchArtifact)
        assert reg.has("ResearchArtifact")
        reg.unregister("ResearchArtifact")
        assert not reg.has("ResearchArtifact")

    def test_version_migration(self):
        reg = ArtifactRegistry()

        def migrate_v1_to_v2(data):
            data = dict(data)
            data["version"] = "2.0.0"
            data["content"]["new_field"] = "migrated"
            return data

        reg.register_migrator("ResearchArtifact", "1.0.0", migrate_v1_to_v2)

        old_data = {
            "artifact_type": "ResearchArtifact",
            "version": "1.0.0",
            "content": {"topic": "T", "summary": "S"},
        }
        migrated = reg.migrate(old_data, "2.0.0")
        assert migrated["version"] == "2.0.0"
        assert migrated["content"]["new_field"] == "migrated"


# ============================================================================
# Factory Tests
# ============================================================================

class TestFactory:
    def test_from_dict(self):
        factory = ArtifactFactory()
        a = ScriptArtifact(title="T", raw_text="R")
        d = a.to_dict()
        b = factory.from_dict(d)
        assert isinstance(b, ScriptArtifact)
        assert b.title == "T"

    def test_from_json(self):
        factory = ArtifactFactory()
        a = ResearchArtifact(topic="T", summary="S")
        j = a.to_json()
        b = factory.from_json(j)
        assert isinstance(b, ResearchArtifact)
        assert b.topic == "T"

    def test_from_yaml(self):
        factory = ArtifactFactory()
        a = MusicArtifact(title="T", mood="M")
        y = a.to_yaml()
        b = factory.from_yaml(y)
        assert isinstance(b, MusicArtifact)

    def test_missing_type_raises(self):
        factory = ArtifactFactory()
        with pytest.raises(ArtifactFactoryError):
            factory.from_dict({"content": {}})

    def test_from_dict_with_migration(self):
        reg = ArtifactRegistry()
        reg.register(ResearchArtifact)

        def migrate_v1_to_v2(data):
            data = dict(data)
            data["version"] = "2.0.0"
            return data

        reg.register_migrator("ResearchArtifact", "1.0.0", migrate_v1_to_v2)
        factory = ArtifactFactory(registry=reg)

        old_data = {
            "artifact_type": "ResearchArtifact",
            "version": "1.0.0",
            "content": {"topic": "T", "summary": "S"},
        }
        b = factory.from_dict_with_migration(old_data, "2.0.0")
        assert isinstance(b, ResearchArtifact)


# ============================================================================
# Exporter Tests
# ============================================================================

class TestExporter:
    def test_to_json(self):
        a = ScriptArtifact(title="T", raw_text="R")
        j = ArtifactExporter.to_json(a)
        parsed = json.loads(j)
        assert parsed["artifact_type"] == "ScriptArtifact"

    def test_to_markdown(self):
        a = ResearchArtifact(topic="AI", summary="Research summary", findings=["F1"])
        md = ArtifactExporter.to_markdown(a)
        assert "# ResearchArtifact: " in md
        assert "## Content" in md
        assert "## Research: AI" in md

    def test_to_dict(self):
        a = MusicArtifact(title="T", mood="M")
        d = ArtifactExporter.to_dict(a)
        assert isinstance(d, dict)
        assert d["artifact_type"] == "MusicArtifact"

    def test_markdown_includes_provenance(self):
        prov = ArtifactProvenance(provider="openai", model="gpt-4", cost_usd=0.05)
        a = ResearchArtifact(topic="T", summary="S", provenance=prov)
        md = ArtifactExporter.to_markdown(a)
        assert "openai" in md
        assert "gpt-4" in md

    def test_all_types_export_markdown(self):
        """Every artifact type can export to Markdown."""
        artifacts = [
            ResearchArtifact(topic="T", summary="S"),
            ScriptArtifact(title="T", raw_text="R"),
            SceneArtifact(heading="H", action="A"),
            ImageArtifact(prompt="P", file_path="/f.png"),
            NarrationArtifact(text="T", voice="V"),
            MusicArtifact(title="T", mood="M"),
            SFXArtifact(name="N", file_path="/f.wav"),
            TimelineArtifact(duration_s=60.0),
            ThumbnailArtifact(file_path="/f.png"),
            MetadataArtifact(title="T"),
            VideoArtifact(title="T", file_path="/f.mp4"),
        ]
        for a in artifacts:
            md = ArtifactExporter.to_markdown(a)
            assert len(md) > 0
            assert a.artifact_type() in md


# ============================================================================
# Provenance Tests
# ============================================================================

class TestProvenance:
    def test_provenance_separate_from_content(self):
        a = ResearchArtifact(topic="T", summary="S")
        prov = ArtifactProvenance(
            provider="openai",
            model="gpt-4",
            workflow_stage="research",
            cost_usd=0.10,
            duration_s=2.5,
            manifest_id="m-001",
        )
        a.provenance = prov
        d = a.to_dict()
        assert d["provenance"]["provider"] == "openai"
        assert "provider" not in d["content"]

    def test_provenance_fields_in_dict(self):
        prov = ArtifactProvenance(
            provider="stability",
            model="sdxl",
            workflow_stage="image_gen",
            prompt_hash="ph123",
            cost_usd=0.02,
            duration_s=5.0,
            software_version="1.0.0",
            manifest_id="m-002",
        )
        d = prov.to_dict()
        assert d["provider"] == "stability"
        assert d["model"] == "sdxl"
        assert d["workflow_stage"] == "image_gen"
        assert d["prompt_hash"] == "ph123"
        assert d["cost_usd"] == 0.02
        assert d["duration_s"] == 5.0
        assert d["manifest_id"] == "m-002"


# ============================================================================
# Hashing Integration Tests
# ============================================================================

class TestHashingIntegration:
    def test_compute_hash_stores_hash(self):
        a = ResearchArtifact(topic="T", summary="S")
        h = a.compute_hash()
        assert a.content_hash == h
        assert len(h) == 64

    def test_same_content_same_hash(self):
        a1 = ScriptArtifact(title="T", raw_text="R")
        a2 = ScriptArtifact(title="T", raw_text="R")
        assert a1.compute_hash() == a2.compute_hash()

    def test_different_content_different_hash(self):
        a1 = ScriptArtifact(title="T1", raw_text="R")
        a2 = ScriptArtifact(title="T2", raw_text="R")
        assert a1.compute_hash() != a2.compute_hash()

    def test_hash_survives_serialization(self):
        a = MusicArtifact(title="T", mood="M", tempo_bpm=120)
        a.compute_hash()
        j = a.to_json()
        b = MusicArtifact.from_json(j)
        assert b.content_hash == a.content_hash


# ============================================================================
# End-to-end Workflow Test
# ============================================================================

class TestEndToEnd:
    def test_artifact_workflow_lifecycle(self):
        """Simulate a full workflow: create → hash → export → serialize → reconstruct."""
        # 1. Create a research artifact
        research = ResearchArtifact(
            topic="Dragon Mythology",
            summary="Research on dragon lore across cultures",
            findings=["European dragons are evil", "Asian dragons are benevolent"],
            keywords=["dragon", "mythology"],
            metadata=ArtifactMetadata(name="Dragon Research", tags=["research"]),
            provenance=ArtifactProvenance(
                provider="openai",
                model="gpt-4",
                workflow_stage="research",
                cost_usd=0.05,
                duration_s=3.0,
            ),
        )

        # 2. Validate
        assert research.is_valid()

        # 3. Hash
        research.compute_hash()
        assert research.content_hash

        # 4. Export to all formats
        j = ArtifactExporter.to_json(research)
        md = ArtifactExporter.to_markdown(research)
        d = ArtifactExporter.to_dict(research)

        assert json.loads(j)["artifact_type"] == "ResearchArtifact"
        assert "Dragon Mythology" in md
        assert d["content"]["topic"] == "Dragon Mythology"

        # 5. Reconstruct via factory
        factory = ArtifactFactory()
        reconstructed = factory.from_json(j)
        assert isinstance(reconstructed, ResearchArtifact)
        assert reconstructed.topic == "Dragon Mythology"
        assert reconstructed.content_hash == research.content_hash

        # 6. Create a script from research
        script = ScriptArtifact(
            title="Dragon's Fury",
            genre="Fantasy",
            raw_text="FADE IN:\nEXT. MOUNTAIN - DAY\nA dragon soars above.",
            provenance=ArtifactProvenance(
                provider="anthropic",
                model="claude-3",
                workflow_stage="scripting",
            ),
        )
        assert script.is_valid()
        script.compute_hash()

        # 7. Serialize script and verify roundtrip
        script_json = script.to_json()
        script_back = ScriptArtifact.from_json(script_json)
        assert script_back.title == "Dragon's Fury"
        assert script_back.content_hash == script.content_hash

    def test_all_artifacts_in_registry(self):
        """Verify all 11 artifact types are registered and factory-accessible."""
        factory = ArtifactFactory()
        types = [
            ("ResearchArtifact", ResearchArtifact, {"topic": "T", "summary": "S"}),
            ("ScriptArtifact", ScriptArtifact, {"title": "T", "raw_text": "R"}),
            ("SceneArtifact", SceneArtifact, {"heading": "H", "action": "A"}),
            ("ImageArtifact", ImageArtifact, {"prompt": "P", "file_path": "/f.png"}),
            ("NarrationArtifact", NarrationArtifact, {"text": "T", "voice": "V"}),
            ("MusicArtifact", MusicArtifact, {"title": "T", "mood": "M"}),
            ("SFXArtifact", SFXArtifact, {"name": "N", "file_path": "/f.wav"}),
            ("TimelineArtifact", TimelineArtifact, {"duration_s": 60.0}),
            ("ThumbnailArtifact", ThumbnailArtifact, {"file_path": "/f.png"}),
            ("MetadataArtifact", MetadataArtifact, {"title": "T"}),
            ("VideoArtifact", VideoArtifact, {"title": "T", "file_path": "/f.mp4"}),
        ]
        for type_name, cls, kwargs in types:
            a = cls(**kwargs)
            a.compute_hash()
            d = a.to_dict()
            assert d["artifact_type"] == type_name
            reconstructed = factory.from_dict(d)
            assert isinstance(reconstructed, cls)
            assert reconstructed.content_hash == a.content_hash