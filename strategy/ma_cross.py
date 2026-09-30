"""이동평균 골든/데드크로스 전략 (예시 - 실전 전 반드시 백테스트)"""
from .base import Strategy, Signal


class MACrossStrategy(Strategy):
    def __init__(self, short: int = 5, long: int = 20):
        assert short < long
        self.short, self.long = short, long
        self.closes = {}   # code -> 전일까지 종가 리스트

    def on_init(self, code, daily_bars):
        closes = [b["close"] for b in daily_bars]
        # 장중 조회 시 마지막 봉은 오늘 → 제외 (오늘 가격은 실시간으로 대체)
        self.closes[code] = closes[:-1] if closes else []

    @staticmethod
    def _ma(values, n):
        return sum(values[-n:]) / n

    def on_tick(self, code, price):
        hist = self.closes.get(code, [])
        if len(hist) < self.long:
            return Signal.HOLD

        prev_s, prev_l = self._ma(hist, self.short), self._ma(hist, self.long)
        today = hist + [price]
        cur_s, cur_l = self._ma(today, self.short), self._ma(today, self.long)

        if prev_s <= prev_l and cur_s > cur_l:
            return Signal.BUY
        if prev_s >= prev_l and cur_s < cur_l:
            return Signal.SELL
        return Signal.HOLD
