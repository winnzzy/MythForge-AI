"""
Concrete artifact types for the MythForge pipeline.

Each artifact is a strongly-typed container for workflow data.  Artifacts
never contain provider-specific logic — they hold pure domain data.

Artifact types:
    ResearchArtifact, ScriptArtifact, SceneArtifact, ImageArtifact,
    NarrationArtifact, MusicArtifact, SFXArtifact, TimelineArtifact,
    ThumbnailArtifact, MetadataArtifact, VideoArtifact
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import BaseArtifact
from .models import ArtifactMetadata, ArtifactProvenance
from .versioning import ArtifactVersion


# ---------------------------------------------------------------------------
# Research Artifact
# ---------------------------------------------------------------------------

class ResearchArtifact(BaseArtifact):
    """Research results: topics, findings, sources, summaries, and cultural notes."""

    def __init__(
        self,
        *,
        topic: str = "",
        summary: str = "",
        findings: Optional[List[str]] = None,
        sources: Optional[List[Dict[str, str]]] = None,
        keywords: Optional[List[str]] = None,
        african_mythology: str = "",
        historical_context: str = "",
        characters: Optional[List[Dict[str, str]]] = None,
        timeline: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
        themes: Optional[List[str]] = None,
        cultural_notes: Optional[List[str]] = None,
        pronunciation_notes: Optional[List[str]] = None,
        bibliography: Optional[List[Dict[str, str]]] = None,
        visual_style: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.topic = topic
        self.summary = summary
        self.findings = findings or []
        self.sources = sources or []
        self.keywords = keywords or []
        self.african_mythology = african_mythology
        self.historical_context = historical_context
        self.characters = characters or []
        self.timeline = timeline or []
        self.locations = locations or []
        self.themes = themes or []
        self.cultural_notes = cultural_notes or []
        self.pronunciation_notes = pronunciation_notes or []
        self.bibliography = bibliography or []
        self.visual_style = visual_style

    @classmethod
    def artifact_type(cls) -> str:
        return "ResearchArtifact"

    def content_fields(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "summary": self.summary,
            "findings": self.findings,
            "sources": self.sources,
            "keywords": self.keywords,
            "african_mythology": self.african_mythology,
            "historical_context": self.historical_context,
            "characters": self.characters,
            "timeline": self.timeline,
            "locations": self.locations,
            "themes": self.themes,
            "cultural_notes": self.cultural_notes,
            "pronunciation_notes": self.pronunciation_notes,
            "bibliography": self.bibliography,
            "visual_style": self.visual_style,
        }

    def validate_content(self) -> List[str]:
        errors = []
        if not self.topic:
            errors.append("ResearchArtifact: topic is required")
        if not self.summary:
            errors.append("ResearchArtifact: summary is required")
        return errors

    def to_markdown(self) -> str:
        parts = [f"## Research: {self.topic}", "", self.summary, ""]
        if self.findings:
            parts.append("### Findings")
            for i, f in enumerate(self.findings, 1):
                parts.append(f"{i}. {f}")
            parts.append("")
        if self.african_mythology:
            parts.append("### African mythology")
            parts.append(self.african_mythology)
            parts.append("")
        if self.historical_context:
            parts.append("### Historical context")
            parts.append(self.historical_context)
            parts.append("")
        if self.characters:
            parts.append("### Characters")
            for character in self.characters:
                parts.append(f"- **{character.get('name', '')}**: {character.get('description', '')}")
            parts.append("")
        if self.timeline:
            parts.append("### Timeline")
            for item in self.timeline:
                parts.append(f"- {item}")
            parts.append("")
        if self.locations:
            parts.append("### Locations")
            for item in self.locations:
                parts.append(f"- {item}")
            parts.append("")
        if self.keywords:
            parts.append(f"**Keywords:** {', '.join(self.keywords)}")
        if self.sources:
            parts.append("### Sources")
            for s in self.sources:
                parts.append(f"- [{s.get('title', 'Source')}]({s.get('url', '')})")
        return "\n".join(parts)

    def _content_dict(self) -> Dict[str, Any]:
        return self.content_fields()

    @classmethod
    def _from_content_dict(cls, data: Dict[str, Any], **kwargs) -> ResearchArtifact:
        return cls(
            topic=data.get("topic", ""),
            summary=data.get("summary", ""),
            findings=data.get("findings", []),
            sources=data.get("sources", []),
            keywords=data.get("keywords", []),
            african_mythology=data.get("african_mythology", ""),
            historical_context=data.get("historical_context", ""),
            characters=data.get("characters", []),
            timeline=data.get("timeline", []),
            locations=data.get("locations", []),
            themes=data.get("themes", []),
            cultural_notes=data.get("cultural_notes", []),
            pronunciation_notes=data.get("pronunciation_notes", []),
            bibliography=data.get("bibliography", []),
            visual_style=data.get("visual_style", ""),
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Script Artifact
# ---------------------------------------------------------------------------

class ScriptArtifact(BaseArtifact):
    """Screenplay / narration script with scenes, dialogue, and directions."""

    def __init__(
        self,
        *,
        title: str = "",
        genre: str = "",
        logline: str = "",
        scenes: List[Dict[str, Any]] = None,
        characters: List[Dict[str, str]] = None,
        raw_text: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.title = title
        self.genre = genre
        self.logline = logline
        self.scenes = scenes or []
        self.characters = characters or []
        self.raw_text = raw_text

    @classmethod
    def artifact_type(cls) -> str:
        return "ScriptArtifact"

    def content_fields(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "genre": self.genre,
            "logline": self.logline,
            "scenes": self.scenes,
            "characters": self.characters,
            "raw_text": self.raw_text,
        }

    def validate_content(self) -> List[str]:
        errors = []
        if not self.title:
            errors.append("ScriptArtifact: title is required")
        if not self.raw_text and not self.scenes:
            errors.append("ScriptArtifact: raw_text or scenes required")
        return errors

    def to_markdown(self) -> str:
        parts = [f"## Script: {self.title}", ""]
        if self.genre:
            parts.append(f"**Genre:** {self.genre}")
        if self.logline:
            parts.append(f"**Logline:** {self.logline}")
        parts.append("")
        if self.characters:
            parts.append("### Characters")
            for c in self.characters:
                parts.append(f"- **{c.get('name', '')}**: {c.get('description', '')}")
            parts.append("")
        if self.scenes:
            for i, scene in enumerate(self.scenes, 1):
                parts.append(f"### Scene {i}: {scene.get('heading', '')}")
                parts.append(scene.get("action", ""))
                for d in scene.get("dialogue", []):
                    parts.append(f"**{d.get('character', '')}:** {d.get('line', '')}")
                parts.append("")
        elif self.raw_text:
            parts.append(self.raw_text)
        return "\n".join(parts)

    def _content_dict(self) -> Dict[str, Any]:
        return self.content_fields()

    @classmethod
    def _from_content_dict(cls, data: Dict[str, Any], **kwargs) -> ScriptArtifact:
        return cls(
            title=data.get("title", ""),
            genre=data.get("genre", ""),
            logline=data.get("logline", ""),
            scenes=data.get("scenes", []),
            characters=data.get("characters", []),
            raw_text=data.get("raw_text", ""),
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Scene Artifact
# ---------------------------------------------------------------------------

class SceneArtifact(BaseArtifact):
    """A single scene description with visual direction and dialogue."""

    def __init__(
        self,
        *,
        scene_id: str = "",
        heading: str = "",
        action: str = "",
        dialogue: List[Dict[str, str]] = None,
        visual_direction: str = "",
        location: str = "",
        time_of_day: str = "",
        mood: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.scene_id = scene_id
        self.heading = heading
        self.action = action
        self.dialogue = dialogue or []
        self.visual_direction = visual_direction
        self.location = location
        self.time_of_day = time_of_day
        self.mood = mood

    @classmethod
    def artifact_type(cls) -> str:
        return "SceneArtifact"

    def content_fields(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "heading": self.heading,
            "action": self.action,
            "dialogue": self.dialogue,
            "visual_direction": self.visual_direction,
            "location": self.location,
            "time_of_day": self.time_of_day,
            "mood": self.mood,
        }

    def validate_content(self) -> List[str]:
        errors = []
        if not self.heading:
            errors.append("SceneArtifact: heading is required")
        if not self.action:
            errors.append("SceneArtifact: action is required")
        return errors

    def to_markdown(self) -> str:
        parts = [f"## Scene: {self.heading}", ""]
        if self.location:
            parts.append(f"**Location:** {self.location}")
        if self.time_of_day:
            parts.append(f"**Time:** {self.time_of_day}")
        if self.mood:
            parts.append(f"**Mood:** {self.mood}")
        parts.append("")
        parts.append(self.action)
        if self.visual_direction:
            parts.append(f"\n**Visual Direction:** {self.visual_direction}")
        if self.dialogue:
            parts.append("\n### Dialogue")
            for d in self.dialogue:
                parts.append(f"**{d.get('character', '')}:** {d.get('line', '')}")
        return "\n".join(parts)

    def _content_dict(self) -> Dict[str, Any]:
        return self.content_fields()

    @classmethod
    def _from_content_dict(cls, data: Dict[str, Any], **kwargs) -> SceneArtifact:
        return cls(
            scene_id=data.get("scene_id", ""),
            heading=data.get("heading", ""),
            action=data.get("action", ""),
            dialogue=data.get("dialogue", []),
            visual_direction=data.get("visual_direction", ""),
            location=data.get("location", ""),
            time_of_day=data.get("time_of_day", ""),
            mood=data.get("mood", ""),
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Image Artifact
# ---------------------------------------------------------------------------

class ImageArtifact(BaseArtifact):
    """Generated or sourced image (still frame, concept art, etc.)."""

    def __init__(
        self,
        *,
        prompt: str = "",
        negative_prompt: str = "",
        file_path: str = "",
        url: str = "",
        width: int = 0,
        height: int = 0,
        format: str = "",
        seed: int = 0,
        style: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.prompt = prompt
        self.negative_prompt = negative_prompt
        self.file_path = file_path
        self.url = url
        self.width = width
        self.height = height
        self.format = format
        self.seed = seed
        self.style = style
        # Sync dimensions to metadata
        if width and height:
            self.metadata.dimensions = {"width": width, "height": height}

    @classmethod
    def artifact_type(cls) -> str:
        return "ImageArtifact"

    def content_fields(self) -> Dict[str, Any]:
        return {
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "file_path": self.file_path,
            "url": self.url,
            "width": self.width,
            "height": self.height,
            "format": self.format,
            "seed": self.seed,
            "style": self.style,
        }

    def validate_content(self) -> List[str]:
        errors = []
        if not self.prompt:
            errors.append("ImageArtifact: prompt is required")
        if not self.file_path and not self.url:
            errors.append("ImageArtifact: file_path or url required")
        return errors

    def to_markdown(self) -> str:
        parts = ["## Image", ""]
        parts.append(f"**Prompt:** {self.prompt}")
        if self.negative_prompt:
            parts.append(f"**Negative Prompt:** {self.negative_prompt}")
        parts.append(f"**Dimensions:** {self.width}x{self.height}")
        if self.format:
            parts.append(f"**Format:** {self.format}")
        if self.style:
            parts.append(f"**Style:** {self.style}")
        if self.seed:
            parts.append(f"**Seed:** {self.seed}")
        if self.file_path:
            parts.append(f"**File:** {self.file_path}")
        return "\n".join(parts)

    def _content_dict(self) -> Dict[str, Any]:
        return self.content_fields()

    @classmethod
    def _from_content_dict(cls, data: Dict[str, Any], **kwargs) -> ImageArtifact:
        return cls(
            prompt=data.get("prompt", ""),
            negative_prompt=data.get("negative_prompt", ""),
            file_path=data.get("file_path", ""),
            url=data.get("url", ""),
            width=data.get("width", 0),
            height=data.get("height", 0),
            format=data.get("format", ""),
            seed=data.get("seed", 0),
            style=data.get("style", ""),
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Narration Artifact
# ---------------------------------------------------------------------------

class NarrationArtifact(BaseArtifact):
    """Narration audio with transcript and timing."""

    def __init__(
        self,
        *,
        text: str = "",
        voice: str = "",
        file_path: str = "",
        duration_s: float = 0.0,
        language: str = "en",
        segments: List[Dict[str, Any]] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.text = text
        self.voice = voice
        self.file_path = file_path
        self.duration_s = duration_s
        self.language = language
        self.segments = segments or []
        if duration_s:
            self.metadata.duration_s = duration_s

    @classmethod
    def artifact_type(cls) -> str:
        return "NarrationArtifact"

    def content_fields(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "voice": self.voice,
            "file_path": self.file_path,
            "duration_s": self.duration_s,
            "language": self.language,
            "segments": self.segments,
        }

    def validate_content(self) -> List[str]:
        errors = []
        if not self.text:
            errors.append("NarrationArtifact: text is required")
        if not self.voice:
            errors.append("NarrationArtifact: voice is required")
        return errors

    def to_markdown(self) -> str:
        parts = ["## Narration", ""]
        parts.append(f"**Voice:** {self.voice}")
        parts.append(f"**Language:** {self.language}")
        if self.duration_s:
            parts.append(f"**Duration:** {self.duration_s:.2f}s")
        parts.append("")
        parts.append(self.text)
        if self.segments:
            parts.append("\n### Segments")
            for seg in self.segments:
                parts.append(f"- [{seg.get('start', 0):.2f}s - {seg.get('end', 0):.2f}s] {seg.get('text', '')}")
        return "\n".join(parts)

    def _content_dict(self) -> Dict[str, Any]:
        return self.content_fields()

    @classmethod
    def _from_content_dict(cls, data: Dict[str, Any], **kwargs) -> NarrationArtifact:
        return cls(
            text=data.get("text", ""),
            voice=data.get("voice", ""),
            file_path=data.get("file_path", ""),
            duration_s=data.get("duration_s", 0.0),
            language=data.get("language", "en"),
            segments=data.get("segments", []),
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Music Artifact
# ---------------------------------------------------------------------------

class MusicArtifact(BaseArtifact):
    """Background music track with mood, tempo, and file reference."""

    def __init__(
        self,
        *,
        title: str = "",
        mood: str = "",
        tempo_bpm: int = 0,
        key: str = "",
        file_path: str = "",
        duration_s: float = 0.0,
        genre: str = "",
        loop: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.title = title
        self.mood = mood
        self.tempo_bpm = tempo_bpm
        self.key = key
        self.file_path = file_path
        self.duration_s = duration_s
        self.genre = genre
        self.loop = loop
        if duration_s:
            self.metadata.duration_s = duration_s

    @classmethod
    def artifact_type(cls) -> str:
        return "MusicArtifact"

    def content_fields(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "mood": self.mood,
            "tempo_bpm": self.tempo_bpm,
            "key": self.key,
            "file_path": self.file_path,
            "duration_s": self.duration_s,
            "genre": self.genre,
            "loop": self.loop,
        }

    def validate_content(self) -> List[str]:
        errors = []
        if not self.title:
            errors.append("MusicArtifact: title is required")
        if not self.mood:
            errors.append("MusicArtifact: mood is required")
        return errors

    def to_markdown(self) -> str:
        parts = ["## Music", ""]
        parts.append(f"**Title:** {self.title}")
        parts.append(f"**Mood:** {self.mood}")
        if self.genre:
            parts.append(f"**Genre:** {self.genre}")
        if self.tempo_bpm:
            parts.append(f"**Tempo:** {self.tempo_bpm} BPM")
        if self.key:
            parts.append(f"**Key:** {self.key}")
        if self.duration_s:
            parts.append(f"**Duration:** {self.duration_s:.2f}s")
        parts.append(f"**Loop:** {'Yes' if self.loop else 'No'}")
        if self.file_path:
            parts.append(f"**File:** {self.file_path}")
        return "\n".join(parts)

    def _content_dict(self) -> Dict[str, Any]:
        return self.content_fields()

    @classmethod
    def _from_content_dict(cls, data: Dict[str, Any], **kwargs) -> MusicArtifact:
        return cls(
            title=data.get("title", ""),
            mood=data.get("mood", ""),
            tempo_bpm=data.get("tempo_bpm", 0),
            key=data.get("key", ""),
            file_path=data.get("file_path", ""),
            duration_s=data.get("duration_s", 0.0),
            genre=data.get("genre", ""),
            loop=data.get("loop", False),
            **kwargs,
        )


# ---------------------------------------------------------------------------
# SFX Artifact
# ---------------------------------------------------------------------------

class SFXArtifact(BaseArtifact):
    """Sound effect with trigger, category, and file reference."""

    def __init__(
        self,
        *,
        name: str = "",
        category: str = "",
        trigger: str = "",
        file_path: str = "",
        duration_s: float = 0.0,
        volume: float = 1.0,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.category = category
        self.trigger = trigger
        self.file_path = file_path
        self.duration_s = duration_s
        self.volume = volume
        if duration_s:
            self.metadata.duration_s = duration_s

    @classmethod
    def artifact_type(cls) -> str:
        return "SFXArtifact"

    def content_fields(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "trigger": self.trigger,
            "file_path": self.file_path,
            "duration_s": self.duration_s,
            "volume": self.volume,
        }

    def validate_content(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("SFXArtifact: name is required")
        if not self.file_path:
            errors.append("SFXArtifact: file_path is required")
        return errors

    def to_markdown(self) -> str:
        parts = ["## Sound Effect", ""]
        parts.append(f"**Name:** {self.name}")
        if self.category:
            parts.append(f"**Category:** {self.category}")
        if self.trigger:
            parts.append(f"**Trigger:** {self.trigger}")
        if self.duration_s:
            parts.append(f"**Duration:** {self.duration_s:.2f}s")
        parts.append(f"**Volume:** {self.volume}")
        if self.file_path:
            parts.append(f"**File:** {self.file_path}")
        return "\n".join(parts)

    def _content_dict(self) -> Dict[str, Any]:
        return self.content_fields()

    @classmethod
    def _from_content_dict(cls, data: Dict[str, Any], **kwargs) -> SFXArtifact:
        return cls(
            name=data.get("name", ""),
            category=data.get("category", ""),
            trigger=data.get("trigger", ""),
            file_path=data.get("file_path", ""),
            duration_s=data.get("duration_s", 0.0),
            volume=data.get("volume", 1.0),
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Timeline Artifact
# ---------------------------------------------------------------------------

class TimelineArtifact(BaseArtifact):
    """Master timeline with tracks and clips for compositing."""

    def __init__(
        self,
        *,
        duration_s: float = 0.0,
        fps: float = 24.0,
        resolution: Dict[str, int] = None,
        tracks: List[Dict[str, Any]] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.duration_s = duration_s
        self.fps = fps
        self.resolution = resolution or {"width": 1920, "height": 1080}
        self.tracks = tracks or []
        if duration_s:
            self.metadata.duration_s = duration_s

    @classmethod
    def artifact_type(cls) -> str:
        return "TimelineArtifact"

    def content_fields(self) -> Dict[str, Any]:
        return {
            "duration_s": self.duration_s,
            "fps": self.fps,
            "resolution": self.resolution,
            "tracks": self.tracks,
        }

    def validate_content(self) -> List[str]:
        errors = []
        if self.duration_s <= 0:
            errors.append("TimelineArtifact: duration_s must be positive")
        if self.fps <= 0:
            errors.append("TimelineArtifact: fps must be positive")
        return errors

    def to_markdown(self) -> str:
        parts = ["## Timeline", ""]
        parts.append(f"**Duration:** {self.duration_s:.2f}s")
        parts.append(f"**FPS:** {self.fps}")
        parts.append(f"**Resolution:** {self.resolution.get('width', 0)}x{self.resolution.get('height', 0)}")
        parts.append(f"**Tracks:** {len(self.tracks)}")
        for track in self.tracks:
            parts.append(f"\n### Track: {track.get('name', 'Unnamed')} ({track.get('type', 'unknown')})")
            for clip in track.get("clips", []):
                parts.append(f"- [{clip.get('start', 0):.2f}s - {clip.get('end', 0):.2f}s] {clip.get('label', '')}")
        return "\n".join(parts)

    def _content_dict(self) -> Dict[str, Any]:
        return self.content_fields()

    @classmethod
    def _from_content_dict(cls, data: Dict[str, Any], **kwargs) -> TimelineArtifact:
        return cls(
            duration_s=data.get("duration_s", 0.0),
            fps=data.get("fps", 24.0),
            resolution=data.get("resolution", {"width": 1920, "height": 1080}),
            tracks=data.get("tracks", []),
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Thumbnail Artifact
# ---------------------------------------------------------------------------

class ThumbnailArtifact(BaseArtifact):
    """Thumbnail image for video/content discovery."""

    def __init__(
        self,
        *,
        title: str = "",
        file_path: str = "",
        url: str = "",
        width: int = 1280,
        height: int = 720,
        format: str = "png",
        style: str = "",
        overlay_text: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.title = title
        self.file_path = file_path
        self.url = url
        self.width = width
        self.height = height
        self.format = format
        self.style = style
        self.overlay_text = overlay_text

    @classmethod
    def artifact_type(cls) -> str:
        return "ThumbnailArtifact"

    def content_fields(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "file_path": self.file_path,
            "url": self.url,
            "width": self.width,
            "height": self.height,
            "format": self.format,
            "style": self.style,
            "overlay_text": self.overlay_text,
        }

    def validate_content(self) -> List[str]:
        errors = []
        if not self.file_path and not self.url:
            errors.append("ThumbnailArtifact: file_path or url required")
        return errors

    def to_markdown(self) -> str:
        parts = ["## Thumbnail", ""]
        if self.title:
            parts.append(f"**Title:** {self.title}")
        parts.append(f"**Dimensions:** {self.width}x{self.height}")
        parts.append(f"**Format:** {self.format}")
        if self.style:
            parts.append(f"**Style:** {self.style}")
        if self.overlay_text:
            parts.append(f"**Overlay Text:** {self.overlay_text}")
        if self.file_path:
            parts.append(f"**File:** {self.file_path}")
        return "\n".join(parts)

    def _content_dict(self) -> Dict[str, Any]:
        return self.content_fields()

    @classmethod
    def _from_content_dict(cls, data: Dict[str, Any], **kwargs) -> ThumbnailArtifact:
        return cls(
            title=data.get("title", ""),
            file_path=data.get("file_path", ""),
            url=data.get("url", ""),
            width=data.get("width", 1280),
            height=data.get("height", 720),
            format=data.get("format", "png"),
            style=data.get("style", ""),
            overlay_text=data.get("overlay_text", ""),
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Metadata Artifact
# ---------------------------------------------------------------------------

class MetadataArtifact(BaseArtifact):
    """Project-level metadata: title, description, tags, publishing info."""

    def __init__(
        self,
        *,
        title: str = "",
        description: str = "",
        tags: List[str] = None,
        category: str = "",
        language: str = "en",
        visibility: str = "private",
        publish_date: str = "",
        platform: str = "",
        extra: Dict[str, Any] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.title = title
        self.description = description
        self.tags = tags or []
        self.category = category
        self.language = language
        self.visibility = visibility
        self.publish_date = publish_date
        self.platform = platform
        self.extra = extra or {}

    @classmethod
    def artifact_type(cls) -> str:
        return "MetadataArtifact"

    def content_fields(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "tags": self.tags,
            "category": self.category,
            "language": self.language,
            "visibility": self.visibility,
            "publish_date": self.publish_date,
            "platform": self.platform,
            "extra": self.extra,
        }

    def validate_content(self) -> List[str]:
        errors = []
        if not self.title:
            errors.append("MetadataArtifact: title is required")
        return errors

    def to_markdown(self) -> str:
        parts = ["## Metadata", ""]
        parts.append(f"**Title:** {self.title}")
        if self.description:
            parts.append(f"**Description:** {self.description}")
        if self.tags:
            parts.append(f"**Tags:** {', '.join(self.tags)}")
        if self.category:
            parts.append(f"**Category:** {self.category}")
        parts.append(f"**Language:** {self.language}")
        parts.append(f"**Visibility:** {self.visibility}")
        if self.platform:
            parts.append(f"**Platform:** {self.platform}")
        if self.publish_date:
            parts.append(f"**Publish Date:** {self.publish_date}")
        return "\n".join(parts)

    def _content_dict(self) -> Dict[str, Any]:
        return self.content_fields()

    @classmethod
    def _from_content_dict(cls, data: Dict[str, Any], **kwargs) -> MetadataArtifact:
        return cls(
            title=data.get("title", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            category=data.get("category", ""),
            language=data.get("language", "en"),
            visibility=data.get("visibility", "private"),
            publish_date=data.get("publish_date", ""),
            platform=data.get("platform", ""),
            extra=data.get("extra", {}),
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Video Artifact
# ---------------------------------------------------------------------------

class VideoArtifact(BaseArtifact):
    """Final rendered video or intermediate render."""

    def __init__(
        self,
        *,
        title: str = "",
        file_path: str = "",
        url: str = "",
        width: int = 1920,
        height: int = 1080,
        fps: float = 24.0,
        duration_s: float = 0.0,
        format: str = "mp4",
        codec: str = "h264",
        bitrate: str = "",
        file_size_bytes: int = 0,
        scene_ids: List[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.title = title
        self.file_path = file_path
        self.url = url
        self.width = width
        self.height = height
        self.fps = fps
        self.duration_s = duration_s
        self.format = format
        self.codec = codec
        self.bitrate = bitrate
        self.file_size_bytes = file_size_bytes
        self.scene_ids = scene_ids or []
        if duration_s:
            self.metadata.duration_s = duration_s
        if file_size_bytes:
            self.metadata.file_size_bytes = file_size_bytes

    @classmethod
    def artifact_type(cls) -> str:
        return "VideoArtifact"

    def content_fields(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "file_path": self.file_path,
            "url": self.url,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "duration_s": self.duration_s,
            "format": self.format,
            "codec": self.codec,
            "bitrate": self.bitrate,
            "file_size_bytes": self.file_size_bytes,
            "scene_ids": self.scene_ids,
        }

    def validate_content(self) -> List[str]:
        errors = []
        if not self.title:
            errors.append("VideoArtifact: title is required")
        if not self.file_path and not self.url:
            errors.append("VideoArtifact: file_path or url required")
        return errors

    def to_markdown(self) -> str:
        parts = ["## Video", ""]
        parts.append(f"**Title:** {self.title}")
        parts.append(f"**Resolution:** {self.width}x{self.height}")
        parts.append(f"**FPS:** {self.fps}")
        if self.duration_s:
            parts.append(f"**Duration:** {self.duration_s:.2f}s")
        parts.append(f"**Format:** {self.format}")
        parts.append(f"**Codec:** {self.codec}")
        if self.bitrate:
            parts.append(f"**Bitrate:** {self.bitrate}")
        if self.file_size_bytes:
            parts.append(f"**Size:** {self.file_size_bytes:,} bytes")
        if self.scene_ids:
            parts.append(f"**Scene IDs:** {', '.join(self.scene_ids)}")
        if self.file_path:
            parts.append(f"**File:** {self.file_path}")
        return "\n".join(parts)

    def _content_dict(self) -> Dict[str, Any]:
        return self.content_fields()

    @classmethod
    def _from_content_dict(cls, data: Dict[str, Any], **kwargs) -> VideoArtifact:
        return cls(
            title=data.get("title", ""),
            file_path=data.get("file_path", ""),
            url=data.get("url", ""),
            width=data.get("width", 1920),
            height=data.get("height", 1080),
            fps=data.get("fps", 24.0),
            duration_s=data.get("duration_s", 0.0),
            format=data.get("format", "mp4"),
            codec=data.get("codec", "h264"),
            bitrate=data.get("bitrate", ""),
            file_size_bytes=data.get("file_size_bytes", 0),
            scene_ids=data.get("scene_ids", []),
            **kwargs,
        )