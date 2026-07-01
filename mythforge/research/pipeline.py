from __future__ import annotations

import asyncio
import inspect
import json
import os
from pathlib import Path
from typing import Any, Dict, List

from mythforge.artifacts.artifacts import ResearchArtifact
from mythforge.engine.engine import ManifestEngine
from mythforge.engine.schema import AssetRecord, ProviderRecord
from mythforge.prompt_engine.composer import PromptComposer
from mythforge.prompt_engine.models import PromptTemplate, TemplateMetadata, VariableSpec
from mythforge.prompt_engine.templates import TemplateRegistry
from mythforge.providers.models import LLMRequest
from mythforge.providers.openai import OpenAIConfig, OpenAIProvider


class ResearchStage:
    """Build a validated research artifact from a video title."""

    def __init__(
        self,
        provider: Any = None,
        manifest_engine: ManifestEngine | None = None,
        *,
        output_dir: str | Path | None = None,
    ) -> None:
        self.provider = provider
        self.manifest_engine = manifest_engine
        self.output_dir = Path(output_dir) if output_dir is not None else None
        self._registry = self._build_template_registry()
        self._composer = PromptComposer(registry=self._registry)

    def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        title = str(input_data.get("title") or context.get("title") or "").strip()
        if not title:
            raise ValueError("A video title is required")

        if self.manifest_engine is not None:
            self.manifest_engine.begin_stage("RESEARCHING")

        try:
            if self.provider is None:
                api_key = os.getenv("OPENAI_API_KEY") or ""
                if not api_key:
                    raise RuntimeError("OPENAI_API_KEY is not configured")
                config = OpenAIConfig(api_key=api_key, default_model="gpt-4o")
                self.provider = OpenAIProvider(config)

            prompt_package = self._composer.compose(
                "research-brief",
                variables={"title": title},
            )

            request = LLMRequest(
                prompt=prompt_package.user_prompt,
                system_prompt=prompt_package.system_prompt,
                metadata={
                    "json_mode": True,
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "research_artifact",
                            "schema": self._research_schema(),
                        },
                    },
                },
            )
            response = self._invoke_provider(request)
            payload = self._parse_payload(response)
            self._validate_payload(payload)
            artifact = self._build_artifact(title, payload)
            artifact.compute_hash()
            self._export_artifact(artifact)

            if self.manifest_engine is not None:
                self._sync_manifest(artifact, payload)

            return {"artifact": artifact, "research": payload}
        except Exception as exc:
            if self.manifest_engine is not None:
                self.manifest_engine.fail_stage("RESEARCHING", str(exc))
            raise

    def _invoke_provider(self, request: LLMRequest) -> Any:
        result = self.provider.generate(request)
        if inspect.isawaitable(result):
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                return asyncio.run(result)
            raise RuntimeError("Async provider execution is not supported in this sync workflow")
        return result

    def _parse_payload(self, response: Any) -> Dict[str, Any]:
        text = ""
        if hasattr(response, "text"):
            text = getattr(response, "text") or ""
        elif isinstance(response, str):
            text = response
        elif isinstance(response, dict):
            text = response.get("text", "")
        if not text:
            raise RuntimeError("The provider returned an empty response")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Malformed research response") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("Malformed research response")
        return payload

    def _validate_payload(self, payload: Dict[str, Any]) -> None:
        schema = self._research_schema()
        required = schema.get("required", [])
        for field in required:
            if field not in payload:
                raise RuntimeError(f"Schema validation failure: missing '{field}'")

        if not isinstance(payload.get("topic"), str) or not payload.get("topic", "").strip():
            raise RuntimeError("Schema validation failure: 'topic' must be a non-empty string")
        if not isinstance(payload.get("summary"), str) or not payload.get("summary", "").strip():
            raise RuntimeError("Schema validation failure: 'summary' must be a non-empty string")

        for field in ("findings", "keywords", "timeline", "locations", "themes", "cultural_notes", "pronunciation_notes"):
            value = payload.get(field)
            if value is None:
                raise RuntimeError(f"Schema validation failure: missing '{field}'")
            if not isinstance(value, list):
                raise RuntimeError(f"Schema validation failure: '{field}' must be a list")

        for field in ("sources", "bibliography"):
            value = payload.get(field)
            if not isinstance(value, list):
                raise RuntimeError(f"Schema validation failure: '{field}' must be a list")
            for entry in value:
                if not isinstance(entry, dict):
                    raise RuntimeError(f"Schema validation failure: '{field}' entries must be objects")

        characters = payload.get("characters")
        if not isinstance(characters, list):
            raise RuntimeError("Schema validation failure: 'characters' must be a list")
        for item in characters:
            if not isinstance(item, dict):
                raise RuntimeError("Schema validation failure: 'characters' entries must be objects")
            for key in ("name", "role", "description"):
                if not isinstance(item.get(key), str):
                    raise RuntimeError(f"Schema validation failure: 'characters[{key}]' must be a string")

    def _build_artifact(self, title: str, data: Dict[str, Any]) -> ResearchArtifact:
        artifact = ResearchArtifact(
            topic=str(data.get("topic") or title),
            summary=str(data.get("summary") or ""),
            findings=[str(item) for item in data.get("findings", [])],
            sources=[dict(item) for item in data.get("sources", [])],
            keywords=[str(item) for item in data.get("keywords", [])],
            african_mythology=str(data.get("african_mythology") or ""),
            historical_context=str(data.get("historical_context") or ""),
            characters=[dict(item) for item in data.get("characters", [])],
            timeline=[str(item) for item in data.get("timeline", [])],
            locations=[str(item) for item in data.get("locations", [])],
            themes=[str(item) for item in data.get("themes", [])],
            cultural_notes=[str(item) for item in data.get("cultural_notes", [])],
            pronunciation_notes=[str(item) for item in data.get("pronunciation_notes", [])],
            bibliography=[dict(item) for item in data.get("bibliography", [])],
            visual_style=str(data.get("visual_style") or ""),
        )
        artifact.metadata.name = "research"
        artifact.metadata.description = "Research output"
        artifact.metadata.tags = ["research", "mythology"]
        artifact.metadata.category = "research"
        artifact.metadata.author = "mythforge"
        artifact.metadata.language = "en"
        artifact.provenance.provider = getattr(self.provider, "name", "openai")
        artifact.provenance.model = getattr(getattr(self.provider, "_config", None), "default_model", "") or "gpt-4o"
        artifact.provenance.workflow_stage = "RESEARCH"
        artifact.provenance.extra = {"title": title}
        artifact.content_hash = artifact.compute_hash()
        return artifact

    def _export_artifact(self, artifact: ResearchArtifact) -> None:
        target_dir = self.manifest_engine.project_dir if self.manifest_engine is not None else (self.output_dir or Path("."))
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "research.json").write_text(artifact.to_json(indent=2), encoding="utf-8")
        (target_dir / "research.md").write_text(artifact.to_markdown(), encoding="utf-8")

    def _sync_manifest(self, artifact: ResearchArtifact, payload: Dict[str, Any]) -> None:
        if self.manifest_engine is None:
            return
        self.manifest_engine.record_asset(
            AssetRecord(
                stage="RESEARCHING",
                kind="research",
                path="research.json",
                provider=getattr(self.provider, "name", "openai"),
                metadata={"artifact_id": artifact.artifact_id, "title": payload.get("topic", "")},
            )
        )
        self.manifest_engine.record_provider(
            ProviderRecord(
                capability="llm",
                provider=getattr(self.provider, "name", "openai"),
                model=getattr(getattr(self.provider, "_config", None), "default_model", "") or "gpt-4o",
                metadata={"stage": "RESEARCHING"},
            )
        )
        self.manifest_engine.complete_stage("RESEARCHING")
        self.manifest_engine.save()

    def _build_template_registry(self) -> TemplateRegistry:
        registry = TemplateRegistry()
        registry.register(
            PromptTemplate(
                name="research-brief",
                version="1.0.0",
                system_prompt="You are a research specialist for mythology content. You must return strict JSON and never include commentary outside the schema.",
                developer_prompt="Return strict JSON matching the requested schema.",
                user_prompt="Research the mythology topic: {{title}}. Return a JSON object with topic, summary, findings, sources, keywords, african_mythology, historical_context, characters, timeline, locations, themes, cultural_notes, pronunciation_notes, bibliography, visual_style.",
                variables=[VariableSpec(name="title", required=True, description="The video title to research")],
                output_schema=self._research_schema(),
                metadata=TemplateMetadata(description="Research brief template", tags=["research", "mythology"]),
            )
        )
        return registry

    def _research_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "summary": {"type": "string"},
                "findings": {"type": "array", "items": {"type": "string"}},
                "sources": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"title": {"type": "string"}, "url": {"type": "string"}},
                        "required": ["title", "url"],
                    },
                },
                "keywords": {"type": "array", "items": {"type": "string"}},
                "african_mythology": {"type": "string"},
                "historical_context": {"type": "string"},
                "characters": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}, "role": {"type": "string"}, "description": {"type": "string"}},
                        "required": ["name", "role", "description"],
                    },
                },
                "timeline": {"type": "array", "items": {"type": "string"}},
                "locations": {"type": "array", "items": {"type": "string"}},
                "themes": {"type": "array", "items": {"type": "string"}},
                "cultural_notes": {"type": "array", "items": {"type": "string"}},
                "pronunciation_notes": {"type": "array", "items": {"type": "string"}},
                "bibliography": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"title": {"type": "string"}, "url": {"type": "string"}},
                        "required": ["title", "url"],
                    },
                },
                "visual_style": {"type": "string"},
            },
            "required": ["topic", "summary", "findings", "sources", "keywords", "african_mythology", "historical_context", "characters", "timeline", "locations", "themes", "cultural_notes", "pronunciation_notes", "bibliography", "visual_style"],
        }
