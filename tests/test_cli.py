"""The CLI's Ctrl-C handler, with a real SIGINT sent to this process."""

import os
import signal
from collections.abc import Iterator
from pathlib import Path

import pytest

from rig import Agent, Budget, Workspace
from rig.cli import _attach
from rig.providers.fake import FakeProvider


@pytest.fixture
def restore_sigint() -> Iterator[None]:
    saved = signal.getsignal(signal.SIGINT)
    yield
    signal.signal(signal.SIGINT, saved)


def test_first_ctrl_c_aborts_and_the_second_quits(tmp_path: Path, restore_sigint: None) -> None:
    ws = Workspace(root=tmp_path, name="test", run_id="test", use_sandbox=False)
    agent = Agent(ws, budget=Budget.get_dummy_budget(), provider=FakeProvider([]))
    _attach(agent)

    os.kill(os.getpid(), signal.SIGINT)
    assert agent.aborting

    with pytest.raises(SystemExit) as exit_:
        os.kill(os.getpid(), signal.SIGINT)
    assert exit_.value.code == 130
