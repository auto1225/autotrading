# 업비트 자동매매 대시보드

`auto1225/autotrading` 저장소를 바탕으로 만든 업비트 페이퍼 자동매매 시스템입니다.
PC에서 엔진을 실행하고, 데스크톱/모바일 브라우저로 전체 코인 상태와 거래 차트를 확인하는 웹 버전입니다.

이 프로젝트는 투자 조언이나 수익 보장 도구가 아닙니다. 특히 `100만원 -> 1억원 / 30일` 목표는 매우 공격적인 목표이며, 실제 거래에서는 큰 손실이 빠르게 발생할 수 있습니다. 실거래 주문은 기본적으로 잠겨 있고, 충분한 페이퍼 검증 전에는 켜지 않는 것을 전제로 합니다.

## 주요 기능

- 업비트 공개 API 기반 현재가, 분봉 캔들, KRW 마켓 조회
- 업비트 WebSocket 기반 실시간 ticker/trade 캐시
- 데스크톱/모바일 대응 웹 대시보드
- 전체 코인 모니터와 선택 코인의 실제 OHLCV 거래 차트
- 여러 코인 동시 페이퍼 포지션 관리
- 매매 기법 선택: 학습형 적응, 보수적 모멘텀, SMA 교차, 고점 돌파, 평균회귀, RSI, MACD, 볼린저밴드, 스토캐스틱, 일목균형표, VWAP, Donchian 채널
- 전체 KRW 코인 과거 데이터 학습 및 코인별 추천 전략 저장
- 틱/초/분 단위 실시간 상황 판단: 급등, 급락, 상승 추세, 하락 추세, 변동성 과열, 거래대금 증가, 눌림목 감지
- 누적 호가 분석: 주문 전 예상 체결가/슬리피지/체결 가능 잔량을 계산해 금액과 수량을 축소하거나 호가 조정
- 1시간 단위 동적 자금 배분: 전체 KRW 학습 모델과 최신 추세/거래대금을 다시 점수화해 고확률 후보에 분산 또는 집중
- 페이퍼 주문 수수료 반영, 포지션별 평균단가/실현손익/수수료 기록
- 긴급정지, 일일 손실 제한, 재진입 대기시간, 주문 수 제한
- SQLite 운영 기록, JSONL 이벤트 로그
- 실거래 읽기 점검, 주문 미리보기, 업비트 주문 테스트 API 리허설

## 설치

```powershell
cd "C:\Users\cotmd\OneDrive\문서\New project\autotrading"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
Copy-Item .env.example .env
```

공개 시세 조회와 페이퍼 실행은 API 키 없이도 동작합니다. 계좌 조회나 실거래 테스트가 필요할 때만 `.env`에 키를 넣습니다.

## 웹 실행

```powershell
.\scripts\start-local.ps1
```

브라우저에서 접속:

```text
http://127.0.0.1:8000
```

같은 와이파이의 모바일에서 보려면 `.env` 또는 실행 환경에서 호스트를 열고 PC 내부 IP로 접속합니다.

```env
AUTOTRADING_HOST=0.0.0.0
AUTOTRADING_PORT=8000
```

모바일 접속 예:

```text
http://PC내부IP:8000
```

LAN이나 외부망에서 볼 때는 `DASHBOARD_AUTH_ENABLED=true`와 비밀번호 설정을 권장합니다.

## 동적 자금 배분

동적 배분은 100만원을 한 코인에 고정 투자하지 않고, 매 시간 전체 KRW 학습 모델의 후보를 다시 평가합니다.

평가에 쓰는 요소:

- 과거 학습 점수
- 해당 코인에 가장 잘 맞았던 전략의 현재 매수/매도/관망 신호
- 최근 약 1시간 추세
- 최근 거래대금 증가율
- 현재 보유 금액과 목표 비중 차이

기본 동작:

- 점수 차이가 크면 상위 3개 후보에 집중
- 점수 차이가 작으면 상위 8개 후보에 분산
- 총자산의 최대 100%까지 투입
- 한 코인에는 배분 한도의 최대 100%까지 투입
- 선정에서 빠진 보유 코인은 목표 비중을 줄이거나 매도
- 모든 주문은 현재 단계에서 페이퍼 주문으로만 실행

대시보드 버튼:

- `배분 미리보기`: 실제 페이퍼 포트폴리오를 바꾸지 않고 후보와 주문 계획만 확인
- `동적 배분 실행`: 현재 페이퍼 포트폴리오를 기준으로 리밸런싱 주문 실행

관련 `.env` 설정:

```env
DYNAMIC_ALLOCATION_ENABLED=true
ALLOCATION_INTERVAL_SECONDS=3600
ALLOCATION_TOP_N=8
ALLOCATION_FOCUS_TOP_N=3
ALLOCATION_FOCUS_SCORE_GAP=0.12
ALLOCATION_MIN_SCORE=0.02
ALLOCATION_MAX_DEPLOY_PCT=1
ALLOCATION_MAX_POSITION_PCT=1
ALLOCATION_MAX_ORDERS_PER_RUN=1000000
```

