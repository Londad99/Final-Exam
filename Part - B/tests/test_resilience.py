from types import SimpleNamespace

import pytest
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from nubara_agent.resilience import ResilientGemini


class ProviderError(Exception):
    def __init__(self, code):
        self.code = code


class FakeProvider:
    def __init__(self, name, failures):
        self.model = name
        self.failures = list(failures)
        self.calls = 0

    async def generate_content_async(self, request, stream=False):
        assert request.model == self.model
        self.calls += 1
        code = self.failures.pop(0) if self.failures else None
        if code:
            raise ProviderError(code)
        yield LlmResponse(content=types.Content(role='model', parts=[types.Part(text='ok')]))


@pytest.mark.parametrize('code', [429, 503, 504])
async def test_retry_then_fallback_and_keep_successful_model(monkeypatch, code):
    waits = []
    async def sleep(delay):
        waits.append(delay)
    monkeypatch.setattr('nubara_agent.resilience.asyncio.sleep', sleep)
    trace = []
    model = ResilientGemini('primary', trace)
    first, second = FakeProvider('primary', [code]*3), FakeProvider('secondary', [])
    model._models = [first, second]
    request = LlmRequest(model='primary')
    for _ in range(2):
        result = [r async for r in model.generate_content_async(request)]
        assert len(result) == 1
    assert first.calls == 3 and second.calls == 2
    assert 2 <= waits[0] <= 3 and 4 <= waits[1] <= 5
    assert request.model == 'primary'
    assert trace[-1]['model'] == 'secondary'


@pytest.mark.parametrize('code', [400, 401, 403])
async def test_permanent_errors_do_not_retry(monkeypatch, code):
    model = ResilientGemini('primary', [])
    first, second = FakeProvider('primary', [code]), FakeProvider('secondary', [])
    model._models = [first, second]
    with pytest.raises(ProviderError):
        _ = [r async for r in model.generate_content_async(LlmRequest())]
    assert first.calls == 1 and second.calls == 0


async def test_missing_model_skips_to_fallback():
    model = ResilientGemini('primary', [])
    first, second = FakeProvider('primary', [404]), FakeProvider('secondary', [])
    model._models = [first, second]
    assert len([r async for r in model.generate_content_async(LlmRequest())]) == 1
    assert first.calls == second.calls == 1


async def test_all_models_fail_without_fake_response(monkeypatch):
    async def sleep(delay):
        pass
    monkeypatch.setattr('nubara_agent.resilience.asyncio.sleep', sleep)
    model = ResilientGemini('primary', [])
    model._models = [FakeProvider('primary', [503]*3), FakeProvider('secondary', [429]*3)]
    with pytest.raises(ProviderError):
        _ = [r async for r in model.generate_content_async(LlmRequest())]
    assert all(m.calls == 3 for m in model._models)
