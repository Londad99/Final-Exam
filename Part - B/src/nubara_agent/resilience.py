"""Bounded retries of model reads only; no workflow or business-write replay."""
import asyncio
import os
import random

from google.adk.models.base_llm import BaseLlm
from google.adk.models.google_llm import Gemini
from google.genai import types
from pydantic import PrivateAttr


class ResilientGemini(BaseLlm):
    _models: list = PrivateAttr()
    _attempts: list = PrivateAttr()
    _index: int = PrivateAttr(default=0)

    def __init__(self, primary: str, attempts: list):
        super().__init__(model=primary)
        names = list(dict.fromkeys([primary, *[n.strip() for n in os.getenv(
            'GEMINI_FALLBACK_MODELS', 'gemini-3.1-flash-lite').split(',') if n.strip()]]))[:3]
        # One HTTP attempt per adapter call: avoid multiplying SDK and app retries.
        self._models = [Gemini(model=name, retry_options=types.HttpRetryOptions(attempts=1)) for name in names]
        self._attempts = attempts

    async def generate_content_async(self, llm_request, stream=False):
        for index in range(self._index, len(self._models)):
            model = self._models[index]
            for attempt in range(3):
                record = {'model': model.model, 'attempt': attempt + 1}
                self._attempts.append(record)
                try:
                    request = llm_request.model_copy(deep=True)
                    request.model = model.model
                    # Buffer a whole response before exposing tool calls to ADK.
                    async with asyncio.timeout(20):
                        responses = [r async for r in model.generate_content_async(request, stream=False)]
                    record['status'] = 'completed'
                    self._index = index
                    for response in responses:
                        yield response
                    return
                except Exception as exc:
                    code = getattr(exc, 'code', None)
                    record.update(status='failed', error_type=type(exc).__name__)
                    if isinstance(code, int):
                        record['provider_status_code'] = code
                    transient = code in {429, 500, 502, 503, 504} or isinstance(exc, TimeoutError)
                    # Invalid credentials and invalid requests must not trigger failover.
                    if not transient and code != 404:
                        raise
                    last_error = exc
                    if code == 404 or attempt == 2:
                        break
                    delay = 2 ** (attempt + 1) + random.uniform(0, 1)
                    record['wait_seconds'] = round(delay, 2)
                    await asyncio.sleep(delay)
            self._index = index + 1
        raise last_error
