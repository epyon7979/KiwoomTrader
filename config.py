"""전역 설정 - 실제 운영 시 비밀번호 등은 환경변수/별도 파일로 분리하세요."""
from dataclasses import dataclass, field
import os


@dataclass
class TradingConfig:
    # 계좌
    account_no: str = ""                      # 비워두면 첫 번째 계좌 자동 선택
    account_password: str = os.getenv("KIWOOM_PW", "0000")  # 모의투자 기본 0000

    # 감시 종목
    watch_list: list = field(default_factory=lambda: ["005930", "000660", "035420"])

    # 전략 파라미터 (이동평균 교차)
    short_window: int = 5
    long_window: int = 20

    # 리스크 관리
    max_invest_per_stock: int = 1_000_000     # 종목당 최대 투자금
    max_total_exposure: int = 5_000_000       # 총 투자 한도
    stop_loss_pct: float = -3.0               # 손절 (%)
    take_profit_pct: float = 5.0              # 익절 (%)
    daily_loss_limit: int = -300_000          # 일일 손실 한도 (도달 시 신규 매수 중단)

    # 주문
    hoga_type: str = "03"                     # "00" 지정가, "03" 시장가
    dry_run: bool = True                      # True면 주문을 로그로만 남김

    # 운영
    trading_start: str = "09:05"
    trading_end: str = "15:15"
    tr_interval_sec: float = 0.25             # TR 조회 최소 간격 (초당 5회 제한 대응)
