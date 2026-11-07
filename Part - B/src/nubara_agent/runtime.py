from datetime import datetime, timezone
from pathlib import Path

from .adapters.mock_systems import MockSystems
from .clock import ReplayClock
from .engine import Engine
from .storage import Store
from .workflow import AgentService, ROOT


def build_service(database: Path | None = None, evidence_dir: Path | None = None) -> AgentService:
    # Replay the exam date explicitly; production must use current, timezone-aware upstream data.
    store = Store(database or ROOT / "runtime.sqlite3")
    now = datetime.now(timezone.utc)
    epoch = datetime.fromisoformat(store.replay_epoch(now.isoformat()))
    clock = ReplayClock(datetime(2026, 9, 15, 11, 2, 37, tzinfo=timezone.utc) + (now - epoch))
    systems = MockSystems(clock)
    return AgentService(Engine(systems, clock, store), evidence_dir=evidence_dir)
