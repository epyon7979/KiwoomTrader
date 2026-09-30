"""
키움 OpenAPI+ (OCX) 래퍼
- 32bit Python + PyQt5 환경에서만 동작
- 비동기 이벤트 기반 API를 QEventLoop로 감싸 동기식처럼 사용
"""
import time
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QObject, QEventLoop, QTimer, pyqtSignal

from utils.logger import get_logger

log = get_logger("kiwoom")


class KiwoomError(Exception):
    pass


def to_int(value: str) -> int:
    """'+12,500' / '-00012500' / '' 형태를 안전하게 정수로 변환 (부호는 등락 표시라 제거)"""
    v = value.strip().replace(",", "").lstrip("+-")
    return int(v) if v else 0


def to_float(value: str) -> float:
    v = value.strip().replace(",", "")
    return float(v) if v not in ("", "+", "-") else 0.0


class KiwoomAPI(QObject):
    sig_real_price = pyqtSignal(str, int, str)      # code, price, time
    sig_chejan = pyqtSignal(str, dict)              # gubun("0" 주문체결 / "1" 잔고), data
    sig_message = pyqtSignal(str)

    REAL_FIDS = "10;15;20"          # 현재가;거래량;체결시간
    CHEJAN_ORDER_FIDS = {
        "account": 9201, "order_no": 9203, "code": 9001, "name": 302,
        "status": 913, "order_qty": 900, "order_price": 901, "unfilled": 902,
        "side": 907, "filled_price": 910, "filled_qty": 911,
    }
    CHEJAN_BALANCE_FIDS = {
        "code": 9001, "name": 302, "qty": 930, "avg_price": 931, "cur_price": 10,
    }
    ORDER_TYPE = {"buy": 1, "sell": 2, "cancel_buy": 3, "cancel_sell": 4,
                  "modify_buy": 5, "modify_sell": 6}

    def __init__(self, tr_interval: float = 0.25):
        super().__init__()
        self.ocx = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        self.ocx.OnEventConnect.connect(self._on_connect)
        self.ocx.OnReceiveTrData.connect(self._on_tr_data)
        self.ocx.OnReceiveRealData.connect(self._on_real_data)
        self.ocx.OnReceiveChejanData.connect(self._on_chejan)
        self.ocx.OnReceiveMsg.connect(self._on_msg)

        self._tr_interval = tr_interval
        self._last_tr_time = 0.0
        self._loop = None
        self._login_ok = False
        self._tr_parser = None
        self._tr_result = None
        self._tr_prev_next = "0"

    # ------------------------------------------------------------------ 로그인
    def login(self, timeout_ms: int = 60_000) -> bool:
        self.ocx.dynamicCall("CommConnect()")
        self._wait(timeout_ms)
        if self._login_ok:
            log.info(f"로그인 성공 ({'모의투자' if self.is_mock_server() else '실서버'})")
        return self._login_ok

    def _on_connect(self, err_code):
        self._login_ok = (err_code == 0)
        if not self._login_ok:
            log.error(f"로그인 실패: {err_code}")
        self._quit()

    def get_accounts(self) -> list:
        raw = self.ocx.dynamicCall("GetLoginInfo(QString)", "ACCNO")
        return [a for a in raw.split(";") if a]

    def is_mock_server(self) -> bool:
        return self.ocx.dynamicCall("GetLoginInfo(QString)", "GetServerGubun") == "1"

    def get_code_name(self, code: str) -> str:
        return self.ocx.dynamicCall("GetMasterCodeName(QString)", code)

    # ------------------------------------------------------------------ TR 공통
    def request_tr(self, trcode, rqname, inputs: dict, parser,
                   prev_next=0, screen="0101", timeout_ms=10_000):
        """TR 요청 후 응답 대기 → parser(trcode, rqname) 결과 반환"""
        self._throttle()
        for k, v in inputs.items():
            self.ocx.dynamicCall("SetInputValue(QString, QString)", k, v)

        self._tr_parser, self._tr_result = parser, None
        ret = self.ocx.dynamicCall("CommRqData(QString, QString, int, QString)",
                                   rqname, trcode, prev_next, screen)
        if ret != 0:
            raise KiwoomError(f"CommRqData 실패 [{trcode}] ret={ret}")
        self._wait(timeout_ms)
        return self._tr_result

    def _on_tr_data(self, screen, rqname, trcode, record, prev_next, *args):
        self._tr_prev_next = prev_next
        try:
            self._tr_result = self._tr_parser(trcode, rqname) if self._tr_parser else None
        except Exception as e:
            log.exception(f"TR 파싱 오류 [{trcode}]: {e}")
        self._quit()

    def _get(self, trcode, rqname, idx, item) -> str:
        return self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)",
                                    trcode, rqname, idx, item).strip()

    def _repeat_cnt(self, trcode, rqname) -> int:
        return self.ocx.dynamicCall("GetRepeatCnt(QString, QString)", trcode, rqname)

    @property
    def has_next(self) -> bool:
        return self._tr_prev_next == "2"   # 연속조회 여부

    # ------------------------------------------------------------------ 조회 TR
    def get_daily_ohlcv(self, code: str, base_date: str = "") -> list:
        """opt10081 주식일봉차트조회 → 과거→최신 순"""
        base_date = base_date or time.strftime("%Y%m%d")

        def parser(tr, rq):
            return [{
                "date": self._get(tr, rq, i, "일자"),
                "open": to_int(self._get(tr, rq, i, "시가")),
                "high": to_int(self._get(tr, rq, i, "고가")),
                "low": to_int(self._get(tr, rq, i, "저가")),
                "close": to_int(self._get(tr, rq, i, "현재가")),
                "volume": to_int(self._get(tr, rq, i, "거래량")),
            } for i in range(self._repeat_cnt(tr, rq))]

        rows = self.request_tr("opt10081", "일봉조회",
                               {"종목코드": code, "기준일자": base_date, "수정주가구분": "1"},
                               parser) or []
        return list(reversed(rows))

    def get_deposit(self, account: str, password: str) -> int:
        """opw00001 예수금상세현황 → 주문가능금액"""
        return self.request_tr("opw00001", "예수금조회",
                               {"계좌번호": account, "비밀번호": password,
                                "비밀번호입력매체구분": "00", "조회구분": "2"},
                               lambda tr, rq: to_int(self._get(tr, rq, 0, "주문가능금액"))) or 0

    def get_balance(self, account: str, password: str) -> list:
        """opw00018 계좌평가잔고내역 → 보유종목"""
        def parser(tr, rq):
            return [{
                "code": self._get(tr, rq, i, "종목번호").lstrip("A"),
                "name": self._get(tr, rq, i, "종목명"),
                "qty": to_int(self._get(tr, rq, i, "보유수량")),
                "avg_price": to_int(self._get(tr, rq, i, "매입가")),
                "cur_price": to_int(self._get(tr, rq, i, "현재가")),
                "pnl_pct": to_float(self._get(tr, rq, i, "수익률(%)")),
            } for i in range(self._repeat_cnt(tr, rq))]

        return self.request_tr("opw00018", "잔고조회",
                               {"계좌번호": account, "비밀번호": password,
                                "비밀번호입력매체구분": "00", "조회구분": "1"},
                               parser) or []

    # ------------------------------------------------------------------ 실시간
    def register_real(self, codes: list, screen: str = "5000", append: bool = False):
        # 화면번호당 최대 100종목
        self.ocx.dynamicCall("SetRealReg(QString, QString, QString, QString)",
                             screen, ";".join(codes), self.REAL_FIDS, "1" if append else "0")
        log.info(f"실시간 등록: {codes}")

    def unregister_real(self, screen: str = "ALL", code: str = "ALL"):
        self.ocx.dynamicCall("SetRealRemove(QString, QString)", screen, code)

    def _on_real_data(self, code, real_type, real_data):
        if real_type != "주식체결":
            return
        get = lambda fid: self.ocx.dynamicCall("GetCommRealData(QString, int)", code, fid)
        self.sig_real_price.emit(code, to_int(get(10)), get(20))

    # ------------------------------------------------------------------ 주문
    def send_order(self, side, account, code, qty, price=0, hoga="03",
                   org_order_no="", screen="9000") -> int:
        """반환 0 = 전송 성공 (체결 여부는 OnReceiveChejanData로 확인)"""
        self._throttle()
        ret = self.ocx.dynamicCall(
            "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
            [f"{side}_{code}", screen, account, self.ORDER_TYPE[side], code,
             qty, price, hoga, org_order_no])
        log.info(f"주문전송 {side} {code} {qty}주 @{price or '시장가'} ret={ret}")
        return ret

    def _on_chejan(self, gubun, item_cnt, fid_list):
        get = lambda fid: self.ocx.dynamicCall("GetChejanData(int)", fid).strip()
        fids = self.CHEJAN_ORDER_FIDS if gubun == "0" else self.CHEJAN_BALANCE_FIDS
        data = {k: get(f) for k, f in fids.items()}
        data["code"] = data["code"].lstrip("A")
        self.sig_chejan.emit(gubun, data)

    def _on_msg(self, screen, rqname, trcode, msg):
        log.info(f"[MSG] {rqname}: {msg}")
        self.sig_message.emit(msg)

    # ------------------------------------------------------------------ 내부
    def _throttle(self):
        wait = self._tr_interval - (time.time() - self._last_tr_time)
        if wait > 0:
            time.sleep(wait)
        self._last_tr_time = time.time()

    def _wait(self, timeout_ms: int):
        self._loop = QEventLoop()
        QTimer.singleShot(timeout_ms, self._loop.quit)   # 타임아웃 안전장치
        self._loop.exec_()
        self._loop = None

    def _quit(self):
        if self._loop is not None:
            self._loop.quit()
