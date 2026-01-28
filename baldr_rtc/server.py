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
