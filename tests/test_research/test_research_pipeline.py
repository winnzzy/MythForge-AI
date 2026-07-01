import json
from pathlib import Path

import pytest

from mythforge.cli import main
from mythforge.engine.engine import ManifestEngine
from mythforge.research.pipeline import ResearchStage


class FakeProvider:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    async def generate(self, request):
        return type(
            "Response",
            (),
            {
                "text": json.dumps(self.payload),
                "model": "gpt-4o",
                "provider": "openai",
                "latency_ms": 12.0,
                "metadata": {},
                "tokens_in": 20,
                "tokens_out": 10,
                "finish_reason": "stop",
            },
        )()

    async def health_check(self):
        return type("Health", (), {"available": True, "status": type("Status", (), {"value": "healthy"})()})()


def test_research_stage_creates_artifact(tmp_path: Path) -> None:
    manifest_engine = ManifestEngine(base_dir=tmp_path)
    manifest_engine.create_project("The Wrath of Sango", "wrath-of-sango")

    stage = ResearchStage(
        provider=FakeProvider(
            {
                "topic": "The Wrath of Sango",
                "summary": "A rich history of Sango and his myths.",
                "findings": ["Sango is a deity of thunder."],
                "sources": [{"title": "Mythopedia", "url": "https://example.test"}],
                "keywords": ["sango", "thunder"],
                "african_mythology": "Yoruba mythology",
                "historical_context": "The deity is associated with thunder and justice.",
                "characters": [{"name": "Sango", "role": "deity", "description": "Thunder god"}],
                "timeline": ["Origin in Yoruba tradition"],
                "locations": ["Yoruba land"],
                "themes": ["justice", "thunder"],
                "cultural_notes": ["Respect local traditions"],
                "pronunciation_notes": ["Sango pronounced SAN-go"],
                "bibliography": [{"title": "Mythopedia", "url": "https://example.test"}],
                "visual_style": "Bold, dramatic, cinematic",
            }
        ),
        manifest_engine=manifest_engine,
    )

    result = stage.execute({"title": "The Wrath of Sango"}, {})

    artifact = result["artifact"]
    assert artifact.topic == "The Wrath of Sango"
    assert artifact.summary == "A rich history of Sango and his myths."
    assert artifact.characters[0]["name"] == "Sango"
    assert artifact.visual_style == "Bold, dramatic, cinematic"
    assert (manifest_engine.project_dir / "research.json").exists()
    assert (manifest_engine.project_dir / "research.md").exists()


def test_doctor_command_reports_readiness(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    exit_code = main(["doctor"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "System report" in captured.out
    assert "OpenAI API key" in captured.out
