"""Run the actual ADK/Gemini agent and save only sanitized output and trace."""
import asyncio
import json

from nubara_agent.runtime import build_service
from nubara_agent.workflow import ROOT

MESSAGE = "Hola, soy María. Mi vuelo a Lima está retrasado y viajo con mi hijo de 7 años. ¿Alcanzamos la conexión a México? Si no, cámbiennos al vuelo de esta noche. También quiero saber cuánto me van a pagar de compensación."


async def main():
    service = build_service(evidence_dir=ROOT / "evidence")
    result, trace = await service.assess("ABC123", MESSAGE, "demo-maria")
    (ROOT / "evidence" / "latest-real-response.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    (ROOT / "evidence" / "latest-real-trace.json").write_text(json.dumps(trace, indent=2), encoding="utf-8")
    print(result.model_dump_json(indent=2))
    print(json.dumps({"agent_status": result.agent_status, "llm_calls": trace["llm_calls"],
                      "error_type": trace.get("error_type"), "provider_status_code": trace.get("provider_status_code")}))
    return 0 if result.agent_status == "COMPLETED" else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
