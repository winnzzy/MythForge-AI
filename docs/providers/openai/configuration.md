# OpenAI Provider Configuration

The provider accepts an OpenAIConfig object or a provider configuration block with the following fields:

- default_model: default model to use for generation
- reasoning_model: model used when reasoning is requested
- fast_model: fast model override
- vision_model: vision model override
- api_key / api_key_env: authentication configuration
- base_url: custom base URL for proxies or Azure-compatible endpoints
- organization: OpenAI organization ID
- max_output_tokens: default maximum output length
- temperature / top_p: generation controls
- timeout_s / max_retries: runtime behavior
- structured_output_enabled / streaming_enabled: capability toggles

Example:

```yaml
providers:
  - name: openai
    type: llm
    primary: true
    model: gpt-4o
    api_key_env: OPENAI_API_KEY
    timeout_s: 60
    retry:
      max_retries: 3
      base_delay_s: 0.25
    options:
      default_model: gpt-4o
      reasoning_model: o3-mini
      fast_model: gpt-4o-mini
      vision_model: gpt-4o
      structured_output_enabled: true
      streaming_enabled: true
```
