from __future__ import annotations

import threading
import queue
from baldr_rtc.commander.module import Module, ArgumentSpec
from baldr_rtc.core.config import readBDRConfig
from baldr_rtc.core.commands import make_cmd
from baldr_rtc.core.state import RuntimeGlobals, ServoState, MainState


def build_commander_module(
    *,
    globals_: RuntimeGlobals,
    command_queue: "queue.Queue[dict]",
    stop_event: threading.Event,
) -> Module:
    m = Module()

    def read_bdr(args):
        path = str(args[0]) if args else ""
        cfg = readBDRConfig(path)
        command_queue.put(make_cmd("LOAD_CONFIG", rtc_config=cfg, path=path))
        globals_.active_config_filename = path

        configured = 1 if (len(cfg.matrices.I2M_LO) > 0 or len(cfg.matrices.I2M_HO) > 0) else 0
        return {"ok": True, "config_file": path, "configured": configured, "frequency": cfg.fps}

    def pause_rtc(args):
        command_queue.put(make_cmd("PAUSE"))
        return {"ok": True}

    def resume_rtc(args):
        command_queue.put(make_cmd("RESUME"))
        return {"ok": True}

    def stop_baldr(args):
        command_queue.put(make_cmd("STOP"))
        return {"ok": True, "servo_mode": int(MainState.SERVO_STOP)}

    def close_all(args):
        command_queue.put(make_cmd("SET_LOHO", lo=int(ServoState.SERVO_CLOSE), ho=int(ServoState.SERVO_CLOSE)))
        return {"ok": True}

    def open_all(args):
        command_queue.put(make_cmd("SET_LOHO", lo=int(ServoState.SERVO_OPEN), ho=int(ServoState.SERVO_OPEN)))
        return {"ok": True}

    def close_lo(args):
        command_queue.put(make_cmd("SET_LO", value=int(ServoState.SERVO_CLOSE)))
        return {"ok": True}

    def open_lo(args):
        command_queue.put(make_cmd("SET_LO", value=int(ServoState.SERVO_OPEN)))
        return {"ok": True}

    def close_ho(args):
        command_queue.put(make_cmd("SET_HO", value=int(ServoState.SERVO_CLOSE)))
        return {"ok": True}

    def open_ho(args):
        command_queue.put(make_cmd("SET_HO", value=int(ServoState.SERVO_OPEN)))
        return {"ok": True}

    def status(args):
        cfg = globals_.rtc_config
        lo_ready = len(cfg.matrices.I2M_LO) > 0
        ho_ready = len(cfg.matrices.I2M_HO) > 0
        configured = 1 if (lo_ready or ho_ready) else 0

        return {
            "TT_state": int(globals_.servo_mode_LO),
            "HO_state": int(globals_.servo_mode_HO),
            "mode": globals_.observing_mode or "unknown",
            "phasemask": globals_.phasemask or "unknown",
            "frequency": float(cfg.fps),
            "configured": int(configured),
            "ctrl_type": cfg.state.controller_type,
            "config_file": globals_.active_config_filename or "unknown",
            "inj_enabled": 1 if cfg.inj_signal.enabled else 0,
            "auto_loop": 1 if cfg.state.auto_close else 0,
            "close_on_strehl": float(cfg.limits.close_on_strehl_limit),
            "open_on_strehl": float(cfg.limits.open_on_strehl_limit),
            "close_on_snr": 2.0,
            "open_on_snr": float(cfg.limits.open_on_flux_limit),
            "TT_offsets": 0,
        }

    m.def_command("readBDRConfig", read_bdr, description="Load/parse config.", arguments=[ArgumentSpec("config_file", "string")], return_type="object")
    m.def_command("pauseRTC", pause_rtc, description="Pause RTC loop.", return_type="object")
    m.def_command("resumeRTC", resume_rtc, description="Resume RTC loop.", return_type="object")
    m.def_command("stop_baldr", stop_baldr, description="Stop Baldr RTC loop.", return_type="object")

    m.def_command("close_all", close_all, description="Close LO+HO loops.", return_type="object")
    m.def_command("open_all", open_all, description="Open LO+HO loops.", return_type="object")
    m.def_command("close_baldr_LO", close_lo, description="Close LO loop.", return_type="object")
    m.def_command("open_baldr_LO", open_lo, description="Open LO loop.", return_type="object")
    m.def_command("close_baldr_HO", close_ho, description="Close HO loop.", return_type="object")
    m.def_command("open_baldr_HO", open_ho, description="Open HO loop.", return_type="object")

    m.def_command("status", status, description="Get Baldr status snapshot.", return_type="object")
    return m