동시에 더 많은 코인을 들고 가려면 `ALLOCATION_TOP_N`, `ALLOCATION_MAX_ORDERS_PER_RUN`, `RISK_MAX_OPEN_POSITIONS`를 함께 늘려 운영합니다.

## 실시간 상황 판단

`동적 자금 배분`은 큰 틀의 포트폴리오 리밸런싱이고, `실시간 상황 판단`은 그 사이에 계속 돌아가는 빠른 의사결정 계층입니다.

실시간 판단은 다음을 함께 봅니다.

- 과거 학습 모델의 코인별 전략 점수
- WebSocket/REST 현재가 변화
- 최근 가격 히스토리 기반 초단기 추세
- 1분봉 기반 1분/5분/30분 추세
- 최근 변동성, 고점 대비 낙폭, 거래대금 증가율
- 보유 중인 코인의 현재 평가금액과 진입 상태

정형화된 상황 태그:

- `급등`: 초단기 또는 1분 추세가 빠르게 상승
- `급락`: 초단기/1분/5분 하락이 위험 기준을 넘음
- `상승 추세`: 5분과 30분 흐름이 같이 우상향
- `하락 추세`: 5분과 30분 흐름이 같이 우하향
- `변동성 과열`: 흔들림이 커져 진입 위험 증가
- `거래대금 증가`: 최근 거래대금이 평소보다 크게 증가
- `상승 중 눌림`: 큰 흐름은 상승인데 짧게 눌리는 구간

기본 동작:

- 급락 중 미보유 코인은 진입 회피
- 보유 코인이 급락/하락 전환이면 페이퍼 청산 후보
- 학습 점수와 실시간 상승 흐름이 같이 맞으면 페이퍼 진입 후보
- 이미 오른 코인이 계속 강한 추세라면 고정 익절보다 추세 보유를 우선
- 몇 초 단위 자동 실행 루프에서 반복 판단

관련 `.env` 설정:

```env
REALTIME_DECISION_ENABLED=true
REALTIME_DECISION_INTERVAL_SECONDS=5
REALTIME_WATCH_TOP_N=0
REALTIME_CANDLE_TOP_N=60
REALTIME_CANDLE_REFRESH_SECONDS=60
REALTIME_CANDIDATE_TOP_N=12
REALTIME_MIN_SCORE=0.18
REALTIME_MAX_ORDER_PCT=1
REALTIME_LOW_VOLATILITY_PCT=0.30
REALTIME_STAGNATION_EXIT_SECONDS=900
REALTIME_STAGNATION_TREND_PCT=0.20
REALTIME_STAGNATION_VOLUME_RATIO=1.10
REALTIME_IDLE_EXIT_SECONDS=3600
REALTIME_IDLE_EXIT_RETURN_PCT=0.30
REALTIME_IDLE_EXIT_TREND_PCT=0.40
REALTIME_WEAK_BREAKOUT_ENABLED=false
REALTIME_WEAK_BREAKOUT_SCORE_BUFFER=0.45
REALTIME_RECOVERY_SCOUT_ENABLED=false
REALTIME_RECOVERY_SCOUT_MAX_POSITION_PCT=0.12
GOAL_SCHEDULER_TRADING_ENABLED=true
GOAL_SCHEDULER_MAX_ENTRY_RELIEF=0.08
GOAL_SCHEDULER_MAX_DEPLOY_BOOST=0.40
GOAL_SCHEDULER_MAX_ORDER_BOOST=0.25
GOAL_SCHEDULER_MAX_POSITION_BOOST=0.35
```

대시보드의 `순간 판단 보기`는 주문 없이 현재 상황만 계산하고, `순간 판단 실행`은 페이퍼 포트폴리오에 즉시 반영합니다.
목표 스케줄러가 뒤처짐을 감지하면 위 `GOAL_SCHEDULER_*` 값에 따라 진입 점수 기준과 투입 한도를 보정하지만, 급락·risk-off·손실 패턴 같은 하드 리스크 필터는 우선합니다.

## 누적 호가 분석

실시간 판단과 동적 자금 배분이 주문 후보를 만들면, 업비트 누적 호가를 다시 조회해 예상 체결가와 슬리피지를 계산합니다.

- 매수: 누적 매도호가를 위로 쓸어 보며 요청 금액의 예상 평균 체결가와 슬리피지 계산
- 매도: 누적 매수호가를 아래로 쓸어 보며 요청 수량의 예상 평균 체결가와 슬리피지 계산
- 호가 잔량이 얇거나 슬리피지가 크면 주문 금액/수량을 축소하거나 주문 후보에서 제외
- 스프레드가 넓으면 `suggestedLimitPrice`와 `repriceAction`을 주문 계획에 기록해 호가 변경 판단에 사용

