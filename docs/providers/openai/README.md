# OpenAI Provider

The OpenAI provider implements MythForge's LLM provider contract with the official OpenAI Python SDK and the Responses API.

## What it supports

- Configuration-driven model selection for default, reasoning, fast, and vision roles
- Authentication via environment variables or explicit configuration
- Non-streaming and streaming generation
- Structured outputs via JSON schema or JSON object mode
- Retry handling and timeout-aware execution
- Cost estimation and token accounting
- Health checks and basic metrics

## Usage

```python
from mythforge.providers.models import LLMRequest
from mythforge.providers.openai import OpenAIConfig, OpenAIProvider

config = OpenAIConfig(
    api_key="sk-...",
    default_model="gpt-4o",
    reasoning_model="o3-mini",
)
provider = OpenAIProvider(config)
await provider.initialise()

response = await provider.generate(LLMRequest(prompt="Write a short synopsis."))
print(response.text)
```
