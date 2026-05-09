# 재실행/복구 런북

이 문서는 나중에 PC를 재부팅하거나 새 PC에서 다시 실행해도 현재 자동매매 대시보드와 Binance USD-M 선물 모의거래 실험을 복구할 수 있도록 남기는 운영 기록입니다.

실거래는 기본적으로 비활성화 상태를 유지합니다. 이 프로젝트는 투자 조언이나 수익 보장 도구가 아니며, 특히 100배 선물 모의거래 설정은 실제 거래에서 매우 빠르게 큰 손실로 이어질 수 있습니다.

## 1. 저장소 기준

- GitHub 저장소: `https://github.com/auto1225/autotrading.git`
- 기본 브랜치: `main`
- 로컬 작업 폴더: `C:\Users\cotmd\OneDrive\문서\New project\autotrading`
- 실행 진입점: `scripts\start-local.ps1`
- 웹 대시보드: `http://127.0.0.1:8000/`
- 헬스 체크: `http://127.0.0.1:8000/api/health`

현재 커밋은 아래 명령으로 확인합니다.

```powershell
git log -1 --oneline
git status --short --branch
```

정상 상태라면 `main...origin/main`이고 변경 파일이 없어야 합니다.

## 2. 새 PC 또는 새 폴더에서 처음 실행

```powershell
cd "C:\Users\cotmd\OneDrive\문서\New project"
git clone https://github.com/auto1225/autotrading.git
cd autotrading

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .

Copy-Item .env.example .env
```

공개 시세 조회와 모의거래는 API 키 없이도 동작합니다. 실제 계좌 조회나 실거래를 사용할 때만 `.env`에 API 키를 입력합니다.

## 3. 기존 폴더에서 최신 소스 받기

```powershell
cd "C:\Users\cotmd\OneDrive\문서\New project\autotrading"
git pull --ff-only
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

`git pull --ff-only`가 실패하면 로컬 변경 파일이 있다는 뜻입니다. 이때는 변경 파일을 먼저 확인합니다.

```powershell
git status --short
```

## 4. 로컬 서버 실행

일반 실행:

```powershell
.\scripts\start-local.ps1
```

자동 모의거래 루프까지 함께 실행:

```powershell
.\scripts\start-local.ps1 -AutoRun
```

실행 확인:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 10
.\scripts\status-local.ps1
```

브라우저 접속:

```text
http://127.0.0.1:8000/
```

서버 중지:

```powershell
.\scripts\stop-local.ps1
```

## 5. `.env` 핵심 설정

최소 실행에는 `.env.example`을 `.env`로 복사하면 됩니다.

실거래 안전 잠금은 아래처럼 유지합니다.

```env
LIVE_TRADING_ENABLED=false
WEB_LIVE_TRADING_ENABLED=false
LIVE_TEST_ORDER_ENABLED=false
LIVE_ORDER_CONFIRMATION=
```

전략 선택은 `.env`의 `STRATEGY_NAME`으로 합니다.

```env
STRATEGY_NAME=alex_method
```

또는 매억남 카드만 테스트할 때:

```env
STRATEGY_NAME=maeuknam_cards
```

서버를 이미 실행 중이면 `.env` 변경 후 서버를 재시작합니다.

```powershell
.\scripts\stop-local.ps1
.\scripts\start-local.ps1 -AutoRun
```

## 6. 현재 Binance USD-M 선물 모의거래 기준

현재 코드 기준의 Binance 선물 모의거래 실험은 아래 값으로 동작합니다.

- 대상 종목: `BTCUSDT`
- 거래소 모드: Binance USD-M Futures paper
- 레버리지: `100x`
- 기본 최대 포지션 수: `1`
- 알렉스 모델 심볼: `BTCUSDT` 단일 종목
- 알렉스 기준 캔들: `1m`
- 알렉스 문맥 캔들: `12h`, `30m`, `1d`
- 알렉스 일반 진입 마진: 가용 잔고의 `10% ~ 30%`
- 알렉스 watch-probe 진입: 가용 잔고의 `10%`
- 알렉스 순수 성능 검증: 현재 `ALEX_ZERO_FEE_EXPERIMENT = True`
- 매억남 카드 문맥 캔들: `1d`, `1w`, `1M`
- 모의 상태 파일: `state\binance_futures_paper_state.json`

주의: `state\` 폴더는 Git에 커밋하지 않습니다. 이 폴더는 각 PC의 실행 상태, 잔고, 포지션, 로그를 저장하는 런타임 데이터입니다.

## 7. 1000 USDT로 모의계좌 리셋

서버가 켜져 있을 때 API로 리셋하는 방법:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/binance/futures/paper/reset" `
  -ContentType "application/json" `
  -Body '{"balanceUsdt":"1000"}'
```

