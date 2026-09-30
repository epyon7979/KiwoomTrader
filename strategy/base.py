from abc import ABC, abstractmethod
from enum import Enum


class Signal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class Strategy(ABC):
    """전략 공통 인터페이스 - 브로커 API와 분리해 백테스트에도 재사용"""

    @abstractmethod
    def on_init(self, code: str, daily_bars: list) -> None:
        """장 시작 전 과거 데이터 주입"""

    @abstractmethod
    def on_tick(self, code: str, price: int) -> Signal:
        """실시간 체결가 수신 시 호출"""
