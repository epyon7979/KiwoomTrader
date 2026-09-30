from .portfolio import Portfolio, Position


class RiskManager:
    def __init__(self, cfg, portfolio: Portfolio):
        self.cfg, self.pf = cfg, portfolio

    def buy_qty(self, code: str, price: int) -> int:
        """매수 가능 수량 (0이면 매수 불가)"""
        if price <= 0 or code in self.pf.positions or code in self.pf.pending:
            return 0
        if self.pf.realized_pnl <= self.cfg.daily_loss_limit:
            return 0   # 일일 손실 한도 도달
        room = self.cfg.max_total_exposure - self.pf.exposure()
        budget = min(self.cfg.max_invest_per_stock, room, self.pf.cash)
        return max(budget // price, 0)

    def exit_reason(self, pos: Position, price: int):
        pct = pos.pnl_pct(price)
        if pct <= self.cfg.stop_loss_pct:
            return f"손절({pct:.2f}%)"
        if pct >= self.cfg.take_profit_pct:
            return f"익절({pct:.2f}%)"
        return None
