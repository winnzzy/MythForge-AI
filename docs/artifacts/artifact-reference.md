# Artifact Reference

Complete reference for all 11 MythForge artifact types.

---

## ResearchArtifact

Research results from the research stage.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `topic` | `str` | Yes | Research topic |
| `summary` | `str` | Yes | Executive summary |
| `findings` | `list[str]` | No | Key findings |
| `sources` | `list[str]` | No | Source URLs |
| `keywords` | `list[str]` | No | Search keywords |

---

## ScriptArtifact

Screenplay with scenes and dialogue.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | `str` | Yes | Script title |
| `genre` | `str` | No | Genre |
| `raw_text` | `str` | Yes* | Raw screenplay text |
| `scenes` | `list[dict]` | Yes* | Parsed scene list |
| `characters` | `list[dict]` | No | Character descriptions |

\* At least one of `raw_text` or `scenes` must be provided.

---

## SceneArtifact

Single scene description.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `heading` | `str` | Yes | Scene heading (e.g. "INT. OFFICE - DAY") |
| `action` | `str` | Yes | Action description |
| `scene_id` | `str` | No | Unique scene identifier |
| `mood` | `str` | No | Mood/atmosphere |
| `location` | `str` | No | Location name |
| `dialogue` | `list[dict]` | No | Dialogue lines |
| `transitions` | `list[str]` | No | Scene transitions |
| `sound_effects` | `list[str]` | No | Sound effect cues |
| `camera_directions` | `list[str]` | No | Camera directions |
| `voiceover` | `str` | No | Voiceover text |

---

## ImageArtifact

Generated or sourced image.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | `str` | Yes | Generation prompt |
| `file_path` | `str` | Yes* | Local file path |
| `url` | `str` | Yes* | Remote URL |
| `scene_id` | `str` | No | Associated scene |
| `width` | `int` | No | Image width |
| `height` | `int` | No | Image height |
| `seed` | `int` | No | Generation seed |
| `style` | `str` | No | Style description |

\* At least one of `file_path` or `url` must be provided.

---

## NarrationArtifact

Narration audio with transcript.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | `str` | Yes | Narration text |
| `voice` | `str` | Yes | Voice identifier |
| `file_path` | `str` | No | Audio file path |
| `duration_s` | `float` | No | Duration in seconds |
| `segments` | `list[dict]` | No | Timed segments |
| `scene_id` | `str` | No | Associated scene |
| `speed` | `float` | No | Playback speed |

---

## MusicArtifact

Background music track.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | `str` | Yes | Track title |
| `mood` | `str` | Yes | Mood descriptor |
| `file_path` | `str` | No | Audio file path |
| `tempo_bpm` | `int` | No | Tempo in BPM |
| `key` | `str` | No | Musical key |
| `duration_s` | `float` | No | Duration |
| `genre` | `str` | No | Musical genre |
| `scene_ids` | `list[str]` | No | Associated scenes |

---

## SFXArtifact

Sound effect.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `str` | Yes | Effect name |
| `file_path` | `str` | Yes | Audio file path |
| `category` | `str` | No | Category (nature, impact, etc.) |
| `trigger` | `str` | No | What triggers this effect |
| `volume` | `float` | No | Volume 0.0-1.0 |
| `scene_id` | `str` | No | Associated scene |

---

## TimelineArtifact

Master compositing timeline.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `duration_s` | `float` | Yes | Total duration (must be > 0) |
| `fps` | `float` | No | Frames per second |
| `resolution` | `dict` | No | `{width, height}` |
| `tracks` | `list[dict]` | No | Timeline tracks |
| `transitions` | `list[dict]` | No | Track transitions |

---

## ThumbnailArtifact

Video thumbnail.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file_path` | `str` | Yes* | Image file path |
| `url` | `str` | Yes* | Image URL |
| `title` | `str` | No | Title text |
| `width` | `int` | No | Image width |
| `height` | `int` | No | Image height |
| `overlay_text` | `str` | No | Text overlay |
| `style` | `str` | No | Visual style |

---

## MetadataArtifact

Project-level metadata.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | `str` | Yes | Project title |
| `description` | `str` | No | Description |
| `tags` | `list[str]` | No | Tags |
| `category` | `str` | No | Category |
| `platform` | `str` | No | Target platform |
| `language` | `str` | No | Language code |
| `visibility` | `str` | No | public/private/unlisted |
| `custom` | `dict` | No | Custom metadata |

---

## VideoArtifact

Final rendered video.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | `str` | Yes | Video title |
| `file_path` | `str` | Yes* | Video file path |
| `url` | `str` | Yes* | Video URL |
| `width` | `int` | No | Resolution width |
| `height` | `int` | No | Resolution height |
| `fps` | `float` | No | Frame rate |
| `duration_s` | `float` | No | Duration |
| `codec` | `str` | No | Video codec |
| `scene_ids` | `list[str]` | No | Source scenes |
| `timeline_id` | `str` | No | Source timeline |

---

## Common Operations (All Types)

```python
# Validate
errors = artifact.validate()
valid = artifact.is_valid()

# Hash
artifact.compute_hash()

# Serialize
json_str = artifact.to_json()
yaml_str = artifact.to_yaml()
dict_data = artifact.to_dict()

# Deserialize (classmethods)
artifact = MyArtifact.from_json(json_str)
artifact = MyArtifact.from_yaml(yaml_str)
artifact = MyArtifact.from_dict(dict_data)

# Export
md = artifact.to_markdown()

# Type
name = artifact.artifact_type()