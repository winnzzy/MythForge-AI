"""
MythForge Manifest Engine.

Provides the ``ManifestEngine`` class which is the single source of truth
for every video project.  All pipeline stages interact with the manifest
through this public API — they never touch JSON files directly.
"""

from mythforge.engine.schema import (
    AssetRecord,
    CostRecord,
    ErrorRecord,
    Manifest,
    ManifestVersion,
    ProjectStatus,
    ProviderRecord,
    QualityCheck,
    RenderRecord,
    StageRecord,
    WarningRecord,
)
from mythforge.engine.engine import ManifestEngine

__all__ = [
    "ManifestEngine",
    "Manifest",
    "ManifestVersion",
    "ProjectStatus",
    "AssetRecord",
    "CostRecord",
    "ErrorRecord",
    "WarningRecord",
    "ProviderRecord",
    "QualityCheck",
    "RenderRecord",
    "StageRecord",
]