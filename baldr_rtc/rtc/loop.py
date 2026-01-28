from __future__ import annotations

import queue
import threading
import time
import numpy as np

from baldr_rtc.core.state import MainState, RuntimeGlobals, ServoState
from baldr_rtc.telemetry.ring import TelemetryRingBuffer


class RTCThread(threading.Thread):
    def __init__(
        self,
        globals_: RuntimeGlobals,
        command_queue: "queue.Queue[dict]",
        telem_ring: TelemetryRingBuffer,
        stop_event: threading.Event,
    ):
        super().__init__(daemon=True)
        self.g = globals_
        self.command_queue = command_queue
        self.telem_ring = telem_ring
        self.stop_event = stop_event
        self._frame_id = 0

    def run(self) -> None:
        fps = float(self.g.rtc_config.fps) if self.g.rtc_config.fps > 0 else 1000.0
        dt = 1.0 / fps
        next_t = time.perf_counter()

        while not self.stop_event.is_set():
            if self.g.servo_mode == MainState.SERVO_STOP:
                self.stop_event.set()
                break

            self._drain_commands()

            if self.g.pause_rtc:
                time.sleep(0.01)
                continue

            self._frame_id += 1
            t_now = time.time()

            metric_flux = float(np.random.random())
            metric_strehl = float(np.clip(np.random.normal(0.5, 0.1), 0.0, 1.0))

            self.telem_ring.push(
                frame_id=self._frame_id,
                t_s=t_now,
                lo_state=int(self.g.servo_mode_LO),
                ho_state=int(self.g.servo_mode_HO),
                paused=bool(self.g.pause_rtc),
                metric_flux=metric_flux,
                metric_strehl=metric_strehl,
            )

            next_t += dt
            sleep = next_t - time.perf_counter()
            if sleep > 0:
                time.sleep(sleep)

    def _drain_commands(self) -> None:
        for _ in range(100):
            try:
                cmd = self.command_queue.get_nowait()
            except queue.Empty:
                return
            try:
                self._apply_command(cmd)
            finally:
                self.command_queue.task_done()

    def _apply_command(self, cmd: dict) -> None:
        t = cmd.get("type", "")
        if t == "PAUSE":
            self.g.pause_rtc = True
        elif t == "RESUME":
            self.g.pause_rtc = False
        elif t == "STOP":
            self.g.servo_mode = MainState.SERVO_STOP
        elif t == "SET_LO":
            self.g.servo_mode_LO = ServoState(int(cmd["value"]))
        elif t == "SET_HO":
            self.g.servo_mode_HO = ServoState(int(cmd["value"]))
        elif t == "SET_LOHO":
            self.g.servo_mode_LO = ServoState(int(cmd["lo"]))
            self.g.servo_mode_HO = ServoState(int(cmd["ho"]))
        elif t == "SET_TELEM":
            self.g.rtc_config.state.take_telemetry = bool(cmd.get("enabled", False))
        elif t == "LOAD_CONFIG":
            new_cfg = cmd.get("rtc_config")
            if new_cfg is not None:
                self.g.rtc_config = new_cfg
                self.g.active_config_filename = cmd.get("path", self.g.active_config_filename)
