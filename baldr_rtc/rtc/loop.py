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

            # --- IO: read camera frame ---
            if self.g.camera_io is None:
                # fallback: dummy frame (keeps thread alive)
                i_raw = np.zeros((1, 1), dtype=np.float32)
            else:
                fr = self.g.camera_io.get_frame( ) #reform=True)
                i_raw = fr.data
                #print(i_raw)
            

            """            
            # input list process_frame, i_setpoint_runtime, N0_runtime ,perf_param, i_setpoint_runtime

            # get raw frame (assume dark and bias corrected - this is the camera servers job)
            i_raw = get_frame_from_shm() 
            
            # process (average or otherwise)
            i = process_frame( i ) # this could be a simple moving average . In my sim I think i did this in error space - but should it be here? LPF straight up 

            # normalized intensity 
            i_norm = i / N0_runtime 

            # opd estimate 
            opd_est = perf_model( i_norm , perf_param)
             
             
            # signal  (i_setpoint_runtime should always be in the right space, if change space (function) we must update it )
            if signal_space.lower().strip() == 'pix':
                s = i_norm  - i_setpoint_runtime
            elif signal_space.lower().strip() == 'dm':
                s = I2A @ i_norm  - i_setpoint_runtime
            else:
                raise UserWarning("invalid signal_space. Must be 'pix' | 'dm'")
            
            # project intensity signal to error in modal space 
            e_LO = I2M_LO @ s 
            e_HO = I2M_HO @ s

            # control signals
            u_LO = ctrl_LO.process( e_LO + e_LO_inj )
            u_HO = ctrl_HO.process( e_HO + e_HO_inj )
            
            # Project mode to DM commands 
            c_LO = M2C_LO @ u_LO 
            c_HO = M2C_LO @ u_HO

            dcmd = c_LO + c_LO + c_LO_inj + c_HO_inj

            update_DM_shm( dcmd )

            """
            # TODO: replace metrics with real computation
            metric_flux = float(np.mean(i_raw))
            metric_strehl = float(np.clip(np.random.normal(0.5, 0.1), 0.0, 1.0))

            # --- IO: write DM command (placeholder) ---
            if self.g.dm_io is not None:
                # replace with real computed command vector
                self.g.dm_io.write(np.zeros(140, dtype=np.float32))

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

# from __future__ import annotations

# import queue
# import threading
# import time
# import numpy as np

# from baldr_rtc.core.state import MainState, RuntimeGlobals, ServoState
# from baldr_rtc.telemetry.ring import TelemetryRingBuffer



# class RTCThread(threading.Thread):
#     def __init__(
#         self,
#         globals_: RuntimeGlobals,
#         command_queue: "queue.Queue[dict]",
#         telem_ring: TelemetryRingBuffer,
#         stop_event: threading.Event,
#     ):
#         super().__init__(daemon=True)
#         self.g = globals_
#         self.command_queue = command_queue
#         self.telem_ring = telem_ring
#         self.stop_event = stop_event
#         self._frame_id = 0

#     def run(self) -> None:
#         fps = float(self.g.rtc_config.fps) if self.g.rtc_config.fps > 0 else 1000.0
#         dt = 1.0 / fps
#         next_t = time.perf_counter()

#         while not self.stop_event.is_set():
#             if self.g.servo_mode == MainState.SERVO_STOP:
#                 self.stop_event.set()
#                 break

#             self._drain_commands()

#             if self.g.pause_rtc:
#                 time.sleep(0.01)
#                 continue

#             self._frame_id += 1
#             t_now = time.time()


#             """            
#             # input list process_frame, i_setpoint_runtime, N0_runtime ,perf_param, i_setpoint_runtime

#             # get raw frame (assume dark and bias corrected - this is the camera servers job)
#             i_raw = get_frame_from_shm() 
            
#             # process (average or otherwise)
#             i = process_frame( i ) # this could be a simple moving average . In my sim I think i did this in error space - but should it be here? LPF straight up 

#             # normalized intensity 
#             i_norm = i / N0_runtime 

#             # opd estimate 
#             opd_est = perf_model( i_norm , perf_param)
             
             
#             # signal  (i_setpoint_runtime should always be in the right space, if change space (function) we must update it )
#             if signal_space.lower().strip() == 'pix':
#                 s = i_norm  - i_setpoint_runtime
#             elif signal_space.lower().strip() == 'dm':
#                 s = I2A @ i_norm  - i_setpoint_runtime
#             else:
#                 raise UserWarning("invalid signal_space. Must be 'pix' | 'dm'")
            
#             # project intensity signal to error in modal space 
#             e_LO = I2M_LO @ s 
#             e_HO = I2M_HO @ s

#             # control signals
#             u_LO = ctrl_LO.process( e_LO + e_LO_inj )
#             u_HO = ctrl_HO.process( e_HO + e_HO_inj )
            
#             # Project mode to DM commands 
#             c_LO = M2C_LO @ u_LO 
#             c_HO = M2C_LO @ u_HO

#             dcmd = c_LO + c_LO + c_LO_inj + c_HO_inj

#             update_DM_shm( dcmd )

#             """
#             metric_flux = float(np.random.random())
#             metric_strehl = float(np.clip(np.random.normal(0.5, 0.1), 0.0, 1.0))

#             self.telem_ring.push(
#                 frame_id=self._frame_id,
#                 t_s=t_now,
#                 lo_state=int(self.g.servo_mode_LO),
#                 ho_state=int(self.g.servo_mode_HO),
#                 paused=bool(self.g.pause_rtc),
#                 metric_flux=metric_flux,
#                 metric_strehl=metric_strehl,
#             )

#             next_t += dt
#             sleep = next_t - time.perf_counter()
#             if sleep > 0:
#                 time.sleep(sleep)

#     def _drain_commands(self) -> None:
#         for _ in range(100):
#             try:
#                 cmd = self.command_queue.get_nowait()
#             except queue.Empty:
#                 return
#             try:
#                 self._apply_command(cmd)
#             finally:
#                 self.command_queue.task_done()

#     def _apply_command(self, cmd: dict) -> None:
#         t = cmd.get("type", "")
#         if t == "PAUSE":
#             self.g.pause_rtc = True
#         elif t == "RESUME":
#             self.g.pause_rtc = False
#         elif t == "STOP":
#             self.g.servo_mode = MainState.SERVO_STOP
#         elif t == "SET_LO":
#             self.g.servo_mode_LO = ServoState(int(cmd["value"]))
#         elif t == "SET_HO":
#             self.g.servo_mode_HO = ServoState(int(cmd["value"]))
#         elif t == "SET_LOHO":
#             self.g.servo_mode_LO = ServoState(int(cmd["lo"]))
#             self.g.servo_mode_HO = ServoState(int(cmd["ho"]))
#         elif t == "SET_TELEM":
#             self.g.rtc_config.state.take_telemetry = bool(cmd.get("enabled", False))
#         elif t == "LOAD_CONFIG":
#             new_cfg = cmd.get("rtc_config")
#             if new_cfg is not None:
#                 self.g.rtc_config = new_cfg
#                 self.g.active_config_filename = cmd.get("path", self.g.active_config_filename)
