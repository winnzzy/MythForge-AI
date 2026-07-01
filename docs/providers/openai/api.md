# OpenAI Provider API

## OpenAIProvider

### Methods

- initialise(): create the SDK client and prepare the provider
- generate(request): run a non-streaming generation request
- stream(request): yield streaming chunks
- health_check(): run a lightweight model availability check
- estimate_cost(operation, **kwargs): estimate the cost of an operation
- capability_report(): return capability metadata for the provider

## OpenAIConfig

OpenAIConfig is a small configuration container that keeps all model selection and runtime settings outside of the provider logic.
