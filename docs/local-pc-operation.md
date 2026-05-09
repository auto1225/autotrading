# 로컬 PC 운영 가이드

도메인 없이 이 컴퓨터에서 먼저 운영하는 구성입니다.

```text
이 컴퓨터
├─ FastAPI 대시보드
├─ 업비트 실시간 WebSocket 수신
├─ 페이퍼 자동매매 루프
├─ state/paper_state.json
├─ state/events.jsonl
└─ state/autotrading.sqlite3
```

## 기본 실행

로컬 PC에서만 볼 때:

```powershell
.\scripts\start-local.ps1
```

접속 주소:

```text
http://127.0.0.1:8000/
```

## 같은 와이파이 모바일 접속

휴대폰에서도 보려면 LAN 모드로 실행합니다.

```powershell
.\scripts\start-local.ps1 -Lan
```

현재 이 컴퓨터의 와이파이 내부 IP는 다음 형태입니다.

```text
http://192.168.0.60:8000/
```

연결이 안 되면 Windows 방화벽에서 `8000` 포트를 개인 네트워크에 허용해야 합니다. 방화벽 설정 변경은 보안에 영향을 줄 수 있으니 직접 확인하고 허용하세요.

## 대시보드 로그인 보호

기본값은 이 컴퓨터 전용 운영을 방해하지 않기 위해 꺼져 있습니다. 휴대폰이나 다른 PC에서 접속할 예정이면 `.env`에 다음 값을 넣고 서버를 다시 시작하세요.

```env
DASHBOARD_AUTH_ENABLED=true
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=길고_추측하기_어려운_비밀번호
```

로그인 보호를 켜면 `/`, `/static/*`, `/api/*`가 브라우저 기본 로그인 창으로 보호됩니다. `.\scripts\status-local.ps1`가 계속 동작하도록 `/api/health`만 예외로 둡니다.

## 페이퍼 자동매매 켜기

실거래가 아닌 페이퍼 자동 스캔 루프만 켜려면:

```powershell
.\scripts\start-local.ps1 -AutoRun
```

모바일 접속과 페이퍼 자동매매를 함께 켜려면:

```powershell
.\scripts\start-local.ps1 -Lan -AutoRun
```

## 상태 확인

```powershell
.\scripts\status-local.ps1
```

확인되는 항목:

- 실행 여부
- PID
- 헬스 체크
- 로컬 접속 주소
- LAN 접속 주소

## 운영 알림 확인

대시보드의 `운영 알림`은 다음 상황을 즉시 표시합니다.

- 긴급정지 상태
- 일일 실현손실이 `RISK_DAILY_LOSS_LIMIT_KRW` 이상인 상태
- 일일 주문 수가 `RISK_MAX_DAILY_ORDERS`에 도달한 상태
- Upbit 실시간 WebSocket 수신 끊김
- `AUTO_RUN_ENABLED=true`인데 자동 실행 루프가 멈춘 상태
- LAN 모드인데 대시보드 로그인 보호가 꺼진 상태
- 실거래 또는 웹 실거래 잠금이 해제된 상태

서버 자체가 죽었는지는 외부 감시 스크립트로 확인합니다.

```powershell
.\scripts\watchdog-local.ps1
```

서버가 죽었을 때 자동 재시작까지 원하면:

```powershell
.\scripts\watchdog-local.ps1 -Restart -AutoRun
```

감시 결과는 `state/watchdog-alerts.jsonl`에 기록됩니다.

## Windows 자동 시작과 감시 작업

다음 스크립트는 Windows 작업 스케줄러에 지속 설정을 만듭니다. 실행 전 내용을 확인하고, 원하지 않으면 실행하지 마세요.

로그인할 때 자동 시작:

```powershell
.\scripts\install-autostart-task.ps1 -Lan
```

5분마다 헬스 체크하고 죽었으면 재시작:

```powershell
.\scripts\install-watchdog-task.ps1 -Restart -Lan -AutoRun
```

등록 상태 확인:

```powershell
.\scripts\status-ops-tasks.ps1
```

등록 해제:

```powershell
.\scripts\uninstall-ops-tasks.ps1
```

## 중지

```powershell
.\scripts\stop-local.ps1
```

## 운영 주의사항

- 이 컴퓨터가 꺼지거나 절전 모드에 들어가면 봇도 멈춥니다.
- 인터넷 연결이 끊기면 가격 수신과 주문 검증도 멈춥니다.
- 현재 실거래는 기본 잠금 상태입니다.
- SQLite DB는 `state/autotrading.sqlite3`에 저장됩니다.
- 실거래 전에 이전에 노출된 업비트 API 키는 반드시 폐기하고 새로 발급하세요.
- 외부 인터넷에 직접 공개하지 마세요. 외부 접속이 필요하면 VPN 또는 보안 터널을 먼저 붙이는 쪽이 안전합니다.

## 소액 테스트 주문 리허설

업비트 `/v1/orders/test`는 실제 주문을 만들지 않는 테스트 엔드포인트지만, `주문하기` 권한이 필요하고 인증 요청이 Upbit로 전송됩니다. 기본값은 꺼져 있습니다.

리허설을 열려면 새 API 키를 발급한 뒤 `.env`에 아래 값을 명시적으로 설정하세요.

```env
LIVE_TRADING_ENABLED=true
LIVE_TEST_ORDER_ENABLED=true
LIVE_ORDER_CONFIRMATION=LIVE-RISK-ACCEPTED
```

웹에서 실제 주문 제출까지 열려면 별도로 `WEB_LIVE_TRADING_ENABLED=true`가 필요합니다. 페이퍼 운영 단계에서는 이 값은 계속 `false`로 두세요.
