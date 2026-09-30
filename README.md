# Kiwoom 자동매매 프로토타입

## 구조
```
kiwoom_trader/
├─ main.py                # 진입점 (QApplication 이벤트 루프)
├─ config.py              # 계좌·종목·전략·리스크 파라미터
├─ kiwoom/api.py          # OpenAPI+ OCX 래퍼 (로그인/TR/실시간/주문/체결)
├─ strategy/
│   ├─ base.py            # 전략 인터페이스 (Signal: BUY/SELL/HOLD)
│   └─ ma_cross.py        # 이동평균 교차 예시 전략
├─ core/
│   ├─ trader.py          # 오케스트레이터
│   ├─ portfolio.py       # 포지션·미체결·현금 관리
│   └─ risk.py            # 수량 산정, 손절/익절, 일일손실 한도
├─ utils/logger.py        # 콘솔 + 일자별 파일 로그
└─ rest_client_sample.py  # (참고) REST API 버전 최소 예제
```

## 데이터 흐름
로그인 → 계좌/예수금/잔고 조회 → 일봉 로드(전략 초기화) → 실시간 등록
→ 체결가 수신 → 리스크 청산 체크 → 전략 신호 → 주문 → 체결/잔고 이벤트로 포트폴리오 갱신

## 환경
1. 키움 OpenAPI+ 모듈 설치, 상시 모의투자 신청
2. **32bit Python** (3.8~3.10 권장) 가상환경 → `pip install -r requirements.txt`
3. 첫 실행 시 로그인 창에서 "모의투자 접속" 체크
4. `config.py`의 `dry_run=True`로 로그 검증 → 모의투자에서 `False`로 실주문 테스트

## 주의
- TR 조회/주문은 초당 5회 제한, 장시간 반복 조회 시 추가 제한이 있으니 조회 최소화
- 실시간 등록은 화면번호당 100종목
- 이벤트 콜백 안에서 오래 걸리는 작업 금지 (이벤트 루프 블로킹)

# VS Code에서 실행하려면 **32bit Python 환경 준비 → VS Code 인터프리터 지정 → 실행** 순서로 진행
## 1. 사전 준비 (최초 1회)
**키움 쪽 설정**
- 키움증권 홈페이지에서 OpenAPI+ 사용 신청을 하고, 모듈을 설치합니다.
- 상시 모의투자도 신청해 둡니다.

**32bit Python 설치**
- python.org에서 **Windows installer (32-bit)** 를 받아 설치합니다. 3.10 버전을 권장합니다.
- 기존 64bit Python과 함께 설치해도 괜찮습니다.
- 설치 경로를 기억해 두세요. 예: `C:\Python310-32\python.exe`

## 2. VS Code 설정
**① 프로젝트 폴더 열기**
zip을 풀고 `파일 → 폴더 열기`로 **`kiwoom_trader` 폴더 자체**를 엽니다. 상위 폴더를 열면 `import kiwoom` 경로가 맞지 않아 실행되지 않습니다.

**② 32bit 가상환경 만들기**
VS Code 터미널(`Ctrl+``)에서 실행합니다.
```powershell
C:\Python310-32\python.exe -m venv .venv32
.\.venv32\Scripts\activate
python -c "import struct; print(struct.calcsize('P')*8)"   # 32 가 나와야 정상
pip install -r requirements.txt
```
PowerShell에서 activate가 막히면 먼저 `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`를 실행하세요.

**③ 인터프리터 선택**
`Ctrl+Shift+P` → **Python: Select Interpreter** → `.venv32`를 선택합니다. 선택이 잘 됐는지는 우측 하단 상태바에서 확인할 수 있습니다.

**④ 디버그 설정 (F5 실행용)**
`.vscode/launch.json` 파일을 만들고 아래 내용을 넣습니다.
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Kiwoom Trader",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/main.py",
      "cwd": "${workspaceFolder}",
      "console": "integratedTerminal",
      "env": { "KIWOOM_PW": "0000" }
    }
  ]
}
```

## 3. 실행
실행 방법은 두 가지입니다.
- **F5**: 디버그 모드로 실행되어 브레이크포인트를 쓸 수 있습니다.
- **터미널**: `python main.py`

실행하면 다음 순서로 진행됩니다.
1. 키움 로그인 창이 뜨면 **"모의투자 접속"을 체크**하고 로그인합니다.
2. 버전 업데이트 창이 뜨면 업데이트를 마친 뒤 프로그램을 종료하고 다시 실행합니다.
3. 로그인이 끝나면 터미널과 `logs/날짜.log`에 계좌, 예수금, 일봉 로드, 실시간 등록 로그가 출력됩니다.
4. 실시간 시세는 장중(09:00~15:30)에만 들어옵니다. 장외 시간에는 로그인과 조회까지만 확인됩니다.

## 4. 자주 나는 오류
| 증상 | 원인 / 해결 |
|---|---|
| `QAxBase::setControl` 실패, 빈 창만 뜸 | 64bit Python으로 실행됨 → `.venv32` 선택 확인. 또는 OpenAPI+ 미설치 |
| `ModuleNotFoundError: kiwoom` | VS Code에서 상위 폴더를 열었음 → `kiwoom_trader` 폴더로 다시 열기 |
| 잔고/예수금 조회 오류 (비밀번호) | 트레이 아이콘 우클릭 → **계좌비밀번호 저장**에서 등록 (모의투자는 보통 `0000`) |
| 조회 과다 오류 | `config.py`의 `tr_interval_sec` 값을 늘리기 |
| 신호는 나오는데 주문이 안 나감 | 기본값이 `dry_run=True`라서 정상 동작 → 모의투자에서 `False`로 변경 |

처음에는 `dry_run=True` 상태로 장중에 한 번 돌려 보고, 로그에서 신호가 제대로 찍히는지 확인한 다음 실주문으로 넘어가는 것을 권합니다.
# kiwoom