```env
ORDERBOOK_ANALYSIS_ENABLED=true
ORDERBOOK_DEPTH_LEVELS=15
ORDERBOOK_MAX_SLIPPAGE_PCT=0.35
ORDERBOOK_MIN_FILL_RATIO=0.95
ORDERBOOK_MIN_DEPTH_RATIO=0.35
ORDERBOOK_LIQUIDITY_USE_PCT=0.35
ORDERBOOK_REPRICE_SPREAD_PCT=0.12
ORDERBOOK_PRICE_STEP_BPS=5
```

대시보드의 차트 아래 `호가 분석`은 현재 선택 코인의 최소 주문금액 기준 예상 체결가, 슬리피지, 스프레드, 매수/매도 잔량비를 보여줍니다.

## 기본 환경 설정

```env
UPBIT_MARKETS=KRW-BTC,KRW-ETH,KRW-XRP,KRW-SOL,KRW-DOGE,KRW-ADA,KRW-AVAX,KRW-LINK,KRW-DOT,KRW-TRX
UPBIT_CANDLE_UNIT=5
UPBIT_CANDLE_COUNT=80

STRATEGY_NAME=guarded_momentum
LEARNING_CANDLE_COUNT=400
LEARNING_MAX_MARKETS=0
LEARNING_EXCLUDE_MARKET_WARNINGS=true

REALTIME_DECISION_ENABLED=true
REALTIME_DECISION_INTERVAL_SECONDS=5
REALTIME_WATCH_TOP_N=0
REALTIME_CANDLE_TOP_N=60
REALTIME_CANDLE_REFRESH_SECONDS=60
REALTIME_CANDIDATE_TOP_N=12
REALTIME_MIN_SCORE=0.18
REALTIME_MAX_ORDER_PCT=1
REALTIME_LOW_VOLATILITY_PCT=0.30
REALTIME_STAGNATION_EXIT_SECONDS=900
REALTIME_STAGNATION_TREND_PCT=0.20
REALTIME_STAGNATION_VOLUME_RATIO=1.10
REALTIME_IDLE_EXIT_SECONDS=3600
REALTIME_IDLE_EXIT_RETURN_PCT=0.30
REALTIME_IDLE_EXIT_TREND_PCT=0.40
REALTIME_WEAK_BREAKOUT_ENABLED=false
REALTIME_WEAK_BREAKOUT_SCORE_BUFFER=0.45
REALTIME_RECOVERY_SCOUT_ENABLED=false
REALTIME_RECOVERY_SCOUT_MAX_POSITION_PCT=0.12

ORDERBOOK_ANALYSIS_ENABLED=true
ORDERBOOK_DEPTH_LEVELS=15
ORDERBOOK_MAX_SLIPPAGE_PCT=0.35
ORDERBOOK_MIN_FILL_RATIO=0.95
ORDERBOOK_MIN_DEPTH_RATIO=0.35
ORDERBOOK_LIQUIDITY_USE_PCT=0.35
ORDERBOOK_REPRICE_SPREAD_PCT=0.12
ORDERBOOK_PRICE_STEP_BPS=5

PAPER_CASH_KRW=1000000
GOAL_START_KRW=1000000
GOAL_TARGET_KRW=100000000
GOAL_DAYS=30
GOAL_SCHEDULER_TRADING_ENABLED=true
GOAL_SCHEDULER_MAX_ENTRY_RELIEF=0.08
GOAL_SCHEDULER_MAX_DEPLOY_BOOST=0.40
GOAL_SCHEDULER_MAX_ORDER_BOOST=0.25
GOAL_SCHEDULER_MAX_POSITION_BOOST=0.35

RISK_MIN_ORDER_KRW=5000
RISK_MAX_ORDER_KRW=100000000
RISK_MAX_POSITION_KRW=100000000
RISK_DAILY_LOSS_LIMIT_KRW=50000
RISK_STOP_LOSS_PCT=3
RISK_TAKE_PROFIT_PCT=6
RISK_COOLDOWN_SECONDS=300
RISK_MAX_OPEN_POSITIONS=50
RISK_MAX_DAILY_ORDERS=1000000
RISK_FEE_RATE=0.0005

AUTO_RUN_ENABLED=false
DASHBOARD_AUTH_ENABLED=false
```

## 실거래 잠금

실거래는 이중 잠금입니다. 아래 값들이 모두 명시적으로 맞아야 주문 제출 경로가 열립니다.

```env
LIVE_TRADING_ENABLED=true
WEB_LIVE_TRADING_ENABLED=true
LIVE_ORDER_CONFIRMATION=실거래 손실 동의
```

터미널/서버에서 한글 입력이 불편하면 다음 코드도 허용됩니다.

```env
LIVE_ORDER_CONFIRMATION=LIVE-RISK-ACCEPTED
```

이전에 채팅이나 화면에 노출된 업비트 API 키는 즉시 폐기하고 새로 발급해야 합니다. 실거래 권한은 필요한 권한만 켜고, 허용 IP를 이 봇이 실행되는 PC/VPS의 공인 IP로 제한하세요.

## 테스트

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests
```

문법 검사:

```powershell
python -m compileall src tests
```
