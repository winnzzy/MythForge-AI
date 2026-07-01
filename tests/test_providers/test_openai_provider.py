import types
from typing import Any

import pytest

from mythforge.providers.models import LLMRequest, LLMResponse, LLMStreamChunk
from mythforge.providers.openai import OpenAIConfig, OpenAIProvider
from mythforge.providers.transaction import TransactionRecorder


class DummyResponsesClient:
    def __init__(self, response: Any = None, stream_events: Any = None):
        self._response = response
        self._stream_events = stream_events
        self.calls = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self._stream_events is not None:
            return self._stream_events
        return self._response


class DummyModelClient:
    def __init__(self, data: list[Any]):
        self._data = data

    async def list(self) -> Any:
        return types.SimpleNamespace(data=self._data)


@pytest.mark.asyncio
async def test_openai_generate_maps_response_and_cost(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeUsage:
        input_tokens = 11
        output_tokens = 7

    response_obj = types.SimpleNamespace(
        output_text="hello",
        usage=FakeUsage(),
        model="gpt-4o",
        id="resp-1",
        created_at=123,
        status="completed",
    )

    fake_client = DummyResponsesClient(response=response_obj)
    fake_module = types.SimpleNamespace(AsyncOpenAI=lambda **kwargs: types.SimpleNamespace(responses=types.SimpleNamespace(create=fake_client.create), models=DummyModelClient([]), close=lambda: None))
    monkeypatch.setitem(__import__("sys").modules, "openai", fake_module)

    config = OpenAIConfig(api_key="sk-test", default_model="gpt-4o", max_output_tokens=256)
    provider = OpenAIProvider(config)
    await provider.initialise()

    result = await provider.generate(LLMRequest(prompt="hi", metadata={"json_mode": True}))

    assert result.text == "hello"
    assert result.tokens_in == 11
    assert result.tokens_out == 7
    assert result.model == "gpt-4o"
    assert result.provider == "openai"
    assert result.metadata["response_id"] == "resp-1"


@pytest.mark.asyncio
async def test_openai_stream_emits_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    stream_events = [
        types.SimpleNamespace(type="response.output_text.delta", delta="hel"),
        types.SimpleNamespace(type="response.output_text.delta", delta="lo"),
        types.SimpleNamespace(type="response.output_text.done"),
    ]

    async def fake_create(**body: Any) -> Any:
        return stream_events

    fake_module = types.SimpleNamespace(AsyncOpenAI=lambda **kwargs: types.SimpleNamespace(responses=types.SimpleNamespace(create=fake_create), models=DummyModelClient([]), close=lambda: None))
    monkeypatch.setitem(__import__("sys").modules, "openai", fake_module)

    config = OpenAIConfig(api_key="sk-test", default_model="gpt-4o")
    provider = OpenAIProvider(config)
    await provider.initialise()

    chunks = [chunk async for chunk in provider.stream(LLMRequest(prompt="hi"))]
    assert [chunk.delta for chunk in chunks] == ["hel", "lo", ""]
    assert chunks[-1].finished is True


@pytest.mark.asyncio
async def test_openai_health_and_capabilities(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_create(**body: Any) -> Any:
        return None

    fake_module = types.SimpleNamespace(AsyncOpenAI=lambda **kwargs: types.SimpleNamespace(responses=types.SimpleNamespace(create=fake_create), models=DummyModelClient([types.SimpleNamespace(id="gpt-4o")]), close=lambda: None))
    monkeypatch.setitem(__import__("sys").modules, "openai", fake_module)

    config = OpenAIConfig(api_key="sk-test", default_model="gpt-4o", reasoning_model="o3-mini")
    provider = OpenAIProvider(config)
    await provider.initialise()

    health = await provider.health_check()
    assert health.available is True
    assert health.status.value == "healthy"

    report = provider.capability_report()
    assert report["streaming"] is True
    assert report["structured_outputs"] is True
    assert report["reasoning"] is True


@pytest.mark.asyncio
async def test_openai_transaction_recorder(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeUsage:
        input_tokens = 3
        output_tokens = 2

    response_obj = types.SimpleNamespace(output_text="ok", usage=FakeUsage(), model="gpt-4o", id="resp-2", created_at=456, status="completed")

    async def fake_create(**body: Any) -> Any:
        return response_obj

    fake_module = types.SimpleNamespace(AsyncOpenAI=lambda **kwargs: types.SimpleNamespace(responses=types.SimpleNamespace(create=fake_create), models=DummyModelClient([]), close=lambda: None))
    monkeypatch.setitem(__import__("sys").modules, "openai", fake_module)

    recorder = TransactionRecorder(max_history=10)
    config = OpenAIConfig(api_key="sk-test", default_model="gpt-4o")
    provider = OpenAIProvider(config, transaction_recorder=recorder)
    await provider.initialise()

    await provider.generate(LLMRequest(prompt="hi"))

    history = recorder.get_history()
    assert len(history) == 1
    assert history[0].status.value == "success"
    assert history[0].tokens_out == 2
