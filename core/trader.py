"""API · 전략 · 리스크 · 포트폴리오 오케스트레이터"""
from datetime import datetime

from kiwoom.api import KiwoomAPI, to_int
from strategy.base import Signal
from utils.logger import get_logger
from .portfolio import Portfolio
from .risk import RiskManager

log = get_logger("trader")


class Trader:
    def __init__(self, cfg, strategy):
        self.cfg = cfg
        self.api = KiwoomAPI(cfg.tr_interval_sec)
        self.strategy = strategy
        self.pf = Portfolio()
        self.risk = RiskManager(cfg, self.pf)
        self.account = ""

        self.api.sig_real_price.connect(self.on_price)
        self.api.sig_chejan.connect(self.on_chejan)

    # ------------------------------------------------------------ 초기화
    def start(self):
        if not self.api.login():
            raise SystemExit("로그인 실패")
        if not self.api.is_mock_server() and not self.cfg.dry_run:
            log.warning("⚠ 실서버 + 실주문 모드입니다.")

        self.account = self.cfg.account_no or self.api.get_accounts()[0]
        pw = self.cfg.account_password
        self.pf.cash = self.api.get_deposit(self.account, pw)
        for h in self.api.get_balance(self.account, pw):
            self.pf.update(h["code"], h["qty"], h["avg_price"])
        log.info(f"계좌 {self.account} / 주문가능 {self.pf.cash:,}원 / 보유 {list(self.pf.positions)}")

        codes = list(dict.fromkeys(self.cfg.watch_list + list(self.pf.positions)))
        for code in codes:
            bars = self.api.get_daily_ohlcv(code)
            self.strategy.on_init(code, bars)
            log.info(f"{code} {self.api.get_code_name(code)} 일봉 {len(bars)}개 로드")

        self.api.register_real(codes)

    # ------------------------------------------------------------ 실시간
    def _in_trading_time(self) -> bool:
        now = datetime.now().strftime("%H:%M")
        return self.cfg.trading_start <= now <= self.cfg.trading_end

    def on_price(self, code: str, price: int, tm: str):
        if not self._in_trading_time() or code in self.pf.pending:
            return

        pos = self.pf.positions.get(code)
        if pos:                                   # 1) 리스크 청산 우선
            reason = self.risk.exit_reason(pos, price)
            if reason:
                return self._order("sell", code, pos.qty, price, reason)

        signal = self.strategy.on_tick(code, price)   # 2) 전략 신호
        if signal == Signal.BUY:
            qty = self.risk.buy_qty(code, price)
            if qty > 0:
                self._order("buy", code, qty, price, "전략 매수")
        elif signal == Signal.SELL and pos:
            self._order("sell", code, pos.qty, price, "전략 매도")

    def _order(self, side, code, qty, price, reason):
        log.info(f"[{reason}] {side.upper()} {code} {qty}주 (기준가 {price:,})")
        if self.cfg.dry_run:
            self.pf.pending.add(code)   # dry-run에서도 신호 폭주 방지
            return
        hoga_price = 0 if self.cfg.hoga_type == "03" else price
        if self.api.send_order(side, self.account, code, qty, hoga_price, self.cfg.hoga_type) == 0:
            self.pf.pending.add(code)

    # ------------------------------------------------------------ 체결/잔고
    def on_chejan(self, gubun: str, d: dict):
        code = d["code"]
        if gubun == "0":   # 주문 접수/체결
            log.info(f"[주문] {code} {d['status']} 체결 {d['filled_qty'] or 0}주 "
                     f"@{d['filled_price'] or '-'} 미체결 {d['unfilled']}")
            if d["status"] == "체결" and to_int(d["unfilled"]) == 0:
                self.pf.pending.discard(code)
        elif gubun == "1":  # 잔고 변경 = 포지션의 기준 데이터
            old = self.pf.positions.get(code)
            new_qty = to_int(d["qty"])
            if old and new_qty < old.qty:
                self.pf.realized_pnl += (to_int(d["cur_price"]) - old.avg_price) * (old.qty - new_qty)
            self.pf.update(code, new_qty, to_int(d["avg_price"]))
            log.info(f"[잔고] {code} {new_qty}주 / 실현손익 {self.pf.realized_pnl:,}원")