서버가 꺼져 있고 상태 파일만 직접 초기화해야 할 때는 `state\` 폴더를 만든 뒤 최소 상태를 저장합니다. 보통은 API 리셋을 우선 사용하세요.

```powershell
New-Item -ItemType Directory -Force -Path state | Out-Null
@'
{
  "walletBalanceUsdt": "1000",
  "positions": {},
  "realizedPnlUsdt": "0",
  "grossRealizedPnlUsdt": "0",
  "feesPaidUsdt": "0",
  "openFeesPaidUsdt": "0",
  "closeFeesPaidUsdt": "0",
  "orderCount": 0,
  "lastOrderAt": null,
  "manualAction": null,
  "maeuknamWatchlist": {},
  "maeuknamCooldowns": {},
  "lastClosedCandles": {}
}
'@ | Set-Content -Path state\binance_futures_paper_state.json -Encoding utf8
```

리셋 후 확인:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/binance/futures/paper"
```

## 8. 수동 거래 API

대시보드의 롱, 숏, 스탑, 수동, 자동 버튼은 아래 API를 사용합니다.

롱 진입 또는 전환:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/binance/futures/paper/manual" `
  -ContentType "application/json" `
  -Body '{"action":"LONG","marginPercent":"10"}'
```

숏 진입 또는 전환:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/binance/futures/paper/manual" `
  -ContentType "application/json" `
  -Body '{"action":"SHORT","marginPercent":"10"}'
```

청산 후 수동 스탑 상태:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/binance/futures/paper/manual" `
  -ContentType "application/json" `
  -Body '{"action":"STOP"}'
```

자동 모드 복귀:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/binance/futures/paper/manual" `
  -ContentType "application/json" `
  -Body '{"action":"AUTO"}'
```

금액을 직접 지정하려면 `amountUsdt`를 사용합니다.

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/binance/futures/paper/manual" `
  -ContentType "application/json" `
  -Body '{"action":"LONG","amountUsdt":"100"}'
```

## 9. 자동 판단 사이클 수동 실행

자동 루프를 기다리지 않고 한 번만 실행하려면:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/binance/futures/paper/run"
```

판단 결과에서 꼭 볼 항목:

- `strategySide`: `ALEX_METHOD` 또는 `MAEUKNAM_CARDS`
- `analysisSide`: 모델이 판단한 방향
- `executionSide`: 실제 모의 진입 방향
- `entryStage`: `watch_probe`, `confirmed`, `blocked` 등
- `entryBlockReason`: 진입하지 않은 이유
- `actions`: 실제 오픈/클로즈 액션
- `grossRealizedPnlUsdt`: 수수료 제외 순수 가격 손익
- `feesPaidUsdt`, `openFeesPaidUsdt`, `closeFeesPaidUsdt`: 누적/진입/청산 수수료
- `zeroFeeExperiment`: 알렉스 제로 수수료 실험 여부

## 10. 24시간 점검 에이전시

장시간 자동 점검은 아래 스크립트를 사용합니다.

```powershell
python scripts\maeuknam_24h_agency.py `
  --base-url http://127.0.0.1:8000 `
  --duration-hours 24 `
  --interval-seconds 60 `
  --reset-balance-usdt 1000 `
  --depletion-floor-usdt 5 `
  --fee-cap-reset-seconds 1800
```

점검 결과 위치:

- `reports\maeuknam_24h_agency\status.json`
- `reports\maeuknam_24h_agency\events.jsonl`
- `reports\maeuknam_24h_agency\report.md`

이 스크립트는 모의계좌가 고갈되었거나 운영 정지가 너무 길어질 때 1000 USDT로 다시 시작하도록 설계되어 있습니다. 실제 거래 계좌는 건드리지 않습니다.

## 11. 알렉스 모델 현재 기록

알렉스 모델은 `reports\alex_analysis\alex_strategy_cards.json`의 카드와 `src\upbit_autotrader\alex_strategy.py`, `src\upbit_autotrader\binance_paper.py`의 실행 규칙을 사용합니다.

현재 반영된 핵심 운영 규칙:

- 롱/숏을 미리 고정하지 않고 현재 점수와 문맥에 따라 판단
- 상위 시간대가 과도하게 반대하면 진입 차단
- 손절선이 너무 가까운 노이즈 구간이면 진입 차단
- 목표폭이 너무 작으면 일반 진입 차단
- 확정 신호가 아니어도 조건이 맞으면 작은 watch-probe로 테스트 진입
- 수익 구간에서는 전체를 너무 빨리 닫지 않고 일부 러너 성격의 보호 로직 적용
- 롱/숏 전환은 전환 비용을 이길 가능성이 있을 때만 허용

현재 중요한 실험 결과:

- 수수료를 0으로 둔 상태에서도 이전 알렉스 실험은 24회 청산, 24회 손실이 발생했습니다.
- 따라서 손실 원인은 수수료만이 아니라 진입/청산 구조, 짧은 목표폭, 상위 시간대 역행, 너무 빠른 손절/전환에 있었습니다.
- 이를 줄이기 위해 HTF veto, stop noise block, watch-probe, 10~30% 마진 제한을 반영했습니다.

## 12. 매억남 카드 현재 기록

매억남 모드는 `reports\maeuknam_strategy_cards.json`, `scripts\maeuknam_strategy_extraction.py`, `src\upbit_autotrader\maeuknam_strategy.py`, `src\upbit_autotrader\binance_paper.py`를 사용합니다.

현재 반영된 핵심 운영 규칙:

- 기존 일반 전략과 섞지 않고 매억남 카드 기준만 사용
- 바이낸스 USD-M 선물 종목 정보를 가져오되 실험 대상은 현재 BTCUSDT 중심
- 카드 방향이 롱이면 롱, 숏이면 숏으로 실행
- 영상/카드 근거가 약하면 `entryAllowed=False` 또는 watch 상태 유지
- 목표폭이 왕복 수수료보다 충분히 작으면 진입 차단
- 카드 후보는 관찰, 확인, 진입 단계로 나눔
- 동일 봉/동일 조건에서 과도한 재진입을 막는 보호 로직을 둘 수 있음

## 13. 실행 중 반드시 확인할 화면

대시보드에서 다음 섹션을 우선 확인합니다.

- `자산/상태`: 총자산, 현금, 노출/보유, 실현손익, 총자산 변동
- `실시간 투자금액`: BTCUSDT 포지션, 현재가, 진입가, 평가, 손익, 수익률, 수동 버튼
- `전문가 에이전시`: 현재 선택된 매매기법의 판단 설명
- `전 기능 상태`: 데이터 수집, 실시간 판단, 자동 루프, 차트 갱신 상태
- `차트/판단`: 현재 캔들, SMA5/SMA20, 거래량, 과거 차트 이동

멈춘 것처럼 보이면 먼저 아래 API를 확인합니다.

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/status"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/realtime-decision"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/binance/futures/paper"
```

