# MythForge AI — Character Bible Design

## Overview

The Character Bible is a structured data system that ensures visual and narrative consistency of mythological characters across all videos in the MythForge AI catalog. It serves as the single source of truth for character appearance, personality, voice, and behavior — enabling any agent in the pipeline to reference character attributes without ambiguity.

---

## Purpose

The Character Bible solves three critical problems:

1. **Visual Consistency**: When Shango appears in multiple videos, he must look the same every time. The Character Bible defines his exact visual attributes so every image prompt produces consistent results.

2. **Narrative Consistency**: When Shango speaks or acts, his personality must be consistent. The Character Bible defines his personality traits, speech patterns, and behavioral tendencies.

3. **Cultural Authenticity**: Every character must be depicted respectfully and accurately. The Character Bible includes cultural notes that prevent misrepresentation.

---

## Architecture

```
mythforge/
└── knowledge/
    └── characters/
        ├── _schema.json           # Character schema definition
        ├── _style_anchors.json    # Shared style anchors per mythology
        ├── shango.json            # Shango character bible
        ├── oya.json               # Oya character bible
        ├── anansi.json            # Anansi character bible
        ├── mami_wata.json         # Mami Wata character bible
        └── ...
```

---

## Character Bible Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["id", "name", "mythology_origin", "visual", "personality", "cultural"],
  "properties": {
    "id": {
      "type": "string",
      "description": "Unique identifier (lowercase, underscores)"
    },
    "name": {
      "type": "string",
      "description": "Primary display name"
    },
    "alternative_names": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Alternate spellings, regional names, translations"
    },
    "mythology_origin": {
      "type": "string",
      "enum": ["yoruba", "egyptian", "greek", "norse", "hindu", "celtic", "mesoamerican", "japanese", "other"],
      "description": "Cultural origin of the mythology"
    },
    "type": {
      "type": "string",
      "enum": ["deity", "hero", "creature", "spirit", "trickster", "king", "warrior", "sage"],
      "description": "Character archetype"
    },
    "visual": {
      "type": "object",
      "required": ["appearance", "skin_tone", "build", "clothing", "distinguishing_features"],
      "properties": {
        "appearance": {
          "type": "string",
          "description": "One-sentence overall appearance summary for image prompts"
        },
        "skin_tone": {
          "type": "string",
          "description": "Specific skin tone description (culturally accurate)"
        },
        "build": {
          "type": "string",
          "description": "Body type and physical stature"
        },
        "clothing": {
          "type": "string",
          "description": "Default clothing/garments description"
        },
        "accessories": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Jewelry, weapons, symbolic items always present"
        },
        "distinguishing_features": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Unique visual markers (scars, marks, supernatural features)"
        },
        "color_palette": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Primary colors associated with this character"
        },
        "prompt_fragment": {
          "type": "string",
          "description": "Pre-written prompt fragment for consistent image generation"
        }
      }
    },
    "personality": {
      "type": "object",
      "required": ["traits", "speech_style", "motivation"],
      "properties": {
        "traits": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Core personality traits (3-7 words)"
        },
        "speech_style": {
          "type": "string",
          "description": "How this character speaks (formal, poetic, booming, etc.)"
        },
        "motivation": {
          "type": "string",
          "description": "What drives this character"
        },
        "fears": {
          "type": "array",
          "items": { "type": "string" },
          "description": "What this character fears or avoids"
        },
        "values": {
          "type": "array",
          "items": { "type": "string" },
          "description": "What this character values most"
        }
      }
    },
    "cultural": {
      "type": "object",
      "required": ["actively_worshipped", "sensitivity_notes"],
      "properties": {
        "actively_worshipped": {
          "type": "boolean",
          "description": "Whether this character is part of a living religion"
        },
        "sensitivity_notes": {
          "type": "string",
          "description": "Guidelines for respectful representation"
        },
        "taboos": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Things that must NEVER be depicted or said about this character"
        },
        "sacred_elements": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Elements that must be treated with reverence"
        },
        "sources": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Academic or cultural sources for this character's depiction"
        }
      }
    },
    "voice": {
      "type": "object",
      "properties": {
        "elevenlabs_voice_id": {
          "type": "string",
          "description": "ElevenLabs voice ID if this character speaks directly"
        },
        "voice_description": {
          "type": "string",
          "description": "Voice characteristics (deep, resonant, melodic, etc.)"
        },
        "language": {
          "type": "string",
          "description": "Primary language for dialogue"
        }
      }
    },
    "relationships": {
      "type": "object",
      "description": "Connections to other characters",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "character_id": { "type": "string" },
          "relationship_type": { "type": "string" },
          "description": { "type": "string" }
        }
      }
    }
  }
}
```

---

## Example: Shango Character Bible

```json
{
  "id": "shango",
  "name": "Shango",
  "alternative_names": ["Chango", "Xangô", "Sàngó", "Jakuta"],
  "mythology_origin": "yoruba",
  "type": "deity",
  "visual": {
    "appearance": "A powerfully built dark-skinned man with commanding presence, wearing royal white and red robes with a crown of thunder stones",
    "skin_tone": "Deep dark brown, rich and radiant",
    "build": "Tall, muscular, imposing athletic build",
    "clothing": "White and red agbada robes with golden embroidery, ceremonial wrapper",
    "accessories": [
      "Double-headed axe (oshe) — his primary symbol",
      "Crown adorned with thunder stones (edun ara)",
      "Red and white bead necklace (ileke)",
      "Brass armlets"
    ],
    "distinguishing_features": [
      "Facial scarification marks (ila) — traditional Yoruba facial markings",
      "Intense, fiery eyes that seem to glow during anger",
      "Six-pack abdominal markings representing thunder"
    ],
    "color_palette": ["#8B0000", "#FFFFFF", "#FFD700", "#8B4513"],
    "prompt_fragment": "muscular dark-skinned man with intricate facial scarification marks, wearing royal white and red agbada robes with golden embroidery, crown of thunder stones, double-headed axe, lightning crackling around him"
  },
  "personality": {
    "traits": ["Powerful", "Just", "Dramatic", "Proud", "Passionate", "Fierce"],
    "speech_style": "Booming, authoritative, poetic. Speaks in proverbs and declarations. Never whispers.",
    "motivation": "To maintain justice and order through the power of divine law",
    "fears": ["Dishonor", "The weakening of his followers' faith"],
    "values": ["Justice", "Courage", "Honor", "Power", "Loyalty"]
  },
  "cultural": {
    "actively_worshipped": true,
    "sensitivity_notes": "Shango is a living deity worshipped in Yoruba religion, Candomblé (Brazil), Santería (Cuba), Trinidad Orisha, and Haitian Vodun. He must be depicted with respect and dignity. Never mock or trivialize his divine status.",
    "taboos": [
      "Never depict Shango as weak or cowardly",
      "Never show him being defeated by mortals",
      "Never use cartoonish or comedic depiction",
      "Never associate him with evil or Satan (common Western mischaracterization)"
    ],
    "sacred_elements": [
      "The double-headed axe (oshe) — do not break or misuse in imagery",
      "Thunder stones (edun ara) — sacred objects",
      "The colors red and white — sacred to Shango"
    ],
    "sources": [
      "Courtney-Clarke, M. (1990). African Art: A Century at the Brooklyn Museum",
      "Law, R. (1977). The Oyo Empire c.1600-c.1836",
      "Thompson, R.F. (1983). Flash of the Spirit"
    ]
  },
  "voice": {
    "elevenlabs_voice_id": "",
    "voice_description": "Deep, resonant, thunderous baritone. Speaks with authority and weight. Every word sounds like a pronouncement.",
    "language": "English with Yoruba phrases"
  },
  "relationships": {
    "oya": {
      "character_id": "oya",
      "relationship_type": "consort",
      "description": "Oya is Shango's favorite wife, goddess of winds and storms. Their relationship is passionate and tempestuous."
    },
    "oshun": {
      "character_id": "oshun",
      "relationship_type": "consort",
      "description": "Oshun is Shango's other wife, goddess of rivers and love. She brings calm to his fire."
    },
    "ogun": {
      "character_id": "ogun",
      "relationship_type": "ally",
      "description": "Ogun, god of iron and war, is Shango's brother and ally in battle."
    }
  }
}
```

---

## Character Bible Tool

The `character_bible_tool` provides agents with character data during prompt generation and script writing.

### Operations

| Operation | Description | Used By |
|-----------|-------------|---------|
| `get_visual(character_id)` | Get visual prompt fragment | Prompt Agent |
| `get_personality(character_id)` | Get personality traits | Script Writer |
| `get_voice(character_id)` | Get voice settings | Narrator |
| `get_cultural(character_id)` | Get cultural notes | Researcher, QA |
| `get_all(character_id)` | Get complete character entry | All agents |
| `search(query)` | Search characters by name or trait | Researcher |

### Usage in Pipeline

```
Script Writer → get_personality("shango") → Writes dialogue matching his speech style
Scene Director → get_visual("shango") → Plans scenes with his visual in mind
Prompt Agent → get_visual("shango") → Injects exact prompt fragment into image prompts
Narrator → get_voice("shango") → Selects appropriate TTS voice
QA → get_cultural("shango") → Validates cultural accuracy of final video
```

---

## Style Anchors

Style anchors ensure visual consistency across all images in a video. They are defined per mythology origin and applied to every prompt.

```json
{
  "yoruba": {
    "style_anchor": "Cinematic dark fantasy art style inspired by West African mythology, dramatic lighting, rich earth tones, highly detailed, 8K quality",
    "negative_anchor": "european architecture, medieval style, western fantasy castle, anime style"
  },
  "egyptian": {
    "style_anchor": "Cinematic epic art style inspired by Ancient Egyptian mythology, golden light, monumental scale, hieroglyphic details, highly detailed, 8K quality",
    "negative_anchor": "modern buildings, european style, anime style, low quality"
  },
  "greek": {
    "style_anchor": "Cinematic classical art style inspired by Greek mythology, marble and bronze textures, Mediterranean light, dramatic composition, highly detailed, 8K quality",
    "negative_anchor": "modern buildings, african architecture, anime style, low quality"
  },
  "norse": {
    "style_anchor": "Cinematic dark art style inspired by Norse mythology, icy blue and silver tones, runic details, atmospheric fog, highly detailed, 8K quality",
    "negative_anchor": "tropical setting, modern buildings, anime style, low quality"
  }
}
```

---

## Extension Guidelines

### Adding a New Character

1. Create `mythforge/knowledge/characters/{character_id}.json`
2. Follow the schema exactly — all required fields must be present
3. Write the `prompt_fragment` carefully — this is the most important field for visual consistency
4. Include cultural sensitivity notes — even for mythological characters from dead religions
5. Cite at least 2 academic sources
6. Test the prompt fragment by generating a sample image before committing

### Modifying an Existing Character

1. Only modify if you have new academic sources
2. Never change the `prompt_fragment` for a character that has already appeared in published videos (breaks visual continuity)
3. If a visual change is needed, create a new variant (e.g., `shango_young`, `shango_elder`)

### Character Variants

Some characters may need visual variants for different life stages or forms:

```
shango.json          — Standard/primary depiction
shango_young.json    — Before becoming king
shango_divine.json   — Full divine form with lightning
```

Variants share the same base character data but override the `visual` section.