from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional


class ServoState(IntEnum):
    SERVO_OPEN = 0
    SERVO_CLOSE = 1


class MainState(IntEnum):
    SERVO_RUN = 0
    SERVO_STOP = 2


@dataclass
class Matrices:
    I2M_LO: list = field(default_factory=list)
    I2M_HO: list = field(default_factory=list)


@dataclass
class Limits:
    open_on_flux_limit: float = 0.0
    close_on_strehl_limit: float = 0.0
    open_on_strehl_limit: float = 0.0


@dataclass
class InjSignal:
    enabled: bool = False


@dataclass
class StateConfig:
    controller_type: str = "unknown"
    auto_close: bool = False
    take_telemetry: bool = False


@dataclass
class BDRConfig:
    fps: float = 0.0
    matrices: Matrices = field(default_factory=Matrices)
    limits: Limits = field(default_factory=Limits)
    inj_signal: InjSignal = field(default_factory=InjSignal)
    state: StateConfig = field(default_factory=StateConfig)

    def init_derived_parameters(self) -> None:
        if self.fps <= 0:
            self.fps = 1000.0


@dataclass
class RuntimeGlobals:
    beam: int = 0

    servo_mode: MainState = MainState.SERVO_RUN
    servo_mode_LO: ServoState = ServoState.SERVO_OPEN
    servo_mode_HO: ServoState = ServoState.SERVO_OPEN
    pause_rtc: bool = False

    observing_mode: str = "unknown"
    phasemask: str = "unknown"

    active_config_filename: str = "unknown"
    rtc_config: BDRConfig = field(default_factory=BDRConfig)

    last_error: Optional[str] = None