## 14. 문제별 대응

서버가 켜지지 않을 때:

```powershell
.\scripts\status-local.ps1
.\scripts\stop-local.ps1
.\scripts\start-local.ps1 -AutoRun
Get-Content state\autotrading-web.err.log -Tail 80
```

포트 8000이 이미 사용 중일 때:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen
```

거래가 계속 없을 때 확인할 것:

- 수동 `STOP` 상태인지 확인
- `AUTO` 버튼 또는 manual API로 자동 복귀
- `entryBlockReason`에 HTF veto, target too small, stop inside noise, no closed candles 같은 문구가 있는지 확인
- `/api/binance/futures/paper/run`을 한 번 호출해 즉시 판단 결과 확인

현재가가 멈춘 것처럼 보일 때:

- `/api/binance/futures/paper`의 `updatedAt`이 바뀌는지 확인
- `scripts\status-local.ps1`로 서버가 같은 프로세스로 살아 있는지 확인
- 브라우저 새로고침 후에도 같으면 서버 재시작

글자가 깨져 보일 때:

```powershell
chcp 65001
$OutputEncoding = [System.Text.UTF8Encoding]::new()
```

그 뒤 PowerShell을 새로 열고 다시 실행합니다.

## 15. 테스트

문서나 코드 수정 후 기본 테스트:

```powershell
python -m unittest discover -s tests
```

최근 전체 테스트 기준:

```text
244 tests OK
```

테스트 실패 시 먼저 실패한 테스트명과 변경 파일을 확인합니다.

```powershell
git status --short
python -m unittest tests.test_binance_paper tests.test_web_chart tests.test_investment_agency
```

## 16. 커밋과 푸시

작업 완료 후:

```powershell
git status --short
git add .
git commit -m "작업 내용 요약"
git push
```

커밋 전에는 `.env`, `state\`, `.venv\`, 대용량 영상/이미지 파일이 포함되지 않는지 확인합니다. 현재 `.gitignore`는 이 파일들을 제외하도록 설정되어 있습니다.

## 17. Git에 들어가는 것과 안 들어가는 것

Git에 들어가는 것:

- `src\`: 실행 코드
- `scripts\`: 실행, 분석, 점검 스크립트
- `tests\`: 유닛 테스트
- `docs\`: 운영 문서
- `.env.example`: 공유 가능한 기본 설정
- `reports\`의 텍스트/JSON/Markdown 분석 결과

Git에 들어가지 않는 것:

- `.env`: 개인 키와 로컬 설정
- `.venv\`: 로컬 가상환경
- `state\`: 현재 잔고, 포지션, 로그, DB
- `*.sqlite3`, `*.db`: 런타임 DB
- `reports\` 아래의 대용량 영상, 오디오, 이미지, 로그 파일

새 PC에서 상태 파일이 없으면 앱이 다시 생성합니다. 이전 포지션을 이어가야 할 때만 `state\binance_futures_paper_state.json`을 별도 백업에서 복원합니다.

## 18. 나중에 가장 빠른 재개 순서

이미 설치된 같은 PC에서 다시 시작할 때는 아래 순서만 따르면 됩니다.

```powershell
cd "C:\Users\cotmd\OneDrive\문서\New project\autotrading"
git pull --ff-only
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
.\scripts\start-local.ps1 -AutoRun
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health"
```

1000 USDT로 새 실험을 시작하려면:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/binance/futures/paper/reset" `
  -ContentType "application/json" `
  -Body '{"balanceUsdt":"1000"}'
```

그 다음 대시보드에서 매매기법이 `알렉스기법` 또는 `매억남 카드` 중 원하는 값으로 선택되어 있는지 확인하고, `자동` 상태인지 확인합니다.
