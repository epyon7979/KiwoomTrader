"""실행: 32bit Python에서  python main.py"""
import sys
from PyQt5.QtWidgets import QApplication

from config import TradingConfig
from core.trader import Trader
from strategy.ma_cross import MACrossStrategy


def main():
    app = QApplication(sys.argv)
    cfg = TradingConfig()
    trader = Trader(cfg, MACrossStrategy(cfg.short_window, cfg.long_window))
    trader.start()
    sys.exit(app.exec_())   # Qt 이벤트 루프가 실시간 이벤트를 계속 수신


if __name__ == "__main__":
    main()
