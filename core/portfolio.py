from dataclasses import dataclass


@dataclass
class Position:
    code: str
    qty: int
    avg_price: int

    def pnl_pct(self, price: int) -> float:
        return (price / self.avg_price - 1) * 100 if self.avg_price else 0.0


class Portfolio:
    def __init__(self):
        self.positions = {}      # code -> Position
        self.pending = set()     # 미체결 주문 종목 (중복주문 방지)
        self.cash = 0
        self.realized_pnl = 0

    def exposure(self) -> int:
        return sum(p.qty * p.avg_price for p in self.positions.values())

    def update(self, code: str, qty: int, avg_price: int):
        if qty <= 0:
            self.positions.pop(code, None)
        else:
            self.positions[code] = Position(code, qty, avg_price)
