# 매억남 YouTube Streams Trading Analysis

Source: https://www.youtube.com/@-1maeuknam435/streams
Generated: 2026-05-06T11:35:48.912863+00:00

## Coverage

- Videos listed: 257
- Transcripts fetched: 0
- Transcript failures: 257
- Total stream duration: 388.76 hours
- Transcript characters analyzed: 0

## Top Terms



## Category Frequency

| Category | Keyword hits | Videos with hits |
|---|---:|---:|


## Most Strategy-Dense Videos

| Rank | Date | Video | Hits/hour | Tags |
|---:|---|---|---:|---|


## Extracted Trading-Rule Shape

1. 방향 맞히기보다 먼저 시장 구조를 나눕니다: 고점/저점, 구간, 추세선, 지지/저항, 매물대.
2. 진입은 돌파/이탈 자체보다 확인 캔들, 마감, 눌림/반등, 되돌림 이후가 핵심입니다.
3. 손절/익절은 고정 퍼센트보다 무효화 구간 밖 손절, 다음 구조 구간 익절이 더 적합합니다.
4. 파동/조정/피보나치 키워드가 반복되어 현재 위치가 충동파인지 조정파인지 먼저 분류해야 합니다.
5. 자동매매에는 단일 신호보다 구조 점수, 확인 점수, 손익비 점수, 변동성 점수, 비중 점수를 분리해야 합니다.

## Implementation Notes For The Bot

- Add a market-structure layer before entry scoring: range, support/resistance, recent high/low, trendline proxy, volatility regime.
- Require a confirmation trigger: candle close beyond level, retest/failed retest, volume expansion, or rejection wick.
- Position sizing should be scenario-based: strong confirmation uses higher margin, weak confirmation stays small or watches.
- Stop should be placed outside the invalidation level, not a fixed percent only.
- Take profit should be staged: first target near next level, remainder trailed by structure.
- Contrarian execution should be tested as one mode, but execution direction should ultimately follow measured win rate by structure type.

## Machine Files

- JSON detail: reports/maeuknam_streams_analysis.json
