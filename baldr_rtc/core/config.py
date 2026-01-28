from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from baldr_rtc.core.state import BDRConfig, Limits, InjSignal, StateConfig


def _get(d: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def readBDRConfig(config_path: str) -> BDRConfig:
    p = Path(config_path).expanduser()
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {p}")

    data: Dict[str, Any]
    try:
        import tomllib  # py>=3.11
        data = tomllib.loads(p.read_text())
    except Exception:
        import toml  # fallback
        data = toml.loads(p.read_text())

    cfg = BDRConfig()

    cfg.state = StateConfig(
        controller_type=str(_get(data, "state", "controller_type", default="unknown")),
        auto_close=bool(_get(data, "state", "auto_close", default=False)),
        take_telemetry=bool(_get(data, "state", "take_telemetry", default=False)),
    )
    cfg.inj_signal = InjSignal(enabled=bool(_get(data, "inj_signal", "enabled", default=False)))
    cfg.limits = Limits(
        open_on_flux_limit=float(_get(data, "limits", "open_on_flux_limit", default=0.0)),
        close_on_strehl_limit=float(_get(data, "limits", "close_on_strehl_limit", default=0.0)),
        open_on_strehl_limit=float(_get(data, "limits", "open_on_strehl_limit", default=0.0)),
    )

    cam_fps = _get(data, "cam", "fps", default="0")
    try:
        cfg.fps = float(cam_fps)
    except Exception:
        cfg.fps = 0.0

    cfg.init_derived_parameters()
    return cfg
