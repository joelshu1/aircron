from types import SimpleNamespace
from typing import Any, List

import pytest

from app.services import control_service


def test_run_control_action_preserves_raw_argument_values(monkeypatch: Any) -> None:
    calls: List[List[str]] = []

    monkeypatch.setattr(control_service, "_get_script_path", lambda: "/tmp/aircron_run.sh")

    def fake_run(cmd: List[str], **_: Any) -> Any:
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(control_service.subprocess, "run", fake_run)

    result = control_service.run_control_action(
        {
            "action": "volume",
            "service": "applemusic",
            "zone": "Custom:Living Room,Kitchen",
            "args": {"volume": 50},
        }
    )

    assert result == {"ok": True}
    assert calls == [
        [
            "/tmp/aircron_run.sh",
            "Custom:Living Room,Kitchen",
            "volume",
            "50",
            "",
            "applemusic",
        ]
    ]


def test_run_control_action_surfaces_script_failures(monkeypatch: Any) -> None:
    monkeypatch.setattr(control_service, "_get_script_path", lambda: "/tmp/aircron_run.sh")

    def fake_run(cmd: List[str], **_: Any) -> Any:
        return SimpleNamespace(
            returncode=1,
            stdout="Apple Music AirPlay device not found",
            stderr="",
        )

    monkeypatch.setattr(control_service.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="Apple Music AirPlay device not found"):
        control_service.run_control_action(
            {
                "action": "volume",
                "service": "applemusic",
                "zone": "Living Room",
                "args": {"volume": 50},
            }
        )
