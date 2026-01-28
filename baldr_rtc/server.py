from __future__ import annotations

import queue
import threading

from baldr_rtc.core.config import readBDRConfig
from baldr_rtc.core.state import RuntimeGlobals
from baldr_rtc.telemetry.ring import TelemetryRingBuffer
from baldr_rtc.telemetry.worker import TelemetryThread, TelemetryWriter
from baldr_rtc.rtc.loop import RTCThread
from baldr_rtc.commander.server import CommanderServer
from baldr_rtc.commander.commands import build_commander_module

def _print_banner(*, beam: int, socket: str, cfg_path: str, cfg) -> None:
    # Keep this pure printing: no side effects beyond stdout.
    banner = r"""
  ____    _    _      ____   ____      ____  _____  ____ 
 | __ )  / \  | |    |  _ \ |  _ \    |  _ \|_   _|/ ___|
 |  _ \ / _ \ | |    | | | || |_) |   | |_) | | | | |    
 | |_) / ___ \| |___ | |_| ||  _ <    |  _ <  | | | |___ 
 |____/_/   \_\_____||____/ |_| \_\   |_| \_\ |_|  \____|

                 BALDR RTC (Python)
"""
    # Minimal “sanity” fields; safe to show even if internals change.
    mode = getattr(cfg, "mode", "unknown")
    pmask = getattr(cfg, "phasemask", "unknown")
    fps = getattr(cfg, "fps", None)
    ctrl = getattr(getattr(cfg, "state", None), "controller_type", "unknown")
    telem = getattr(getattr(cfg, "state", None), "take_telemetry", False)

    # If you store LO/HO matrix sizes in cfg.matrices, print them (optional).
    lo_sz = None
    ho_sz = None
    mats = getattr(cfg, "matrices", None)
    if mats is not None:
        I2M_LO = getattr(mats, "I2M_LO", None)
        I2M_HO = getattr(mats, "I2M_HO", None)
        try:
            lo_sz = tuple(I2M_LO.shape) if I2M_LO is not None else None
        except Exception:
            lo_sz = None
        try:
            ho_sz = tuple(I2M_HO.shape) if I2M_HO is not None else None
        except Exception:
            ho_sz = None

    print(banner)
    print("Startup sanity:")
    print(f"  beam:           {beam}")
    print(f"  commander:      {socket}")
    print(f"  config:         {cfg_path}")
    print(f"  mode:           {mode}")
    print(f"  phasemask:      {pmask}")
    if fps is not None:
        print(f"  fps:            {fps}")
    print(f"  controller:     {ctrl}")
    print(f"  telemetry:      {'ON' if telem else 'OFF'}")
    if lo_sz is not None:
        print(f"  I2M_LO shape:   {lo_sz}")
    if ho_sz is not None:
        print(f"  I2M_HO shape:   {ho_sz}")
    print("")


def main(
    *,
    beam: int,
    socket: str,
    config_path: str,
    telem_dir: str,
    telem_capacity: int,
    flush_hz: float,
    chunk_seconds: float,
) -> int:
    stop_event = threading.Event()
    cmd_queue: "queue.Queue[dict]" = queue.Queue()

    cfg = readBDRConfig(config_path)
    
    _print_banner(beam=beam, socket=socket, cfg_path=str(config_path), cfg=cfg)

    g = RuntimeGlobals(beam=beam, active_config_filename=config_path, rtc_config=cfg)


    ring = TelemetryRingBuffer(capacity=telem_capacity)

    writer = TelemetryWriter(out_dir=telem_dir, beam=beam)
    telem_thread = TelemetryThread(
        globals_=g,
        ring=ring,
        writer=writer,
        stop_event=stop_event,
        flush_hz=flush_hz,
        chunk_seconds=chunk_seconds,
    )

    rtc_thread = RTCThread(globals_=g, command_queue=cmd_queue, telem_ring=ring, stop_event=stop_event)

    module = build_commander_module(globals_=g, command_queue=cmd_queue, stop_event=stop_event)
    cmd_server = CommanderServer(endpoint=socket, module=module, stop_event=stop_event)

    rtc_thread.start()
    telem_thread.start()
    cmd_server.start()

    stop_event.wait()

    rtc_thread.join(timeout=2.0)
    telem_thread.join(timeout=2.0)
    cmd_server.join(timeout=2.0)
    return 0
