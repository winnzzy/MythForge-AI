# MythForge AI — Knowledge Base Design

## Overview

The Knowledge Base is a structured, version-controlled collection of mythology data that serves as the factual foundation for all content generation. It ensures cultural accuracy, consistency across videos, and dramatically reduces API costs by providing local data instead of relying solely on web research.

---

## Architecture

```
mythforge/
└── knowledge/
    ├── characters/           # Character definitions
    │   ├── shango.json
    │   ├── anansi.json
    │   ├── mami_wata.json
    │   └── ...
    ├── kingdoms/             # Kingdom/nation definitions
    │   ├── oyo.json
    │   ├── dahomey.json
    │   └── ...
    ├── stories/              # Canonical story outlines
    │   ├── shango_thunder.json
    │   ├── anansi_spider.json
    │   └── ...
    ├── cosmology/            # Creation myths, afterlife, spiritual systems
    │   ├── yoruba_cosmology.json
    │   ├── egyptian_cosmology.json
    │   └── ...
    ├── artifacts/            # Magical objects, weapons, symbols
    │   ├── oshe_shango.json
    │   ├── anansi_golden_box.json
    │   └── ...
    ├── pronunciation/        # Name pronunciation guides
    │   ├── yoruba_names.json
    │   ├── egyptian_names.json
    │   └── ...
    ├── cultural_notes/       # Cultural context and sensitivity
    │   ├── yoruba_culture.json
    │   ├── egyptian_culture.json
    │   └── ...
    └── index.json            # Master index of all entries
```

---

## Entry Schema

### Character Entry

```json
{
  "id": "shango",
  "name": "Shango",
  "alternative_names": ["Chango", "Xangô", "Sàngó"],
  "mythology_origin": "yoruba",
  "domain": ["Thunder", "Lightning", "Fire", "Justice"],
  "role": "Orisha (Deity)",
  "personality": ["Powerful", "Just", "Dramatic", "Proud"],
  "relationships": {
    "consorts": ["Oya", "Oshun", "Oba"],
    "allies": ["Ogun", "Ochossi"],
    "rivals": ["Ogun (in some traditions)"]
  },
  "stories": ["shango_thunder", "shango_exile", "shango_vs_ogun"],
  "cultural_sensitivity": {
    "actively_worshipped": true,
    "notes": "Shango is a living deity in Yoruba religion, Candomblé, Santería, and Vodun. Treat with respect."
  }
}
```

### Kingdom Entry

```json
{
  "id": "oyo",
  "name": "Oyo Empire",
  "mythology_origin": "yoruba",
  "period": "1300-1896 CE",
  "location": "West Africa (modern Nigeria)",
  "key_figures": ["shango", "alaafin"],
  "description": "One of the most powerful empires in West Africa...",
  "architecture": "Mud-brick palaces, open courtyards, carved wooden pillars",
  "cultural_elements": ["Gelede masquerade", "Ifa divination", "Oriki praise poetry"]
}
```

### Story Entry

```json
{
  "id": "shango_thunder",
  "title": "Shango and the Thunder Stones",
  "mythology_origin": "yoruba",
  "characters": ["shango", "oya"],
  "setting": "oyo",
  "arc": {
    "setup": "Shango rules Oyo with an iron fist, but his generals doubt his divine power.",
    "conflict": "The generals conspire to overthrow him, claiming his lightning is mere trickery.",
    "resolution": "Shango calls down real thunder, proving his divinity. Thunder stones (edun ara) fall from the sky."
  },
  "moral": "True power reveals itself when challenged.",
  "key_scenes": [
    "Shango on the throne of Oyo",
    "Generals plotting in the shadows",
    "Shango calling lightning from the heavens",
    "Thunder stones falling from the sky"
  ],
  "estimated_duration": "10-12 minutes"
}
```

### Pronunciation Entry

```json
{
  "language": "yoruba",
  "names": [
    {
      "name": "Shango",
      "ipa": "/ˈʃɑːŋɡoʊ/",
      "phonetic": "SHAHN-goh",
      "ssml": "<phoneme alphabet=\"ipa\" ph=\"ˈʃɑːŋɡoʊ\">Shango</phoneme>"
    },
    {
      "name": "Oshun",
      "ipa": "/oʊˈʃuːn/",
      "phonetic": "oh-SHOON",
      "ssml": "<phoneme alphabet=\"ipa\" ph=\"oʊˈʃuːn\">Oshun</phoneme>"
    }
  ]
}
```

---

## Knowledge Base Tool

The `knowledge_base_tool` is a custom MythForge tool that provides agents with local data access.

### Operations

| Operation | Description | Example |
|-----------|-------------|---------|
| `search` | Search entries by keyword | `search("shango", type="character")` |
| `get` | Get entry by ID | `get("characters/shango")` |
| `list` | List all entries of a type | `list(type="story", origin="yoruba")` |
| `related` | Get related entries | `related("shango")` → returns Oya, Oyo, etc. |

### Implementation

The Knowledge Base tool uses file-based storage (JSON files) with an in-memory index for fast search. No database required for V1.

### Extension

To add a new mythology domain:
1. Add character entries to `knowledge/characters/`
2. Add kingdom entries to `knowledge/kingdoms/`
3. Add story entries to `knowledge/stories/`
4. Add pronunciation entries to `knowledge/pronunciation/`
5. Add cultural notes to `knowledge/cultural_notes/`
6. Update `knowledge/index.json`

---

## Data Quality Rules

1. Every entry must have an `id`, `name`, and `mythology_origin`
2. Every character must have `cultural_sensitivity` notes
3. Every name must have IPA pronunciation
4. No entry may contain offensive or mocking language about living religions
5. All entries must cite at least one source
6. Character descriptions must be specific (not generic)

---

## V1 Content Scope

| Domain | Characters | Kingdoms | Stories | Status |
|--------|-----------|----------|---------|--------|
| Yoruba | Shango, Oya, Oshun, Anansi, Ogun | Oyo, Ife | 3-5 stories | Priority 1 |
| Egyptian | Ra, Osiris, Isis, Anubis, Thoth | Egypt, Memphis | 3-5 stories | Priority 2 |
| Greek | Zeus, Athena, Hades, Prometheus | Olympus | 2-3 stories | Priority 3 |
| Norse | Odin, Thor, Loki, Freya | Asgard | 2-3 stories | Priority 4 |