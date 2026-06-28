"""
Unit tests for the MythForge Manifest Engine.

Covers:
- Project creation
- Manifest validation
- Serialization / deserialization
- Resume capability
- Status updates (stage lifecycle)
- Asset registration
- Cost tracking
- Provider tracking
- Error / warning tracking
- Quality checks
- Render tracking
- Summary generation
- Edge cases and error conditions
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from mythforge.engine import (
    ManifestEngine,
    Manifest,
    ManifestVersion,
    ProjectStatus,
    AssetRecord,
    CostRecord,
    ErrorRecord,
    WarningRecord,
    ProviderRecord,
    QualityCheck,
    RenderRecord,
    StageRecord,
)
from mythforge.engine.schema import PIPELINE_ORDER, _now_iso


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_base(tmp_path: Path) -> Path:
    """Provide a temporary base directory for project creation."""
    return tmp_path / "projects"


@pytest.fixture
def engine(tmp_base: Path) -> ManifestEngine:
    """Provide a fresh ManifestEngine pointed at a temp directory."""
    return ManifestEngine(base_dir=tmp_base)


@pytest.fixture
def created_engine(engine: ManifestEngine) -> ManifestEngine:
    """Provide an engine with a project already created."""
    engine.create_project(title="Test Video", slug="test-video")
    return engine


# ===========================================================================
# 1. Project Creation
# ===========================================================================

class TestProjectCreation:
    """Tests for ManifestEngine.create_project()."""

    def test_creates_directory_structure(self, engine: ManifestEngine, tmp_base: Path):
        manifest = engine.create_project(title="My Video", slug="my-video")
        project_dir = tmp_base / "my-video"
        assert project_dir.is_dir()
        assert (project_dir / "manifest.json").is_file()
        assert (project_dir / "assets" / "images").is_dir()
        assert (project_dir / "assets" / "narration").is_dir()
        assert (project_dir / "assets" / "music").is_dir()
        assert (project_dir / "assets" / "sfx").is_dir()
        assert (project_dir / "assets" / "thumbnails").is_dir()
        assert (project_dir / "assets" / "renders" / "draft").is_dir()
        assert (project_dir / "assets" / "renders" / "final").is_dir()
        assert (project_dir / "logs").is_dir()

    def test_manifest_has_correct_identity(self, engine: ManifestEngine):
        manifest = engine.create_project(title="Shango Rises", slug="shango-rises")
        assert manifest.title == "Shango Rises"
        assert manifest.slug == "shango-rises"
        assert len(manifest.project_id) == 12
        assert manifest.version == ManifestVersion.CURRENT.value

    def test_initial_status_is_created(self, engine: ManifestEngine):
        manifest = engine.create_project(title="T", slug="t")
        assert manifest.status == ProjectStatus.CREATED.value
        assert manifest.current_stage == ProjectStatus.CREATED.value
        assert manifest.completed_stages == []

    def test_creates_empty_collections(self, engine: ManifestEngine):
        manifest = engine.create_project(title="T", slug="t")
        assert manifest.providers == []
        assert manifest.costs == []
        assert manifest.assets == []
        assert manifest.render_history == []
        assert manifest.quality_checks == []
        assert manifest.errors == []
        assert manifest.warnings == []
        assert manifest.retry_counts == {}

    def test_settings_and_metadata(self, engine: ManifestEngine):
        manifest = engine.create_project(
            title="T",
            slug="t",
            settings={"resolution": "4k"},
            configuration_snapshot={"llm": "gemini"},
            metadata={"genre": "mythology"},
        )
        assert manifest.settings["resolution"] == "4k"
        assert manifest.configuration_snapshot["llm"] == "gemini"
        assert manifest.metadata["genre"] == "mythology"

    def test_duplicate_slug_raises(self, engine: ManifestEngine):
        engine.create_project(title="A", slug="dup")
        with pytest.raises(FileExistsError):
            engine.create_project(title="B", slug="dup")

    def test_persists_manifest_json(self, engine: ManifestEngine, tmp_base: Path):
        engine.create_project(title="T", slug="persist")
        manifest_path = tmp_base / "persist" / "manifest.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert data["title"] == "T"
        assert data["slug"] == "persist"


# ===========================================================================
# 2. Manifest Validation & Serialization
# ===========================================================================

class TestManifestSerialization:
    """Tests for to_dict / from_dict round-trip."""

    def test_round_trip(self, engine: ManifestEngine):
        engine.create_project(
            title="Round Trip",
            slug="round-trip",
            settings={"fps": 30},
            metadata={"audience": "adults"},
        )
        engine.record_asset(AssetRecord(stage="IMAGE_GENERATION", kind="image", path="assets/images/001.png"))
        engine.record_cost(CostRecord(stage="RESEARCHING", provider="gemini", amount_usd=0.05))
        engine.record_error("NARRATION", "timeout")
        engine.record_warning("SFX", "low volume")
        engine.record_provider(ProviderRecord(capability="llm", provider="gemini", model="gemini-2.0-flash"))
        engine.record_quality_check(QualityCheck(stage="QA", check_type="subtitle_sync", passed=True, score=0.95))
        engine.record_render(RenderRecord(kind="final", path="assets/renders/final/out.mp4"))

        # Serialise
        data = engine.manifest.to_dict()

        # Deserialise
        restored = Manifest.from_dict(data)

        assert restored.title == "Round Trip"
        assert restored.slug == "round-trip"
        assert restored.settings["fps"] == 30
        assert restored.metadata["audience"] == "adults"
        assert len(restored.assets) == 1
        assert len(restored.costs) == 1
        assert len(restored.errors) == 1
        assert len(restored.warnings) == 1
        assert len(restored.providers) == 1
        assert len(restored.quality_checks) == 1
        assert len(restored.render_history) == 1

    def test_from_dict_ignores_unknown_keys(self):
        data = {
            "project_id": "abc123",
            "title": "Test",
            "slug": "test",
            "unknown_future_field": "should be ignored",
        }
        manifest = Manifest.from_dict(data)
        assert manifest.title == "Test"

    def test_total_cost_property(self):
        m = Manifest()
        m.costs = [
            {"amount_usd": 1.5},
            {"amount_usd": 2.3},
            {"amount_usd": 0.0},
        ]
        assert m.total_cost_usd == pytest.approx(3.8)

    def test_is_terminal(self):
        m = Manifest()
        m.status = ProjectStatus.CREATED.value
        assert m.is_terminal is False

        m.status = ProjectStatus.READY.value
        assert m.is_terminal is True

        m.status = ProjectStatus.PUBLISHED.value
        assert m.is_terminal is True

        m.status = ProjectStatus.FAILED.value
        assert m.is_terminal is True

        m.status = ProjectStatus.RENDERING.value
        assert m.is_terminal is False


# ===========================================================================
# 3. Load / Save
# ===========================================================================

class TestLoadSave:
    """Tests for loading projects from disk after saving."""

    def test_load_round_trip(self, engine: ManifestEngine):
        engine.create_project(title="Save Load", slug="save-load")
        engine.begin_stage("RESEARCHING")
        engine.complete_stage("RESEARCHING")
        engine.record_asset(AssetRecord(stage="RESEARCHING", kind="research", path="research.md"))

        # Load in a fresh engine
        engine2 = ManifestEngine(base_dir=engine._base_dir)
        manifest = engine2.load_project("save-load")

        assert manifest.title == "Save Load"
        assert manifest.completed_stages == ["RESEARCHING"]
        assert len(manifest.assets) == 1
        assert len(engine2.stage_records) == 1
        assert engine2.stage_records["RESEARCHING"].status == "completed"

    def test_load_nonexistent_raises(self, engine: ManifestEngine):
        with pytest.raises(FileNotFoundError, match="not found"):
            engine.load_project("does-not-exist")

    def test_save_updates_timestamp(self, engine: ManifestEngine):
        engine.create_project(title="T", slug="ts")
        t1 = engine.manifest.updated_at
        engine.record_warning("CREATED", "test")
        t2 = engine.manifest.updated_at
        assert t2 >= t1  # should be updated


# ===========================================================================
# 4. Stage Lifecycle
# ===========================================================================

class TestStageLifecycle:
    """Tests for begin_stage / complete_stage / fail_stage / skip_stage."""

    def test_begin_and_complete_stage(self, created_engine: ManifestEngine):
        e = created_engine
        rec = e.begin_stage("RESEARCHING")
        assert rec.status == "running"
        assert e.manifest.current_stage == "RESEARCHING"
        assert e.manifest.status == "RESEARCHING"

        rec = e.complete_stage("RESEARCHING")
        assert rec.status == "completed"
        assert rec.duration_s >= 0
        assert "RESEARCHING" in e.manifest.completed_stages
        assert e.manifest.current_stage == "WRITING"  # next stage

    def test_begin_without_load_raises(self):
        e = ManifestEngine()
        with pytest.raises(RuntimeError, match="No project loaded"):
            e.begin_stage("RESEARCHING")

    def test_invalid_stage_raises(self, created_engine: ManifestEngine):
        with pytest.raises(ValueError, match="Unknown stage"):
            created_engine.begin_stage("INVALID_STAGE")

    def test_complete_without_begin_raises(self, created_engine: ManifestEngine):
        with pytest.raises(ValueError, match="never started"):
            created_engine.complete_stage("WRITING")

    def test_fail_stage(self, created_engine: ManifestEngine):
        e = created_engine
        e.begin_stage("IMAGE_GENERATION")
        rec = e.fail_stage("IMAGE_GENERATION", "API timeout")
        assert rec.status == "failed"
        assert rec.error == "API timeout"
        assert rec.retry_count == 1
        assert e.manifest.status == ProjectStatus.FAILED.value
        assert len(e.manifest.errors) == 1

    def test_fail_increments_retry(self, created_engine: ManifestEngine):
        e = created_engine
        e.begin_stage("NARRATION")
        e.fail_stage("NARRATION", "err1")
        e.begin_stage("NARRATION")
        e.fail_stage("NARRATION", "err2")
        rec = e.get_stage_record("NARRATION")
        assert rec.retry_count == 2
        assert e.manifest.retry_counts["NARRATION"] == 2

    def test_skip_stage(self, created_engine: ManifestEngine):
        e = created_engine
        rec = e.skip_stage("SFX", reason="cached assets exist")
        assert rec.status == "skipped"
        assert rec.metadata["skip_reason"] == "cached assets exist"
        assert "SFX" in e.manifest.completed_stages

    def test_is_stage_completed(self, created_engine: ManifestEngine):
        e = created_engine
        assert e.is_stage_completed("RESEARCHING") is False
        e.begin_stage("RESEARCHING")
        e.complete_stage("RESEARCHING")
        assert e.is_stage_completed("RESEARCHING") is True

    def test_begin_terminal_project_raises(self, created_engine: ManifestEngine):
        e = created_engine
        e._manifest.status = ProjectStatus.READY.value
        with pytest.raises(RuntimeError, match="terminal state"):
            e.begin_stage("RESEARCHING")

    def test_stage_advances_through_pipeline(self, created_engine: ManifestEngine):
        e = created_engine
        stages = [
            "RESEARCHING", "WRITING", "SCENE_BREAKDOWN", "PROMPT_GENERATION",
            "IMAGE_GENERATION", "NARRATION", "SFX", "MUSIC", "RENDERING", "QA",
        ]
        for stage in stages:
            e.begin_stage(stage)
            e.complete_stage(stage)
        # After QA, next should be READY (terminal), so current_stage stays at QA
        # Actually QA completes and next is READY which is terminal
        assert e.manifest.completed_stages == stages


# ===========================================================================
# 5. Resume Capability
# ===========================================================================

class TestResumeCapability:
    """Tests for get_next_stage() and resume()."""

    def test_get_next_stage_from_beginning(self, created_engine: ManifestEngine):
        assert created_engine.get_next_stage() == "RESEARCHING"

    def test_get_next_stage_after_progress(self, created_engine: ManifestEngine):
        e = created_engine
        e.begin_stage("RESEARCHING")
        e.complete_stage("RESEARCHING")
        e.begin_stage("WRITING")
        e.complete_stage("WRITING")
        assert e.get_next_stage() == "SCENE_BREAKDOWN"

    def test_get_next_stage_all_done(self, created_engine: ManifestEngine):
        e = created_engine
        for stage in PIPELINE_ORDER:
            if stage.value in (ProjectStatus.READY.value, ProjectStatus.PUBLISHED.value):
                continue
            e.begin_stage(stage.value)
            e.complete_stage(stage.value)
        assert e.get_next_stage() is None

    def test_resume_from_failure(self, created_engine: ManifestEngine):
        e = created_engine
        e.begin_stage("IMAGE_GENERATION")
        e.fail_stage("IMAGE_GENERATION", "quota exceeded")
        assert e.manifest.status == ProjectStatus.FAILED.value

        next_stage = e.resume()
        assert next_stage == "IMAGE_GENERATION"
        rec = e.get_stage_record("IMAGE_GENERATION")
        assert rec.status == "pending"  # reset for retry

    def test_resume_from_normal(self, created_engine: ManifestEngine):
        e = created_engine
        e.begin_stage("RESEARCHING")
        e.complete_stage("RESEARCHING")
        assert e.resume() == "WRITING"

    def test_resume_when_complete(self, created_engine: ManifestEngine):
        e = created_engine
        for stage in PIPELINE_ORDER:
            if stage.value in (ProjectStatus.READY.value, ProjectStatus.PUBLISHED.value):
                continue
            e.begin_stage(stage.value)
            e.complete_stage(stage.value)
        assert e.resume() is None


# ===========================================================================
# 6. Asset Registration
# ===========================================================================

class TestAssetRegistration:
    """Tests for record_asset() and get_assets()."""

    def test_record_and_retrieve(self, created_engine: ManifestEngine):
        e = created_engine
        asset = AssetRecord(
            stage="IMAGE_GENERATION",
            kind="image",
            path="assets/images/shango_001.png",
            provider="gemini",
        )
        e.record_asset(asset)
        assert e.manifest.asset_count == 1

        assets = e.get_assets()
        assert len(assets) == 1
        assert assets[0].path == "assets/images/shango_001.png"

    def test_filter_by_stage(self, created_engine: ManifestEngine):
        e = created_engine
        e.record_asset(AssetRecord(stage="IMAGE_GENERATION", kind="image", path="a.png"))
        e.record_asset(AssetRecord(stage="NARRATION", kind="narration", path="a.mp3"))
        e.record_asset(AssetRecord(stage="IMAGE_GENERATION", kind="image", path="b.png"))

        images = e.get_assets(stage="IMAGE_GENERATION")
        assert len(images) == 2

        audio = e.get_assets(kind="narration")
        assert len(audio) == 1

    def test_filter_by_stage_and_kind(self, created_engine: ManifestEngine):
        e = created_engine
        e.record_asset(AssetRecord(stage="IMAGE_GENERATION", kind="image", path="a.png"))
        e.record_asset(AssetRecord(stage="IMAGE_GENERATION", kind="thumbnail", path="thumb.png"))
        e.record_asset(AssetRecord(stage="NARRATION", kind="narration", path="n.mp3"))

        result = e.get_assets(stage="IMAGE_GENERATION", kind="image")
        assert len(result) == 1
        assert result[0].kind == "image"


# ===========================================================================
# 7. Cost Tracking
# ===========================================================================

class TestCostTracking:
    """Tests for record_cost() and cost queries."""

    def test_record_and_total(self, created_engine: ManifestEngine):
        e = created_engine
        e.record_cost(CostRecord(stage="RESEARCHING", provider="gemini", amount_usd=0.05))
        e.record_cost(CostRecord(stage="WRITING", provider="openai", amount_usd=0.12))
        assert e.get_total_cost() == pytest.approx(0.17)

    def test_costs_by_stage(self, created_engine: ManifestEngine):
        e = created_engine
        e.record_cost(CostRecord(stage="RESEARCHING", amount_usd=0.05))
        e.record_cost(CostRecord(stage="RESEARCHING", amount_usd=0.03))
        e.record_cost(CostRecord(stage="WRITING", amount_usd=0.10))

        breakdown = e.get_costs_by_stage()
        assert breakdown["RESEARCHING"] == pytest.approx(0.08)
        assert breakdown["WRITING"] == pytest.approx(0.10)


# ===========================================================================
# 8. Provider Tracking
# ===========================================================================

class TestProviderTracking:
    """Tests for record_provider() and get_providers()."""

    def test_record_and_retrieve(self, created_engine: ManifestEngine):
        e = created_engine
        e.record_provider(ProviderRecord(capability="llm", provider="gemini", model="gemini-2.0-flash"))
        e.record_provider(ProviderRecord(capability="tts", provider="elevenlabs", model="rachel"))

        providers = e.get_providers()
        assert len(providers) == 2

    def test_filter_by_capability(self, created_engine: ManifestEngine):
        e = created_engine
        e.record_provider(ProviderRecord(capability="llm", provider="gemini"))
        e.record_provider(ProviderRecord(capability="tts", provider="elevenlabs"))

        llm = e.get_providers(capability="llm")
        assert len(llm) == 1
        assert llm[0].provider == "gemini"


# ===========================================================================
# 9. Error / Warning Tracking
# ===========================================================================

class TestErrorWarningTracking:
    """Tests for record_error() and record_warning()."""

    def test_record_error(self, created_engine: ManifestEngine):
        e = created_engine
        e.record_error("NARRATION", "API timeout", traceback="Traceback...")
        assert e.manifest.error_count == 1
        assert e.manifest.errors[0]["message"] == "API timeout"

    def test_record_warning(self, created_engine: ManifestEngine):
        e = created_engine
        e.record_warning("SFX", "Volume too low")
        assert len(e.manifest.warnings) == 1
        assert e.manifest.warnings[0]["message"] == "Volume too low"


# ===========================================================================
# 10. Quality Checks
# ===========================================================================

class TestQualityChecks:
    """Tests for record_quality_check()."""

    def test_record_qc(self, created_engine: ManifestEngine):
        e = created_engine
        qc = QualityCheck(
            stage="QA",
            check_type="subtitle_sync",
            passed=True,
            score=0.97,
            details="All subtitles within 50ms tolerance",
        )
        e.record_quality_check(qc)
        assert len(e.manifest.quality_checks) == 1
        assert e.manifest.quality_checks[0]["passed"] is True
        assert e.manifest.quality_checks[0]["score"] == 0.97


# ===========================================================================
# 11. Render Tracking
# ===========================================================================

class TestRenderTracking:
    """Tests for record_render()."""

    def test_record_render(self, created_engine: ManifestEngine):
        e = created_engine
        render = RenderRecord(
            kind="final",
            path="assets/renders/final/output.mp4",
            resolution="1080p",
            duration_s=120.5,
            file_size_bytes=50_000_000,
        )
        e.record_render(render)
        assert len(e.manifest.render_history) == 1
        assert e.manifest.render_history[0]["kind"] == "final"


# ===========================================================================
# 12. Summary Generation
# ===========================================================================

class TestSummaryGeneration:
    """Tests for generate_summary()."""

    def test_summary_structure(self, created_engine: ManifestEngine):
        e = created_engine
        e.begin_stage("RESEARCHING")
        e.complete_stage("RESEARCHING")
        e.record_cost(CostRecord(stage="RESEARCHING", amount_usd=0.05))
        e.record_asset(AssetRecord(stage="RESEARCHING", kind="research", path="research.md"))

        summary = e.generate_summary()

        assert summary["title"] == "Test Video"
        assert summary["slug"] == "test-video"
        assert summary["status"] == "WRITING"  # advanced after RESEARCHING
        assert summary["current_stage"] == "WRITING"
        assert summary["completed_stages"] == ["RESEARCHING"]
        assert summary["total_cost_usd"] == pytest.approx(0.05)
        assert summary["asset_count"] == 1
        assert summary["error_count"] == 0
        assert summary["warning_count"] == 0
        assert summary["progress_pct"] > 0
        assert "created_at" in summary
        assert "updated_at" in summary

    def test_summary_progress_at_zero(self, created_engine: ManifestEngine):
        summary = created_engine.generate_summary()
        assert summary["progress_pct"] == 0.0


# ===========================================================================
# 13. Directory Helpers
# ===========================================================================

class TestDirectoryHelpers:
    """Tests for get_path, ensure_subdir, write_text, read_text."""

    def test_get_path(self, created_engine: ManifestEngine):
        p = created_engine.get_path("assets", "images", "001.png")
        assert p.name == "001.png"
        assert "assets" in str(p)

    def test_ensure_subdir(self, created_engine: ManifestEngine):
        p = created_engine.ensure_subdir("custom", "subdir")
        assert p.is_dir()

    def test_write_and_read_text(self, created_engine: ManifestEngine):
        created_engine.write_text("research.md", "# Research\nContent here")
        content = created_engine.read_text("research.md")
        assert content == "# Research\nContent here"

    def test_write_creates_parent_dirs(self, created_engine: ManifestEngine):
        p = created_engine.write_text("deep/nested/file.txt", "hello")
        assert p.is_file()
        assert p.read_text(encoding="utf-8") == "hello"


# ===========================================================================
# 14. Schema Sub-Records
# ===========================================================================

class TestSubRecords:
    """Tests for individual sub-record to_dict / from_dict round-trips."""

    def test_asset_record_round_trip(self):
        rec = AssetRecord(stage="IMAGE_GENERATION", kind="image", path="a.png", provider="gemini")
        d = rec.to_dict()
        restored = AssetRecord.from_dict(d)
        assert restored.stage == "IMAGE_GENERATION"
        assert restored.path == "a.png"
        assert restored.asset_id == rec.asset_id

    def test_cost_record_round_trip(self):
        rec = CostRecord(stage="RESEARCHING", provider="gemini", operation="search", amount_usd=0.05, tokens_in=1000, tokens_out=500)
        d = rec.to_dict()
        restored = CostRecord.from_dict(d)
        assert restored.amount_usd == 0.05
        assert restored.tokens_in == 1000

    def test_error_record_round_trip(self):
        rec = ErrorRecord(stage="NARRATION", message="timeout", traceback="tb")
        d = rec.to_dict()
        restored = ErrorRecord.from_dict(d)
        assert restored.message == "timeout"

    def test_warning_record_round_trip(self):
        rec = WarningRecord(stage="SFX", message="low vol")
        d = rec.to_dict()
        restored = WarningRecord.from_dict(d)
        assert restored.message == "low vol"

    def test_provider_record_round_trip(self):
        rec = ProviderRecord(capability="llm", provider="gemini", model="flash")
        d = rec.to_dict()
        restored = ProviderRecord.from_dict(d)
        assert restored.model == "flash"

    def test_quality_check_round_trip(self):
        rec = QualityCheck(stage="QA", check_type="sync", passed=True, score=0.9)
        d = rec.to_dict()
        restored = QualityCheck.from_dict(d)
        assert restored.passed is True
        assert restored.score == 0.9

    def test_render_record_round_trip(self):
        rec = RenderRecord(kind="draft", path="out.mp4", resolution="4k", duration_s=60.0)
        d = rec.to_dict()
        restored = RenderRecord.from_dict(d)
        assert restored.resolution == "4k"

    def test_stage_record_round_trip(self):
        rec = StageRecord(stage="RESEARCHING", status="completed", duration_s=12.5, retry_count=0)
        d = rec.to_dict()
        restored = StageRecord.from_dict(d)
        assert restored.status == "completed"
        assert restored.duration_s == 12.5


# ===========================================================================
# 15. Edge Cases
# ===========================================================================

class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_create_then_immediately_load(self, engine: ManifestEngine):
        engine.create_project(title="Edge", slug="edge")
        engine2 = ManifestEngine(base_dir=engine._base_dir)
        m = engine2.load_project("edge")
        assert m.title == "Edge"
        assert m.status == ProjectStatus.CREATED.value

    def test_multiple_saves_preserve_data(self, created_engine: ManifestEngine):
        e = created_engine
        e.record_cost(CostRecord(stage="RESEARCHING", amount_usd=0.01))
        e.save()
        e.record_cost(CostRecord(stage="WRITING", amount_usd=0.02))
        e.save()

        engine2 = ManifestEngine(base_dir=e._base_dir)
        m = engine2.load_project("test-video")
        assert len(m.costs) == 2

    def test_stage_record_metadata(self, created_engine: ManifestEngine):
        e = created_engine
        e.begin_stage("RESEARCHING")
        rec = e.complete_stage("RESEARCHING", metadata={"sources_checked": 15})
        assert rec.metadata["sources_checked"] == 15

    def test_manifest_asset_count_property(self):
        m = Manifest()
        m.assets = [{"a": 1}, {"b": 2}, {"c": 3}]
        assert m.asset_count == 3

    def test_manifest_error_count_property(self):
        m = Manifest()
        m.errors = [{"e": 1}]
        assert m.error_count == 1

    def test_pipeline_order_is_complete(self):
        """Ensure PIPELINE_ORDER covers all non-terminal statuses."""
        # READY and PUBLISHED are terminal; FAILED is a transient error state
        # that is never part of the forward pipeline progression.
        non_pipeline = {ProjectStatus.READY, ProjectStatus.PUBLISHED, ProjectStatus.FAILED}
        all_statuses = set(ProjectStatus)
        covered = set(PIPELINE_ORDER) | non_pipeline
        assert all_statuses == covered

    def test_manifest_version_enum(self):
        assert ManifestVersion.CURRENT == ManifestVersion.V1
        assert ManifestVersion.CURRENT.value == "1.0"