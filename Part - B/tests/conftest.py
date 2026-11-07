import json
from datetime import datetime, timezone

import pytest
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from pydantic import Field

from nubara_agent.adapters.mock_systems import MockSystems
from nubara_agent.clock import FixedClock
from nubara_agent.engine import Engine
from nubara_agent.storage import Store
from nubara_agent.workflow import AgentService


class ScriptedModel(BaseLlm):
    """An explicit test double; still exercises ADK's actual function dispatch."""
    model: str = "scripted-test-model"
    compensation: bool = True
    skip_reads: bool = False
    requests: list[str] = Field(default_factory=list)

    async def generate_content_async(self, llm_request, stream=False):
        self.requests.append(str(llm_request.contents))
        completed = {part.function_response.name for content in llm_request.contents
                     for part in (content.parts or []) if part.function_response}
        if not completed and not self.skip_reads:
            parts = [types.Part(function_call=types.FunctionCall(name="get_trip_context", args={}))]
        elif "get_operational_events" not in completed and not self.skip_reads:
            parts = [types.Part(function_call=types.FunctionCall(name=name, args={})) for name in
                     ["get_operational_events", "get_policy_rules", "get_eligible_options"]]
        else:
            parts = [types.Part(text=json.dumps({"connection_requested": True, "rebooking_requested": True,
                                                "compensation_requested": self.compensation}))]
        yield LlmResponse(content=types.Content(role="model", parts=parts))


@pytest.fixture
def setup(tmp_path):
    clock = FixedClock(datetime(2026, 9, 15, 11, 2, 37, tzinfo=timezone.utc))
    systems = MockSystems(clock)
    engine = Engine(systems, clock, Store(tmp_path / "state.sqlite3"))
    model = ScriptedModel()
    return AgentService(engine, model=model), systems, clock, model
