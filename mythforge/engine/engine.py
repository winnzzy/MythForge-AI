"""
ManifestEngine — the public API for project manifest management.

Every pipeline stage interacts with the manifest exclusively through this
class.  The engine owns all I/O (reading / writing ``manifest.json``) and
enforces invariants such as stage ordering and idempotent completion.

Usage::

    from mythforge.engine import ManifestEngine

    engine = ManifestEngine(base_dir="projects")

    # Create a new project
    manifest = engine.create_project(title="Shango Rises", slug="shango-rises")

    # ... pipeline stages run ...

    engine.begin_stage("RESEARCHING")
    # ... do research ...
    engine.complete_stage("RESEARCHING")

    # Save at any time
    engine.save()

    # Later — resume from disk
    manifest = engine.load_project("shango-rises")
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from mythforge.engine.schema import (
    AssetRecord,
    CostRecord,
    ErrorRecord,
    Manifest,
    ManifestVersion,
    PIPELINE_ORDER,
    ProjectStatus,
    ProviderRecord,
    QualityCheck,
    RenderRecord,
    StageRecord,
    WarningRecord,
    _now_iso,
)


class ManifestEngine:
    """
    Single source of truth for a MythForge video project.

    The engine owns the manifest lifecycle: create → load → mutate → save.
    All pipeline stages call engine methods; they never write JSON directly.

    Parameters
    ----------
    base_dir : str | Path
        Root directory that contains all project folders (default: ``projects``).
    """

    MANIFEST_FILENAME = "manifest.json"

    # Canonical sub-directories created for every project.
    _SUBDIRS = [
        "assets/images",
        "assets/narration",
        "assets/music",
        "assets/sfx",
        "assets/thumbnails",
        "assets/renders/draft",
        "assets/renders/final",
        "logs",
    ]

    def __init__(self, base_dir: str | Path = "projects") -> None:
        self._base_dir = Path(base_dir)
        self._manifest: Optional[Manifest] = None
        self._project_dir: Optional[Path] = None
        self._stage_records: Dict[str, StageRecord] = {}

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def manifest(self) -> Manifest:
        """Return the currently-loaded manifest.  Raises if none loaded."""
        if self._manifest is None:
            raise RuntimeError("No project loaded. Call create_project() or load_project() first.")
        return self._manifest

    @property
    def project_dir(self) -> Path:
        """Return the project directory path.  Raises if none loaded."""
        if self._project_dir is None:
            raise RuntimeError("No project loaded. Call create_project() or load_project() first.")
        return self._project_dir

    @property
    def stage_records(self) -> Dict[str, StageRecord]:
        """Return all stage execution records."""
        return dict(self._stage_records)

    # ------------------------------------------------------------------
    # Project lifecycle
    # ------------------------------------------------------------------

    def create_project(
        self,
        title: str,
        slug: str,
        *,
        settings: Optional[Dict[str, Any]] = None,
        configuration_snapshot: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Manifest:
        """
        Create a brand-new project and its on-disk directory structure.

        Returns the freshly-created manifest.
        """
        project_dir = self._base_dir / slug

        if project_dir.exists():
            raise FileExistsError(f"Project directory already exists: {project_dir}")

        # Create directory tree.
        project_dir.mkdir(parents=True, exist_ok=True)
        for sub in self._SUBDIRS:
            (project_dir / sub).mkdir(parents=True, exist_ok=True)

        # Build manifest.
        manifest = Manifest(
            title=title,
            slug=slug,
            status=ProjectStatus.CREATED.value,
            current_stage=ProjectStatus.CREATED.value,
            settings=settings or {},
            configuration_snapshot=configuration_snapshot or {},
            metadata=metadata or {},
        )

        # Wire up internal state.
        self._manifest = manifest
        self._project_dir = project_dir
        self._stage_records = {}

        # Persist immediately so nothing is lost.
        self.save()

        return manifest

    def load_project(self, slug: str) -> Manifest:
        """
        Load an existing project from disk.

        Raises ``FileNotFoundError`` if the project directory or manifest
        file does not exist.
        """
        project_dir = self._base_dir / slug
        manifest_path = project_dir / self.MANIFEST_FILENAME

        if not project_dir.is_dir():
            raise FileNotFoundError(f"Project directory not found: {project_dir}")
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Manifest file not found: {manifest_path}")

        with open(manifest_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        manifest = Manifest.from_dict(data)

        # Reconstruct stage records from the manifest's costs / errors lists
        # are not needed — stage records are stored in the manifest metadata
        # under ``_stage_records`` key for persistence.
        raw_records = data.get("_stage_records", {})
        stage_records: Dict[str, StageRecord] = {}
        for name, rec_dict in raw_records.items():
            stage_records[name] = StageRecord.from_dict(rec_dict)

        self._manifest = manifest
        self._project_dir = project_dir
        self._stage_records = stage_records

        return manifest

    def save(self) -> None:
        """
        Persist the current manifest (and stage records) to disk.

        This is a **full overwrite** of ``manifest.json`` with an atomic
        write pattern (write to temp file, then rename).
        """
        if self._manifest is None:
            raise RuntimeError("No project loaded.")

        self._manifest.updated_at = _now_iso()

        data = self._manifest.to_dict()
        # Embed stage records inside the manifest JSON so they survive reload.
        data["_stage_records"] = {
            name: rec.to_dict() for name, rec in self._stage_records.items()
        }

        manifest_path = self._project_dir / self.MANIFEST_FILENAME
        tmp_path = manifest_path.with_suffix(".json.tmp")

        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)

        # Atomic rename — with Windows fallback for permission errors.
        try:
            if os.name == "nt":
                os.replace(str(tmp_path), str(manifest_path))
            else:
                tmp_path.rename(manifest_path)
        except PermissionError:
            # Windows: some environments lock the file; fall back to
            # copy-then-delete which is safe for manifest persistence.
            shutil.copy2(str(tmp_path), str(manifest_path))
            tmp_path.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Stage tracking
    # ------------------------------------------------------------------

    def begin_stage(self, stage: str) -> StageRecord:
        """
        Mark *stage* as running.

        Validates that the stage name is a known ``ProjectStatus`` value.
        Returns the ``StageRecord`` for this execution.

        Note: ``FAILED`` is **not** considered terminal for the purpose of
        ``begin_stage`` — it allows retry of the failed stage.
        """
        # Ensure a project is loaded (raises RuntimeError if not).
        _ = self.manifest
        self._validate_stage(stage)
        self._assert_not_terminal_for_begin(stage)

        now = _now_iso()

        # Update manifest-level state.
        self._manifest.current_stage = stage
        self._manifest.status = stage

        # Create / update stage record.
        rec = self._stage_records.get(stage)
        if rec is None:
            rec = StageRecord(stage=stage)
            self._stage_records[stage] = rec

        rec.status = "running"
        rec.started_at = now
        rec.completed_at = None
        rec.error = None

        self.save()
        return rec

    def complete_stage(self, stage: str, *, metadata: Optional[Dict[str, Any]] = None) -> StageRecord:
        """
        Mark *stage* as completed.

        The stage is added to ``completed_stages`` if not already present.
        """
        self._validate_stage(stage)

        now = _now_iso()

        rec = self._stage_records.get(stage)
        if rec is None:
            raise ValueError(f"Stage '{stage}' was never started.")

        rec.status = "completed"
        rec.completed_at = now
        if rec.started_at:
            delta = datetime.fromisoformat(now) - datetime.fromisoformat(rec.started_at)
            rec.duration_s = delta.total_seconds()
        if metadata:
            rec.metadata.update(metadata)

        # Update manifest.
        if stage not in self._manifest.completed_stages:
            self._manifest.completed_stages.append(stage)

        # Advance current_stage to next in pipeline (if any).
        next_stage = self._next_stage(stage)
        if next_stage is not None:
            self._manifest.current_stage = next_stage
            self._manifest.status = next_stage

        self.save()
        return rec

    def fail_stage(self, stage: str, error: str, *, traceback: str = "") -> StageRecord:
        """
        Mark *stage* as failed and record the error.

        The project status is set to ``FAILED``.
        """
        self._validate_stage(stage)

        now = _now_iso()

        rec = self._stage_records.get(stage)
        if rec is None:
            rec = StageRecord(stage=stage)
            self._stage_records[stage] = rec

        rec.status = "failed"
        rec.completed_at = now
        rec.error = error
        if rec.started_at:
            delta = datetime.fromisoformat(now) - datetime.fromisoformat(rec.started_at)
            rec.duration_s = delta.total_seconds()

        # Increment retry count.
        rec.retry_count += 1
        self._manifest.retry_counts[stage] = rec.retry_count

        # Set project to FAILED.
        self._manifest.status = ProjectStatus.FAILED.value

        # Record error in manifest.
        self.record_error(stage, error, traceback=traceback)

        self.save()
        return rec

    def skip_stage(self, stage: str, *, reason: str = "") -> StageRecord:
        """
        Mark *stage* as skipped (e.g. cached assets already exist).
        """
        self._validate_stage(stage)

        rec = self._stage_records.get(stage)
        if rec is None:
            rec = StageRecord(stage=stage)
            self._stage_records[stage] = rec

        rec.status = "skipped"
        rec.completed_at = _now_iso()
        if reason:
            rec.metadata["skip_reason"] = reason

        if stage not in self._manifest.completed_stages:
            self._manifest.completed_stages.append(stage)

        self.save()
        return rec

    def is_stage_completed(self, stage: str) -> bool:
        """Return ``True`` if *stage* has been marked completed or skipped."""
        return stage in self._manifest.completed_stages

    def get_stage_record(self, stage: str) -> Optional[StageRecord]:
        """Return the ``StageRecord`` for *stage*, or ``None``."""
        return self._stage_records.get(stage)

    # ------------------------------------------------------------------
    # Resume logic
    # ------------------------------------------------------------------

    def get_next_stage(self) -> Optional[str]:
        """
        Return the next pipeline stage that needs to run, or ``None`` if
        the project is complete.

        Uses ``completed_stages`` and ``PIPELINE_ORDER`` to determine the
        correct next step.  Skips terminal statuses (``READY``, ``PUBLISHED``)
        and the initial ``CREATED`` state (which is set automatically on
        project creation and never needs to be "executed").
        """
        skip = {ProjectStatus.READY.value, ProjectStatus.PUBLISHED.value, ProjectStatus.CREATED.value}
        for stage in PIPELINE_ORDER:
            if stage.value in skip:
                continue
            if stage.value not in self._manifest.completed_stages:
                return stage.value
        return None

    def resume(self) -> Optional[str]:
        """
        Resume a project: determine the next stage and return it.

        If the project is in ``FAILED`` status, this resets it to the stage
        that failed so it can be retried.  Returns the stage to execute, or
        ``None`` if the project is already complete.
        """
        if self._manifest.status == ProjectStatus.FAILED.value:
            # Find the stage that failed.
            failed_stage = self._manifest.current_stage
            rec = self._stage_records.get(failed_stage)
            if rec and rec.status == "failed":
                # Reset so it can be retried.
                rec.status = "pending"
                rec.error = None
                self._manifest.status = failed_stage
                self.save()
                return failed_stage

        return self.get_next_stage()

    # ------------------------------------------------------------------
    # Asset tracking
    # ------------------------------------------------------------------

    def record_asset(self, asset: AssetRecord) -> None:
        """Add an asset record to the manifest."""
        self._manifest.assets.append(asset.to_dict())
        self.save()

    def get_assets(self, *, stage: Optional[str] = None, kind: Optional[str] = None) -> List[AssetRecord]:
        """Return assets, optionally filtered by stage and/or kind."""
        results: List[AssetRecord] = []
        for raw in self._manifest.assets:
            if stage and raw.get("stage") != stage:
                continue
            if kind and raw.get("kind") != kind:
                continue
            results.append(AssetRecord.from_dict(raw))
        return results

    # ------------------------------------------------------------------
    # Cost tracking
    # ------------------------------------------------------------------

    def record_cost(self, cost: CostRecord) -> None:
        """Add a cost entry to the manifest."""
        self._manifest.costs.append(cost.to_dict())
        self.save()

    def get_total_cost(self) -> float:
        """Return the sum of all recorded costs in USD."""
        return self._manifest.total_cost_usd

    def get_costs_by_stage(self) -> Dict[str, float]:
        """Return a breakdown of costs by stage name."""
        breakdown: Dict[str, float] = {}
        for raw in self._manifest.costs:
            stage = raw.get("stage", "unknown")
            breakdown[stage] = breakdown.get(stage, 0.0) + raw.get("amount_usd", 0.0)
        return breakdown

    # ------------------------------------------------------------------
    # Provider tracking
    # ------------------------------------------------------------------

    def record_provider(self, provider: ProviderRecord) -> None:
        """Record which provider was selected for a capability."""
        self._manifest.providers.append(provider.to_dict())
        self.save()

    def get_providers(self, *, capability: Optional[str] = None) -> List[ProviderRecord]:
        """Return provider records, optionally filtered by capability."""
        results: List[ProviderRecord] = []
        for raw in self._manifest.providers:
            if capability and raw.get("capability") != capability:
                continue
            results.append(ProviderRecord.from_dict(raw))
        return results

    # ------------------------------------------------------------------
    # Error / Warning tracking
    # ------------------------------------------------------------------

    def record_error(self, stage: str, message: str, *, traceback: str = "", metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record an error in the manifest."""
        err = ErrorRecord(
            stage=stage,
            message=message,
            traceback=traceback,
            metadata=metadata or {},
        )
        self._manifest.errors.append(err.to_dict())
        self.save()

    def record_warning(self, stage: str, message: str, *, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record a warning in the manifest."""
        warn = WarningRecord(
            stage=stage,
            message=message,
            metadata=metadata or {},
        )
        self._manifest.warnings.append(warn.to_dict())
        self.save()

    # ------------------------------------------------------------------
    # Quality checks
    # ------------------------------------------------------------------

    def record_quality_check(self, qc: QualityCheck) -> None:
        """Add a QA check result to the manifest."""
        self._manifest.quality_checks.append(qc.to_dict())
        self.save()

    # ------------------------------------------------------------------
    # Render tracking
    # ------------------------------------------------------------------

    def record_render(self, render: RenderRecord) -> None:
        """Add a render record to the manifest."""
        self._manifest.render_history.append(render.to_dict())
        self.save()

    # ------------------------------------------------------------------
    # Status reporting
    # ------------------------------------------------------------------

    def generate_summary(self) -> Dict[str, Any]:
        """
        Return a concise summary dict suitable for CLI display or logging.

        Includes: project identity, status, progress percentage, cost,
        asset count, error count, and per-stage timing.
        """
        m = self._manifest

        # Progress: completed / total pipeline stages (excluding terminal).
        trackable = [
            s for s in PIPELINE_ORDER
            if s.value not in (ProjectStatus.READY.value, ProjectStatus.PUBLISHED.value)
        ]
        completed_count = sum(1 for s in trackable if s.value in m.completed_stages)
        progress_pct = (completed_count / len(trackable) * 100) if trackable else 0.0

        # Per-stage timing.
        stage_timing: Dict[str, float] = {}
        for name, rec in self._stage_records.items():
            if rec.duration_s > 0:
                stage_timing[name] = rec.duration_s

        return {
            "project_id": m.project_id,
            "title": m.title,
            "slug": m.slug,
            "status": m.status,
            "current_stage": m.current_stage,
            "progress_pct": round(progress_pct, 1),
            "completed_stages": list(m.completed_stages),
            "total_cost_usd": round(m.total_cost_usd, 4),
            "asset_count": m.asset_count,
            "error_count": m.error_count,
            "warning_count": len(m.warnings),
            "stage_timing_s": stage_timing,
            "retry_counts": dict(m.retry_counts),
            "created_at": m.created_at,
            "updated_at": m.updated_at,
        }

    # ------------------------------------------------------------------
    # Directory helpers
    # ------------------------------------------------------------------

    def get_path(self, *parts: str) -> Path:
        """Return an absolute path inside the project directory."""
        return self._project_dir.joinpath(*parts)

    def ensure_subdir(self, *parts: str) -> Path:
        """Ensure a sub-directory exists and return its path."""
        p = self._project_dir.joinpath(*parts)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def write_text(self, relative_path: str, content: str) -> Path:
        """Write *content* to *relative_path* inside the project directory."""
        p = self._project_dir / relative_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def read_text(self, relative_path: str) -> str:
        """Read text content from *relative_path* inside the project directory."""
        p = self._project_dir / relative_path
        return p.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_stage(stage: str) -> None:
        """Raise ``ValueError`` if *stage* is not a known pipeline stage."""
        valid = {s.value for s in ProjectStatus}
        if stage not in valid:
            raise ValueError(f"Unknown stage '{stage}'. Valid stages: {sorted(valid)}")

    def _assert_not_terminal(self) -> None:
        """Raise if the project is in a terminal state."""
        if self._manifest.is_terminal:
            raise RuntimeError(
                f"Project is in terminal state '{self._manifest.status}'. "
                "Cannot modify — create a new project or explicitly reset status."
            )

    def _assert_not_terminal_for_begin(self, stage: str) -> None:
        """
        Like ``_assert_not_terminal`` but allows ``FAILED`` status so that
        a failed stage can be retried via ``begin_stage``.

        Only ``READY`` and ``PUBLISHED`` are truly immutable terminal states.
        """
        terminal_blocking = {ProjectStatus.READY.value, ProjectStatus.PUBLISHED.value}
        if self._manifest.status in terminal_blocking:
            raise RuntimeError(
                f"Project is in terminal state '{self._manifest.status}'. "
                "Cannot modify — create a new project or explicitly reset status."
            )

    @staticmethod
    def _next_stage(current: str) -> Optional[str]:
        """Return the stage that follows *current* in ``PIPELINE_ORDER``."""
        for i, stage in enumerate(PIPELINE_ORDER):
            if stage.value == current:
                if i + 1 < len(PIPELINE_ORDER):
                    nxt = PIPELINE_ORDER[i + 1]
                    if nxt not in (ProjectStatus.READY, ProjectStatus.PUBLISHED):
                        return nxt.value
                return None
        return None