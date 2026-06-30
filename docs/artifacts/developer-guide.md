# Developer Guide — Artifact System

## Creating a New Artifact Type

### 1. Define the class

```python
from mythforge.artifacts.base import BaseArtifact

class MyArtifact(BaseArtifact):
    my_field: str = ""
    optional_field: list[str] = []

    @classmethod
    def artifact_type(cls) -> str:
        return "MyArtifact"

    def _get_content_fields(self) -> dict:
        return {"my_field": self.my_field, "optional_field": self.optional_field}

    def validate(self) -> list[str]:
        errors = []
        if not self.my_field:
            errors.append("my_field is required")
        return errors
```

### 2. Register it

The artifact is auto-registered when imported via `mythforge/artifacts/__init__.py`. Add it to the `_ALL_ARTIFACTS` list:

```python
from .artifacts import MyArtifact

_ALL_ARTIFACTS = [
    # ... existing artifacts ...
    MyArtifact,
]
```

### 3. Add Markdown export

Override `_markdown_content()` in your class:

```python
def _markdown_content(self) -> str:
    lines = [f"## My Type: {self.my_field}"]
    if self.optional_field:
        for item in self.optional_field:
            lines.append(f"- {item}")
    return "\n".join(lines)
```

### 4. Write tests

```python
class TestMyArtifact:
    def test_create_valid(self):
        a = MyArtifact(my_field="value")
        assert a.artifact_type() == "MyArtifact"
        assert a.is_valid()

    def test_validation(self):
        a = MyArtifact()
        assert not a.is_valid()

    def test_json_roundtrip(self):
        a = MyArtifact(my_field="value")
        a.compute_hash()
        j = a.to_json()
        b = MyArtifact.from_json(j)
        assert b.my_field == "value"
        assert b.content_hash == a.content_hash
```

---

## Using Artifacts in Workflow Stages

```python
from mythforge.artifacts import (
    ScriptArtifact, ResearchArtifact, ArtifactProvenance, ArtifactExporter
)

# In a research stage
research = ResearchArtifact(
    topic="User topic",
    summary="...",
    provenance=ArtifactProvenance(
        provider="openai",
        model="gpt-4",
        workflow_stage="research",
    ),
)
research.compute_hash()

# In a scripting stage — consume research, produce script
script = ScriptArtifact(
    title="Generated Script",
    raw_text="...",
    provenance=ArtifactProvenance(
        provider="anthropic",
        model="claude-3",
        workflow_stage="scripting",
    ),
)
script.compute_hash()

# Export for debugging/logging
print(ArtifactExporter.to_markdown(script))
```

---

## Version Migration

When an artifact schema changes, register a migrator:

```python
from mythforge.artifacts import ArtifactRegistry

registry = ArtifactRegistry()

def migrate_v1_to_v2(data: dict) -> dict:
    data = dict(data)
    data["version"] = "2.0.0"
    data["content"]["new_field"] = ""
    return data

registry.register_migrator("MyArtifact", "1.0.0", migrate_v1_to_v2)
```

---

## Best Practices

1. **Always validate** before passing artifacts between stages.
2. **Always hash** after creation for integrity checks.
3. **Attach provenance** to every artifact produced by a provider.
4. **Never put provider logic** inside artifact classes.
5. **Use the factory** to reconstruct artifacts from serialized data.
6. **Use the exporter** for human-readable output (debugging, logging).