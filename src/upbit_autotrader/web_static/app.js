const els = {
  updatedAt: document.querySelector("#updatedAt"),
  runtimeBadge: document.querySelector("#runtimeBadge"),
  stopButton: document.querySelector("#stopButton"),
  resumeButton: document.querySelector("#resumeButton"),
  runOnceButton: document.querySelector("#runOnceButton"),
  scanButton: document.querySelector("#scanButton"),
  autoStartButton: document.querySelector("#autoStartButton"),
  autoStopButton: document.querySelector("#autoStopButton"),
  autoRunHeaderDot: document.querySelector("#autoRunHeaderDot"),
  autoRunHeaderState: document.querySelector("#autoRunHeaderState"),
  autoRunHeaderDetail: document.querySelector("#autoRunHeaderDetail"),
  systemStatusSummary: document.querySelector("#systemStatusSummary"),
  systemModeBadge: document.querySelector("#systemModeBadge"),
  systemStatusGrid: document.querySelector("#systemStatusGrid"),
  exchangeModeSelect: document.querySelector("#exchangeModeSelect"),
  exchangeModeButton: document.querySelector("#exchangeModeButton"),
  exchangeModeDetail: document.querySelector("#exchangeModeDetail"),
  refreshButton: document.querySelector("#refreshButton"),
  strategySelect: document.querySelector("#strategySelect"),
  strategyAutoToggle: document.querySelector("#strategyAutoToggle"),
  strategyDescription: document.querySelector("#strategyDescription"),
  goalText: document.querySelector("#goalText"),
  goalDetail: document.querySelector("#goalDetail"),
  goalProgress: document.querySelector("#goalProgress"),
  realtimeState: document.querySelector("#realtimeState"),
  realtimeDetail: document.querySelector("#realtimeDetail"),
  autoRunState: document.querySelector("#autoRunState"),
  autoRunDetail: document.querySelector("#autoRunDetail"),
  dailyRiskState: document.querySelector("#dailyRiskState"),
  dailyRiskDetail: document.querySelector("#dailyRiskDetail"),
  securityState: document.querySelector("#securityState"),
  securityDetail: document.querySelector("#securityDetail"),
  marketName: document.querySelector("#marketName"),
  marketPrice: document.querySelector("#marketPrice"),
  marketChange: document.querySelector("#marketChange"),
  chartTitle: document.querySelector("#chartTitle"),
  chartMeta: document.querySelector("#chartMeta"),
  chartZoomInButton: document.querySelector("#chartZoomInButton"),
  chartZoomOutButton: document.querySelector("#chartZoomOutButton"),
  chartZoomResetButton: document.querySelector("#chartZoomResetButton"),
  chartZoomLabel: document.querySelector("#chartZoomLabel"),
  chartPanOlderButton: document.querySelector("#chartPanOlderButton"),
  chartPanNewerButton: document.querySelector("#chartPanNewerButton"),
  chartPanLatestButton: document.querySelector("#chartPanLatestButton"),
  chartPanLabel: document.querySelector("#chartPanLabel"),
  chartUnitButtons: Array.from(document.querySelectorAll(".chart-unit-button")),
  holdingChartUnitButtons: Array.from(document.querySelectorAll(".holding-chart-unit-button")),
  residentState: document.querySelector("#residentState"),
  residentDetail: document.querySelector("#residentDetail"),
  residentAiState: document.querySelector("#residentAiState"),
  residentAiDetail: document.querySelector("#residentAiDetail"),
  residentCadence: document.querySelector("#residentCadence"),
  residentCoverage: document.querySelector("#residentCoverage"),
  residentDecision: document.querySelector("#residentDecision"),
  residentExecution: document.querySelector("#residentExecution"),
  residentPrimaryNarrative: document.querySelector("#residentPrimaryNarrative"),
  residentWatchList: document.querySelector("#residentWatchList"),
  residentActionList: document.querySelector("#residentActionList"),
  pmAnalyzeButton: document.querySelector("#pmAnalyzeButton"),
  pmChatState: document.querySelector("#pmChatState"),
  pmChatModel: document.querySelector("#pmChatModel"),
  pmChatMessages: document.querySelector("#pmChatMessages"),
  pmChatForm: document.querySelector("#pmChatForm"),
  pmChatInput: document.querySelector("#pmChatInput"),
  pmChatSendButton: document.querySelector("#pmChatSendButton"),
  pmSchedulerState: document.querySelector("#pmSchedulerState"),
  pmSchedulerNarrative: document.querySelector("#pmSchedulerNarrative"),
  pmSchedulerDailyRate: document.querySelector("#pmSchedulerDailyRate"),
  pmSchedulerHourlyRate: document.querySelector("#pmSchedulerHourlyRate"),
  pmSchedulerGap: document.querySelector("#pmSchedulerGap"),
  pmSchedulerLive: document.querySelector("#pmSchedulerLive"),
  pmSchedulerEngine: document.querySelector("#pmSchedulerEngine"),
  pmSchedulerCalendar: document.querySelector("#pmSchedulerCalendar"),
  pmSchedulerHours: document.querySelector("#pmSchedulerHours"),
  pmSchedulerFallback: document.querySelector("#pmSchedulerFallback"),
  pmSchedulerRefreshButton: document.querySelector("#pmSchedulerRefreshButton"),
  analysisNarrative: document.querySelector("#analysisNarrative"),
  analysisMode: document.querySelector("#analysisMode"),
  analysisCoverage: document.querySelector("#analysisCoverage"),
  analysisUpdatedAt: document.querySelector("#analysisUpdatedAt"),
  analysisRegime: document.querySelector("#analysisRegime"),
  analysisScanProgress: document.querySelector("#analysisScanProgress"),
  analysisUniverse: document.querySelector("#analysisUniverse"),
  analysisSelected: document.querySelector("#analysisSelected"),
  analysisOrders: document.querySelector("#analysisOrders"),
  analysisTopScore: document.querySelector("#analysisTopScore"),
  analysisReasonList: document.querySelector("#analysisReasonList"),
  analysisCandidateList: document.querySelector("#analysisCandidateList"),
  intelState: document.querySelector("#intelState"),
  intelUpdatedAt: document.querySelector("#intelUpdatedAt"),
  intelRefreshButton: document.querySelector("#intelRefreshButton"),
  intelNarrative: document.querySelector("#intelNarrative"),
  intelNextRun: document.querySelector("#intelNextRun"),
  intelSourceCount: document.querySelector("#intelSourceCount"),
  intelItemCount: document.querySelector("#intelItemCount"),
  intelGlobalState: document.querySelector("#intelGlobalState"),
  intelCoinList: document.querySelector("#intelCoinList"),
  intelTrendingList: document.querySelector("#intelTrendingList"),
  intelNewsList: document.querySelector("#intelNewsList"),
  intelSourceList: document.querySelector("#intelSourceList"),
  orderbookState: document.querySelector("#orderbookState"),
  orderbookDetail: document.querySelector("#orderbookDetail"),
  orderbookButton: document.querySelector("#orderbookButton"),
  signalLabel: document.querySelector("#signalLabel"),
  signalReason: document.querySelector("#signalReason"),
  riskLabel: document.querySelector("#riskLabel"),
  riskReason: document.querySelector("#riskReason"),
  equityKrw: document.querySelector("#equityKrw"),
  cashKrw: document.querySelector("#cashKrw"),
  positionValue: document.querySelector("#positionValue"),
  realizedPnl: document.querySelector("#realizedPnl"),
  orderCount: document.querySelector("#orderCount"),
  portfolioFlowState: document.querySelector("#portfolioFlowState"),
  portfolioFlowDetail: document.querySelector("#portfolioFlowDetail"),
  portfolioFlowDelta: document.querySelector("#portfolioFlowDelta"),
  portfolioFlowPositionDelta: document.querySelector("#portfolioFlowPositionDelta"),
  portfolioFlowCashDelta: document.querySelector("#portfolioFlowCashDelta"),
  portfolioFlowRealizedDelta: document.querySelector("#portfolioFlowRealizedDelta"),
  portfolioFlowRows: document.querySelector("#portfolioFlowRows"),
  portfolioChartTitle: document.querySelector("#portfolioChartTitle"),
  portfolioChartMeta: document.querySelector("#portfolioChartMeta"),
  portfolioChartZoomInButton: document.querySelector("#portfolioChartZoomInButton"),
  portfolioChartZoomOutButton: document.querySelector("#portfolioChartZoomOutButton"),
  portfolioChartZoomResetButton: document.querySelector("#portfolioChartZoomResetButton"),
  portfolioChartZoomLabel: document.querySelector("#portfolioChartZoomLabel"),
  portfolioChartUnitButtons: Array.from(document.querySelectorAll(".portfolio-chart-unit-button")),
  portfolioChart: document.querySelector("#portfolioFlowChart"),
  portfolioFeeBreakdown: document.querySelector("#portfolioFeeBreakdown"),
  opsWatchState: document.querySelector("#opsWatchState"),
  opsWatchDetail: document.querySelector("#opsWatchDetail"),
  opsRiskList: document.querySelector("#opsRiskList"),
  opsTriggerList: document.querySelector("#opsTriggerList"),
  opsCandidateList: document.querySelector("#opsCandidateList"),
  opsOperationList: document.querySelector("#opsOperationList"),
  agencyState: document.querySelector("#agencyState"),
  agencyDetail: document.querySelector("#agencyDetail"),
  agencyDataList: document.querySelector("#agencyDataList"),
  agencyMemberList: document.querySelector("#agencyMemberList"),
  agencyActionList: document.querySelector("#agencyActionList"),
  liveModeBadge: document.querySelector("#liveModeBadge"),
  liveKeyState: document.querySelector("#liveKeyState"),
  liveKeyDetail: document.querySelector("#liveKeyDetail"),
  liveLockState: document.querySelector("#liveLockState"),
  liveLockDetail: document.querySelector("#liveLockDetail"),
  liveCashKrw: document.querySelector("#liveCashKrw"),
  liveAccountDetail: document.querySelector("#liveAccountDetail"),
  livePreviewState: document.querySelector("#livePreviewState"),
  livePreviewDetail: document.querySelector("#livePreviewDetail"),
  liveTestState: document.querySelector("#liveTestState"),
  liveTestDetail: document.querySelector("#liveTestDetail"),
  liveCheckButton: document.querySelector("#liveCheckButton"),
  livePreviewButton: document.querySelector("#livePreviewButton"),
  liveTestOrderButton: document.querySelector("#liveTestOrderButton"),
  backtestButton: document.querySelector("#backtestButton"),
  simulationButton: document.querySelector("#simulationButton"),
  eventsButton: document.querySelector("#eventsButton"),
  exchangesButton: document.querySelector("#exchangesButton"),
  binancePaperButton: document.querySelector("#binancePaperButton"),
  dbButton: document.querySelector("#dbButton"),
  learnButton: document.querySelector("#learnButton"),
  learnAllButton: document.querySelector("#learnAllButton"),
  allocationPreviewButton: document.querySelector("#allocationPreviewButton"),
  allocationRunButton: document.querySelector("#allocationRunButton"),
  realtimeDecisionPreviewButton: document.querySelector("#realtimeDecisionPreviewButton"),
  realtimeDecisionRunButton: document.querySelector("#realtimeDecisionRunButton"),
  backtestStrategy: document.querySelector("#backtestStrategy"),
  bestBacktestMarket: document.querySelector("#bestBacktestMarket"),
  bestBacktestDetail: document.querySelector("#bestBacktestDetail"),
  worstBacktestMarket: document.querySelector("#worstBacktestMarket"),
  worstBacktestDetail: document.querySelector("#worstBacktestDetail"),
  eventLogCount: document.querySelector("#eventLogCount"),
  eventLogDetail: document.querySelector("#eventLogDetail"),
  exchangeState: document.querySelector("#exchangeState"),
  exchangeDetail: document.querySelector("#exchangeDetail"),
  dbState: document.querySelector("#dbState"),
  dbDetail: document.querySelector("#dbDetail"),
  alertsButton: document.querySelector("#alertsButton"),
  alertState: document.querySelector("#alertState"),
  alertDetail: document.querySelector("#alertDetail"),
  learningState: document.querySelector("#learningState"),
  learningDetail: document.querySelector("#learningDetail"),
  allocationState: document.querySelector("#allocationState"),
  allocationDetail: document.querySelector("#allocationDetail"),
  realtimeDecisionState: document.querySelector("#realtimeDecisionState"),
  realtimeDecisionDetail: document.querySelector("#realtimeDecisionDetail"),
  simulationState: document.querySelector("#simulationState"),
  simulationDetail: document.querySelector("#simulationDetail"),
  simulationRange: document.querySelector("#simulationRange"),
  simulationAssumption: document.querySelector("#simulationAssumption"),
  simulationTopStrategy: document.querySelector("#simulationTopStrategy"),
  simulationTopDetail: document.querySelector("#simulationTopDetail"),
  playbackState: document.querySelector("#playbackState"),
  playbackTime: document.querySelector("#playbackTime"),
  playbackFile: document.querySelector("#playbackFile"),
  playbackEquity: document.querySelector("#playbackEquity"),
  playbackReturn: document.querySelector("#playbackReturn"),
  playbackCash: document.querySelector("#playbackCash"),
  playbackPositions: document.querySelector("#playbackPositions"),
  playbackOrders: document.querySelector("#playbackOrders"),
  playbackProgressText: document.querySelector("#playbackProgressText"),
  playbackProgress: document.querySelector("#playbackProgress"),
  playbackLoadButton: document.querySelector("#playbackLoadButton"),
  playbackStartButton: document.querySelector("#playbackStartButton"),
  playbackPauseButton: document.querySelector("#playbackPauseButton"),
  playbackTradeRows: document.querySelector("#playbackTradeRows"),
  errorCount: document.querySelector("#errorCount"),
  marketCount: document.querySelector("#marketCount"),
  recommendedCount: document.querySelector("#recommendedCount"),
  recommendOnlyButton: document.querySelector("#recommendOnlyButton"),
  recommendAllButton: document.querySelector("#recommendAllButton"),
  excludeAllButton: document.querySelector("#excludeAllButton"),
  recommendedClearButton: document.querySelector("#recommendedClearButton"),
  marketRows: document.querySelector("#marketRows"),
  holdingCharts: document.querySelector("#holdingCharts"),
  holdingChartsState: document.querySelector("#holdingChartsState"),
  logList: document.querySelector("#logList"),
  chart: document.querySelector("#tradeChart"),
  toast: document.querySelector("#toast"),
};

const money = new Intl.NumberFormat("ko-KR", {
  maximumFractionDigits: 0,
});

const number = new Intl.NumberFormat("ko-KR", {
  maximumFractionDigits: 8,
});

const percent2 = new Intl.NumberFormat("ko-KR", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

let latestStatus = null;
let selectedMarket = "KRW-BTC";
let latestChart = [];
let strategyOptions = [];
let learningPollTimer = 0;
let marketSortKey = "changeRate";
let marketSortDirection = "desc";
let simulationApiUnavailable = false;
let investmentBaselineSnapshot = null;
let investmentBaselineSignature = "";
let playbackFrames = [];
let playbackTrades = [];
let playbackPayload = null;
let playbackIndex = 0;
let playbackTimer = 0;
const playbackIntervalMs = 35;
let statusRefreshInFlight = false;
let chartUnit = "5";
let holdingChartUnit = "5";
let portfolioChartUnit = "5";
let latestPortfolioChart = [];
let renderedHoldingMarketsKey = "";
let holdingChartsInFlight = false;
let portfolioChartInFlight = false;
let latestRealtimeDecisionPayload = null;
let pmChatInFlight = false;
const liveFuturesPrices = new Map();
let binanceFuturesTickerSocket = null;
let binanceFuturesTickerSymbol = "";
let binanceFuturesTickerReconnectTimer = 0;
let liveFuturesRenderQueued = false;
let manualFuturesLastTrigger = { action: "", at: 0 };
let lastManualFuturesResult = null;
let manualFuturesSizing = { mode: "percent", percent: "100", customPercent: "", amountUsdt: "", dirty: false };
const manualFuturesFeeRate = 0.0004;
const holdingChartCache = new Map();
const chartZoomLevels = [1, 1.35, 1.8, 2.4, 3.2, 4.4, 6];
const chartZoomState = new Map();
const chartPanState = new Map();
const chartRiseColor = "#d24f45";
const chartFallColor = "#1261c4";
const dashboardSectionOrderKey = "autotrading.dashboardSectionOrder.v3";
const dashboardDefaultSectionOrder = [
  "system-status-panel",
  "overview-panel",
  "ops-watch-panel",
  "agency-panel",
  "trade-workspace",
  "analysis-panel",
  "intel-panel",
  "resident-panel",
  "monitor-panel",
  "controls-panel",
  "live-panel",
  "research-panel",
  "playback-panel",
  "log-panel",
];
let draggedDashboardSection = null;
let dragOverDashboardSection = null;
let dashboardPointerDrag = null;

const dashboardSectionMeta = {
  "system-status-panel": { label: "전 기능 상태", tier: "core", tierLabel: "필수" },
  "overview-panel": { label: "자산/상태", tier: "core", tierLabel: "필수" },
  "ops-watch-panel": { label: "운영 리스크", tier: "core", tierLabel: "필수" },
  "agency-panel": { label: "전문가 에이전시", tier: "core", tierLabel: "필수" },
  "trade-workspace": { label: "차트/판단", tier: "core", tierLabel: "필수" },
  "analysis-panel": { label: "실시간 분석", tier: "core", tierLabel: "필수" },
  "intel-panel": { label: "시장 인텔", tier: "core", tierLabel: "필수" },
  "resident-panel": { label: "AI PM", tier: "core", tierLabel: "필수" },
  "monitor-panel": { label: "전체 코인", tier: "core", tierLabel: "필수" },
  "controls-panel": { label: "수동 제어", tier: "support", tierLabel: "보조" },
  "live-panel": { label: "실거래 준비", tier: "support", tierLabel: "조건부" },
  "research-panel": { label: "검증 리포트", tier: "support", tierLabel: "보조" },
  "playback-panel": { label: "과거 재생", tier: "support", tierLabel: "보조" },
  "log-panel": { label: "로그", tier: "support", tierLabel: "보조" },
};

const dashboardSectionLabels = Object.fromEntries(
  Object.entries(dashboardSectionMeta).map(([key, meta]) => [key, meta.label])
);

const chartUnitLabels = {
  "1": "1분",
  "3": "3분",
  "5": "5분",
  "10": "10분",
  "15": "15분",
  "30": "30분",
  "60": "1시간",
  "240": "4시간",
  day: "일",
  week: "주",
  month: "월",
  year: "년",
};

const marketSorters = {
  recommended: (row) => (row.recommended ? 1 : 0),
  excluded: (row) => (row.excluded ? 1 : 0),
  changeRate: (row) => Number(row.changeRate || 0),
  positionValueKrw: (row) => Number(row.positionValueKrw || 0),
  realizedPnlKrw: (row) => Number(row.realizedPnlKrw || 0),
  price: (row) => Number(row.price || 0),
  tradeValue24h: (row) => Number(row.tradeValue24h || 0),
  returnPct: (row) => Number(row.returnPct || 0),
  unrealizedPnlKrw: (row) => Number(row.unrealizedPnlKrw || 0),
  symbol: (row) => marketLabel(row).toLocaleLowerCase("ko-KR"),
};

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || "요청 처리 중 오류가 발생했습니다");
  }
  return payload;
}

async function loadStrategies() {
  try {
    const payload = await requestJson("/api/strategies");
    renderStrategyOptions(payload);
  } catch (error) {
    els.strategyDescription.textContent = error.message;
  }
}

async function selectStrategy() {
  const strategy = els.strategySelect.value;
  if (!strategy) return;
  els.strategySelect.disabled = true;
  try {
    const payload = await requestJson("/api/strategies/select", {
      method: "POST",
      body: JSON.stringify({ strategy, auto: false }),
    });
    renderStrategyOptions(payload);
    latestStatus = payload.status;
    renderStatus(latestStatus);
    latestChart = [];
    await loadTradingChart(selectedMarket);
    showToast(`매매 기법을 ${selectedStrategyLabel(strategy)}로 바꿨습니다`);
  } catch (error) {
    showToast(error.message);
  } finally {
    els.strategySelect.disabled = false;
  }
}

async function toggleAutoStrategy() {
  const auto = Boolean(els.strategyAutoToggle.checked);
  els.strategyAutoToggle.disabled = true;
  els.strategySelect.disabled = true;
  try {
    const payload = await requestJson("/api/strategies/select", {
      method: "POST",
      body: JSON.stringify({ strategy: els.strategySelect.value || undefined, auto }),
    });
    renderStrategyOptions(payload);
    latestStatus = payload.status;
    renderStatus(latestStatus);
    latestChart = [];
    await loadTradingChart(selectedMarket);
    showToast(auto ? "매매 기법 자동설정을 켰습니다" : "매매 기법 수동선택으로 전환했습니다");
  } catch (error) {
    els.strategyAutoToggle.checked = !auto;
    showToast(error.message);
  } finally {
    els.strategyAutoToggle.disabled = false;
    els.strategySelect.disabled = Boolean(els.strategyAutoToggle.checked);
  }
}

async function refreshStatus(options = {}) {
  if (statusRefreshInFlight) return;
  statusRefreshInFlight = true;
  const loadDetails = options.loadDetails === true;
  setBusy(els.refreshButton, true);
  try {
    const status = await requestJson("/api/status");
    latestStatus = status;
    renderStatus(status);
    if (loadDetails) {
      await loadTradingChart(selectedMarket);
      await loadPortfolioChart({ force: true });
      await loadOrderbookAnalysis(selectedMarket);
      await loadLatestSimulation({ setButtonBusy: false });
    }
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(els.refreshButton, false);
    statusRefreshInFlight = false;
  }
}

async function runOnce() {
  setBusy(els.runOnceButton, true);
  try {
    const payload = await requestJson("/api/run-once", {
      method: "POST",
      body: JSON.stringify({ live: false, market: selectedMarket }),
    });
    latestStatus = payload["상태"];
    renderStatus(latestStatus);
    showToast("페이퍼 1회 실행을 완료했습니다");
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(els.runOnceButton, false);
  }
}

async function scanOnce() {
  setBusy(els.scanButton, true);
  try {
    const payload = await requestJson("/api/scan-once", { method: "POST" });
    latestStatus = payload["상태"];
    renderStatus(latestStatus);
    showToast(`전체 코인 스캔을 완료했습니다 (${payload["스캔결과"].length}개)`);
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(els.scanButton, false);
  }
}

async function toggleRecommendedMarket(market, preference, checked, checkbox) {
  if (checkbox) checkbox.disabled = true;
  try {
    const payload = await requestJson("/api/recommended-markets/toggle", {
      method: "POST",
      body: JSON.stringify({ market, preference, checked }),
    });
    applyRecommendedPayload(payload);
    const label = preference === "excluded" ? "비추천" : "추천";
    showToast(
      checked
        ? `${displayMarketCode(market)} ${label} 체크를 켰습니다`
        : `${displayMarketCode(market)} ${label} 체크를 해제했습니다`,
    );
  } catch (error) {
    if (checkbox) checkbox.checked = !checked;
    showToast(error.message);
  } finally {
    if (checkbox) checkbox.disabled = false;
  }
}

function visibleMarketCodes() {
  return latestStatus ? latestStatus.markets.map((row) => row.market) : [];
}

async function saveMarketPreferences({ markets, excludedMarkets, recommendOnly, busyButton, toastMessage }) {
  if (busyButton) setBusy(busyButton, true);
  try {
    const body = {};
    if (markets) body.markets = markets;
    if (excludedMarkets) body.excludedMarkets = excludedMarkets;
    if (recommendOnly !== undefined) body.recommendOnly = recommendOnly;
    const payload = await requestJson("/api/recommended-markets", {
      method: "POST",
      body: JSON.stringify(body),
    });
    applyRecommendedPayload(payload);
    if (toastMessage) showToast(toastMessage);
  } catch (error) {
    showToast(error.message);
  } finally {
    if (busyButton) setBusy(busyButton, false);
  }
}

async function setRecommendOnlyMode(recommendOnly) {
  setBusy(els.recommendOnlyButton, true);
  try {
    const payload = await requestJson("/api/recommended-markets/mode", {
      method: "POST",
      body: JSON.stringify({ recommendOnly }),
    });
    applyRecommendedPayload(payload);
    showToast(recommendOnly ? "추천 코인을 우선 검토하도록 설정했습니다" : "전체 자동 후보 투자로 전환했습니다");
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(els.recommendOnlyButton, false);
  }
}

function toggleRecommendOnlyMode() {
  const current = Boolean(latestStatus?.recommended?.recommendOnly);
  setRecommendOnlyMode(!current);
}

async function recommendAllMarkets() {
  const markets = visibleMarketCodes();
  await saveMarketPreferences({
    markets,
    excludedMarkets: [],
    busyButton: els.recommendAllButton,
    toastMessage: `전체 ${markets.length}개 코인을 추천 체크했습니다`,
  });
}

async function excludeAllMarkets() {
  const markets = visibleMarketCodes();
  await saveMarketPreferences({
    markets: [],
    excludedMarkets: markets,
    busyButton: els.excludeAllButton,
    toastMessage: `전체 ${markets.length}개 코인을 비추천 체크했습니다`,
  });
}

async function clearRecommendedMarkets() {
  setBusy(els.recommendedClearButton, true);
  await saveMarketPreferences({
    markets: [],
    excludedMarkets: [],
    busyButton: null,
    toastMessage: "추천/비추천 체크를 모두 해제했습니다",
  });
  setBusy(els.recommendedClearButton, false);
}

function applyRecommendedPayload(payload) {
  const recommendedMarkets = new Set(payload.markets || []);
  const excludedMarkets = new Set(payload.excludedMarkets || []);
  if (latestStatus) {
    latestStatus.recommended = payload;
    latestStatus.markets = latestStatus.markets.map((row) => ({
      ...row,
      recommended: recommendedMarkets.has(row.market),
      excluded: excludedMarkets.has(row.market),
    }));
    renderRecommendedSummary(payload);
    renderMarkets(latestStatus.markets);
  } else {
    renderRecommendedSummary(payload);
  }
}

async function startAutoRun() {
  setBusy(els.autoStartButton, true);
  try {
    const payload = await requestJson("/api/autorun/start", { method: "POST" });
    latestStatus = payload["상태"];
    renderStatus(latestStatus);
    showToast("자동 매매 루프를 시작했습니다");
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(els.autoStartButton, false);
    if (latestStatus) renderRuntimeStatus(latestStatus);
  }
}

async function stopAutoRun() {
  setBusy(els.autoStopButton, true);
  try {
    const payload = await requestJson("/api/autorun/stop", { method: "POST" });
    latestStatus = payload["상태"];
    renderStatus(latestStatus);
    showToast("자동 매매 루프를 중지했습니다");
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(els.autoStopButton, false);
    if (latestStatus) renderRuntimeStatus(latestStatus);
  }
}

async function checkLiveReadiness() {
  setBusy(els.liveCheckButton, true);
  try {
    const payload = await requestJson("/api/live/check", {
      method: "POST",
      body: JSON.stringify({ market: selectedMarket }),
    });
    renderLiveCheck(payload);
    showToast(payload.ok ? "실거래 읽기 점검을 완료했습니다" : "실거래 점검 항목이 남아 있습니다");
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(els.liveCheckButton, false);
  }
}

async function previewLiveOrder() {
  setBusy(els.livePreviewButton, true);
  try {
    const payload = await requestJson("/api/live/preview", {
      method: "POST",
      body: JSON.stringify({ market: selectedMarket }),
    });
    renderLivePreview(payload);
    showToast(payload.ok ? "실거래 주문 미리보기를 만들었습니다" : payload.message);
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(els.livePreviewButton, false);
  }
}

async function testLiveOrder() {
  const confirmation =
    window.prompt("실제 주문이 생성되지 않는 업비트 주문 테스트입니다. 확인 문구 또는 코드 입력: 실거래 손실 동의 / LIVE-RISK-ACCEPTED") || "";
  setBusy(els.liveTestOrderButton, true);
  try {
    const payload = await requestJson("/api/live/test-order", {
      method: "POST",
      body: JSON.stringify({ market: selectedMarket, confirmation }),
    });
    els.livePreviewState.textContent = payload.ok ? "테스트 통과" : "테스트 실패";
    els.livePreviewDetail.textContent = `${payload.market} 주문 생성 테스트 완료`;
    showToast("업비트 주문 생성 테스트를 완료했습니다");
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(els.liveTestOrderButton, false);
  }
}

async function runBacktestReport() {
  setBusy(els.backtestButton, true);
  try {
    const payload = await requestJson("/api/backtest?count=160");
    renderBacktest(payload);
    showToast("백테스트 리포트를 갱신했습니다");
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(els.backtestButton, false);
  }
}

async function loadEventLog() {
  setBusy(els.eventsButton, true);
  try {
    const payload = await requestJson("/api/events?limit=60");
    renderEvents(payload);
    showToast("운영 로그를 불러왔습니다");
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(els.eventsButton, false);
  }
}

async function checkExchanges() {
  setBusy(els.exchangesButton, true);
  try {
    const payload = await requestJson("/api/exchanges");
    renderExchanges(payload);
    showToast("거래소 확장 상태를 확인했습니다");
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(els.exchangesButton, false);
  }
}

async function runBinanceFuturesPaper() {
  setBusy(els.binancePaperButton, true);
  try {
    const payload = await requestJson("/api/binance/futures/paper/run", { method: "POST" });
    renderBinanceFuturesPaper(payload);
    const firstAction = (payload.actions || [])[0];
    showToast(
      firstAction
        ? `바이낸스 선물 모의 ${firstAction.type} ${firstAction.symbol} ${firstAction.side || ""}`
        : "바이낸스 선물 모의 사이클을 확인했습니다",
    );
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(els.binancePaperButton, false);
  }
}

function setManualFuturesButtonsBusy(busy) {
  document.querySelectorAll("[data-manual-futures-action]").forEach((button) => setBusy(button, busy));
}

function manualFuturesOrderSizingBody(action = "") {
  const manualAction = String(action || "").toUpperCase();
  if (!["LONG", "SHORT"].includes(manualAction) || !manualFuturesSizing.dirty) {
    return {};
  }
  const amount = String(manualFuturesSizing.amountUsdt || "").trim();
  if (manualFuturesSizing.mode === "amount" && amount) {
    return { amountUsdt: amount };
  }
  const percent = String(
    manualFuturesSizing.mode === "custom_percent"
      ? manualFuturesSizing.customPercent
      : manualFuturesSizing.percent || "100",
  ).trim();
  return { marginPercent: percent || "100" };
}

function sanitizeDecimalInput(value) {
  const clean = String(value || "")
    .replace(/,/g, "")
    .replace(/[^\d.]/g, "");
  const [head, ...tail] = clean.split(".");
  return tail.length ? `${head}.${tail.join("")}` : head;
}

function manualFuturesSizingContext(status = latestStatus) {
  const paper = status?.binanceFuturesPaper || {};
  const available = Math.max(0, Number(paper.availableBalanceUsdt || 0));
  const leverage = Math.max(1, Number(paper.leverage || 100));
  const feeMultiplier = 1 + leverage * manualFuturesFeeRate;
  const maxMargin = feeMultiplier > 0 ? available / feeMultiplier : available;
  return { available, leverage, maxMargin };
}

function manualPercentToAmount(percent, status = latestStatus) {
  const pct = Math.max(0, Math.min(100, Number(percent || 0)));
  return manualFuturesSizingContext(status).maxMargin * pct / 100;
}

function manualAmountInputValue(value) {
  const numeric = Number(value || 0);
  if (!Number.isFinite(numeric) || numeric <= 0) return "";
  return numeric.toFixed(2).replace(/\.?0+$/, "");
}

function syncManualFuturesSizingInputs(options = {}) {
  const forceAmount = Boolean(options.forceAmount);
  const amountInput = els.portfolioFlowRows?.querySelector('[data-manual-futures-field="amount"]');
  const customInput = els.portfolioFlowRows?.querySelector('[data-manual-futures-field="customPercent"]');
  if (amountInput instanceof HTMLInputElement && (forceAmount || document.activeElement !== amountInput)) {
    amountInput.value = manualFuturesSizing.amountUsdt || "";
  }
  if (customInput instanceof HTMLInputElement && document.activeElement !== customInput) {
    customInput.value = manualFuturesSizing.customPercent || "";
  }
  els.portfolioFlowRows?.querySelectorAll("[data-manual-futures-percent]").forEach((button) => {
    button.classList.toggle(
      "active",
      manualFuturesSizing.mode === "percent" &&
        button.getAttribute("data-manual-futures-percent") === manualFuturesSizing.percent,
    );
  });
  els.portfolioFlowRows?.querySelectorAll(".manual-custom-percent").forEach((label) => {
    label.classList.toggle("active", manualFuturesSizing.mode === "custom_percent");
  });
}

function triggerManualFuturesTrade(action) {
  const manualAction = String(action || "").toUpperCase();
  if (!manualAction) return;
  const now = Date.now();
  if (manualFuturesLastTrigger.action === manualAction && now - manualFuturesLastTrigger.at < 1200) return;
  manualFuturesLastTrigger = { action: manualAction, at: now };
  runManualFuturesTrade(manualAction);
}

function handleManualFuturesControlPress(event) {
  const target = event.target instanceof Element ? event.target : null;
  const percentButton = target?.closest("[data-manual-futures-percent]");
  if (percentButton && els.portfolioFlowRows?.contains(percentButton)) {
    event.preventDefault();
    event.stopPropagation();
    manualFuturesSizing = {
      ...manualFuturesSizing,
      mode: "percent",
      percent: percentButton.getAttribute("data-manual-futures-percent") || "100",
      amountUsdt: manualAmountInputValue(manualPercentToAmount(percentButton.getAttribute("data-manual-futures-percent") || "100")),
      dirty: true,
    };
    syncManualFuturesSizingInputs({ forceAmount: true });
    return;
  }
  const button = target?.closest("[data-manual-futures-action]");
  if (!button || !els.portfolioFlowRows?.contains(button)) return;
  event.preventDefault();
  event.stopPropagation();
  triggerManualFuturesTrade(button.getAttribute("data-manual-futures-action"));
}

function handleManualFuturesSizingInput(event) {
  const target = event.target instanceof HTMLInputElement ? event.target : null;
  if (!target || !els.portfolioFlowRows?.contains(target)) return;
  const field = target.getAttribute("data-manual-futures-field");
  if (field === "amount") {
    const clean = sanitizeDecimalInput(target.value);
    if (clean !== target.value) target.value = clean;
    manualFuturesSizing = {
      ...manualFuturesSizing,
      mode: clean.trim() ? "amount" : "percent",
      amountUsdt: clean,
      dirty: Boolean(clean.trim()),
    };
  } else if (field === "customPercent") {
    const clean = sanitizeDecimalInput(target.value);
    if (clean !== target.value) target.value = clean;
    manualFuturesSizing = {
      ...manualFuturesSizing,
      mode: clean.trim() ? "custom_percent" : "percent",
      customPercent: clean,
      amountUsdt: clean.trim() ? manualAmountInputValue(manualPercentToAmount(clean)) : "",
      dirty: Boolean(clean.trim()),
    };
    syncManualFuturesSizingInputs({ forceAmount: true });
    return;
  }
  syncManualFuturesSizingInputs();
}

function numericUsdt(value) {
  const numeric = Number(value || 0);
  return Number.isFinite(numeric) ? numeric : 0;
}

function buildManualFuturesResult(payload = {}, manualAction = "") {
  const actions = Array.isArray(payload.actions) ? payload.actions : [];
  const closes = actions.filter((action) => action.type === "CLOSE");
  const opens = actions.filter((action) => action.type === "OPEN");
  const symbol =
    actions.map((action) => normalizeFuturesSymbol(action.symbol)).find(Boolean) ||
    normalizeFuturesSymbol(payload.symbol) ||
    "BTCUSDT";
  const grossProfit = closes.reduce((total, action) => total + numericUsdt(action.pnlUsdt), 0);
  const netProfit = closes.reduce(
    (total, action) => total + numericUsdt(action.realizedAfterFeeUsdt ?? action.pnlUsdt),
    0,
  );
  const fee = actions.reduce((total, action) => total + numericUsdt(action.feeUsdt), 0);
  const closeSide = closes.map((action) => action.side).filter(Boolean).join(", ");
  const openSide = opens.map((action) => action.side).filter(Boolean).join(", ");
  let conclusion = "";
  if (manualAction === "STOP") {
    conclusion = closes.length
      ? `${closeSide || "포지션"} 청산 완료`
      : "스탑 완료 · 열린 포지션 없음";
  } else if (manualAction === "LONG" || manualAction === "SHORT") {
    if (closes.length && opens.length) {
      conclusion = `${closeSide || "기존 포지션"} 청산 후 ${manualAction} 전환 완료`;
    } else if (opens.length) {
      conclusion = `${manualAction} 진입 완료`;
    } else {
      conclusion = `이미 ${manualAction} 유지 중 · 추가 주문 없음`;
    }
  } else if (manualAction === "AUTO") {
    conclusion = "자동 전환 완료 · 매억남 카드 관리 재개";
  } else if (manualAction === "MANUAL") {
    conclusion = openSide ? `${openSide} 수동 유지` : "수동 고정 완료";
  } else {
    conclusion = payload.message || "수동 명령 처리 완료";
  }
  const cappedOpen = opens.find((action) => {
    const requested = numericUsdt(action.requestedMarginUsdt);
    const maxMargin = numericUsdt(action.maxMarginUsdt);
    return requested > 0 && maxMargin > 0 && requested > maxMargin;
  });
  if (cappedOpen) {
    conclusion += ` · 요청금액 초과로 최대 ${formatMoneyValue(cappedOpen.maxMarginUsdt, "USDT")} 적용`;
  }
  const netAfterAllFees = netProfit - opens.reduce((total, action) => total + numericUsdt(action.feeUsdt), 0);
  return {
    action: manualAction,
    symbol,
    profitUsdt: netAfterAllFees,
    feeUsdt: fee,
    grossProfitUsdt: grossProfit,
    conclusion,
    at: new Date().toISOString(),
  };
}

async function runManualFuturesTrade(action) {
  const manualAction = String(action || "").toUpperCase();
  const labelByAction = {
    MANUAL: "수동",
    AUTO: "자동",
    LONG: "롱",
    SHORT: "숏",
    STOP: "스탑",
  };
  setManualFuturesButtonsBusy(true);
  try {
    const payload = await requestJson("/api/binance/futures/paper/manual", {
      method: "POST",
      body: JSON.stringify({ action: manualAction, ...manualFuturesOrderSizingBody(manualAction) }),
    });
    lastManualFuturesResult = buildManualFuturesResult(payload, manualAction);
    if (payload.status) {
      latestStatus = payload.status;
      renderStatus(latestStatus);
    } else {
      renderBinanceFuturesPaper(payload);
      await refreshStatus();
    }
    const firstAction = (payload.actions || [])[0];
    showToast(
      firstAction
        ? `수동 ${labelByAction[manualAction] || manualAction} 완료 · ${firstAction.type} ${firstAction.symbol || ""} ${firstAction.side || ""}`.trim()
        : lastManualFuturesResult.conclusion || `${labelByAction[manualAction] || manualAction} 전환 완료`,
    );
  } catch (error) {
    showToast(error.message);
  } finally {
    setManualFuturesButtonsBusy(false);
  }
}

async function applyExchangeMode() {
  const mode = els.exchangeModeSelect?.value || "upbit";
  setBusy(els.exchangeModeButton, true);
  try {
    const payload = await requestJson("/api/exchange-mode", {
      method: "POST",
      body: JSON.stringify({ mode }),
    });
    renderExchangeMode(payload.exchangeMode);
    latestStatus = payload.status;
    renderStatus(latestStatus);
    showToast(`${payload.exchangeMode?.label || "거래소"} 모드로 전환했습니다`);
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(els.exchangeModeButton, false);
  }
}

async function checkDatabase() {
  setBusy(els.dbButton, true);
  try {
    const payload = await requestJson("/api/db/status");
    renderDatabase(payload);
    showToast("로컬 DB 상태를 확인했습니다");
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(els.dbButton, false);
  }
}

async function checkAlerts() {
  setBusy(els.alertsButton, true);
  try {
    const payload = await requestJson("/api/alerts");
    renderAlerts(payload);
    const summary = payload.summary || {};
    showToast(summary.count ? `운영 알림 ${summary.count}개를 확인했습니다` : "운영 알림이 없습니다");
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(els.alertsButton, false);
  }
}

async function loadLearningStatus() {
  try {
    const payload = await requestJson("/api/learn");
    renderLearning(payload);
  } catch (error) {
    els.learningState.textContent = "확인 실패";
    els.learningState.className = "warning";
    els.learningDetail.textContent = error.message;
  }
}

async function runHistoricalLearning(scope = "watchlist") {
  setLearningButtonsBusy(true);
  els.learningState.textContent = "학습 중";
  els.learningState.className = "warning";
  els.learningDetail.textContent = scope === "all_krw" ? "전체 KRW 마켓을 준비하는 중입니다" : "전략별 과거 성과를 비교하는 중입니다";
  try {
    const count = latestStatus?.settings?.learningCandleCount || 400;
    const payload = await requestJson("/api/learn", {
      method: "POST",
      body: JSON.stringify({ count, scope }),
    });
    renderLearning(payload);
    scheduleLearningPoll();
    showToast(payload.message || "과거 데이터 학습을 시작했습니다");
  } catch (error) {
    els.learningState.textContent = "학습 실패";
    els.learningState.className = "critical";
    els.learningDetail.textContent = error.message;
    setLearningButtonsBusy(false);
    showToast(error.message);
  }
}

async function loadAllocationStatus() {
  try {
    const payload = await requestJson("/api/allocation");
    renderAllocation(payload);
  } catch (error) {
    els.allocationState.textContent = "확인 실패";
    els.allocationState.className = "warning";
    els.allocationDetail.textContent = error.message;
  }
}

async function loadRealtimeDecisionStatus() {
  try {
    const payload = await requestJson("/api/realtime-decision");
    renderRealtimeDecision(payload);
  } catch (error) {
    els.realtimeDecisionState.textContent = "확인 실패";
    els.realtimeDecisionState.className = "warning";
    els.realtimeDecisionDetail.textContent = error.message;
    renderRealtimeAnalysisError(error.message);
  }
}

async function loadLatestSimulation(options = {}) {
  const setButtonBusy = options.setButtonBusy !== false;
  if (setButtonBusy) setBusy(els.simulationButton, true);
  try {
    const payload = await requestJsonWithFallback("/api/simulations/latest", "/static/latest_simulation.json");
    renderSimulation(payload);
    if (options.toast) {
      showToast(payload.ok ? "공격형 시뮬레이션 결과를 불러왔습니다" : payload.message);
    }
  } catch (error) {
    els.simulationState.textContent = "확인 실패";
    els.simulationState.className = "warning";
    els.simulationDetail.textContent = error.message;
  } finally {
    if (setButtonBusy) setBusy(els.simulationButton, false);
  }
}

async function loadSimulationPlayback(options = {}) {
  const setButtonBusy = options.setButtonBusy !== false;
  if (setButtonBusy) setBusy(els.playbackLoadButton, true);
  try {
    const payload = await requestJson("/api/simulations/playback");
    renderSimulationPlayback(payload);
    if (options.autoplay && payload.ok) startSimulationPlayback();
    if (options.toast) {
      showToast(payload.ok ? "시뮬레이션 재생 데이터를 불러왔습니다" : payload.message);
    }
  } catch (error) {
    if (els.playbackState) {
      els.playbackState.textContent = "확인 실패";
      els.playbackState.className = "warning";
    }
    if (els.playbackFile) els.playbackFile.textContent = error.message;
  } finally {
    if (setButtonBusy) setBusy(els.playbackLoadButton, false);
  }
}

async function requestJsonWithFallback(primaryUrl, fallbackUrl) {
  if (simulationApiUnavailable) {
    return requestJson(fallbackUrl);
  }
  try {
    return await requestJson(primaryUrl);
  } catch (error) {
    simulationApiUnavailable = true;
    return requestJson(fallbackUrl);
  }
}

async function previewAllocation() {
  setAllocationButtonsBusy(true);
  els.allocationState.textContent = "분석 중";
  els.allocationState.className = "warning";
  els.allocationDetail.textContent = "전체 KRW 후보를 다시 점수화하는 중입니다";
  try {
    const payload = await requestJson("/api/allocation/preview", {
      method: "POST",
      body: JSON.stringify({ execute: false }),
    });
    renderAllocation({ last: payload, due: true, enabled: true });
    showToast("동적 배분 미리보기를 만들었습니다");
  } catch (error) {
    els.allocationState.textContent = "미리보기 실패";
    els.allocationState.className = "critical";
    els.allocationDetail.textContent = error.message;
    showToast(error.message);
  } finally {
    setAllocationButtonsBusy(false);
  }
}

async function runDynamicAllocation() {
  setAllocationButtonsBusy(true);
  els.allocationState.textContent = "실행 중";
  els.allocationState.className = "warning";
  els.allocationDetail.textContent = "페이퍼 포트폴리오를 리밸런싱하는 중입니다";
  try {
    const payload = await requestJson("/api/allocation/run", {
      method: "POST",
      body: JSON.stringify({ execute: true }),
    });
    renderAllocation({ last: payload, due: false, enabled: true });
    await refreshStatus({ loadDetails: false });
    showToast(`동적 배분을 실행했습니다 (${payload.orders.length}개 주문)`);
  } catch (error) {
    els.allocationState.textContent = "실행 실패";
    els.allocationState.className = "critical";
    els.allocationDetail.textContent = error.message;
    showToast(error.message);
  } finally {
    setAllocationButtonsBusy(false);
  }
}

async function previewRealtimeDecision() {
  setRealtimeDecisionButtonsBusy(true);
  els.realtimeDecisionState.textContent = "분석 중";
  els.realtimeDecisionState.className = "warning";
  els.realtimeDecisionDetail.textContent = "학습 모델과 실시간 추세를 함께 계산하는 중입니다";
  renderRealtimeAnalysisLoading(
    isBinanceFuturesPaper()
      ? "바이낸스 USD-M 선물 심볼을 분석은 그대로 유지하고 실행은 반대 방향 10x 기준으로 다시 훑으면서 진입 후보, 보유 ROE, 청산 위험을 계산하고 있습니다."
      : "전체 KRW 후보를 다시 훑으면서 진입 후보, 보유 위험, 교체 가능성을 계산하고 있습니다.",
  );
  try {
    const payload = await requestJson("/api/realtime-decision/preview", {
      method: "POST",
      body: JSON.stringify({ execute: false }),
    });
    renderRealtimeDecision({ enabled: true, last: payload });
    showToast("실시간 순간 판단을 만들었습니다");
  } catch (error) {
    els.realtimeDecisionState.textContent = "판단 실패";
    els.realtimeDecisionState.className = "critical";
    els.realtimeDecisionDetail.textContent = error.message;
    showToast(error.message);
  } finally {
    setRealtimeDecisionButtonsBusy(false);
  }
}

async function runRealtimeDecision() {
  setRealtimeDecisionButtonsBusy(true);
  els.realtimeDecisionState.textContent = "실행 중";
  els.realtimeDecisionState.className = "warning";
  els.realtimeDecisionDetail.textContent = "페이퍼 포트폴리오에 순간 판단을 반영하는 중입니다";
  try {
    const payload = await requestJson("/api/realtime-decision/run", {
      method: "POST",
      body: JSON.stringify({ execute: true }),
    });
    renderRealtimeDecision({ enabled: true, last: payload });
    await refreshStatus({ loadDetails: false });
    showToast(`순간 판단을 실행했습니다 (${payload.orders.length}개 주문)`);
  } catch (error) {
    els.realtimeDecisionState.textContent = "실행 실패";
    els.realtimeDecisionState.className = "critical";
    els.realtimeDecisionDetail.textContent = error.message;
    showToast(error.message);
  } finally {
    setRealtimeDecisionButtonsBusy(false);
  }
}

async function loadPmAnalysis() {
  if (!els.pmAnalyzeButton) return;
  setBusy(els.pmAnalyzeButton, true);
  if (els.residentAiState) els.residentAiState.textContent = "연결 확인";
  if (els.residentAiDetail) els.residentAiDetail.textContent = "프로그램 상태를 AI PM 브리지로 보내는 중입니다";
  try {
    const payload = await requestJson("/api/pm/analyze", { method: "POST" });
    if (latestStatus) {
      latestStatus.pm = payload;
      renderResidentSupervisor(latestStatus);
    }
    showToast(payload.ok ? "AI PM 분석을 받았습니다" : payload.narrative || "AI PM 연결 대기 상태입니다");
  } catch (error) {
    if (els.residentAiState) els.residentAiState.textContent = "연결 실패";
    if (els.residentAiDetail) els.residentAiDetail.textContent = error.message;
    showToast(error.message);
  } finally {
    setBusy(els.pmAnalyzeButton, false);
  }
}

async function loadPmChat() {
  if (!els.pmChatMessages) return;
  try {
    const payload = await requestJson("/api/pm/chat");
    renderPmChat(payload);
  } catch (error) {
    if (els.pmChatState) els.pmChatState.textContent = error.message;
  }
}

async function sendPmChat(event) {
  event.preventDefault();
  if (pmChatInFlight) return;
  const message = els.pmChatInput?.value.trim() || "";
  if (!message) {
    showToast("AI PM에게 보낼 메시지를 입력하세요");
    return;
  }
  pmChatInFlight = true;
  setBusy(els.pmChatSendButton, true);
  if (els.pmChatState) els.pmChatState.textContent = "실제 모델 호출 중";
  try {
    const payload = await requestJson("/api/pm/chat", {
      method: "POST",
      body: JSON.stringify({ message }),
    });
    if (els.pmChatInput) els.pmChatInput.value = "";
    renderPmChat(payload);
    if (latestStatus?.pm) {
      latestStatus.pm = {
        ...latestStatus.pm,
        enabled: payload.enabled,
        configured: payload.configured,
        connected: payload.connected,
        model: payload.model,
      };
      renderResidentAiConnection(latestStatus.pm);
    }
    showToast(payload.ok ? "AI PM 응답을 받았습니다" : "AI PM 호출 상태를 확인했습니다");
  } catch (error) {
    if (els.pmChatState) els.pmChatState.textContent = "호출 실패";
    showToast(error.message);
  } finally {
    setBusy(els.pmChatSendButton, false);
    pmChatInFlight = false;
  }
}

async function loadPmScheduler() {
  if (!els.pmSchedulerCalendar) return;
  setBusy(els.pmSchedulerRefreshButton, true);
  try {
    const payload = await requestJson("/api/pm/scheduler");
    renderPmScheduler(payload);
  } catch (error) {
    if (els.pmSchedulerState) els.pmSchedulerState.textContent = error.message;
  } finally {
    setBusy(els.pmSchedulerRefreshButton, false);
  }
}

async function loadMarketIntel(options = {}) {
  if (!els.intelCoinList) return;
  const manual = options.manual === true;
  setBusy(els.intelRefreshButton, manual);
  if (manual && els.intelState) {
    els.intelState.textContent = "수집 중";
    els.intelState.className = "analysis-badge waiting";
  }
  try {
    const payload = await requestJson(manual ? "/api/intel/refresh" : "/api/intel", {
      method: manual ? "POST" : "GET",
    });
    renderMarketIntel(payload);
    if (manual) showToast("시장정보 수집을 완료했습니다");
  } catch (error) {
    if (els.intelState) {
      els.intelState.textContent = "수집 오류";
      els.intelState.className = "analysis-badge critical";
    }
    showToast(error.message);
  } finally {
    setBusy(els.intelRefreshButton, false);
  }
}

async function loadTradingChart(market) {
  try {
    const payload = await requestJson(
      `/api/chart/${encodeURIComponent(market)}?${chartQueryParams()}`,
    );
    latestChart = payload.candles;
    const row = latestStatus?.markets?.find((item) => item.market === payload.market);
    els.chartTitle.textContent = `${row ? marketLabel(row) : displayMarketCode(payload.market)} ${chartUnitLabel(payload.unit)} 캔들`;
    els.chartMeta.textContent = `${payload.count}개 캔들 · SMA5/SMA20 · 거래량`;
    drawTradeChart(payload.candles, els.chart, { market: payload.market, row, unit: payload.unit });
  } catch (error) {
    latestChart = [];
    els.chartMeta.textContent = error.message;
    drawTradeChart([], els.chart, { market });
  }
}

async function loadOrderbookAnalysis(market = selectedMarket) {
  if (!els.orderbookState) return;
  els.orderbookState.textContent = "분석 중";
  els.orderbookState.className = "warning";
  els.orderbookDetail.textContent = "누적 호가 잔량과 예상 체결가를 계산하는 중입니다";
  setBusy(els.orderbookButton, true);
  try {
    const amount = latestStatus?.settings?.minOrderKrw || 5000;
    const payload = await requestJson(`/api/orderbook/${encodeURIComponent(market)}?side=bid&amount_krw=${encodeURIComponent(amount)}`);
    renderOrderbookAnalysis(payload);
  } catch (error) {
    els.orderbookState.textContent = "확인 실패";
    els.orderbookState.className = "critical";
    els.orderbookDetail.textContent = error.message;
  } finally {
    setBusy(els.orderbookButton, false);
  }
}

function chartUnitLabel(unit = chartUnit) {
  const key = String(unit);
  return chartUnitLabels[key] || `${unit}분`;
}

function chartCandleCount(unit = chartUnit) {
  const key = String(unit);
  if (key === "year") return 40;
  if (key === "month") return 240;
  if (key === "week") return 780;
  if (key === "day") return 3650;
  const numeric = Number(key);
  if (numeric <= 1) return 720;
  if (numeric <= 3) return 960;
  if (numeric <= 5) return 1200;
  if (numeric <= 10) return 1440;
  if (numeric <= 15) return 1600;
  if (numeric <= 30) return 2000;
  if (numeric <= 60) return 2200;
  return 2500;
}

function chartQueryParams(unit = chartUnit) {
  const key = String(unit);
  const params = new URLSearchParams({ count: String(chartCandleCount(key)) });
  if (chartUnitLabels[key] && Number.isNaN(Number(key))) {
    params.set("frame", key);
  } else {
    params.set("unit", key);
  }
  return params.toString();
}

async function setChartUnit(unit) {
  const nextUnit = String(unit);
  if (!chartUnitLabels[nextUnit] || nextUnit === chartUnit) return;
  chartUnit = nextUnit;
  latestChart = [];
  updateChartUnitButtons();
  if (selectedMarket) await loadTradingChart(selectedMarket);
}

function updateChartUnitButtons() {
  els.chartUnitButtons.forEach((button) => {
    const active = String(button.dataset.unit) === chartUnit;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", active ? "true" : "false");
  });
}

async function setHoldingChartUnit(unit) {
  const nextUnit = String(unit);
  if (!chartUnitLabels[nextUnit] || nextUnit === holdingChartUnit) return;
  holdingChartUnit = nextUnit;
  renderedHoldingMarketsKey = "";
  holdingChartCache.clear();
  updateHoldingChartUnitButtons();
  if (latestStatus) renderHoldingCharts(latestStatus);
  await loadHoldingCharts({ force: true });
}

function updateHoldingChartUnitButtons() {
  els.holdingChartUnitButtons.forEach((button) => {
    const active = String(button.dataset.unit) === holdingChartUnit;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", active ? "true" : "false");
  });
}

async function setPortfolioChartUnit(unit) {
  const nextUnit = String(unit);
  if (!chartUnitLabels[nextUnit] || nextUnit === portfolioChartUnit) return;
  portfolioChartUnit = nextUnit;
  latestPortfolioChart = [];
  updatePortfolioChartUnitButtons();
  await loadPortfolioChart({ force: true });
}

function updatePortfolioChartUnitButtons() {
  els.portfolioChartUnitButtons.forEach((button) => {
    const active = String(button.dataset.unit) === portfolioChartUnit;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", active ? "true" : "false");
  });
}

async function emergencyStop() {
  setBusy(els.stopButton, true);
  try {
    const payload = await requestJson("/api/emergency-stop", { method: "POST" });
    latestStatus = payload["상태"];
    renderStatus(latestStatus);
    showToast("긴급정지가 활성화되었습니다");
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(els.stopButton, false);
  }
}

async function resumePaper() {
  setBusy(els.resumeButton, true);
  try {
    const payload = await requestJson("/api/resume-paper", { method: "POST" });
    latestStatus = payload["상태"];
    renderStatus(latestStatus);
    showToast("페이퍼 실행을 재개했습니다");
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(els.resumeButton, false);
  }
}

function renderStatus(status) {
  const runtime = status.runtime;
  const goal = status.goal;
  const market = status.market;
  const signal = status.signal;
  const risk = status.risk;
  const account = status.account;

  syncStrategySelection(status.settings.strategyName);
  els.runtimeBadge.textContent = runtime.emergencyStopped ? "긴급정지" : "페이퍼 실행 중";
  els.runtimeBadge.classList.toggle("stopped", runtime.emergencyStopped);
  els.updatedAt.textContent = `${formatTime(runtime.updatedAt)} 업데이트`;
  renderRuntimeStatus(status);
  renderLiveStatus(status.live || {});
  renderSystemStatus(status);
  renderExchangeMode(status.exchangeMode || {});
  renderExchangeRuntimeStatus(status);
  syncBinanceFuturesTicker(status);

  const goalView = goalDisplay(status);
  els.goalText.textContent = `${formatMoneyValue(goalView.start, goalView.currency)} → ${formatMoneyValue(goalView.target, goalView.currency)}`;
  els.goalDetail.textContent = `현재 ${formatMoneyValue(goalView.equity, goalView.currency)} · 남은 ${formatMoneyValue(goalView.remaining, goalView.currency)} · 진행 ${percent2.format(Number(goalView.progressPct || 0))}%`;
  els.goalProgress.style.width = `${Math.min(100, Math.max(0, Number(goalView.progressPct || 0)))}%`;

  selectedMarket = status.markets.some((row) => row.market === selectedMarket) ? selectedMarket : status.settings.market;
  renderActiveMarketSummary(status.markets.find((row) => row.market === selectedMarket) || market);

  els.signalLabel.textContent = signal.label;
  els.signalLabel.className = signal.action;
  els.signalReason.textContent = signal.reason;

  els.riskLabel.textContent = risk.approved ? "승인" : "대기";
  els.riskLabel.className = risk.approved ? "approved" : "rejected";
  els.riskReason.textContent = risk.reason;

  const accountView = accountDisplay(status);
  els.equityKrw.textContent = formatMoneyValue(accountView.equity, accountView.currency);
  els.cashKrw.textContent = formatMoneyValue(accountView.cash, accountView.currency);
  els.positionValue.textContent = formatMoneyValue(accountView.positionValue, accountView.currency);
  els.realizedPnl.textContent = formatMoneyValue(accountView.realizedPnl, accountView.currency);
  els.realizedPnl.className = Number(accountView.realizedPnl) >= 0 ? "positive" : "negative";
  els.orderCount.textContent = `주문 ${accountView.orderCount}회`;
  els.errorCount.textContent = `오류 ${runtime.errors.length}개`;
  els.marketCount.textContent = `전체 KRW ${status.markets.length}개 감시`;
  renderRecommendedSummary(status.recommended || {});

  renderInvestmentFlow(status);
  renderOpsWatch(status.opsWatch || {});
  renderInvestmentAgency(status.investmentAgency || status.realtimeDecision?.investmentAgency || {});
  renderHoldingCharts(status);
  renderAlerts(status.alerts || {});
  renderResidentSupervisor(status);
  renderRealtimeDecision(status.realtimeDecision || {});
  renderMarkets(status.markets);
  renderLogs(status.logs);
  if (!latestChart.length) {
    drawTradeChart(status.chart, els.chart, {
      market: selectedMarket,
      row: status.markets.find((row) => row.market === selectedMarket) || market,
      unit: chartUnit,
    });
  }
}

function renderRecommendedSummary(payload) {
  const count = Number(payload.count || 0);
  const excludedCount = Number(payload.excludedCount || 0);
  const recommendOnly = Boolean(payload.recommendOnly);
  if (els.recommendedCount) {
    const mode = recommendOnly ? payload.modeLabel || "추천 우선" : payload.modeLabel || "전체 자동 후보";
    els.recommendedCount.textContent = `추천 ${count}개 · 비추천 ${excludedCount}개 · ${mode}`;
    els.recommendedCount.className = recommendOnly || count || excludedCount ? "connected" : "waiting";
    els.recommendedCount.title = payload.description || "";
  }
  if (els.recommendOnlyButton) {
    els.recommendOnlyButton.textContent = recommendOnly ? "추천 우선 ON" : "추천 우선 OFF";
    els.recommendOnlyButton.classList.toggle("active", recommendOnly);
    els.recommendOnlyButton.setAttribute("aria-pressed", recommendOnly ? "true" : "false");
    els.recommendOnlyButton.title = payload.description || "";
  }
  if (els.recommendAllButton) {
    els.recommendAllButton.disabled = !latestStatus || !latestStatus.markets.length;
  }
  if (els.excludeAllButton) {
    els.excludeAllButton.disabled = !latestStatus || !latestStatus.markets.length;
  }
  if (els.recommendedClearButton) {
    els.recommendedClearButton.disabled = count === 0 && excludedCount === 0;
  }
}

function manualFuturesInlineControls(row) {
  if (!isBinanceFuturesPaper(latestStatus) || row.currency !== "USDT" || !normalizeFuturesSymbol(row.market)) {
    return "";
  }
  const paper = latestStatus?.binanceFuturesPaper || {};
  const manualAction = String(paper.manualAction || "").toUpperCase();
  const manualActive = Boolean(paper.manualMode || paper.manualAction);
  const availableText = formatMoneyValue(paper.availableBalanceUsdt || 0, "USDT");
  const presetPercents = ["100", "70", "50", "30", "10"];
  const sizing = manualFuturesSizing;
  const activePreset = sizing.mode === "percent" ? sizing.percent : "";
  const displayedAmount =
    sizing.amountUsdt ||
    (sizing.dirty && sizing.mode === "percent" ? manualAmountInputValue(manualPercentToAmount(sizing.percent || "100")) : "") ||
    (sizing.dirty && sizing.mode === "custom_percent" ? manualAmountInputValue(manualPercentToAmount(sizing.customPercent)) : "");
  const modeButton = (action, label, active) => `
    <button class="manual-mode-button${active ? " active" : ""}" type="button" data-manual-futures-action="${action}" aria-pressed="${active ? "true" : "false"}">${label}</button>
  `;
  const tradeButton = (action, label, className) => `
    <button class="manual-trade-button ${className}${manualAction === action ? " active" : ""}" type="button" data-manual-futures-action="${action}" aria-pressed="${manualAction === action ? "true" : "false"}">${label}</button>
  `;
  const percentButton = (percent) => `
    <button class="manual-percent-button${activePreset === percent ? " active" : ""}" type="button" data-manual-futures-percent="${percent}" aria-pressed="${activePreset === percent ? "true" : "false"}">${percent}%</button>
  `;
  return `
    <div class="manual-futures-inline-controls" aria-label="${escapeHtml(row.market)} 수동/자동 거래">
      <div class="manual-futures-sizing" aria-label="수동거래 증거금 설정">
        <label class="manual-amount-label">
          <span>금액</span>
          <input class="manual-amount-input" data-manual-futures-field="amount" type="text" inputmode="decimal" autocomplete="off" value="${escapeHtml(displayedAmount)}" placeholder="USDT" aria-label="수동거래 증거금 USDT" />
        </label>
        <div class="manual-percent-row" aria-label="사용 가능 잔고 대비 비율">
          ${presetPercents.map(percentButton).join("")}
          <label class="manual-custom-percent${sizing.mode === "custom_percent" ? " active" : ""}">
            <span>지정</span>
            <input data-manual-futures-field="customPercent" type="text" inputmode="decimal" autocomplete="off" value="${escapeHtml(sizing.customPercent || "")}" placeholder="%" aria-label="지정 비율" />
          </label>
        </div>
        <div class="manual-futures-helper">
          USDT 증거금 입력 · 현재 가용 ${availableText} · 초과 입력은 최대 가능 금액으로 제한
        </div>
      </div>
      <div class="manual-futures-button-stack">
        <div class="manual-futures-mode-row">
          ${modeButton("MANUAL", "수동", manualActive)}
          ${modeButton("AUTO", "자동", !manualActive)}
        </div>
        <div class="manual-futures-trade-row">
          ${tradeButton("LONG", "롱", "long")}
          ${tradeButton("SHORT", "숏", "short")}
          ${tradeButton("STOP", "스탑", "stop")}
        </div>
      </div>
      ${manualFuturesResultMarkup(row)}
    </div>
  `;
}

function manualFuturesResultMarkup(row) {
  const result = lastManualFuturesResult;
  if (!result || result.symbol !== normalizeFuturesSymbol(row.market)) return "";
  const profitClass = result.profitUsdt > 0 ? "positive" : result.profitUsdt < 0 ? "negative" : "neutral";
  return `
    <div class="manual-futures-result ${profitClass}" aria-label="최근 수동거래 결과">
      <span>수익 <strong>${formatSignedMoneyValue(result.profitUsdt, "USDT")}</strong></span>
      <span>수수료 <strong>${formatMoneyValue(result.feeUsdt, "USDT")}</strong></span>
      <span class="manual-futures-conclusion">결론 <strong>${escapeHtml(result.conclusion)}</strong></span>
    </div>
  `;
}

function futuresMethodNameFromPosition(position = {}, paper = {}) {
  const source = [
    paper.strategySide,
    paper.paperSide,
    paper.exitBasis,
    position.exitBasis,
    position.techniqueId,
    position.reason,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  if (source.includes("alex")) return "알렉스기법";
  if (source.includes("maeuknam")) return "매억남 카드";
  if (paper.manualMode || paper.manualAction) return "수동거래";
  return "자동 선물기법";
}

function futuresRealtimeAnalysisText(status = {}, symbol = "BTCUSDT") {
  const plan = status?.realtimeDecision?.last?.plan || {};
  const situations = Array.isArray(plan.situations) ? plan.situations : [];
  const selected = Array.isArray(plan.selected) ? plan.selected : [];
  const cleanSymbol = normalizeFuturesSymbol(symbol) || "BTCUSDT";
  const item =
    situations.find((row) => normalizeFuturesSymbol(row.market || row.symbol) === cleanSymbol) ||
    selected.find((row) => normalizeFuturesSymbol(row.market || row.symbol) === cleanSymbol) ||
    situations[0] ||
    selected[0] ||
    null;
  if (!item) {
    const fallback = plan.marketRegime?.reason || plan.message || status?.realtimeDecision?.last?.message || "실시간 후보 분석 대기";
    return shortenText(`대기 · ${fallback}`, 96);
  }
  const side = String(item.side || item.executionSide || "FLAT").toUpperCase();
  const action = String(item.action || "watch").toLowerCase();
  const stage = futuresStageLabel(item.entryStage || action);
  const actionLabel =
    action === "hold" ? "보유 감시" : action === "long" ? "롱 진입 후보" : action === "short" ? "숏 진입 후보" : "진입 대기";
  const allowed = item.entryAllowed === true || String(item.entryAllowed || "").toLowerCase() === "true";
  const score = formatScore(item.score);
  const reason = futuresRealtimeReasonText(item, plan);
  return shortenText(`${actionLabel} · ${side} · 점수 ${score} · ${allowed ? "진입 가능" : stage} · ${reason}`, 120);
}

function futuresRealtimeAnalysisStatus(status = {}) {
  const decision = status?.realtimeDecision || {};
  const last = decision.last || {};
  const plan = last.plan || {};
  const updatedAt =
    last.updatedAt ||
    plan.investmentAgency?.source?.cycleUpdatedAt ||
    status?.binanceFuturesPaper?.updatedAt ||
    status?.runtime?.updatedAt ||
    "";
  const updatedMs = updatedAt ? Date.parse(updatedAt) : Number.NaN;
  const ageSeconds = Number.isFinite(updatedMs)
    ? Math.max(0, Math.round((Date.now() - updatedMs) / 1000))
    : null;
  const interval = Number(decision.intervalSeconds || status?.settings?.realtimeDecisionIntervalSeconds || 1);
  const liveLimit = Math.max(5, interval * 4);
  const enabled = decision.enabled !== false && status?.settings?.realtimeDecisionEnabled !== false;
  const state = !enabled ? "off" : ageSeconds === null ? "waiting" : ageSeconds <= liveLimit ? "live" : "stale";
  const label = state === "live" ? "LIVE 분석중" : state === "stale" ? "갱신 지연" : state === "off" ? "분석 꺼짐" : "분석 대기";
  const evaluated = Number(plan.evaluatedCount || 0);
  const universe = Number(plan.universeCount || 0);
  const cadence = interval ? `${interval}초 주기` : "수동 주기";
  const ageText = formatElapsedSeconds(ageSeconds);
  const countText = universe ? `${number.format(evaluated)}/${number.format(universe)} 평가` : "평가 대기";
  const timeText = updatedAt ? `${formatTime(updatedAt)} 갱신` : "갱신 대기";
  return {
    state,
    label,
    meta: `${timeText} · ${ageText} · ${cadence} · ${countText}`,
  };
}

function formatElapsedSeconds(seconds) {
  if (seconds === null || seconds === undefined || !Number.isFinite(Number(seconds))) return "시간 확인 중";
  const safeSeconds = Math.max(0, Math.round(Number(seconds)));
  if (safeSeconds < 60) return `${safeSeconds}초 전`;
  const minutes = Math.floor(safeSeconds / 60);
  const rest = safeSeconds % 60;
  if (minutes < 60) return rest ? `${minutes}분 ${rest}초 전` : `${minutes}분 전`;
  const hours = Math.floor(minutes / 60);
  const minuteRest = minutes % 60;
  return minuteRest ? `${hours}시간 ${minuteRest}분 전` : `${hours}시간 전`;
}

function futuresStageLabel(stage) {
  const key = String(stage || "").toLowerCase();
  const labels = {
    entry: "진입 가능",
    watch: "관찰",
    alex_card: "알렉스 카드 확인",
    fee_gate: "수수료 조건 대기",
    fee_drag_throttle: "수수료 누적 제한",
    execution_proof: "실시간 가격 확인 대기",
    historical: "캔들 확인 대기",
    agency: "상위시간 판단 대기",
    unavailable: "신호 없음",
  };
  return labels[key] || (key ? key : "분석 대기");
}

function futuresRealtimeReasonText(item = {}, plan = {}) {
  const raw = String(item.riskReason || item.entryBlockReason || item.reason || plan.marketRegime?.reason || plan.message || "");
  const lower = raw.toLowerCase();
  if (lower.includes("fee drag throttle")) return "수수료 손실 누적이 높아 더 강한 확인 전까지 대기";
  if (lower.includes("execution proof blocked")) return "실시간 가격이 아직 진입 방향을 확인하지 않음";
  if (lower.includes("confirmation")) return "동일 방향 캔들 확인 수가 아직 부족";
  if (lower.includes("entry allowed") || lower.includes("confirmed")) return "진입 조건 통과";
  if (lower.includes("waiting")) return "다음 실시간 후보 계산 대기";
  return raw || "후보를 실시간 계산 중";
}

function shortenText(value, maxLength = 96) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (text.length <= maxLength) return text;
  return `${text.slice(0, Math.max(0, maxLength - 1))}…`;
}

function futuresMethodGuideForPosition(position = {}, paper = {}, liveMetrics = null, status = {}) {
  const side = String(position.side || paper.executionSide || "").toUpperCase();
  const sideLabel = side === "LONG" ? "롱" : side === "SHORT" ? "숏" : "대기";
  const methodName = futuresMethodNameFromPosition(position, paper);
  const leverage = position.leverage || paper.leverage || "-";
  const entryPrice = formatOptionalFuturesPrice(position.entryPrice);
  const stopPrice = formatOptionalFuturesPrice(position.stopLossPrice);
  const targetPrice = formatOptionalFuturesPrice(position.takeProfitPrice || position.target2Price || position.target1Price);
  const currentPrice = formatOptionalFuturesPrice(liveMetrics?.price || position.currentPrice);
  const entryRule =
    methodName === "알렉스기법"
      ? `${sideLabel} 진입: 0.5 기준선, 프리미엄/디스카운트, 유동성 실패, 4카운트 점수가 맞을 때`
      : methodName === "매억남 카드"
        ? `${sideLabel} 진입: 카드 방향, 수수료 안전 목표, 확인 캔들 조건을 통과할 때`
        : `${sideLabel} 진입: 사용자가 누른 수동 버튼 기준`;
  const holdRule =
    side === "SHORT"
      ? `홀딩: 현재가 ${currentPrice}가 손절 ${stopPrice} 아래이고 목표 ${targetPrice} 전까지, 같은 방향이면 유지`
      : side === "LONG"
        ? `홀딩: 현재가 ${currentPrice}가 손절 ${stopPrice} 위이고 목표 ${targetPrice} 전까지, 같은 방향이면 유지`
        : "홀딩: 포지션이 없으면 자동/수동 다음 신호까지 대기";
  const exitRule =
    side === "SHORT"
      ? `청산: ${targetPrice} 이하면 익절, ${stopPrice} 이상이면 손절, 롱/플랫 전환이면 종료`
      : side === "LONG"
        ? `청산: ${targetPrice} 이상이면 익절, ${stopPrice} 이하면 손절, 숏/플랫 전환이면 종료`
        : "청산: 포지션 없음";
  return {
    methodName,
    title: `${methodName} · ${sideLabel} ${leverage}x`,
    entryRule,
    holdRule,
    exitRule,
    analysisRule: futuresRealtimeAnalysisText(status, position.symbol || "BTCUSDT"),
    analysisStatus: futuresRealtimeAnalysisStatus(status),
    status: `진입가 ${entryPrice} · 목표 ${targetPrice} · 손절 ${stopPrice}`,
  };
}

function futuresFlatMethodGuide(paper = {}, status = {}) {
  const manualAction = String(paper.manualAction || "").toUpperCase();
  const methodName = paper.strategySide === "ALEX_METHOD" || paper.paperSide === "ALEX_METHOD" ? "알렉스기법" : "자동 선물기법";
  const mode = manualAction ? `${manualAction} 수동 대기` : "자동 대기";
  return {
    methodName,
    title: `${methodName} · ${mode}`,
    entryRule: `${methodName} 조건이 성립하면 BTCUSDT 100배 모의 포지션으로 진입`,
    holdRule: "홀딩: 포지션이 열리면 목표/손절/방향전환 기준을 표시",
    exitRule: "청산: 스탑 버튼 또는 자동 청산 조건으로 종료",
    analysisRule: futuresRealtimeAnalysisText(status, "BTCUSDT"),
    analysisStatus: futuresRealtimeAnalysisStatus(status),
    status: "현재 포지션 없음",
  };
}

function futuresDisplaySideLabel(side) {
  const clean = String(side || "").toUpperCase();
  if (clean === "LONG") return "LONG";
  if (clean === "SHORT") return "SHORT";
  if (clean === "FLAT") return "대기";
  return "대기";
}

function futuresMethodGuideMarkup(row) {
  const guide = row.methodGuide;
  if (!guide) return "";
  const analysisStatus = guide.analysisStatus || { state: "waiting", label: "분석 대기", meta: "갱신 대기" };
  const analysisState = String(analysisStatus.state || "waiting").replace(/[^a-z0-9_-]/gi, "") || "waiting";
  return `
    <div class="futures-method-guide" aria-label="현재 매매기법과 진입, 홀딩, 청산 기준">
      <div class="futures-method-guide-head">
        <span>${escapeHtml(guide.methodName)}</span>
        <strong>${escapeHtml(guide.title)}</strong>
        <em>${escapeHtml(guide.status)}</em>
      </div>
      <div class="futures-method-guide-grid">
        <span><b>진입</b>${escapeHtml(guide.entryRule)}</span>
        <span><b>홀딩</b>${escapeHtml(guide.holdRule)}</span>
        <span><b>청산</b>${escapeHtml(guide.exitRule)}</span>
        <span class="futures-live-analysis ${analysisState}">
          <b><i aria-hidden="true"></i>${escapeHtml(analysisStatus.label || "실시간 분석")}</b>
          <strong>${escapeHtml(guide.analysisRule || "실시간 후보 분석 대기")}</strong>
          <em>${escapeHtml(analysisStatus.meta || "갱신 대기")}</em>
        </span>
      </div>
    </div>
  `;
}

function renderInvestmentFlow(status) {
  if (!els.portfolioFlowRows) return;

  const snapshot = investmentSnapshot(status);
  const { baseline, reset } = investmentBaselineFor(snapshot);
  const equityDelta = baseline ? snapshot.equityKrw - baseline.equityKrw : 0;
  const positionDelta = baseline ? snapshot.positionValueKrw - baseline.positionValueKrw : 0;
  const cashDelta = baseline ? snapshot.cashKrw - baseline.cashKrw : 0;
  const realizedDelta = baseline ? snapshot.realizedPnlKrw - baseline.realizedPnlKrw : 0;
  const currency = snapshot.currency || "KRW";

  setFlowMetric(els.portfolioFlowDelta, equityDelta, currency);
  setFlowMetric(els.portfolioFlowPositionDelta, positionDelta, currency);
  setFlowMetric(els.portfolioFlowCashDelta, cashDelta, currency);
  setFlowMetric(els.portfolioFlowRealizedDelta, realizedDelta, currency);
  const resetWithoutMovement = reset && Math.abs(equityDelta) < 0.000001;

  if (els.portfolioFlowState) {
    els.portfolioFlowState.textContent = resetWithoutMovement
      ? "포지션 기준 저장"
      : equityDelta > 0
        ? "증가"
        : equityDelta < 0
          ? "감소"
          : "변동 없음";
    els.portfolioFlowState.className = resetWithoutMovement ? "waiting" : flowClass(equityDelta);
  }

  if (els.portfolioFlowDetail) {
    const modeText = currency === "USDT" ? "바이낸스 USD-M 선물 모의 · USDT 기준" : "업비트 KRW 페이퍼 기준";
    els.portfolioFlowDetail.textContent = resetWithoutMovement
      ? `${modeText} · ${formatTime(snapshot.time)} 현재 포지션 기준값 저장 · 전환 전까지 누적 변동 유지`
      : `${modeText} · ${formatTime(baseline.time)} → ${formatTime(snapshot.time)} 현재 포지션 기준 누적 · 포지션 ${snapshot.openPositions}개`;
  }

  const rows = investmentFlowRows(snapshot, baseline);
  const activeField =
    document.activeElement instanceof HTMLInputElement &&
    els.portfolioFlowRows.contains(document.activeElement)
      ? {
          field: document.activeElement.getAttribute("data-manual-futures-field"),
          selectionStart: document.activeElement.selectionStart,
          selectionEnd: document.activeElement.selectionEnd,
        }
      : null;
  els.portfolioFlowRows.replaceChildren(
    ...(rows.length ? rows.map(renderInvestmentFlowRow) : [emptyInvestmentFlowRow()]),
  );
  if (activeField?.field) {
    const nextInput = els.portfolioFlowRows.querySelector(`[data-manual-futures-field="${activeField.field}"]`);
    if (nextInput instanceof HTMLInputElement) {
      nextInput.focus();
      if (activeField.selectionStart !== null && activeField.selectionEnd !== null) {
        nextInput.setSelectionRange(activeField.selectionStart, activeField.selectionEnd);
      }
    }
  }
}

function investmentBaselineFor(snapshot) {
  const signature = investmentSnapshotSignature(snapshot);
  const reset = !investmentBaselineSnapshot || investmentBaselineSignature !== signature;
  if (reset) {
    investmentBaselineSnapshot = baselineSnapshotFromCurrentPosition(snapshot);
    investmentBaselineSignature = signature;
  }
  return { baseline: investmentBaselineSnapshot, reset };
}

function baselineSnapshotFromCurrentPosition(snapshot) {
  const hasExplicitBaseline =
    snapshot.baselineEquityKrw !== undefined ||
    snapshot.baselineCashKrw !== undefined ||
    snapshot.baselinePositionValueKrw !== undefined ||
    snapshot.baselineRealizedPnlKrw !== undefined;
  if (!hasExplicitBaseline) return snapshot;
  const byMarket = {};
  Object.entries(snapshot.byMarket || {}).forEach(([market, row]) => {
    byMarket[market] = {
      ...row,
      positionValueKrw:
        row.baselinePositionValueKrw !== undefined ? Number(row.baselinePositionValueKrw || 0) : Number(row.positionValueKrw || 0),
      unrealizedPnlKrw: 0,
      realizedPnlKrw:
        row.baselineRealizedPnlKrw !== undefined ? Number(row.baselineRealizedPnlKrw || 0) : Number(row.realizedPnlKrw || 0),
    };
  });
  return {
    ...snapshot,
    equityKrw:
      snapshot.baselineEquityKrw !== undefined ? Number(snapshot.baselineEquityKrw || 0) : Number(snapshot.equityKrw || 0),
    cashKrw:
      snapshot.baselineCashKrw !== undefined ? Number(snapshot.baselineCashKrw || 0) : Number(snapshot.cashKrw || 0),
    positionValueKrw:
      snapshot.baselinePositionValueKrw !== undefined
        ? Number(snapshot.baselinePositionValueKrw || 0)
        : Number(snapshot.positionValueKrw || 0),
    realizedPnlKrw:
      snapshot.baselineRealizedPnlKrw !== undefined
        ? Number(snapshot.baselineRealizedPnlKrw || 0)
        : Number(snapshot.realizedPnlKrw || 0),
    byMarket,
  };
}

function investmentSnapshotSignature(snapshot) {
  if (snapshot.positionSignature) return snapshot.positionSignature;
  const markets = Object.values(snapshot.byMarket || {})
    .filter((row) => Number(row.positionValueKrw || 0) > 0 || row.manualControl)
    .map((row) =>
      [
        row.market,
        row.avgEntryPrice,
        row.marginValueKrw,
        row.manualControl ? "manual" : "auto",
      ].join(":"),
    )
    .sort()
    .join("|");
  return `${snapshot.currency || "KRW"}|${snapshot.openPositions || 0}|${snapshot.orderCount || 0}|${markets || "flat"}`;
}

function renderInvestmentFlowRow(row) {
  const tr = document.createElement("tr");
  if (row.manualControl && row.currency === "USDT") {
    tr.classList.add("manual-futures-card");
  }
  const positionDetailText =
    row.currency === "USDT" && row.marginValueKrw > 0
      ? `margin ${formatMoneyValue(row.marginValueKrw, row.currency)}`
      : formatSignedMoneyValue(row.positionDeltaKrw, row.currency);
  const positionDetailClass =
    row.currency === "USDT" && row.marginValueKrw > 0 ? "" : flowClass(row.positionDeltaKrw);
  tr.innerHTML = `
    <td class="flow-market-jump" title="이 종목 차트 보기">
      <span class="flow-market-title">
        <span class="market-symbol">${escapeHtml(row.label)}</span>
        <small>${escapeHtml(displayMarketCode(row.market))}</small>
      </span>
      ${manualFuturesInlineControls(row)}
      ${futuresMethodGuideMarkup(row)}
    </td>
    <td>
      <span class="flow-cell-main">${formatMoneyValue(row.positionValueKrw, row.currency)}</span>
      <small class="${positionDetailClass}">${positionDetailText}</small>
    </td>
    <td>
      <span class="flow-cell-main ${flowClass(row.unrealizedPnlKrw)}">${formatMoneyValue(row.unrealizedPnlKrw, row.currency)}</span>
      <small class="${flowClass(row.realizedDeltaKrw)}">실현 ${formatSignedMoneyValue(row.realizedDeltaKrw, row.currency)}</small>
    </td>
    <td class="${flowClass(row.returnPct)}">${formatSignedPercent2(Number(row.returnPct || 0))}%</td>
    <td>${formatFlowPrice(row.price, row.currency)}</td>
    <td>${formatFlowOptionalPrice(row.avgEntryPrice, row.currency)}</td>
    <td>
      <span class="flow-cell-main">${formatFlowOptionalPrice(row.targetSellPrice, row.currency)}</span>
      <small class="negative">손절 ${formatFlowOptionalPrice(row.stopLossPrice, row.currency)}</small>
    </td>
    <td class="flow-analysis-cell">
      <strong>${escapeHtml(row.analysisTitle)}</strong>
      <small>${escapeHtml(row.analysisNarrative)}</small>
    </td>
  `;
  const marketCell = tr.querySelector(".flow-market-jump");
  marketCell.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target : null;
    if (target?.closest(".manual-futures-inline-controls")) return;
    openInvestmentFlowChart(row.market);
  });
  tr.querySelectorAll("[data-manual-futures-action]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      triggerManualFuturesTrade(button.dataset.manualFuturesAction);
    });
  });
  return tr;
}

function renderOpsWatch(payload = {}) {
  if (!els.opsWatchState) return;
  const state = payload.state || {};
  const className = state.className || "waiting";
  els.opsWatchState.textContent = state.label || "관제 대기";
  els.opsWatchState.className = `analysis-badge ${className}`;
  if (els.opsWatchDetail) {
    els.opsWatchDetail.textContent =
      state.detail || "API 429, 시장 positive ratio, 손절선, 후보 6종, 운영 규칙을 한 번에 감시합니다.";
  }
  renderOpsWatchList(els.opsRiskList, payload.risk, "리스크 점검 대기");
  renderOpsWatchList(els.opsTriggerList, payload.triggers, "손절선 근접 알림 대기");
  renderOpsWatchList(els.opsCandidateList, payload.candidates, "후보 6종 개선 대기");
  renderOpsWatchList(els.opsOperationList, payload.operations, "운영 규칙 대기");
}

function renderInvestmentAgency(payload = {}) {
  if (!els.agencyState) return;
  const verdict = String(payload.verdict || "WAIT").toUpperCase();
  const className = payload.className || (verdict === "APPROVE" ? "ok" : verdict === "REJECT" ? "critical" : "warning");
  els.agencyState.textContent = `${payload.name || "Investment Agency"} · ${verdict}`;
  els.agencyState.className = `analysis-badge ${className}`;
  if (els.agencyDetail) {
    els.agencyDetail.textContent =
      payload.summary || "Agency waits for candle coverage, Maeuknam card thesis, risk veto, and execution desk review.";
  }
  renderOpsWatchList(els.agencyDataList, payload.dataChecks, "Waiting for candle coverage audit");
  renderOpsWatchList(els.agencyMemberList, payload.members, "Waiting for expert votes");
  renderOpsWatchList(els.agencyActionList, payload.nextActions, "Waiting for agency instructions");
}

function renderOpsWatchList(container, items, emptyText) {
  if (!container) return;
  const rows = Array.isArray(items) ? items : [];
  if (!rows.length) {
    const empty = document.createElement("div");
    empty.className = "ops-watch-empty";
    empty.textContent = emptyText;
    container.replaceChildren(empty);
    return;
  }
  container.replaceChildren(
    ...rows.map((item) => {
      const row = document.createElement("div");
      const level = item.level || "waiting";
      row.className = `ops-watch-item ${level}${item.focus ? " focus" : ""}`;
      row.innerHTML = `
        <div>
          <strong>${escapeHtml(item.title || "-")}</strong>
          <small>${escapeHtml(item.body || "")}</small>
        </div>
        <em>${escapeHtml(item.value || opsLevelLabel(level))}</em>
      `;
      return row;
    }),
  );
}

function opsLevelLabel(level) {
  if (level === "critical") return "위험";
  if (level === "warning") return "주의";
  if (level === "ok") return "정상";
  return "대기";
}

function isBinanceFuturesPaper(status = latestStatus) {
  return (status?.exchangeMode?.active || status?.settings?.exchangeMode) === "binance_futures_paper";
}

function normalizeFuturesSymbol(symbol) {
  const clean = String(symbol || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
  return clean.endsWith("USDT") ? clean : "";
}

function futuresTickerTarget(status = latestStatus) {
  if (!isBinanceFuturesPaper(status)) return "";
  const positions = Array.isArray(status?.binanceFuturesPaper?.positions) ? status.binanceFuturesPaper.positions : [];
  const selected = normalizeFuturesSymbol(selectedMarket);
  if (selected && positions.some((position) => normalizeFuturesSymbol(position.symbol) === selected)) return selected;
  const openPosition = positions.map((position) => normalizeFuturesSymbol(position.symbol)).find(Boolean);
  if (openPosition) return openPosition;
  const marketRows = Array.isArray(status?.markets) ? status.markets : [];
  return marketRows.map((row) => normalizeFuturesSymbol(row.market || row.symbol)).find(Boolean) || "BTCUSDT";
}

function closeBinanceFuturesTicker() {
  if (binanceFuturesTickerReconnectTimer) {
    window.clearTimeout(binanceFuturesTickerReconnectTimer);
    binanceFuturesTickerReconnectTimer = 0;
  }
  if (binanceFuturesTickerSocket) {
    binanceFuturesTickerSocket.onclose = null;
    binanceFuturesTickerSocket.close();
  }
  binanceFuturesTickerSocket = null;
  binanceFuturesTickerSymbol = "";
}

function syncBinanceFuturesTicker(status = latestStatus) {
  if (!isBinanceFuturesPaper(status)) {
    closeBinanceFuturesTicker();
    return;
  }
  const symbol = futuresTickerTarget(status);
  if (!symbol) return;
  connectBinanceFuturesTicker(symbol);
}

function connectBinanceFuturesTicker(symbol) {
  const cleanSymbol = normalizeFuturesSymbol(symbol);
  if (!cleanSymbol || !("WebSocket" in window)) return;
  if (
    binanceFuturesTickerSocket &&
    binanceFuturesTickerSymbol === cleanSymbol &&
    [WebSocket.CONNECTING, WebSocket.OPEN].includes(binanceFuturesTickerSocket.readyState)
  ) {
    return;
  }
  closeBinanceFuturesTicker();
  binanceFuturesTickerSymbol = cleanSymbol;
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws/binance/futures/ticker/${encodeURIComponent(cleanSymbol)}`);
  binanceFuturesTickerSocket = socket;
  socket.onmessage = (event) => {
    let payload = {};
    try {
      payload = JSON.parse(event.data);
    } catch (_error) {
      return;
    }
    if (payload.type !== "trade") return;
    const price = Number(payload.price || 0);
    const tickSymbol = normalizeFuturesSymbol(payload.symbol || cleanSymbol);
    if (!tickSymbol || !Number.isFinite(price) || price <= 0) return;
    liveFuturesPrices.set(tickSymbol, {
      price,
      eventTime: Number(payload.eventTime || 0),
      tradeTime: Number(payload.tradeTime || 0),
      receivedAt: Number(payload.receivedAt || Date.now()),
      latencyMs: Number(payload.latencyMs || 0),
    });
    applyLiveFuturesPriceToStatus(latestStatus, tickSymbol, price);
    scheduleLiveFuturesRender();
  };
  socket.onclose = () => {
    if (binanceFuturesTickerSymbol !== cleanSymbol || !isBinanceFuturesPaper()) return;
    binanceFuturesTickerReconnectTimer = window.setTimeout(() => connectBinanceFuturesTicker(cleanSymbol), 350);
  };
  socket.onerror = () => {
    try {
      socket.close();
    } catch (_error) {
      // Ignore close races; the reconnect path is handled by onclose.
    }
  };
}

function liveFuturesPositionMetrics(position, price) {
  const currentPrice = Number(price || 0);
  const entryPrice = Number(position.entryPrice || 0);
  const quantity = Number(position.quantity || 0);
  const margin = Number(position.marginUsdt || 0);
  const leverage = Number(position.leverage || 0);
  if (!Number.isFinite(currentPrice) || currentPrice <= 0 || !entryPrice || !quantity) return null;
  const side = String(position.side || "").toUpperCase();
  const signedMove = side === "SHORT" ? entryPrice - currentPrice : currentPrice - entryPrice;
  const pnl = signedMove * quantity;
  const priceMovePct = entryPrice ? (signedMove / entryPrice) * 100 : 0;
  const roe = margin > 0 ? (pnl / margin) * 100 : priceMovePct * leverage;
  return {
    price: currentPrice,
    notional: quantity * currentPrice,
    pnl,
    priceMovePct,
    roe,
  };
}

function applyLiveFuturesPriceToStatus(status, symbol, price) {
  const paper = status?.binanceFuturesPaper || {};
  const positions = Array.isArray(paper.positions) ? paper.positions : [];
  const cleanSymbol = normalizeFuturesSymbol(symbol);
  if (!cleanSymbol || !positions.length) return;
  const baseWallet = Number(paper.walletBalanceUsdt || Number(paper.equityUsdt || 0) - Number(paper.unrealizedPnlUsdt || 0));
  let touched = false;
  let totalNotional = 0;
  let totalPnl = 0;
  let usedMargin = 0;
  paper.positions = positions.map((position) => {
    const positionSymbol = normalizeFuturesSymbol(position.symbol);
    const live = liveFuturesPrices.get(positionSymbol);
    const nextPrice = positionSymbol === cleanSymbol ? price : Number(live?.price || position.currentPrice || position.entryPrice || 0);
    const metrics = liveFuturesPositionMetrics(position, nextPrice);
    usedMargin += Number(position.marginUsdt || 0);
    totalNotional += Number(metrics?.notional || position.notionalUsdt || 0);
    totalPnl += Number(metrics?.pnl || position.unrealizedPnlUsdt || 0);
    if (positionSymbol !== cleanSymbol || !metrics) return position;
    touched = true;
    return {
      ...position,
      currentPrice: String(metrics.price),
      notionalUsdt: String(metrics.notional),
      unrealizedPnlUsdt: String(metrics.pnl),
      priceMovePct: String(metrics.priceMovePct),
      returnOnMarginPct: String(metrics.roe),
    };
  });
  if (!touched) return;
  const equity = baseWallet + totalPnl;
  paper.totalNotionalUsdt = String(totalNotional);
  paper.unrealizedPnlUsdt = String(totalPnl);
  paper.equityUsdt = String(equity);
  paper.availableBalanceUsdt = String(Math.max(0, equity - usedMargin));
  paper.updatedAt = new Date().toISOString();
}

function scheduleLiveFuturesRender() {
  if (liveFuturesRenderQueued || !latestStatus) return;
  liveFuturesRenderQueued = true;
  window.requestAnimationFrame(() => {
    liveFuturesRenderQueued = false;
    if (!latestStatus || !isBinanceFuturesPaper(latestStatus)) return;
    const accountView = accountDisplay(latestStatus);
    if (els.equityKrw) els.equityKrw.textContent = formatMoneyValue(accountView.equity, accountView.currency);
    if (els.cashKrw) els.cashKrw.textContent = formatMoneyValue(accountView.cash, accountView.currency);
    if (els.positionValue) els.positionValue.textContent = formatMoneyValue(accountView.positionValue, accountView.currency);
    if (els.realizedPnl) els.realizedPnl.textContent = formatMoneyValue(accountView.realizedPnl, accountView.currency);
    renderInvestmentFlow(latestStatus);
    renderExchangeRuntimeStatus(latestStatus);
  });
}

function isFuturesAnalysisPlan(plan = {}) {
  return (
    plan.scope === "binance_usdm_futures" ||
    plan.marketUnit === "USDT" ||
    String(plan.strategySide || "").toUpperCase() === "SHORT"
  );
}

function accountDisplay(status) {
  const account = status.account || {};
  const paper = status.binanceFuturesPaper || {};
  if (isBinanceFuturesPaper(status) && paper && !paper.error) {
    return {
      currency: "USDT",
      equity: Number(paper.equityUsdt || 0),
      cash: Number(paper.availableBalanceUsdt || 0),
      positionValue: futuresPaperExposureUsdt(paper),
      realizedPnl: Number(paper.realizedPnlUsdt || 0),
      orderCount: Number(paper.orderCount || 0),
    };
  }
  return {
    currency: "KRW",
    equity: Number(account.equityKrw || 0),
    cash: Number(account.cashKrw || 0),
    positionValue: Number(account.positionValueKrw || 0),
    realizedPnl: Number(account.realizedPnlKrw || 0),
    orderCount: Number(account.orderCount || 0),
  };
}

function futuresPaperExposureUsdt(paper = {}) {
  const reported = Number(paper.totalNotionalUsdt || 0);
  if (Number.isFinite(reported) && reported > 0) return reported;
  const positions = Array.isArray(paper.positions) ? paper.positions : [];
  return positions.reduce((total, position) => total + Number(position.notionalUsdt || 0), 0);
}

function goalDisplay(status) {
  const goal = status.goal || {};
  const paper = status.binanceFuturesPaper || {};
  if (isBinanceFuturesPaper(status) && paper && !paper.error) {
    const start = Number(paper.goalStartUsdt || 1000);
    const target = Number(paper.goalTargetUsdt || start * 100);
    const equity = Number(paper.equityUsdt || 0);
    const remaining = Math.max(0, target - equity);
    const progressPct = target > start ? Math.max(0, Math.min(100, ((equity - start) / (target - start)) * 100)) : 0;
    return { currency: "USDT", start, target, equity, remaining, progressPct };
  }
  return {
    currency: "KRW",
    start: Number(goal.startKrw || 0),
    target: Number(goal.targetKrw || 0),
    equity: Number(goal.equityKrw || 0),
    remaining: Number(goal.remainingKrw || 0),
    progressPct: Number(goal.progressPct || 0),
  };
}

function investmentSnapshot(status) {
  if (isBinanceFuturesPaper(status) && status.binanceFuturesPaper && !status.binanceFuturesPaper.error) {
    return futuresPaperInvestmentSnapshot(status);
  }
  const account = status.account || {};
  const markets = Array.isArray(status.markets) ? status.markets : [];
  const byMarket = {};
  let openPositions = 0;

  markets.forEach((row) => {
    if (!row.market) return;
    const positionValueKrw = Number(row.positionValueKrw || 0);
    if (positionValueKrw > 0) openPositions += 1;
    byMarket[row.market] = {
      market: row.market,
      label: marketLabel(row),
      price: Number(row.price || 0),
      positionValueKrw,
      avgEntryPrice: Number(row.avgEntryPrice || 0),
      targetSellPrice: Number(row.targetSellPrice || 0),
      stopLossPrice: Number(row.stopLossPrice || 0),
      unrealizedPnlKrw: Number(row.unrealizedPnlKrw || 0),
      realizedPnlKrw: Number(row.realizedPnlKrw || 0),
      returnPct: Number(row.returnPct || 0),
      analysis: row.analysis || {},
    };
  });

  return {
    time: status.runtime?.updatedAt || new Date().toISOString(),
    currency: "KRW",
    equityKrw: Number(account.equityKrw || 0),
    cashKrw: Number(account.cashKrw || 0),
    positionValueKrw: Number(account.positionValueKrw || 0),
    realizedPnlKrw: Number(account.realizedPnlKrw || 0),
    openPositions,
    orderCount: Number(account.orderCount || 0),
    positionSignature: `KRW|${openPositions}|${Number(account.orderCount || 0)}|${Object.values(byMarket)
      .filter((row) => Number(row.positionValueKrw || 0) > 0)
      .map((row) => `${row.market}:${row.avgEntryPrice}`)
      .sort()
      .join("|") || "flat"}`,
    byMarket,
  };
}

function futuresPaperInvestmentSnapshot(status) {
  const paper = status.binanceFuturesPaper || {};
  const positions = Array.isArray(paper.positions) ? paper.positions : [];
  const byMarket = {};
  positions.forEach((position) => {
    const symbol = position.symbol || "";
    if (!symbol) return;
    const live = liveFuturesPrices.get(normalizeFuturesSymbol(symbol));
    const livePrice = Number(live?.price || position.currentPrice || 0);
    const liveMetrics = liveFuturesPositionMetrics(position, livePrice);
    const margin = Number(position.marginUsdt || 0);
    const notional = Number(liveMetrics?.notional || position.notionalUsdt || 0);
    const pnl = Number(liveMetrics?.pnl || position.unrealizedPnlUsdt || 0);
    const side = position.side || "";
    const leverage = Number(position.leverage || paper.leverage || 0);
    const roe = Number(liveMetrics?.roe || position.returnOnMarginPct || 0);
    const priceMovePct = Number(liveMetrics?.priceMovePct || position.priceMovePct || (leverage ? roe / leverage : 0));
    const entryNotional = Number(position.entryPrice || 0) * Number(position.quantity || 0);
    byMarket[symbol] = {
      market: symbol,
      label: `${symbol} ${side}`.trim(),
      price: Number(liveMetrics?.price || position.currentPrice || 0),
      positionValueKrw: notional,
      baselinePositionValueKrw: entryNotional || notional,
      marginValueKrw: margin,
      avgEntryPrice: Number(position.entryPrice || 0),
      targetSellPrice: Number(position.takeProfitPrice || 0),
      stopLossPrice: Number(position.stopLossPrice || 0),
      unrealizedPnlKrw: pnl,
      realizedPnlKrw: 0,
      baselineRealizedPnlKrw: 0,
      returnPct: roe,
      analysis: {
        title: `${side || "FUTURES"} ${position.leverage || paper.leverage || "-"}x · ${formatSignedPercent2(priceMovePct)}% -> ROE ${formatSignedPercent2(roe)}%`,
        narrative: position.reason || `바이낸스 USD-M 선물 모의 ${symbol} 포지션을 USDT 기준으로 감시합니다.`,
      },
      methodGuide: futuresMethodGuideForPosition(position, paper, liveMetrics, status),
      manualControl: true,
      positionSignature: [
        symbol,
        side,
        position.entryPrice || "",
        position.quantity || "",
        position.marginUsdt || "",
        position.openedAt || "",
      ].join(":"),
    };
  });
  if (!positions.length) {
    const symbol = "BTCUSDT";
    const live = liveFuturesPrices.get(symbol);
    const manualAction = String(paper.manualAction || "").toUpperCase();
    const displaySide = futuresDisplaySideLabel(paper.executionSide || paper.analysisSide || "FLAT");
    byMarket[symbol] = {
      market: symbol,
      label: `${symbol} ${displaySide}`.trim(),
      price: Number(live?.price || 0),
      positionValueKrw: 0,
      marginValueKrw: 0,
      avgEntryPrice: 0,
      targetSellPrice: 0,
      stopLossPrice: 0,
      unrealizedPnlKrw: 0,
      realizedPnlKrw: 0,
      returnPct: 0,
      analysis: {
        title: manualAction ? `${manualAction} · 수동 대기` : "AUTO · 자동 대기",
        narrative: "포지션이 없어도 BTCUSDT 수동/자동 조작 카드는 유지합니다.",
      },
      methodGuide: futuresFlatMethodGuide(paper, status),
      manualControl: true,
    };
  }
  const currentEquity = Number(paper.equityUsdt || 0);
  const currentCash = Number(paper.availableBalanceUsdt || 0);
  const currentExposure = futuresPaperExposureUsdt(paper);
  const marketRows = Object.values(byMarket);
  const totalUnrealizedPnl = marketRows.reduce((total, row) => total + Number(row.unrealizedPnlKrw || 0), 0);
  const entryExposure = marketRows.reduce(
    (total, row) => total + Number(row.baselinePositionValueKrw ?? row.positionValueKrw ?? 0),
    0,
  );
  const realizedPnl = Number(paper.realizedPnlUsdt || 0);
  return {
    time: paper.updatedAt || status.runtime?.updatedAt || new Date().toISOString(),
    currency: "USDT",
    equityKrw: currentEquity,
    baselineEquityKrw: currentEquity - totalUnrealizedPnl,
    cashKrw: currentCash,
    baselineCashKrw: currentCash - totalUnrealizedPnl,
    positionValueKrw: currentExposure,
    baselinePositionValueKrw: entryExposure || currentExposure,
    realizedPnlKrw: realizedPnl,
    baselineRealizedPnlKrw: realizedPnl,
    openPositions: Number(paper.openPositions || positions.length || 0),
    orderCount: Number(paper.orderCount || 0),
    positionSignature:
      positions.length > 0
        ? `USDT|${positions
            .map((position) => {
              const symbol = normalizeFuturesSymbol(position.symbol);
              return [
                symbol,
                position.side || "",
                position.entryPrice || "",
                position.quantity || "",
                position.marginUsdt || "",
                position.openedAt || "",
              ].join(":");
            })
            .sort()
            .join("|")}`
        : `USDT|FLAT|${String(paper.manualAction || "AUTO").toUpperCase()}|${Number(paper.orderCount || 0)}`,
    byMarket,
  };
}

function investmentFlowRows(snapshot, previous) {
  const previousMarkets = previous?.byMarket || {};
  const markets = new Set([...Object.keys(snapshot.byMarket), ...Object.keys(previousMarkets)]);
  return [...markets]
    .map((market) => {
      const current = snapshot.byMarket[market] || previousMarkets[market] || {};
      const prev = previousMarkets[market] || {};
      const positionValueKrw = Number(current.positionValueKrw || 0);
      const positionDeltaKrw = previous ? positionValueKrw - Number(prev.positionValueKrw || 0) : 0;
      const marginValueKrw = Number(current.marginValueKrw || prev.marginValueKrw || 0);
      const realizedDeltaKrw = previous
        ? Number(current.realizedPnlKrw || 0) - Number(prev.realizedPnlKrw || 0)
        : 0;
      const unrealizedPnlKrw = Number(current.unrealizedPnlKrw || 0);

      return {
        market,
        label: current.label || displayMarketCode(market),
        currency: snapshot.currency || current.currency || "KRW",
        price: Number(current.price || prev.price || 0),
        positionValueKrw,
        marginValueKrw,
        avgEntryPrice: Number(current.avgEntryPrice || prev.avgEntryPrice || 0),
        targetSellPrice: Number(current.targetSellPrice || prev.targetSellPrice || 0),
        stopLossPrice: Number(current.stopLossPrice || prev.stopLossPrice || 0),
        positionDeltaKrw,
        unrealizedPnlKrw,
        realizedDeltaKrw,
        returnPct: Number(current.returnPct || 0),
        analysisTitle: current.analysis?.title || "판단 대기",
        analysisNarrative: current.analysis?.narrative || buildFlowNarrative(current, positionValueKrw, unrealizedPnlKrw),
        methodGuide: current.methodGuide || prev.methodGuide || null,
        manualControl: Boolean(current.manualControl || prev.manualControl),
        changeWeight: Math.max(Math.abs(positionDeltaKrw), Math.abs(realizedDeltaKrw)),
        holdingWeight: Math.max(
          positionValueKrw,
          Math.abs(unrealizedPnlKrw),
        ),
      };
    })
    .filter(
      (row) =>
        row.positionValueKrw > 0 ||
        row.manualControl ||
        Math.abs(row.positionDeltaKrw) >= 1 ||
        Math.abs(row.realizedDeltaKrw) >= 1 ||
        Math.abs(row.unrealizedPnlKrw) >= 1,
    )
    .sort((a, b) => b.changeWeight - a.changeWeight || b.holdingWeight - a.holdingWeight)
    .slice(0, 40);
}

function emptyInvestmentFlowRow() {
  if (isBinanceFuturesPaper(latestStatus)) {
    const paper = latestStatus?.binanceFuturesPaper || {};
    const symbol = "BTCUSDT";
    const live = liveFuturesPrices.get(symbol);
    const manualAction = String(paper.manualAction || "").toUpperCase();
    const displaySide = futuresDisplaySideLabel(paper.executionSide || paper.analysisSide || "FLAT");
    return renderInvestmentFlowRow({
      market: symbol,
      label: `${symbol} ${displaySide}`.trim(),
      currency: "USDT",
      price: Number(live?.price || 0),
      positionValueKrw: 0,
      marginValueKrw: 0,
      avgEntryPrice: 0,
      targetSellPrice: 0,
      stopLossPrice: 0,
      positionDeltaKrw: 0,
      unrealizedPnlKrw: 0,
      realizedDeltaKrw: 0,
      returnPct: 0,
      analysisTitle: manualAction ? `${manualAction} · 수동 대기` : "AUTO · 자동 대기",
      analysisNarrative: "포지션 0개 상태에서도 BTCUSDT 수동/자동/롱/숏/스탑 버튼을 유지합니다.",
      methodGuide: futuresFlatMethodGuide(paper, latestStatus || {}),
      manualControl: true,
    });
  }
  const tr = document.createElement("tr");
  tr.innerHTML = `<td colspan="8" class="empty-cell">현재 보유 또는 변동 종목이 없습니다</td>`;
  return tr;
}

function buildFlowNarrative(row, positionValueKrw, unrealizedPnlKrw) {
  if (positionValueKrw > 0) {
    return `평균 매수가 ${formatOptionalPrice(row.avgEntryPrice)}, 현재 평가 ${formatKrw(positionValueKrw)}원, 미실현 손익 ${formatSignedKrw(unrealizedPnlKrw)} 기준으로 목표가와 손절가를 감시합니다.`;
  }
  return "미보유 상태입니다. 신규 매수는 실시간 점수, 거래대금, 급등 추격 제한, 시장 레짐 필터를 통과할 때만 검토합니다.";
}

function openInvestmentFlowChart(market) {
  const row = latestStatus?.markets?.find((item) => item.market === market) || {
    market,
    symbol: displayMarketCode(market),
    price: 0,
    change: "EVEN",
    changeRate: 0,
    tradeValue24h: 0,
  };
  openMarketChart(row, latestStatus?.markets || [row]);
}

function holdingMarketRows(status = latestStatus) {
  if (isBinanceFuturesPaper(status)) return [];
  const markets = Array.isArray(status?.markets) ? status.markets : [];
  return markets
    .filter((row) => Number(row.positionValueKrw || 0) > 0)
    .sort((a, b) => Number(b.positionValueKrw || 0) - Number(a.positionValueKrw || 0));
}

function renderHoldingCharts(status) {
  if (!els.holdingCharts) return;
  const holdings = holdingMarketRows(status);
  if (els.holdingChartsState) {
    els.holdingChartsState.textContent = holdings.length
      ? `${holdings.length}개 보유 · ${chartUnitLabel(holdingChartUnit)}`
      : "보유 종목 대기";
    els.holdingChartsState.className = holdings.length ? "connected" : "waiting";
  }
  if (!holdings.length) {
    renderedHoldingMarketsKey = "";
    holdingChartCache.clear();
    els.holdingCharts.className = "holding-chart-grid";
    els.holdingCharts.replaceChildren(holdingEmptyNode());
    return;
  }

  const key = `${holdingChartUnit}:${holdings.map((row) => row.market).join("|")}`;
  els.holdingCharts.className = `holding-chart-grid ${holdingGridClass(holdings.length)}`;
  if (key !== renderedHoldingMarketsKey) {
    renderedHoldingMarketsKey = key;
    const cards = holdings.map((row) => holdingChartCard(row));
    els.holdingCharts.replaceChildren(...cards);
    loadHoldingCharts({ force: true });
  } else {
    holdings.forEach(updateHoldingChartCard);
  }
}

function holdingGridClass(count) {
  if (count <= 1) return "count-1";
  if (count === 2) return "count-2";
  if (count === 3) return "count-3";
  return "count-4-plus";
}

function holdingChartCard(row) {
  const article = document.createElement("article");
  article.className = "holding-chart-card";
  article.dataset.market = row.market;
  article.innerHTML = `
    <div class="holding-chart-head">
      <button class="holding-chart-title" type="button" title="메인 차트로 보기">
        <strong>${escapeHtml(marketLabel(row))}</strong>
        <small>${escapeHtml(displayMarketCode(row.market))} · ${chartUnitLabel(holdingChartUnit)} 캔들</small>
      </button>
      <div class="holding-chart-value">
        <span>${formatKrw(row.positionValueKrw)}원</span>
        <small class="${flowClass(Number(row.returnPct || 0))}">${formatSignedPercent2(Number(row.returnPct || 0))}%</small>
      </div>
      <div class="holding-chart-actions" aria-label="${escapeHtml(marketLabel(row))} 차트 줌">
        <button class="holding-chart-zoom-button" type="button" data-chart-zoom-action="out" aria-label="${escapeHtml(marketLabel(row))} 차트 축소" title="축소">-</button>
        <button class="holding-chart-zoom-button" type="button" data-chart-zoom-action="reset" aria-label="${escapeHtml(marketLabel(row))} 차트 기본 보기" title="기본 보기">↺</button>
        <button class="holding-chart-zoom-button" type="button" data-chart-zoom-action="in" aria-label="${escapeHtml(marketLabel(row))} 차트 확대" title="확대">+</button>
      </div>
    </div>
    <canvas class="holding-chart" width="480" height="190" aria-label="${escapeHtml(marketLabel(row))} 보유 종목 차트"></canvas>
    <div class="holding-chart-meta">차트 로딩 중</div>
  `;
  article.querySelector(".holding-chart-title").addEventListener("click", () => {
    openMarketChart(row, latestStatus?.markets || [row]);
  });
  return article;
}

function updateHoldingChartCard(row) {
  const card = els.holdingCharts?.querySelector(`[data-market="${cssEscape(row.market)}"]`);
  if (!card) return;
  const value = card.querySelector(".holding-chart-value span");
  const returnNode = card.querySelector(".holding-chart-value small");
  const titleSmall = card.querySelector(".holding-chart-title small");
  if (value) value.textContent = `${formatKrw(row.positionValueKrw)}원`;
  if (returnNode) {
    const returnPct = Number(row.returnPct || 0);
    returnNode.textContent = `${formatSignedPercent2(returnPct)}%`;
    returnNode.className = flowClass(returnPct);
  }
  if (titleSmall) titleSmall.textContent = `${displayMarketCode(row.market)} · ${chartUnitLabel(holdingChartUnit)} 캔들`;
}

function holdingEmptyNode() {
  const node = document.createElement("div");
  node.className = "holding-empty";
  node.textContent = "현재 보유 중인 종목이 생기면 이곳에 차트가 표시됩니다";
  return node;
}

async function loadHoldingCharts(options = {}) {
  if (holdingChartsInFlight || !latestStatus || !els.holdingCharts) return;
  const holdings = holdingMarketRows(latestStatus);
  if (!holdings.length) return;
  holdingChartsInFlight = true;
  if (els.holdingChartsState) {
    els.holdingChartsState.textContent = `${holdings.length}개 보유 · 차트 갱신 중`;
    els.holdingChartsState.className = "waiting";
  }
  try {
    for (const row of holdings) {
      const card = els.holdingCharts.querySelector(`[data-market="${cssEscape(row.market)}"]`);
      const canvas = card?.querySelector(".holding-chart");
      const meta = card?.querySelector(".holding-chart-meta");
      if (!canvas) continue;
      const cacheKey = `${row.market}:${holdingChartUnit}`;
      if (!options.force && holdingChartCache.has(cacheKey)) {
        drawTradeChart(holdingChartCache.get(cacheKey), canvas, { compact: true, market: row.market, row, unit: holdingChartUnit });
        continue;
      }
      try {
        const payload = await requestJson(
          `/api/chart/${encodeURIComponent(row.market)}?${chartQueryParams(holdingChartUnit)}`,
        );
        holdingChartCache.set(cacheKey, payload.candles);
        drawTradeChart(payload.candles, canvas, { compact: true, market: row.market, row, unit: payload.unit || holdingChartUnit });
        if (meta) meta.textContent = `${payload.count}개 캔들 · ${chartUnitLabel(payload.unit)} · ${formatTime(new Date().toISOString())} 갱신`;
      } catch (error) {
        if (meta) meta.textContent = error.message;
        drawTradeChart([], canvas, { compact: true, market: row.market, row, unit: holdingChartUnit });
      }
      await delay(180);
    }
  } finally {
    holdingChartsInFlight = false;
    const currentCount = holdingMarketRows(latestStatus).length;
    if (els.holdingChartsState) {
      els.holdingChartsState.textContent = currentCount ? `${currentCount}개 보유 · ${chartUnitLabel(holdingChartUnit)}` : "보유 종목 대기";
      els.holdingChartsState.className = currentCount ? "connected" : "waiting";
    }
  }
}

function redrawHoldingCharts() {
  if (!els.holdingCharts) return;
  els.holdingCharts.querySelectorAll(".holding-chart-card").forEach((card) => {
    const market = card.dataset.market;
    const canvas = card.querySelector(".holding-chart");
    const cached = holdingChartCache.get(`${market}:${holdingChartUnit}`);
    const row = latestStatus?.markets?.find((item) => item.market === market);
    if (canvas && cached) drawTradeChart(cached, canvas, { compact: true, market, row, unit: holdingChartUnit });
  });
}

async function loadPortfolioChart(options = {}) {
  if (portfolioChartInFlight || !els.portfolioChart) return;
  if (!options.force && latestPortfolioChart.length && document.hidden) return;
  portfolioChartInFlight = true;
  if (els.portfolioChartMeta && !latestPortfolioChart.length) {
    els.portfolioChartMeta.textContent = "총자산 스냅샷을 불러오는 중입니다";
  }
  try {
    const payload = await requestJson(`/api/portfolio-chart?${chartQueryParams(portfolioChartUnit)}`);
    latestPortfolioChart = Array.isArray(payload.candles) ? payload.candles : [];
    renderPortfolioChart(payload);
  } catch (error) {
    latestPortfolioChart = [];
    if (els.portfolioChartMeta) els.portfolioChartMeta.textContent = error.message;
    drawTradeChart([], els.portfolioChart, { portfolio: true, unit: portfolioChartUnit, showTradeLevels: false });
  } finally {
    portfolioChartInFlight = false;
  }
}

function renderPortfolioChart(payload = {}) {
  if (!els.portfolioChart) return;
  const points = Array.isArray(payload.candles) ? payload.candles : latestPortfolioChart;
  const latest = points.at(-1) || {};
  const unit = payload.unit || portfolioChartUnit;
  const currency = payload.currency || latest.currency || (isBinanceFuturesPaper() ? "USDT" : "KRW");
  if (els.portfolioChartTitle) {
    els.portfolioChartTitle.textContent = `실시간 총자산 ${chartUnitLabel(unit)} 차트 · ${currency}`;
  }
  if (els.portfolioChartMeta) {
    const latestEquity = Number(latest.close || latest.equityKrw || 0);
    const latestInvestment = Number(latest.positionValueKrw || 0);
    const latestCash = Number(latest.cashKrw || 0);
    els.portfolioChartMeta.textContent = points.length
      ? `${points.length}개 구간 · 총자산 ${formatMoneyValue(latestEquity, currency)} · 노출/보유 ${formatMoneyValue(latestInvestment, currency)} · 가용 ${formatMoneyValue(latestCash, currency)}`
      : "자동매매 스냅샷이 쌓이면 차트가 표시됩니다";
  }
  renderPortfolioFeeBreakdown(latest, currency);
  drawTradeChart(points, els.portfolioChart, {
    portfolio: true,
    unit,
    showTradeLevels: false,
    priceLevels: portfolioChartLevels(points),
  });
}

function renderPortfolioFeeBreakdown(latest = {}, currency = "KRW") {
  if (!els.portfolioFeeBreakdown) return;
  const rows = [
    ["가격손익", Number(latest.pricePnlKrw || 0), "price"],
    ["진입수수료", Number(latest.openFeesPaidKrw || 0), "fee"],
    ["청산수수료", Number(latest.closeFeesPaidKrw || 0), "fee"],
    ["누적수수료", Number(latest.feesPaidKrw || 0), "fee"],
  ];
  els.portfolioFeeBreakdown.replaceChildren(
    ...rows.map(([label, value, type]) => {
      const item = document.createElement("span");
      item.className = `fee-breakdown-chip ${type} ${value >= 0 ? "positive" : "negative"}`;
      item.textContent = `${label} ${formatMoneyValue(value, currency)}`;
      return item;
    }),
  );
}

function portfolioChartLevels(points) {
  const latest = Array.isArray(points) ? points.at(-1) : null;
  const close = Number(latest?.close || 0);
  if (!Number.isFinite(close) || close <= 0) return [];
  return [{ label: "현재 총자산", price: close, color: "#111827", dashed: false }];
}

function redrawPortfolioChart() {
  if (!els.portfolioChart) return;
  renderPortfolioChart({ unit: portfolioChartUnit, candles: latestPortfolioChart });
}

function cssEscape(value) {
  if (window.CSS && CSS.escape) return CSS.escape(value);
  return String(value).replaceAll('"', '\\"');
}

function delay(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function setFlowMetric(element, value, currency = "KRW") {
  if (!element) return;
  element.textContent = formatSignedMoneyValue(value, currency);
  element.className = flowClass(value);
}

function flowClass(value) {
  const numeric = Number(value || 0);
  if (numeric > 0) return "positive";
  if (numeric < 0) return "negative";
  return "waiting";
}

function renderSystemStatus(status = {}) {
  if (!els.systemStatusGrid) return;
  const runtime = status.runtime || {};
  const realtime = status.realtime || {};
  const autorun = status.autorun || {};
  const monitors = status.monitors || {};
  const settings = status.settings || {};
  const exchangeMode = status.exchangeMode || {};
  const pm = status.pm || {};
  const live = status.live || {};
  const decision = status.realtimeDecision || {};
  const last = decision.last || {};
  const plan = last.plan || {};
  const selected = Array.isArray(plan.selected) ? plan.selected : [];
  const planOrders = Array.isArray(plan.orders) ? plan.orders : [];
  const executedOrders = Array.isArray(last.orders) ? last.orders : [];
  const orders = executedOrders.length ? executedOrders : planOrders;
  const evaluated = Number(plan.evaluatedCount || 0);
  const universe = Number(plan.universeCount || status.markets?.length || 0);
  const analysisScopeLabel = isFuturesAnalysisPlan(plan) ? "바이낸스 선물" : "전체 KRW";
  const realtimeDecisionMonitor = monitors.realtimeDecision || {};
  const aiPmMonitor = monitors.aiPm || {};
  const marketIntelMonitor = monitors.marketIntel || {};
  const liveArmed = Boolean(live.armed || runtime.liveTradingEnabled);
  const realtimeAnalysisActive = Boolean(
    settings.realtimeDecisionEnabled && (autorun.running || realtimeDecisionMonitor.running || evaluated > 0),
  );
  const aiPmActive = Boolean(pm.connected && (aiPmMonitor.running || pm.configured));
  const intelActive = Boolean(marketIntelMonitor.running);

  const items = [
    {
      key: "autorun",
      title: "매매 루프",
      state: autorun.running ? "작동 중" : "정지",
      level: autorun.running ? "ok" : "waiting",
      detail: autorun.running
        ? `${autorun.intervalSeconds || 0}초마다 분석 결과를 주문 루프로 실행 · ${number.format(Number(autorun.iterations || 0))}회`
        : "이 버튼은 매매 실행 루프만 시작합니다.",
      active: Boolean(autorun.running),
    },
    {
      key: "exchange",
      title: "거래소 운용",
      state: exchangeMode.label || "업비트 현물",
      level: "locked",
      detail: exchangeMode.orderBoundary || exchangeMode.description || "선택된 거래소 모드 기준으로 자동 실행 루프가 분기됩니다.",
      active: true,
    },
    {
      key: "realtime",
      title: "실시간 시세",
      state: realtime.connected ? "연결됨" : "대기",
      level: realtime.connected ? "ok" : realtime.lastError ? "critical" : "waiting",
      detail: realtime.lastMessageAt
        ? `${formatTime(realtime.lastMessageAt)} 수신 · 재연결 ${realtime.reconnects || 0}회`
        : realtime.lastError || "WebSocket 수신 대기",
      active: Boolean(realtime.connected),
    },
    {
      key: "analysis",
      title: "실시간 분석",
      state: realtimeAnalysisActive ? "분석 중" : settings.realtimeDecisionEnabled ? "대기" : "꺼짐",
      level: realtimeAnalysisActive ? "ok" : settings.realtimeDecisionEnabled ? "waiting" : "critical",
      detail: universe
        ? `${analysisScopeLabel} ${number.format(evaluated)}/${number.format(universe)} 평가 · 후보 ${selected.length}개 · 주문 ${orders.length}개`
        : `${analysisScopeLabel} 분석 기록 대기`,
      active: realtimeAnalysisActive,
    },
    {
      key: "pm",
      title: "AI PM",
      state: aiPmActive ? "상주 관리" : pm.enabled && pm.configured ? "호출 대기" : pm.enabled ? "API키 대기" : "꺼짐",
      level: aiPmActive ? "ok" : pm.enabled && pm.configured ? "waiting" : "critical",
      detail: aiPmMonitor.running
        ? `${pm.model || "AI"} · ${monitorStatusDetail(aiPmMonitor, "PM 상주 점검 대기")}`
        : pm.connected
          ? `${pm.model || "AI"} · 실제 모델 호출 가능`
          : pm.enabled && !pm.configured
            ? "OPENAI_API_KEY 또는 AI_PM_API_KEY 필요"
            : "AI_PM_ENABLED=false",
      active: aiPmActive,
    },
    {
      key: "intel",
      title: "시장 인텔",
      state: intelActive ? "자동 수집" : "대기",
      level: intelActive ? "ok" : "waiting",
      detail: monitorStatusDetail(marketIntelMonitor, "뉴스·호재·악재 자동 수집 대기"),
      active: intelActive,
    },
    {
      key: "live",
      title: "실거래 잠금",
      state: liveArmed ? "해제됨" : "잠금",
      level: liveArmed ? "critical" : "locked",
      detail: liveArmed
        ? "실주문 가능 상태입니다. 주문 전 확인 문구와 리스크 검사를 통과해야 합니다."
        : live.keyConfigured
          ? "업비트 키는 있으나 실거래 플래그와 확인 문구가 잠겨 있습니다."
          : "현재 페이퍼 주문만 반영됩니다.",
      active: !liveArmed,
    },
  ];

  const activeCoreCount = items.filter((item) => item.key !== "live" && item.active).length;
  if (els.systemModeBadge) {
    els.systemModeBadge.textContent = runtime.emergencyStopped ? "긴급정지" : liveArmed ? "실거래 주의" : "페이퍼 운영";
    els.systemModeBadge.className = `analysis-badge ${runtime.emergencyStopped || liveArmed ? "critical" : "ok"}`;
  }
  if (els.systemStatusSummary) {
    els.systemStatusSummary.textContent =
      `운용 ${exchangeMode.label || "업비트 현물"} · 상주 기능 ${activeCoreCount}/6 작동 · 실거래 ${liveArmed ? "해제" : "잠금"}`;
  }
  els.systemStatusGrid.replaceChildren(...items.map(systemStatusItemNode));
}

function monitorStatusDetail(snapshot = {}, idleText = "대기") {
  const interval = Number(snapshot.intervalSeconds || 0);
  const cadence = interval >= 3600
    ? `${Math.round(interval / 3600)}시간 주기`
    : interval > 0
      ? `${interval}초 주기`
      : "상주";
  const iterations = number.format(Number(snapshot.iterations || 0));
  if (snapshot.running) return `${cadence} · ${iterations}회 완료`;
  if (snapshot.lastError) return snapshot.lastError;
  if (snapshot.lastFinishedAt) return `${formatTime(snapshot.lastFinishedAt)} 마지막 실행`;
  return idleText;
}

function systemStatusItemNode(item) {
  const article = document.createElement("article");
  article.className = `system-status-item ${item.level}`;
  article.dataset.key = item.key;
  article.innerHTML = `
    <div>
      <span>${escapeHtml(item.title)}</span>
      <strong>${escapeHtml(item.state)}</strong>
    </div>
    <p>${escapeHtml(item.detail)}</p>
  `;
  return article;
}

function renderRuntimeStatus(status) {
  const realtime = status.realtime || {};
  const autorun = status.autorun || {};
  const settings = status.settings || {};
  const account = status.account || {};
  const runtime = status.runtime || {};
  const security = status.security || {};

  els.realtimeState.textContent = realtime.connected ? "연결됨" : "대기";
  els.realtimeState.className = realtime.connected ? "connected" : "waiting";
  const realtimeDetail = realtime.lastMessageAt
    ? `${formatTime(realtime.lastMessageAt)} 수신 · 재연결 ${realtime.reconnects || 0}회`
    : realtime.lastError || "실시간 수신 대기";
  els.realtimeDetail.textContent = realtimeDetail;

  els.autoRunState.textContent = autorun.running ? "작동 중" : "정지";
  els.autoRunState.className = autorun.running ? "connected" : "waiting";
  const autoRunDetail = autorun.running
    ? `${autorun.intervalSeconds || 0}초 주기 · ${autorun.iterations || 0}회 완료`
    : autorun.lastFinishedAt
      ? `${formatTime(autorun.lastFinishedAt)} 중지`
      : "수동 실행 대기";
  els.autoRunDetail.textContent = autoRunDetail;
  const live = status.live || {};
  const liveGuardText = live.armed || runtime.liveTradingEnabled ? "실거래 가능" : "실거래 잠금";
  els.autoRunHeaderState.textContent = autorun.running ? "매매 루프 작동 중" : "매매 루프 정지";
  els.autoRunHeaderState.className = autorun.running ? "connected" : "waiting";
  els.autoRunHeaderDetail.textContent = `${autoRunDetail} · ${liveGuardText}`;
  els.autoRunHeaderDot.className = `autorun-dot ${autorun.running ? "running" : "waiting"}`;

  els.dailyRiskState.textContent =
    `${number.format(Number(account.dailyOrderCount || 0))}/${number.format(Number(settings.maxDailyOrders || 0))}회`;
  els.dailyRiskDetail.textContent = `일일손익 ${formatKrw(account.dailyRealizedPnlKrw)}원 · 손절 ${settings.stopLossPct}% · 익절 ${settings.takeProfitPct}%`;

  els.securityState.textContent = security.dashboardAuthEnabled ? "로그인 보호" : "로컬 전용";
  els.securityState.className = security.dashboardAuthEnabled ? "connected" : "waiting";
  els.securityDetail.textContent = security.dashboardAuthEnabled
    ? `사용자 ${security.dashboardUsername || "admin"} · 상태 점검 제외`
    : "LAN/모바일 접속 전 DASHBOARD_AUTH_ENABLED=true 권장";

  els.autoStartButton.disabled = Boolean(autorun.running || runtime.emergencyStopped);
  els.autoStopButton.disabled = !autorun.running;
}

function renderStrategyOptions(payload) {
  strategyOptions = payload.strategies || [];
  const active = payload.active || strategyOptions.find((item) => item.active)?.name || "";
  const auto = Boolean(payload.auto);
  els.strategySelect.replaceChildren(
    ...strategyOptions.map((strategy) => {
      const option = document.createElement("option");
      option.value = strategy.name;
      option.textContent = `${strategy.label} · ${strategy.risk}`;
      option.selected = strategy.name === active;
      return option;
    }),
  );
  els.strategyAutoToggle.checked = auto;
  els.strategySelect.disabled = auto;
  syncStrategySelection(active);
}

function syncStrategySelection(active) {
  if (!active || !els.strategySelect) return;
  if (els.strategySelect.value !== active) {
    els.strategySelect.value = active;
  }
  const selected = strategyOptions.find((strategy) => strategy.name === active);
  if (selected) {
    const auto = Boolean(els.strategyAutoToggle?.checked);
    els.strategyDescription.textContent = auto
      ? `자동설정: 학습 결과와 실시간 추세, 거래대금, 리스크 필터를 보고 ${selected.label} 기반으로 코인별 기법을 선택합니다.`
      : selected.description;
    els.backtestStrategy.textContent = auto ? `${selected.label} · 자동설정` : selected.label;
  }
}

function selectedStrategyLabel(name) {
  return strategyOptions.find((strategy) => strategy.name === name)?.label || name;
}

function renderLiveStatus(live) {
  els.liveModeBadge.textContent = live.webArmed ? "웹 실거래 가능" : "실거래 잠금";
  els.liveModeBadge.className = live.webArmed ? "ready" : "locked";
  els.liveKeyState.textContent = live.keyConfigured ? "설정됨" : "미설정";
  els.liveKeyState.className = live.keyConfigured ? "connected" : "waiting";
  els.liveKeyDetail.textContent = live.accessKeyMasked ? `Access ${live.accessKeyMasked}` : "UPBIT_ACCESS_KEY 필요";
  els.liveLockState.textContent = live.webArmed ? "해제됨" : "잠금";
  els.liveLockState.className = live.webArmed ? "connected" : "waiting";
  els.liveLockDetail.textContent = live.confirmationArmed
    ? "동의 문구 확인됨"
    : `LIVE_ORDER_CONFIRMATION="${live.confirmationPhrase || "실거래 손실 동의"}" 또는 "${live.confirmationCode || "LIVE-RISK-ACCEPTED"}" 필요`;
  els.liveTestState.textContent = live.testOrderArmed ? "리허설 가능" : "잠금";
  els.liveTestState.className = live.testOrderArmed ? "connected" : "waiting";
  els.liveTestDetail.textContent = live.testOrderEnabled
    ? "테스트 주문도 확인 문구 필요"
    : "LIVE_TEST_ORDER_ENABLED=true 필요";
  els.liveTestOrderButton.disabled = !live.testOrderArmed;
}

function renderLiveCheck(payload) {
  renderLiveStatus(payload.live || {});
  const account = payload.account;
  if (account) {
    els.liveCashKrw.textContent = `${formatKrw(account.cashKrw)}원`;
    els.liveAccountDetail.textContent = `계좌 ${account.accountCount}개 · 잠금 ${formatKrw(account.lockedKrw)}원`;
  } else {
    els.liveCashKrw.textContent = "-";
    els.liveAccountDetail.textContent = (payload.errors || []).join(" · ") || "읽기 전용 점검 대기";
  }
  if (payload.orderChance) {
    els.livePreviewDetail.textContent = `매수유형 ${payload.orderChance.bidTypes.join(", ") || "-"} · 매도유형 ${payload.orderChance.askTypes.join(", ") || "-"}`;
  }
}

function renderLivePreview(payload) {
  renderLiveStatus(payload.live || {});
  if (!payload.ok) {
    els.livePreviewState.textContent = "불가";
    els.livePreviewState.className = "rejected";
    els.livePreviewDetail.textContent = payload.message || "미리보기를 만들 수 없습니다";
    return;
  }
  if (payload.account) {
    els.liveCashKrw.textContent = `${formatKrw(payload.account.cashKrw)}원`;
    els.liveAccountDetail.textContent = `계좌 ${payload.account.accountCount}개 · 잠금 ${formatKrw(payload.account.lockedKrw)}원`;
  }
  const risk = payload.risk || {};
  els.livePreviewState.textContent = risk.approved ? "주문 후보" : "대기";
  els.livePreviewState.className = risk.approved ? "approved" : "rejected";
  const intent = risk.intent;
  els.livePreviewDetail.textContent = intent
    ? `${payload.market} ${intent.side} · ${intent.price ? `${formatKrw(intent.price)}원` : `${number.format(Number(intent.volume || 0))}개`}`
    : risk.reason || "주문 후보 없음";
}

function renderBacktest(payload) {
  els.backtestStrategy.textContent = selectedStrategyLabel(payload.strategy || els.strategySelect.value || "전략");
  const best = payload.best;
  const worst = payload.worst;
  els.bestBacktestMarket.textContent = best ? best.market : "-";
  els.bestBacktestDetail.textContent = best
    ? `수익률 ${formatSignedPercent2(Number(best.totalReturnPct || 0))}% · MDD ${formatSignedPercent2(Number(best.maxDrawdownPct || 0))}%`
    : "백테스트 결과 없음";
  els.worstBacktestMarket.textContent = worst ? worst.market : "-";
  els.worstBacktestDetail.textContent = worst
    ? `수익률 ${formatSignedPercent2(Number(worst.totalReturnPct || 0))}% · MDD ${formatSignedPercent2(Number(worst.maxDrawdownPct || 0))}%`
    : "백테스트 결과 없음";
}

function renderEvents(payload) {
  const events = payload.events || [];
  els.eventLogCount.textContent = `${events.length}개`;
  const latest = events.at(-1);
  els.eventLogDetail.textContent = latest
    ? `${formatTime(latest.time)} · ${latest.type}`
    : "아직 기록된 운영 이벤트가 없습니다";
}

function renderExchanges(payload) {
  const binance = payload.binance || {};
  const futures = payload.binanceFutures || {};
  const paper = futures.paper || {};
  renderExchangeMode(payload.exchangeMode || {});
  if (paper.openPositions > 0) {
    els.exchangeState.textContent = "바이낸스 선물 모의거래";
  } else if (futures.accountOk) {
    els.exchangeState.textContent = "업비트+바이낸스 선물";
  } else if (futures.publicOk) {
    els.exchangeState.textContent = "바이낸스 선물 공개 연결";
  } else if (binance.publicOk) {
    els.exchangeState.textContent = "업비트+바이낸스";
  } else {
    els.exchangeState.textContent = "업비트";
  }
  const futuresBalance = futures.account?.availableBalance
    ? ` · 선물 가용 ${formatNumber(Number(futures.account.availableBalance), 2)} USDT`
    : "";
  const paperDetail = paper.simulated ? ` · 모의 ${binanceFuturesPaperSummary(paper)}` : "";
  els.exchangeDetail.textContent = futures.publicOk
    ? `USD-M Futures ${futures.symbols.length}개 심볼 · ${futures.prices.length}개 가격 확인${futuresBalance}${paperDetail} · 실제 주문 잠금`
    : binance.publicOk
      ? `Spot ${binance.symbols.length}개 심볼 · ${binance.prices.length}개 가격 확인`
      : futures.accountError || futures.error || binance.error || "바이낸스 연결 대기";
}

function renderBinanceFuturesPaper(payload) {
  if (!payload || payload.error) {
    els.exchangeState.textContent = "선물 모의 오류";
    els.exchangeDetail.textContent = payload?.error || "바이낸스 선물 모의거래 상태를 확인하지 못했습니다";
    return;
  }
  const firstPosition = (payload.positions || [])[0];
  els.exchangeState.textContent = firstPosition
    ? `모의 ${firstPosition.side} ${firstPosition.symbol}`
    : "선물 모의 대기";
  const action = (payload.actions || [])[0];
  const actionText = action
    ? ` · ${action.type} ${action.symbol} ${action.side || ""}`.trim()
    : "";
  els.exchangeDetail.textContent = `${binanceFuturesPaperSummary(payload)}${actionText} · 실제 주문 없음`;
}

function binanceFuturesPaperSummary(payload) {
  const equity = formatNumber(Number(payload.equityUsdt || 0), 2);
  const available = formatNumber(Number(payload.availableBalanceUsdt || 0), 2);
  const unrealized = formatNumber(Number(payload.unrealizedPnlUsdt || 0), 2);
  const realized = formatNumber(Number(payload.realizedPnlUsdt || 0), 2);
  const sideMode = payload.paperSide ? ` · ${payload.paperSide} ${payload.leverage || "-"}x` : "";
  return `자산 ${equity} USDT · 가용 ${available} USDT · 미실현 ${unrealized} · 실현 ${realized} · 포지션 ${payload.openPositions || 0}개${sideMode}`;
}

function renderExchangeRuntimeStatus(status = latestStatus) {
  if (!els.exchangeState || !els.exchangeDetail) return;
  if (isBinanceFuturesPaper(status)) {
    const paper = status?.binanceFuturesPaper || {};
    els.exchangeState.textContent = "바이낸스 선물 모의거래";
    els.exchangeDetail.textContent = paper && !paper.error
      ? `${binanceFuturesPaperSummary(paper)} · ${paper.maxOpenPositions || 4}개까지 분산 · 실제 주문 없음`
      : "바이낸스 USD-M 선물 모의 상태 확인 대기 · 실제 주문 없음";
    return;
  }
  if (status?.exchangeMode?.active === "binance_spot") {
    els.exchangeState.textContent = "바이낸스 현물 감시";
    els.exchangeDetail.textContent = "바이낸스 현물 공개 시세 감시 · 실제 주문 잠금";
  }
}

function renderExchangeMode(payload) {
  if (!payload) return;
  const active = payload.active || "upbit";
  if (els.exchangeModeSelect) els.exchangeModeSelect.value = active;
  if (els.exchangeModeDetail) {
    const boundary = payload.orderBoundary ? ` · ${payload.orderBoundary}` : "";
    els.exchangeModeDetail.textContent = `${payload.label || "업비트 현물"} · ${payload.description || ""}${boundary}`;
  }
  if (els.binancePaperButton) {
    const futuresSelected = active === "binance_futures_paper";
    els.binancePaperButton.classList.toggle("active", futuresSelected);
    els.binancePaperButton.title = futuresSelected
      ? "선택된 바이낸스 선물 모의 모드를 즉시 한 번 실행합니다"
      : "바이낸스 선물 모의 모드로 전환한 뒤 실행하는 것이 좋습니다";
  }
}

function renderDatabase(payload) {
  const database = payload.database || {};
  const counts = database.counts || {};
  els.dbState.textContent = database.exists ? "저장 중" : "준비 중";
  const snapshotCount = counts.portfolio_snapshots || 0;
  const eventCount = counts.events || 0;
  const orderCount = counts.paper_orders || 0;
  const backtestCount = counts.backtest_reports || 0;
  const learningCount = counts.learning_runs || 0;
  els.dbDetail.textContent = `스냅샷 ${snapshotCount}개 · 이벤트 ${eventCount}개 · 주문 ${orderCount}개 · 백테스트 ${backtestCount}개 · 학습 ${learningCount}개`;
}

function renderAlerts(payload) {
  const summary = payload.summary || { level: "ok", label: "정상", count: 0 };
  const items = payload.items || [];
  const first = items[0];
  els.alertState.textContent = summary.count ? `${summary.label} ${summary.count}개` : "정상";
  els.alertState.className = summary.level || "ok";
  els.alertDetail.textContent = first ? `${first.title} · ${first.message}` : "위험 신호 없음";
}

function renderLearning(payload) {
  const model = payload.model || {};
  const job = payload.job || {};
  const overall = model.overall || {};
  const ranking = model.ranking || [];
  const best = ranking[0] || {};
  const marketCount = model.marketCount || Object.keys(model.markets || {}).length || 0;
  if (job.running) {
    const processed = job.processedMarkets || 0;
    const total = job.totalMarkets || 0;
    els.learningState.textContent = "학습 중";
    els.learningState.className = "warning";
    els.learningDetail.textContent = `${scopeLabel(job.scope)} · ${processed}/${total || "-"}개${job.currentMarket ? ` · ${job.currentMarket}` : ""}`;
    setLearningButtonsBusy(true);
    scheduleLearningPoll();
    return;
  }

  setLearningButtonsBusy(false);
  if (job.status === "failed") {
    els.learningState.textContent = "학습 실패";
    els.learningState.className = "critical";
    els.learningDetail.textContent = job.error || "학습 작업이 실패했습니다";
    return;
  }

  if (!model.trainedAt) {
    els.learningState.textContent = "대기";
    els.learningState.className = "waiting";
    els.learningDetail.textContent = "과거 학습 모델 없음";
    return;
  }

  els.learningState.textContent = overall.label || best.label || "학습 완료";
  els.learningState.className = "ok";
  const score = formatScore(overall.score || best.score);
  const candleCount = model.candleCount || "-";
  const errors = (model.errors || []).length;
  els.learningDetail.textContent = `${scopeLabel(model.scope)} · ${marketCount}개 코인 · ${candleCount}캔들 · 평균점수 ${score}${errors ? ` · 오류 ${errors}개` : ""}`;
}

function renderAllocation(payload) {
  const last = payload.last || {};
  const plan = last.plan || {};
  const selected = plan.selected || [];
  const orders =
    Array.isArray(plan.orders) && plan.orders.length
      ? plan.orders
      : Array.isArray(last.orders)
        ? last.orders
        : [];
  if (!payload.enabled) {
    els.allocationState.textContent = "꺼짐";
    els.allocationState.className = "waiting";
    els.allocationDetail.textContent = "DYNAMIC_ALLOCATION_ENABLED=false";
    return;
  }
  if (!plan.mode) {
    els.allocationState.textContent = "대기";
    els.allocationState.className = payload.due ? "ok" : "waiting";
    els.allocationDetail.textContent = payload.nextRunMessage || "동적 배분 기록 없음";
    return;
  }
  const top = selected[0];
  els.allocationState.textContent = `${plan.mode || "배분"} ${selected.length || 0}개`;
  els.allocationState.className = "ok";
  const topText = top ? `${top.market} ${top.label} 점수 ${formatScore(top.score)}` : "후보 없음";
  els.allocationDetail.textContent = `${topText} · 주문 ${orders.length}개 · ${payload.nextRunMessage || plan.message || ""}`;
}

function renderRealtimeDecision(payload) {
  latestRealtimeDecisionPayload = payload;
  renderRealtimeAnalysis(payload);
  const last = payload.last || payload || {};
  const plan = last.plan || {};
  renderInvestmentAgency(plan.investmentAgency || last.investmentAgency || payload.investmentAgency || {});
  const selected = plan.selected || [];
  const situations = plan.situations || [];
  const orders = last.orders || plan.orders || [];
  if (payload.enabled === false) {
    els.realtimeDecisionState.textContent = "꺼짐";
    els.realtimeDecisionState.className = "waiting";
    els.realtimeDecisionDetail.textContent = "REALTIME_DECISION_ENABLED=false";
    return;
  }
  if (!plan.mode) {
    els.realtimeDecisionState.textContent = "대기";
    els.realtimeDecisionState.className = "waiting";
    els.realtimeDecisionDetail.textContent = "순간 상황 판단 기록 없음";
    return;
  }
  const rankedSituations = sortAnalysisSituations(situations, selected, orders);
  const top = selected[0] || rankedSituations[0];
  const tags = top?.tags?.length ? top.tags.slice(0, 2).join("/") : top?.action || "감시";
  els.realtimeDecisionState.textContent = `${plan.mode} ${selected.length || 0}개`;
  els.realtimeDecisionState.className = orders.length ? "ok" : "waiting";
  const topText = top ? `${top.market} ${tags} 점수 ${formatScore(top.score)}` : "후보 없음";
  els.realtimeDecisionDetail.textContent = `${topText} · 주문 ${orders.length}개 · ${plan.evaluatedCount || 0}/${plan.universeCount || 0} 평가`;
}

function renderResidentSupervisor(status) {
  if (!els.residentState) return;
  const runtime = status.runtime || {};
  const realtime = status.realtime || {};
  const account = status.account || {};
  const pm = status.pm || {};
  const pmLast = pm.last || {};
  const markets = Array.isArray(status.markets) ? status.markets : [];
  const decisionPayload = status.realtimeDecision || {};
  const last = decisionPayload.last || {};
  const plan = last.plan || {};
  const selected = Array.isArray(plan.selected) ? plan.selected : [];
  const situations = Array.isArray(plan.situations) ? plan.situations : [];
  const planOrders = Array.isArray(plan.orders) ? plan.orders : [];
  const executedOrders = Array.isArray(last.orders) ? last.orders : [];
  const orders = executedOrders.length ? executedOrders : planOrders;
  const rankedSituations = sortAnalysisSituations(situations, selected, orders);
  const heldRows = markets.filter((row) => Number(row.positionValueKrw || 0) > 0);
  const evaluated = Number(plan.evaluatedCount || 0);
  const universe = Number(plan.universeCount || markets.length || 0);
  const coverageText = universe ? `${number.format(evaluated)}/${number.format(universe)}개` : "대기";
  const interval = Number(decisionPayload.intervalSeconds || status.settings?.realtimeDecisionIntervalSeconds || 0);
  const buyOrders = orders.filter((order) => residentOrderSide(order) === "buy");
  const sellOrders = orders.filter((order) => residentOrderSide(order) === "sell");

  const state = residentSupervisorState(runtime, realtime, decisionPayload, plan, orders);
  els.residentState.textContent = state.label;
  els.residentState.className = `resident-badge ${state.className}`;
  els.residentDetail.textContent = state.detail;
  renderResidentAiConnection(pm);
  els.residentCadence.textContent = interval ? `${interval}초` : "수동";
  els.residentCoverage.textContent = coverageText;
  els.residentDecision.textContent = residentDecisionText(selected, buyOrders, sellOrders, heldRows);
  els.residentExecution.textContent = residentExecutionText(status, account);
  els.residentPrimaryNarrative.textContent = pmLast.ok && pmLast.narrative
    ? pmLast.narrative
    : residentSupervisorNarrative({
    runtime,
    realtime,
    account,
    pm,
    plan,
    selected,
    rankedSituations,
    orders,
    heldRows,
    universe,
    evaluated,
  });
  renderResidentWatchList(rankedSituations, selected, orders, markets);
  renderResidentActionList({
    status,
    pm,
    plan,
    selected,
    rankedSituations,
    orders,
    buyOrders,
    sellOrders,
    heldRows,
    universe,
    evaluated,
  });
}

function renderResidentAiConnection(pm = {}) {
  if (!els.residentAiState) return;
  const last = pm.last || {};
  if (pm.connected) {
    els.residentAiState.textContent = last.state === "error" ? "호출 오류" : last.ok ? "모델 연결됨" : "모델 준비";
    els.residentAiDetail.textContent = last.updatedAt
      ? `${pm.model || "AI"} · ${formatTime(last.updatedAt)} 분석`
      : `${pm.model || "AI"} · 실제 호출 가능`;
    return;
  }
  if (pm.enabled && !pm.configured) {
    els.residentAiState.textContent = "API키 대기";
    els.residentAiDetail.textContent = "OPENAI_API_KEY 또는 AI_PM_API_KEY 필요";
    return;
  }
  els.residentAiState.textContent = "비활성";
  els.residentAiDetail.textContent = "AI_PM_ENABLED=false";
}

function renderPmChat(payload = {}) {
  if (!els.pmChatMessages) return;
  const messages = Array.isArray(payload.messages) ? payload.messages : [];
  if (els.pmChatModel) els.pmChatModel.textContent = payload.model || "-";
  if (els.pmChatState) {
    if (payload.connected) {
      els.pmChatState.textContent = payload.ok === false ? "모델 응답 확인 필요" : "모델 연결됨";
    } else if (payload.enabled && !payload.configured) {
      els.pmChatState.textContent = "API키 대기";
    } else {
      els.pmChatState.textContent = "AI PM 비활성";
    }
  }
  els.pmChatMessages.replaceChildren();
  if (!messages.length) {
    const empty = document.createElement("div");
    empty.className = "pm-chat-empty";
    empty.textContent = payload.connected
      ? "AI PM이 현재 프로그램 상태를 읽고 대기 중입니다."
      : "AI PM 대화 기록이 없습니다.";
    els.pmChatMessages.appendChild(empty);
    return;
  }
  messages.forEach((message) => {
    const row = document.createElement("div");
    const role = message.role === "user" ? "user" : "assistant";
    row.className = `pm-chat-message ${role}`;
    const meta = document.createElement("span");
    meta.className = "pm-chat-meta";
    meta.textContent = `${role === "user" ? "나" : "AI PM"} · ${formatTime(message.createdAt)}`;
    const body = document.createElement("span");
    body.textContent = message.content || "";
    row.append(meta, body);
    els.pmChatMessages.appendChild(row);
  });
  els.pmChatMessages.scrollTop = els.pmChatMessages.scrollHeight;
}

function renderPmScheduler(payload = {}) {
  if (!els.pmSchedulerCalendar) return;
  const target = payload.target || {};
  const state = payload.state || {};
  const live = payload.live || {};
  const pressure = payload.pressure || {};
  if (els.pmSchedulerState) {
    els.pmSchedulerState.textContent = `${state.label || "목표 페이스 계산"} · ${state.detail || ""}`.trim();
    els.pmSchedulerState.className = state.className || "";
  }
  if (els.pmSchedulerNarrative) els.pmSchedulerNarrative.textContent = payload.narrative || "";
  if (els.pmSchedulerDailyRate) {
    els.pmSchedulerDailyRate.textContent = `${formatSignedPercent2(Number(target.stretchDailyRequiredPct || target.dailyRequiredPct || 0))}%`;
  }
  if (els.pmSchedulerHourlyRate) {
    els.pmSchedulerHourlyRate.textContent = `${formatSignedPercent2(Number(target.hourlyRecoveryPct || 0))}%`;
  }
  if (els.pmSchedulerGap) {
    els.pmSchedulerGap.textContent = `${formatCompactKrw(target.gapKrw)}원`;
  }
  if (els.pmSchedulerLive) {
    els.pmSchedulerLive.textContent = live.armed && live.webArmed ? "실거래 관리 가능" : live.keyConfigured ? "키 연결·주문 잠금" : "키 대기";
  }
  if (els.pmSchedulerEngine) {
    const deploy = Number(pressure.deployMultiplier || 1);
    const entry = Number(pressure.entryScoreAdjustment || 0);
    els.pmSchedulerEngine.textContent = pressure.engineApplied
      ? `${pressure.label || "반영 중"} · 진입 ${entry.toFixed(2)} · 투입 x${deploy.toFixed(2)}`
      : "화면 계산만";
  }
  renderPmSchedulerCalendar(payload.days || []);
  renderPmSchedulerHours(payload.hours || []);
  renderPmSchedulerFallback(payload.fallback || []);
}

function renderPmSchedulerCalendar(days) {
  els.pmSchedulerCalendar.replaceChildren();
  if (!days.length) {
    const empty = document.createElement("div");
    empty.className = "pm-scheduler-empty";
    empty.textContent = "스케줄 데이터가 없습니다.";
    els.pmSchedulerCalendar.appendChild(empty);
    return;
  }
  days.forEach((day) => {
    const card = document.createElement("article");
    card.className = `pm-day-card ${day.status === "today" ? "today" : ""}`;
    card.innerHTML = `
      <div class="pm-day-top">
        <strong>D+${number.format(Number(day.day || 0))}</strong>
        <span>${formatMonthDay(day.date)}</span>
      </div>
      <div class="pm-day-stage">${escapeHtml(day.stage || "")}</div>
      <div class="pm-day-target">${formatCompactKrw(day.stretchTargetKrw)}원</div>
      <div class="pm-day-brief">${escapeHtml(day.pmBrief || "")}</div>
      <div class="pm-day-rule">${escapeHtml(day.fallbackRule || "")}</div>
    `;
    els.pmSchedulerCalendar.appendChild(card);
  });
}

function renderPmSchedulerHours(hours) {
  els.pmSchedulerHours.replaceChildren();
  if (!hours.length) {
    const empty = document.createElement("div");
    empty.className = "pm-scheduler-empty";
    empty.textContent = "시간별 실행판이 없습니다.";
    els.pmSchedulerHours.appendChild(empty);
    return;
  }
  hours.forEach((slot) => {
    const card = document.createElement("div");
    card.className = "pm-hour-card";
    card.innerHTML = `
      <strong>${formatTime(slot.time)} · 목표 ${formatCompactKrw(slot.requiredEquityKrw)}원</strong>
      <small>${escapeHtml(slot.focus || "")}</small>
      <small>트리거: ${escapeHtml(slot.trigger || "")}</small>
      <small>백업: ${escapeHtml(slot.fallbackRule || "")}</small>
    `;
    els.pmSchedulerHours.appendChild(card);
  });
}

function renderPmSchedulerFallback(items) {
  els.pmSchedulerFallback.replaceChildren();
  if (!items.length) {
    const item = document.createElement("li");
    item.textContent = "PM 장애 대비 알고리즘이 없습니다.";
    els.pmSchedulerFallback.appendChild(item);
    return;
  }
  items.forEach((entry) => {
    const item = document.createElement("li");
    item.innerHTML = `<strong>${escapeHtml(entry.title || "")}</strong><br>${escapeHtml(entry.body || "")}`;
    els.pmSchedulerFallback.appendChild(item);
  });
}

function renderMarketIntel(payload = {}) {
  if (!els.intelCoinList) return;
  const sources = Array.isArray(payload.sources) ? payload.sources : [];
  const items = Array.isArray(payload.items) ? payload.items : [];
  const trending = Array.isArray(payload.trending) ? payload.trending : [];
  const coinAnalyses = Array.isArray(payload.coinAnalyses) ? payload.coinAnalyses : [];
  const global = payload.global || {};
  const monitor = payload.monitor || {};
  const running = monitor.running ? "자동 수집 중" : "자동 대기";

  if (els.intelState) {
    els.intelState.textContent = payload.ok ? running : "수집 대기";
    els.intelState.className = `analysis-badge ${payload.ok ? "ok" : "waiting"}`;
  }
  if (els.intelUpdatedAt) els.intelUpdatedAt.textContent = payload.updatedAt ? `${formatTime(payload.updatedAt)} 갱신` : "갱신 대기";
  if (els.intelNarrative) els.intelNarrative.textContent = payload.summary || "시장정보 수집 대기 중입니다.";
  if (els.intelNextRun) {
    els.intelNextRun.textContent = payload.nextRunAt
      ? `${formatTime(payload.nextRunAt)} 다음`
      : `${Math.round(Number(payload.intervalSeconds || 21600) / 3600)}시간 자동`;
  }
  if (els.intelSourceCount) {
    const okCount = sources.filter((source) => source.ok).length;
    els.intelSourceCount.textContent = `${okCount}/${sources.length || 0}`;
  }
  if (els.intelItemCount) els.intelItemCount.textContent = `${number.format(items.length)}건`;
  if (els.intelGlobalState) {
    const fear = global.fearGreedValue ? `F&G ${global.fearGreedValue}` : "F&G -";
    const cap = global.marketCapChange24hPct !== undefined ? `${formatSignedPercent2(Number(global.marketCapChange24hPct))}%` : "-";
    els.intelGlobalState.textContent = `${fear} · 시총 ${cap}`;
  }
  renderIntelCoinList(coinAnalyses);
  renderIntelTrendingList(trending);
  renderIntelNewsList(items);
  renderIntelSourceList(sources, payload.errors || []);
}

function renderIntelCoinList(rows) {
  els.intelCoinList.replaceChildren();
  if (!rows.length) {
    const empty = document.createElement("div");
    empty.className = "intel-empty";
    empty.textContent = "코인별 정보 분석 결과가 없습니다.";
    els.intelCoinList.appendChild(empty);
    return;
  }
  rows.slice(0, 12).forEach((row) => {
    const card = document.createElement("article");
    card.className = "intel-coin-card";
    const reasons = Array.isArray(row.reasons) ? row.reasons.slice(0, 5) : [];
    card.innerHTML = `
      <div class="intel-coin-top">
        <div>
          <strong>${escapeHtml(row.label || row.market || "-")}</strong>
          <p>${escapeHtml(row.headline || "")}</p>
        </div>
        <span class="intel-signal ${escapeHtml(row.signal || "watch")}">${intelSignalLabel(row.signal)} · ${formatScore(row.impactScore)}</span>
      </div>
      <div class="intel-reason-list">
        ${reasons.map((reason) => `<span>${escapeHtml(reason)}</span>`).join("") || "<span>시장동향</span>"}
      </div>
    `;
    els.intelCoinList.appendChild(card);
  });
}

function renderIntelTrendingList(rows) {
  els.intelTrendingList.replaceChildren();
  if (!rows.length) {
    const empty = document.createElement("span");
    empty.className = "intel-empty";
    empty.textContent = "트렌딩 대기";
    els.intelTrendingList.appendChild(empty);
    return;
  }
  rows.slice(0, 10).forEach((row) => {
    const link = document.createElement(row.url ? "a" : "span");
    if (row.url) link.href = row.url;
    if (row.url) link.target = "_blank";
    link.textContent = `${row.rank}. ${row.symbol || row.name}`;
    els.intelTrendingList.appendChild(link);
  });
}

function renderIntelNewsList(items) {
  els.intelNewsList.replaceChildren();
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "intel-empty";
    empty.textContent = "뉴스 수집 대기";
    els.intelNewsList.appendChild(empty);
    return;
  }
  items.slice(0, 8).forEach((item) => {
    const card = document.createElement("article");
    card.className = "intel-news-card";
    const title = escapeHtml(item.title || "");
    const source = escapeHtml(item.source || "");
    const sentiment = intelSignalLabel(item.sentiment);
    card.innerHTML = `
      <strong>${item.url ? `<a href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">${title}</a>` : title}</strong>
      <small>${source} · ${formatTime(item.publishedAt)} · ${sentiment} · ${formatScore(item.impactScore)}</small>
    `;
    els.intelNewsList.appendChild(card);
  });
}

function renderIntelSourceList(sources, errors) {
  els.intelSourceList.replaceChildren();
  if (!sources.length) {
    const empty = document.createElement("div");
    empty.className = "intel-empty";
    empty.textContent = "소스 점검 대기";
    els.intelSourceList.appendChild(empty);
    return;
  }
  sources.forEach((source) => {
    const row = document.createElement("div");
    row.className = "intel-source-row";
    row.textContent = `${source.ok ? "정상" : "오류"} · ${source.name || source.id} · ${source.kind || ""}`;
    els.intelSourceList.appendChild(row);
  });
  if (Array.isArray(errors) && errors.length) {
    const row = document.createElement("div");
    row.className = "intel-source-row";
    row.textContent = `최근 오류 ${errors.length}건: ${errors[0]}`;
    els.intelSourceList.appendChild(row);
  }
}

function intelSignalLabel(value) {
  if (value === "favorable" || value === "positive") return "호재";
  if (value === "adverse" || value === "negative") return "악재";
  return "관찰";
}

function residentSupervisorState(runtime, realtime, decisionPayload, plan, orders) {
  if (runtime.emergencyStopped) {
    return {
      label: "긴급정지",
      className: "critical",
      detail: "주문 실행이 차단되어 관제만 가능합니다.",
    };
  }
  if (decisionPayload.enabled === false) {
    return {
      label: "관제 꺼짐",
      className: "waiting",
      detail: "REALTIME_DECISION_ENABLED=false 상태입니다.",
    };
  }
  if (orders.length) {
    return {
      label: "개입 후보",
      className: "ok",
      detail: `주문 후보 ${orders.length}개를 검토 중입니다.`,
    };
  }
  if (plan.mode) {
    return {
      label: "상주 분석 중",
      className: realtime.connected ? "ok" : "warning",
      detail: realtime.connected ? "실시간 시세와 판단 기록이 연결되어 있습니다." : "REST 분석은 가능하지만 실시간 스트림 확인이 필요합니다.",
    };
  }
  return {
    label: "상주 대기",
    className: "waiting",
    detail: "첫 실시간 판단 기록을 기다리는 중입니다.",
  };
}

function residentDecisionText(selected, buyOrders, sellOrders, heldRows) {
  if (sellOrders.length) return `청산 후보 ${sellOrders.length}개`;
  if (buyOrders.length) return `진입 실행 후보 ${buyOrders.length}개`;
  if (selected.length) return `진입 후보 ${selected.length}개`;
  if (heldRows.length) return `보유 감시 ${heldRows.length}개`;
  return "현금 대기";
}

function residentExecutionText(status, account) {
  if (status.runtime?.emergencyStopped) return "긴급정지";
  if (status.live?.armed || status.runtime?.liveTradingEnabled) return "실거래 잠금 확인";
  return `페이퍼 ${formatKrw(account.equityKrw)}원`;
}

function residentSupervisorNarrative(context) {
  const { runtime, realtime, account, plan, selected, rankedSituations, orders, heldRows, universe, evaluated } = context;
  if (runtime.emergencyStopped) {
    return "긴급정지 상태입니다. 분석은 계속 읽을 수 있지만 자동 주문 실행은 차단되어 있습니다.";
  }
  if (!plan.mode) {
    return "상주 관제자가 아직 첫 판단 기록을 기다리고 있습니다. 기록이 들어오면 전체 시장, 보유 위험, 진입 후보, 주문 가능성을 한 문장으로 계속 요약합니다.";
  }
  if (isFuturesAnalysisPlan(plan)) {
    const top = selected[0] || rankedSituations[0] || null;
    const topText = top ? `${displayMarketCode(top.market)} 점수 ${formatScore(top.score)}` : "뚜렷한 상위 후보 없음";
    const orderText = orders.length ? `선물 액션 ${orders.length}개` : "선물 액션 없이 감시";
    const paper = latestStatus?.binanceFuturesPaper || {};
    const equityText = paper.equityUsdt !== undefined ? `총자산 ${formatMoneyValue(paper.equityUsdt, "USDT")}` : "총자산 확인 중";
    return `바이낸스 USD-M 선물 모의 기준으로 ${evaluated}/${universe}개 후보를 읽고 있습니다. 현재 핵심 판단은 ${topText}, ${orderText}이며 ${equityText} 기준으로 숏 진입 또는 청산 조건을 기다립니다.`;
  }
  const top = selected[0] || rankedSituations[0] || null;
  const topText = top ? `${displayMarketCode(top.market)} 점수 ${formatScore(top.score)}` : "뚜렷한 상위 후보 없음";
  const streamText = realtime.connected ? "실시간 스트림 연결" : "실시간 스트림 확인 필요";
  const orderText = orders.length ? `주문 후보 ${orders.length}개` : "주문 없이 관망";
  const cashText = `현금 ${formatKrw(account.cashKrw)}원, 보유 ${heldRows.length}개`;
  return `${streamText} 상태에서 ${evaluated}/${universe}개 후보를 읽고 있습니다. 현재 핵심 판단은 ${topText}, ${orderText}이며 ${cashText} 기준으로 다음 진입 또는 청산 조건을 기다립니다.`;
}

function renderResidentWatchList(situations, selected, orders, markets) {
  if (!els.residentWatchList) return;
  const selectedMarkets = new Set((selected || []).map((item) => item.market));
  const orderMarkets = new Set((orders || []).map((item) => item.market).filter(Boolean));
  const marketRows = new Map((markets || []).map((row) => [row.market, row]));
  const topRows = (situations || []).slice(0, 5);
  if (!topRows.length) {
    els.residentWatchList.replaceChildren(residentEmptyNode("감시 후보가 아직 없습니다. 다음 실시간 판단 결과를 기다립니다."));
    return;
  }
  els.residentWatchList.replaceChildren(
    ...topRows.map((item) => {
      const row = marketRows.get(item.market);
      const hasOrder = orderMarkets.has(item.market);
      const action = selectedMarkets.has(item.market) ? "buy" : item.action || "watch";
      const actionTone = actionClass(action);
      const node = document.createElement("div");
      node.className = `resident-watch-row ${actionTone}`;
      node.innerHTML = `
        <div>
          <strong>${escapeHtml(row ? marketLabel(row) : displayMarketCode(item.market))}</strong>
          <small>${escapeHtml(displayMarketCode(item.market))} · ${escapeHtml(compactSituationReason(item))}</small>
        </div>
        <em>${escapeHtml(analysisActionLabel(action, hasOrder))} ${escapeHtml(formatScore(item.score))}</em>
      `;
      return node;
    }),
  );
}

function renderResidentActionList(context) {
  if (!els.residentActionList) return;
  const { status, pm, plan, selected, rankedSituations, orders, buyOrders, sellOrders, heldRows, universe, evaluated } = context;
  const notes = [];
  const pmActions = Array.isArray(pm?.last?.actions) ? pm.last.actions.filter(Boolean) : [];
  if (pm?.last?.ok && pmActions.length) {
    notes.push(...pmActions.slice(0, 2));
  }
  if (status.runtime?.emergencyStopped) {
    notes.push("긴급정지 상태라 주문 실행보다 원인 확인과 재개 판단이 우선입니다.");
  } else if (!status.live?.armed && !status.runtime?.liveTradingEnabled) {
    notes.push("실거래 잠금은 닫혀 있고 현재 판단은 페이퍼 상태에만 반영됩니다.");
  } else {
    notes.push("실거래 잠금 상태를 먼저 확인하고, 주문 전 호가/슬리피지 보호를 반드시 통과해야 합니다.");
  }
  if (plan.mode) {
    notes.push(`전체 후보 ${universe}개 중 ${evaluated}개를 평가했고, 판단 모드는 ${plan.mode}입니다.`);
  } else {
    notes.push("아직 판단 모드가 없으므로 다음 실시간 분석 사이클을 기다립니다.");
  }
  if (sellOrders.length) {
    notes.push(`청산 후보 ${sellOrders.length}개가 있어 신규 진입보다 위험 축소가 우선입니다.`);
  } else if (buyOrders.length || selected.length) {
    notes.push(`진입 후보 ${buyOrders.length || selected.length}개가 있으므로 현금, 최소 주문금액, 기존 보유 종목 교체 가치를 함께 확인합니다.`);
  } else if (heldRows.length) {
    notes.push(`보유 종목 ${heldRows.length}개는 목표가, 손절가, 추세 훼손 여부를 계속 감시합니다.`);
  } else {
    notes.push("현재 보유 종목이 없으므로 성급히 진입하지 않고 상위 후보가 기준을 넘을 때까지 현금 대기합니다.");
  }
  const top = rankedSituations[0];
  if (top) {
    notes.push(`최상위 감시 종목은 ${displayMarketCode(top.market)}이며 핵심 근거는 ${compactSituationReason(top)}입니다.`);
  }
  if (!orders.length) {
    notes.push("주문 후보가 없다는 뜻은 분석 중단이 아니라, 조건 미충족으로 실행을 보류한다는 의미입니다.");
  }
  els.residentActionList.replaceChildren(
    ...notes.slice(0, 5).map((text) => {
      const item = document.createElement("li");
      item.textContent = text;
      return item;
    }),
  );
}

function residentOrderSide(order) {
  const side = String(order?.side || order?.intent?.side || "").toLowerCase();
  if (side.includes("short")) return "sell";
  if (side.includes("cover")) return "buy";
  if (side.includes("ask") || side.includes("sell") || side.includes("매도")) return "sell";
  if (side.includes("bid") || side.includes("buy") || side.includes("매수")) return "buy";
  return "";
}

function residentEmptyNode(message) {
  const node = document.createElement("div");
  node.className = "resident-empty";
  node.textContent = message;
  return node;
}

function renderRealtimeAnalysis(payload) {
  if (!els.analysisCandidateList) return;
  const last = payload?.last || payload || {};
  const plan = last.plan || {};
  const selected = Array.isArray(plan.selected) ? plan.selected : [];
  const situations = Array.isArray(plan.situations) ? plan.situations : [];
  const orders =
    Array.isArray(plan.orders) && plan.orders.length
      ? plan.orders
      : Array.isArray(last.orders)
        ? last.orders
        : [];
  const rankedSituations = sortAnalysisSituations(situations, selected, orders);
  const evaluated = Number(plan.evaluatedCount || 0);
  const universe = Number(plan.universeCount || 0);
  const coveragePct = universe > 0 ? Math.min(100, Math.max(0, (evaluated / universe) * 100)) : 0;
  const top = selected[0] || rankedSituations[0] || null;
  const mode = plan.mode || (payload?.enabled === false ? "꺼짐" : "대기");
  const modeClass = payload?.enabled === false ? "waiting" : orders.length ? "ok" : plan.mode ? "warning" : "waiting";
  const futuresAnalysis = isFuturesAnalysisPlan(plan);

  setAnalysisBadge(els.analysisMode, mode, modeClass);
  setAnalysisBadge(els.analysisCoverage, `${evaluated}/${universe} 평가`, coveragePct >= 90 ? "ok" : plan.mode ? "warning" : "waiting");
  setAnalysisBadge(els.analysisUpdatedAt, analysisTimestampLabel(last, payload), "waiting");
  if (els.analysisScanProgress) els.analysisScanProgress.style.width = `${coveragePct}%`;
  if (els.analysisUniverse) {
    const monitorCount = futuresAnalysis ? 0 : latestStatus?.markets?.length || 0;
    els.analysisUniverse.textContent =
      universe && monitorCount && monitorCount !== universe
        ? `${number.format(universe)} / ${number.format(monitorCount)}`
        : universe
          ? `${number.format(universe)}개`
          : "-";
  }
  if (els.analysisSelected) els.analysisSelected.textContent = `${number.format(selected.length)}개`;
  if (els.analysisOrders) els.analysisOrders.textContent = `${number.format(orders.length)}개`;
  if (els.analysisTopScore) els.analysisTopScore.textContent = top ? formatScore(top.score) : "-";
  if (els.analysisRegime) els.analysisRegime.textContent = marketRegimeLabel(plan.marketRegime || top?.marketRegime);
  if (els.analysisNarrative) els.analysisNarrative.textContent = realtimeAnalysisNarrative(plan, selected, rankedSituations, orders, payload);
  renderAnalysisReasons(plan, selected, rankedSituations, orders, payload);
  renderAnalysisCandidates(rankedSituations, selected, orders);
}

function renderRealtimeAnalysisLoading(message) {
  if (!els.analysisCandidateList) return;
  setAnalysisBadge(els.analysisMode, "분석 중", "warning");
  setAnalysisBadge(els.analysisCoverage, "재계산", "warning");
  setAnalysisBadge(els.analysisUpdatedAt, "방금 요청", "waiting");
  if (els.analysisNarrative) els.analysisNarrative.textContent = message;
  if (els.analysisRegime) els.analysisRegime.textContent = "실시간 후보 재평가";
  if (els.analysisScanProgress) els.analysisScanProgress.style.width = "42%";
  if (els.analysisUniverse) els.analysisUniverse.textContent = latestStatus?.markets?.length ? `${latestStatus.markets.length}개+` : "-";
  if (els.analysisSelected) els.analysisSelected.textContent = "계산 중";
  if (els.analysisOrders) els.analysisOrders.textContent = "계산 중";
  if (els.analysisTopScore) els.analysisTopScore.textContent = "-";
  els.analysisReasonList?.replaceChildren(
    ...[
      "가격 변화율, 거래대금, 단기 추세, 보유 수익률을 동시에 갱신합니다.",
      "추천 코인은 우선순위 힌트로만 쓰고, 추천이 비어 있어도 전체 후보를 계속 비교합니다.",
      "더 강한 후보가 나오면 기존 보유 종목의 약화 여부까지 같이 확인합니다.",
    ].map((text) => {
      const item = document.createElement("li");
      item.textContent = text;
      return item;
    }),
  );
  els.analysisCandidateList.replaceChildren(analysisEmpty("실시간 판단을 다시 만들고 있습니다. 결과가 도착하면 후보별 근거가 갱신됩니다."));
}

function renderRealtimeAnalysisError(message) {
  if (!els.analysisCandidateList) return;
  setAnalysisBadge(els.analysisMode, "확인 실패", "critical");
  setAnalysisBadge(els.analysisCoverage, "연결 확인", "critical");
  if (els.analysisNarrative) els.analysisNarrative.textContent = message;
  els.analysisCandidateList.replaceChildren(analysisEmpty("실시간 분석 상태를 불러오지 못했습니다. 다음 갱신 때 다시 확인합니다."));
}

function renderAnalysisReasons(plan, selected, situations, orders, payload) {
  if (!els.analysisReasonList) return;
  const top = selected[0] || situations[0] || null;
  const reasons = [];
  if (isFuturesAnalysisPlan(plan)) {
    reasons.push(`바이낸스 USD-M 선물 ${plan.universeCount || 0}개 심볼 중 ${plan.evaluatedCount || 0}개를 평가했고, 상위 ${situations.length || 0}개를 투자 가능성 순서로 정리했습니다.`);
    reasons.push(`전체 심볼은 24시간 티커로 빠짐없이 스크리닝하고, 상위 ${plan.deepAnalysisCount || 0}개는 1분봉 캔들까지 정밀 계산합니다.`);
    reasons.push(`현재 레짐은 ${plan.marketRegime?.label || "확인 중"}이며 허용 방향은 ${plan.tradeSide || "FLAT"}입니다. 방향 우위가 없으면 신규 진입을 막습니다.`);
    if (top) {
      reasons.push(`${displayMarketCode(top.market)}이 현재 최상위 ${top.side || ""} 후보입니다. ${compactSituationReason(top)}`);
    }
    if (selected.length) {
      reasons.push(`숏 진입 후보 ${selected.length}개가 기준선을 통과했습니다. 가용 증거금, 보유 ROE, 청산/손절 위험을 함께 보며 실행합니다.`);
    } else {
      reasons.push("숏 기준을 넘은 후보가 없으면 주문을 만들지 않고 감시합니다. 이때도 바이낸스 선물 후보 비교는 계속됩니다.");
    }
    if (orders.length) {
      reasons.push(`직전 선물 액션 ${orders.length}개가 발생했습니다. OPEN/INCREASE는 숏 노출 확대, CLOSE는 숏 청산으로 표시됩니다.`);
    } else {
      reasons.push("직전 선물 액션은 없습니다. 다음 루프에서 더 강한 하락 후보나 보유 포지션의 목표/손절 조건을 다시 계산합니다.");
    }
    els.analysisReasonList.replaceChildren(
      ...reasons.slice(0, 6).map((text) => {
        const item = document.createElement("li");
        item.textContent = text;
        return item;
      }),
    );
    return;
  }
  if (plan.mode) {
    reasons.push(`${plan.universeCount || 0}개 후보 중 ${plan.evaluatedCount || 0}개를 평가했고, 상위 ${situations.length || 0}개 상황을 설명 대상으로 정리했습니다.`);
  } else if (payload?.enabled === false) {
    reasons.push("실시간 판단 기능이 꺼져 있어 현재는 자동 분석 기록을 만들지 않습니다.");
  } else {
    reasons.push("아직 실시간 판단 기록이 없습니다. 미리보기 또는 다음 자동 판단 때 후보 설명이 채워집니다.");
  }
  if (top) {
    reasons.push(`${displayMarketCode(top.market)}이 현재 최상위 후보입니다. ${compactSituationReason(top)}`);
  }
  if (selected.length) {
    reasons.push(`진입 후보 ${selected.length}개가 기준선을 통과했습니다. 주문 가능 현금과 보유 위험을 함께 보며 실제 주문 여부를 결정합니다.`);
  } else {
    reasons.push("진입 기준을 넘은 후보가 없으면 주문을 만들지 않고 감시를 유지합니다. 이때도 전체 후보 비교는 계속됩니다.");
  }
  if (orders.length) {
    reasons.push(`주문 후보 ${orders.length}개가 만들어졌습니다. 자동 실행 상태와 최소 주문금액, 리스크 제한을 통과해야 실제 반영됩니다.`);
  } else {
    reasons.push("현재 주문은 없습니다. 더 좋은 후보가 발견되면 약한 보유 종목을 줄이고 새 후보로 교체할 수 있는지 다시 계산합니다.");
  }
  reasons.push("추천 코인은 우선 검토 대상으로 올릴 뿐입니다. 추천 목록이 비어 있어도 포트폴리오 구성은 전체 KRW 후보에서 계속 탐색합니다.");
  els.analysisReasonList.replaceChildren(
    ...reasons.slice(0, 5).map((text) => {
      const item = document.createElement("li");
      item.textContent = text;
      return item;
    }),
  );
}

function renderAnalysisCandidates(situations, selected, orders) {
  if (!els.analysisCandidateList) return;
  const selectedMarkets = new Set(selected.map((item) => item.market));
  const orderedMarkets = new Set(orders.map((item) => item.market).filter(Boolean));
  const marketRows = new Map((latestStatus?.markets || []).map((row) => [row.market, row]));
  const candidates = Array.isArray(situations) ? situations : [];
  if (!candidates.length) {
    els.analysisCandidateList.replaceChildren(analysisEmpty("분석 후보가 아직 없습니다. 다음 실시간 판단 결과를 기다리는 중입니다."));
    return;
  }
  els.analysisCandidateList.dataset.count = String(candidates.length);
  els.analysisCandidateList.replaceChildren(
    ...candidates.map((item, index) => {
      const row = marketRows.get(item.market);
      const card = document.createElement("article");
      const isSelected = selectedMarkets.has(item.market);
      const hasOrder = orderedMarkets.has(item.market);
      const action = item.action || (isSelected ? "buy" : "watch");
      const actionTone = actionClass(action);
      const score = Number(item.score || 0);
      const pct = Math.min(100, Math.max(5, score * 100));
      const thesis = candidateInvestmentThesis(item, row, isSelected, hasOrder);
      const metrics = candidateMetricChips(item, row);
      card.className = `analysis-candidate ${actionTone}`;
      card.dataset.market = item.market || "";
      card.dataset.action = actionTone;
      card.innerHTML = `
        <div class="analysis-candidate-head">
          <div>
            <strong>${escapeHtml(row ? marketLabel(row) : displayMarketCode(item.market))}</strong>
            <small>${escapeHtml(displayMarketCode(item.market))} · 투자 가능성 ${index + 1}/${candidates.length} · 현재가 ${formatPrice(item.currentPrice || row?.price || 0)}</small>
          </div>
          <span class="analysis-action ${escapeHtml(actionTone)}">${escapeHtml(analysisActionLabel(action, hasOrder))}</span>
        </div>
        <div class="analysis-score-row">
          <div class="analysis-score-bar"><span style="width:${pct}%"></span></div>
          <em>${formatScore(score)}</em>
        </div>
        <div class="analysis-thesis">
          <strong>${escapeHtml(thesis.title)}</strong>
          <p>${escapeHtml(thesis.body)}</p>
        </div>
        ${metrics ? `<div class="analysis-candidate-metrics">${metrics}</div>` : ""}
        <p class="analysis-candidate-detail">${escapeHtml(candidateExplanation(item, row))}</p>
      `;
      return card;
    }),
  );
}

function sortAnalysisSituations(situations, selected, orders) {
  const selectedMarkets = new Set((selected || []).map((item) => item.market));
  const ordersByMarket = new Map((orders || []).map((item) => [item.market, item]));
  return [...(Array.isArray(situations) ? situations : [])].sort((a, b) => {
    const priorityDiff =
      investmentPriorityScore(b, selectedMarkets, ordersByMarket) -
      investmentPriorityScore(a, selectedMarkets, ordersByMarket);
    if (priorityDiff !== 0) return priorityDiff;
    return Number(b.score || 0) - Number(a.score || 0);
  });
}

function investmentPriorityScore(item, selectedMarkets, ordersByMarket) {
  const score = Number(item?.score || 0);
  let priority = Number.isFinite(score) ? score : 0;
  const market = item?.market || "";
  const order = ordersByMarket.get(market);
  const side = String(order?.side || order?.intent?.side || "").toLowerCase();
  const rawAction = String(item?.action || "").toLowerCase();
  const hasBuyOrder = Boolean(order) && (side.includes("bid") || side.includes("buy") || side.includes("매수"));
  const hasShortOrder = Boolean(order) && side.includes("short");
  const hasSellOrder = Boolean(order) && (side.includes("ask") || side.includes("sell") || side.includes("매도"));
  const isSelected = selectedMarkets.has(market);
  const action = actionClass(item?.action || (isSelected ? "buy" : "watch"));
  const riskText = String(item?.riskReason || "").toLowerCase();
  const regimeText = String(item?.marketRegime || "").toLowerCase();
  const tags = Array.isArray(item?.tags) ? item.tags.map((tag) => String(tag).toLowerCase()) : [];
  const heldValue = Number(item?.currentValueKrw || 0);

  if (hasBuyOrder || hasShortOrder) priority += 10000;
  else if (isSelected) priority += 9000;
  else if (action === "buy" || rawAction.includes("short")) priority += 8000;
  else if (action === "hold" && heldValue > 0) priority += 2500;
  else if (action === "hold" || action === "watch") priority += 1000;
  else if (hasSellOrder || action === "sell") priority -= 3000;
  else if (action === "avoid") priority -= 6000;

  if (riskText.includes("liquidity below guard")) priority -= 250;
  if (riskText.includes("overheated")) priority -= 200;
  if (riskText.includes("sell pressure dominates")) priority -= 150;
  if (regimeText.includes("risk-off") || regimeText.includes("weak")) priority -= 350;
  if (tags.some((tag) => tag.includes("market-risk-off"))) priority -= 250;
  if (tags.some((tag) => tag.includes("손절선 도달"))) priority -= 1200;
  if (tags.some((tag) => tag.includes("목표가 도달"))) priority -= 900;
  return priority;
}

function realtimeAnalysisNarrative(plan, selected, situations, orders, payload) {
  if (payload?.enabled === false) return "실시간 판단 기능이 꺼져 있습니다. 기능을 켜면 전체 KRW 후보를 주기적으로 다시 평가합니다.";
  if (!plan.mode) return "실시간 판단 기록을 기다리고 있습니다. 기록이 생기면 어떤 코인을 왜 보고 있는지 설명 중심으로 표시합니다.";
  if (isFuturesAnalysisPlan(plan)) {
    const evaluated = `${plan.evaluatedCount || 0}/${plan.universeCount || 0}`;
    const top = selected[0] || situations[0];
    const topText = top ? `${displayMarketCode(top.market)} 점수 ${formatScore(top.score)}` : "뚜렷한 상위 후보 없음";
    const orderText = orders.length ? `${orders.length}개 선물 액션` : "주문 없이 감시";
    const analysisSideText = plan.analysisSide && plan.analysisSide !== "FLAT" ? plan.analysisSide : "FLAT";
    const executionSideText = plan.executionSide || plan.tradeSide || "FLAT";
    const sideText =
      analysisSideText !== "FLAT" && executionSideText !== "FLAT"
        ? `분석은 ${analysisSideText}, 실제 베팅은 ${executionSideText}`
        : "분석 우위가 확인될 때만 반대 베팅";
    const depthText = plan.deepAnalysisCount
      ? ` 상위 ${plan.deepAnalysisCount}개와 보유 포지션은 1분봉 정밀 분석까지 반영했습니다.`
      : " 전체 심볼은 24시간 티커로 전수 스크리닝 중입니다.";
    const regime = plan.marketRegime?.reason ? ` 시장 배경은 ${humanAnalysisText(plan.marketRegime.reason)}입니다.` : "";
    const block = plan.entryBlockReason ? ` 신규 진입 차단 사유는 ${humanAnalysisText(plan.entryBlockReason)}입니다.` : "";
    return `바이낸스 USD-M 선물 ${evaluated}개 심볼을 분석 결과는 그대로 두고 실행만 반대로 거는 ${plan.leverage || "-"}x 기준으로 비교했습니다. ${sideText}입니다.${depthText} 현재 최상위는 ${topText}이고, 결과는 ${orderText}입니다.${regime}${block} 업비트 KRW가 아니라 선택된 바이낸스 선물 모의 모드의 후보를 보고 있습니다.`;
  }
  const monitorCount = latestStatus?.markets?.length || 0;
  const evaluated = `${plan.evaluatedCount || 0}/${plan.universeCount || 0}`;
  const scopeText = monitorCount && monitorCount !== Number(plan.universeCount || 0) ? `전체 모니터 ${monitorCount}개 중 ` : "";
  const top = selected[0] || situations[0];
  const topText = top ? `${displayMarketCode(top.market)} 점수 ${formatScore(top.score)}` : "뚜렷한 상위 후보 없음";
  const orderText = orders.length ? `${orders.length}개 주문 후보` : "주문 없이 감시";
  const regime = plan.marketRegime?.reason ? ` 시장 배경은 ${humanAnalysisText(plan.marketRegime.reason)}입니다.` : "";
  return `${scopeText}${evaluated}개 후보를 실시간으로 비교했습니다. 현재 최상위는 ${topText}이고, 결과는 ${orderText}입니다.${regime} 추천 여부와 별개로 전체 후보를 계속 비교합니다.`;
}

function candidateExplanation(item, row) {
  if (item.exchangeMode === "binance_futures_paper" || item.currency === "USDT") {
    const parts = [];
    const depth = String(item.analysisDepth || "");
    const tickerOnly = depth === "ticker_24h";
    const trend5m = tickerOnly ? "" : optionalPercentPart("5분", item.trend5mPct ?? item.momentum5mPct);
    const trend15m = tickerOnly ? "" : optionalPercentPart("15분", item.momentum15mPct);
    const day = optionalPercentPart("24시간", item.priceChange24hPct);
    if (trend5m || trend15m) parts.push([trend5m, trend15m].filter(Boolean).join(", "));
    if (day) parts.push(day);
    if (Number(item.range24hPct || 0) > 0) parts.push(`24h 변동폭 ${formatSignedPercent2(Number(item.range24hPct))}%`);
    if (Number(item.quoteVolumeUsdt || 0) > 0) parts.push(`24h 거래대금 ${formatCompactUsdt(item.quoteVolumeUsdt)}`);
    if (item.volumeRatio !== undefined && item.volumeRatio !== null) parts.push(`거래량 ${Number(item.volumeRatio).toFixed(2)}배`);
    const analysisSide = item.analysisSide || item.side;
    const executionSide = item.executionSide || item.side;
    if (analysisSide && executionSide && analysisSide !== executionSide) {
      parts.push(`분석 ${analysisSide} -> 베팅 ${executionSide} ${item.leverage || "-"}x`);
    } else if (item.side) {
      parts.push(`${item.side} ${item.leverage || "-"}x`);
    }
    const exposure = Number(item.currentValueUsdt || item.currentValueKrw || 0);
    if (exposure > 0) parts.push(`노출 ${formatMoneyValue(exposure, "USDT")}`);
    const roe = Number(item.returnOnMarginPct || item.returnPct || 0);
    if (exposure > 0) parts.push(`ROE ${formatSignedPercent2(roe)}%`);
    const base = compactSituationReason(item);
    const depthText = tickerOnly ? "전체 심볼 24시간 티커 스크리닝" : "1분봉 정밀 분석과 24시간 티커 스크리닝";
    return parts.length ? `근거: ${base} 현재 선물 지표는 ${parts.join(" · ")}이며, 분석 깊이는 ${depthText}입니다.` : `근거: ${base}`;
  }
  const parts = [];
  const trend1m = optionalPercentPart("1분", item.trend1mPct ?? item.secondsTrendPct);
  const trend5m = optionalPercentPart("5분", item.trend5mPct);
  const trend30m = optionalPercentPart("30분", item.trend30mPct);
  const day = optionalPercentPart("일간", item.dayChangePct);
  if (trend1m || trend5m || trend30m || day) parts.push([trend1m, trend5m, trend30m, day].filter(Boolean).join(", "));
  if (item.volumeRatio !== undefined && item.volumeRatio !== null) parts.push(`거래량 ${Number(item.volumeRatio).toFixed(2)}배`);
  if (item.tradePressure !== undefined && item.tradePressure !== null) parts.push(`체결 압력 ${Number(item.tradePressure).toFixed(2)}`);
  if (Number(item.currentValueKrw || row?.positionValueKrw || 0) > 0) parts.push(`보유 평가 ${formatKrw(item.currentValueKrw || row?.positionValueKrw)}원`);
  if (Number(item.currentValueKrw || row?.positionValueKrw || 0) > 0) parts.push(`보유 수익률 ${formatSignedPercent2(Number(row?.returnPct || 0))}%`);
  const base = compactSituationReason(item);
  return parts.length ? `근거: ${base} 세부 지표는 ${parts.join(" · ")}입니다.` : `근거: ${base}`;
}

function candidateInvestmentThesis(item, row, isSelected, hasOrder) {
  const action = actionClass(item.action || (isSelected ? "buy" : "watch"));
  const score = formatScore(item.score);
  const risk = item.riskReason ? humanAnalysisText(item.riskReason) : "리스크 확인 중";
  const regime = item.marketRegime ? humanMarketRegime(item.marketRegime) : "중립";
  const current = Number(item.currentPrice || row?.price || 0);
  const avg = Number(row?.avgEntryPrice || 0);
  const target = Number(row?.targetSellPrice || 0);
  const stop = Number(row?.stopLossPrice || 0);
  const heldValue = Number(item.currentValueKrw || row?.positionValueKrw || 0);
  const hasPosition = heldValue >= 1;
  const positionText =
    hasPosition && avg > 0
      ? `보유 기준은 매수가 ${formatOptionalPrice(avg)}, 현재가 ${formatPrice(current)}, 목표가 ${formatOptionalPrice(target)}, 손절가 ${formatOptionalPrice(stop)}입니다.`
      : `미보유 종목이라 신규 진입 가치는 점수, 거래대금, 추세, 시장 레짐 통과 여부로 봅니다.`;

  if (item.exchangeMode === "binance_futures_paper" || item.currency === "USDT") {
    const side = item.executionSide || item.side || "SHORT";
    const analysisSide = item.analysisSide || side;
    const leverage = String(item.leverage || "-").replace(/x$/i, "");
    const entry = Number(item.entryPrice || item.avgEntryPrice || 0);
    const takeProfit = Number(item.takeProfitPrice || item.targetSellPrice || 0);
    const stopLoss = Number(item.stopLossPrice || 0);
    const roe = Number(item.returnOnMarginPct || item.returnPct || 0);
    const directionName = String(side).toUpperCase() === "LONG" ? "롱" : "숏";
    const contrarianText =
      analysisSide && analysisSide !== side ? `분석 판정은 ${analysisSide}, 실제 베팅은 ${side}입니다. ` : "";
    const futuresPositionText =
      hasPosition && entry > 0
        ? `${side} ${leverage}x 보유 중이며 ${contrarianText}진입가 ${formatPrice(entry)}, 현재가 ${formatPrice(current)}, 목표가 ${formatOptionalPrice(takeProfit)}, 손절가 ${formatOptionalPrice(stopLoss)}, ROE ${formatSignedPercent2(roe)}%입니다.`
        : `${side} ${leverage}x 신규 후보이며 ${contrarianText}5분/15분 모멘텀, 거래량 배수, 변동폭, 시장 레짐을 기준으로 반대 베팅 가치를 봅니다.`;
    return {
      title: action === "hold" ? "선물 보유 판단" : action === "sell" || action === "buy" ? `${directionName} 반대베팅 후보` : "선물 감시",
      body: `바이낸스 USD-M 선물 모의 분석입니다. 점수 ${score}, 리스크 ${risk}, 시장 ${regime} 기준으로 판단합니다. ${futuresPositionText}`,
    };
  }

  if (hasOrder && action === "sell") {
    return {
      title: "즉시 매도 실행 후보",
      body: `손절선, 목표가, 급락/리스크, 또는 더 강한 후보로의 교체 조건이 주문 후보까지 올라왔습니다. 자동 실행과 주문 제한을 통과하면 매도 주문으로 반영됩니다. ${positionText}`,
    };
  }
  if (hasOrder && action === "buy") {
    return {
      title: "즉시 매수 실행 후보",
      body: `투자 점수 ${score}가 진입 기준을 넘었고 현금/포지션 한도까지 주문 후보로 계산됐습니다. 자동 실행과 주문 제한을 통과하면 매수 주문으로 반영됩니다. ${positionText}`,
    };
  }
  if (isSelected || action === "buy") {
    return {
      title: "매수 검토 가치 있음",
      body: `투자 점수 ${score}가 진입 후보권입니다. 다만 실제 주문은 현금, 기존 보유 종목 교체 가치, 최소 주문금액, 시장 ${regime} 조건까지 통과해야 합니다. ${positionText}`,
    };
  }
  if (action === "sell") {
    return {
      title: "매도/손절 감시",
      body: `보유 위험이 커졌거나 청산 신호가 감지됐습니다. 주문 후보가 되려면 평가금액과 주문 제한을 통과해야 하며, 조건이 충족되면 다음 판단에서 매도 쪽으로 이동합니다. ${positionText}`,
    };
  }
  if (action === "hold" && hasPosition) {
    return {
      title: "보유 유지",
      body: `현재는 목표가/손절가 사이에서 보유를 유지합니다. 더 강한 후보가 발견되거나 손절/익절 조건에 닿으면 보유 종목을 줄이거나 매도하도록 다시 계산합니다. ${positionText}`,
    };
  }
  if (action === "watch" || action === "hold") {
    return {
      title: "관망",
      body: `지금 당장 투자할 근거가 충분하지 않습니다. 점수 ${score}, 리스크 ${risk}, 시장 ${regime}을 계속 비교하며 진입 기준을 넘는 순간 후보로 올립니다. ${positionText}`,
    };
  }
  return {
    title: "투자 보류",
    body: `진입 가치보다 리스크가 큽니다. 현재 리스크 판단은 ${risk}이고, 시장 배경은 ${regime}입니다. 조건이 개선되기 전까지 주문 후보에서 제외합니다. ${positionText}`,
  };
}

function candidateMetricChips(item, row) {
  const chips = [];
  const currency = String(item.currency || row?.currency || "KRW").toUpperCase();
  const avg = Number(row?.avgEntryPrice || item.avgEntryPrice || item.entryPrice || 0);
  const target = Number(row?.targetSellPrice || item.targetSellPrice || item.takeProfitPrice || 0);
  const stop = Number(row?.stopLossPrice || item.stopLossPrice || 0);
  const heldValue = Number(item.currentValueUsdt || item.currentValueKrw || row?.positionValueKrw || 0);
  const returnPct = Number(item.returnOnMarginPct || item.returnPct || row?.returnPct || 0);
  const leverage = item.leverage ? String(item.leverage).replace(/x$/i, "") : "";
  const analysisSide = item.analysisSide || "";
  const executionSide = item.executionSide || item.side || "";
  if (currency === "USDT" && analysisSide && executionSide && String(analysisSide).toUpperCase() !== String(executionSide).toUpperCase()) {
    chips.push(["분석", String(analysisSide), String(analysisSide).toUpperCase() === "SHORT" ? "stop" : "entry"]);
    chips.push(["베팅", String(executionSide), String(executionSide).toUpperCase() === "SHORT" ? "stop" : "entry"]);
  } else if (item.side) {
    chips.push(["방향", String(item.side), String(item.side).toUpperCase() === "SHORT" ? "stop" : "entry"]);
  }
  if (leverage) chips.push(["레버리지", `${leverage}x`, "entry"]);
  if (currency === "USDT" && item.priceChange24hPct !== undefined) {
    const dayPct = Number(item.priceChange24hPct || 0);
    chips.push(["24h", `${formatSignedPercent2(dayPct)}%`, dayPct >= 0 ? "positive" : "negative"]);
  }
  if (currency === "USDT" && Number(item.quoteVolumeUsdt || 0) > 0) {
    chips.push(["거래대금", formatCompactUsdt(item.quoteVolumeUsdt), "value"]);
  }
  if (currency === "USDT" && item.analysisDepth) {
    chips.push(["분석", String(item.analysisDepth).includes("candle") ? "정밀" : "전체", "entry"]);
  }
  if (avg > 0) chips.push([currency === "USDT" ? "진입가" : "매수가", formatOptionalPrice(avg), "entry"]);
  if (target > 0) chips.push(["목표가", formatOptionalPrice(target), "target"]);
  if (stop > 0) chips.push(["손절가", formatOptionalPrice(stop), "stop"]);
  if (heldValue > 0) chips.push([currency === "USDT" ? "노출" : "보유", formatMoneyValue(heldValue, currency), "value"]);
  if (Number.isFinite(returnPct) && returnPct !== 0) {
    chips.push([currency === "USDT" ? "ROE" : "수익률", `${formatSignedPercent2(returnPct)}%`, returnPct >= 0 ? "positive" : "negative"]);
  }
  if (!chips.length) return "";
  return chips
    .map(
      ([label, value, tone]) =>
        `<span class="${escapeHtml(String(tone || ""))}"><b>${escapeHtml(label)}</b>${escapeHtml(value)}</span>`,
    )
    .join("");
}

function compactSituationReason(item) {
  const reason = humanAnalysisText(item.reason || item.riskReason || "");
  const tags = Array.isArray(item.tags) && item.tags.length ? item.tags.slice(0, 3).map(humanAnalysisText).join(", ") : "";
  return reason || tags || "가격, 거래대금, 추세, 보유 위험을 종합 평가 중입니다.";
}

function humanAnalysisText(value) {
  let text = String(value || "");
  const replacements = [
    [/loss-pattern/g, "손실 패턴 경계"],
    [/profit-pattern/g, "수익 패턴 유사성"],
    [/강한 점수 후보/g, "강한 투자점수 후보"],
    [/market-risk-off/g, "시장 위험 회피"],
    [/market-narrow-breadth/g, "상승 종목 폭 좁음"],
    [/market-weak/g, "시장 약세"],
    [/risk-off/g, "위험 회피 장세"],
    [/liquidity-guard/g, "유동성 기준"],
    [/overheat-guard/g, "과열 진입 경계"],
    [/microstructure-guard/g, "체결 압력 경계"],
    [/risk-clear/g, "리스크 통과"],
    [/liquidity below guard/g, "유동성 기준 미달"],
    [/overheated entry risk/g, "과열 진입 위험"],
    [/sell pressure dominates recent trades/g, "최근 매도 체결 우세"],
    [/weak breadth positive=([0-9.]+) crash=([0-9.]+) avgTrend=([0-9.+-]+)%/g, "상승 종목 비율 $1, 급락 비율 $2, 평균 추세 $3%"],
    [/breadth positive=([0-9.]+) crash=([0-9.]+) avgTrend=([0-9.+-]+)%/g, "상승 종목 비율 $1, 급락 비율 $2, 평균 추세 $3%"],
    [/market=weak/g, "시장=약세"],
    [/market=risk-off/g, "시장=위험 회피"],
    [/entryFloor=([0-9.]+)/g, "진입 기준 $1"],
    [/broken=([0-9.]+)/g, "붕괴 $1"],
    [/adj=([-0-9.]+)/g, "조정 $1"],
    [/profit=([0-9.]+)/g, "수익확률 $1"],
    [/loss=([0-9.]+)/g, "손실확률 $1"],
    [/pattern KRW-[A-Z0-9-_/]+/g, "패턴 통계"],
  ];
  replacements.forEach(([pattern, replacement]) => {
    text = text.replace(pattern, replacement);
  });
  const parts = text
    .split("·")
    .map((part) => part.trim())
    .filter(Boolean)
    .slice(0, 6);
  return parts.length ? parts.join(" · ") : text;
}

function optionalPercentPart(label, value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "";
  return `${label} ${formatSignedPercent2(numeric)}%`;
}

function marketRegimeLabel(regime) {
  if (!regime) return "시장 레짐 확인 중";
  if (typeof regime === "string") return `시장 ${humanMarketRegime(regime)}`;
  const label = regime.label || regime.name || regime.state || regime.mode || "레짐";
  const score = regime.score !== undefined ? ` · 점수 ${formatScore(regime.score)}` : "";
  return `시장 ${humanMarketRegime(label)}${score}`;
}

function humanMarketRegime(label) {
  const text = String(label || "");
  if (text === "weak") return "약세";
  if (text === "strong") return "강세";
  if (text === "neutral") return "중립";
  if (text === "crash") return "급락 경계";
  if (text === "risk-off") return "위험 회피";
  return text;
}

function analysisTimestampLabel(last, payload) {
  const value =
    last.completedAt ||
    last.finishedAt ||
    last.updatedAt ||
    last.createdAt ||
    last.startedAt ||
    payload?.updatedAt ||
    latestStatus?.runtime?.updatedAt;
  return value ? `${formatTime(value)} 갱신` : "갱신 대기";
}

function setAnalysisBadge(element, text, className) {
  if (!element) return;
  element.textContent = text;
  element.className = `analysis-badge ${className || ""}`.trim();
}

function analysisEmpty(text) {
  const item = document.createElement("div");
  item.className = "analysis-empty";
  item.textContent = text;
  return item;
}

function actionClass(action) {
  const normalized = String(action || "").toLowerCase();
  if (normalized.includes("short")) return "sell";
  if (normalized.includes("long")) return "buy";
  if (normalized.includes("cover")) return "buy";
  if (normalized.includes("buy") || normalized.includes("bid") || normalized.includes("entry")) return "buy";
  if (normalized.includes("sell") || normalized.includes("ask") || normalized.includes("exit")) return "sell";
  if (normalized.includes("hold")) return "hold";
  if (normalized.includes("avoid") || normalized.includes("block")) return "avoid";
  return "watch";
}

function analysisActionLabel(action, hasOrder) {
  const raw = String(action || "").toLowerCase();
  if (hasOrder && raw.includes("short")) return "숏 주문 후보";
  if (raw.includes("short")) return "숏 진입 후보";
  if (hasOrder && raw.includes("long")) return "롱 주문 후보";
  if (raw.includes("long")) return "롱 진입 후보";
  if (raw.includes("cover")) return "숏 청산";
  if (hasOrder) return "주문 후보";
  const normalized = actionClass(action);
  if (normalized === "buy") return "진입 후보";
  if (normalized === "sell") return "매도/손절";
  if (normalized === "hold") return "보유";
  if (normalized === "avoid") return "투자 보류";
  return "감시";
}

function renderSimulation(payload) {
  if (!payload.ok) {
    els.simulationState.textContent = "결과 없음";
    els.simulationState.className = "waiting";
    els.simulationDetail.textContent = payload.message || "최근 시뮬레이션 결과가 없습니다";
    els.simulationRange.textContent = "-";
    els.simulationAssumption.textContent = "시뮬레이션을 먼저 실행하면 이곳에 표시됩니다";
    els.simulationTopStrategy.textContent = "-";
    els.simulationTopDetail.textContent = "상위 매매기법 없음";
    return;
  }

  const portfolio = payload.portfolio || {};
  const assumptions = payload.assumptions || {};
  const currentSettings = payload.currentSettings || {};
  const range = payload.range || {};
  const universe = payload.universe || {};
  const riskNotes = payload.riskNotes || {};
  const settingsDrift = Array.isArray(payload.settingsDrift) ? payload.settingsDrift : [];
  const displayAssumptions = { ...assumptions, ...currentSettings };
  const top = (payload.topStrategies || [])[0];
  const finalEquity = Number(portfolio.finalEquityKrw || 0);
  const returnPct = Number(portfolio.totalReturnPct || 0);
  const maxDrawdownPct = Number(portfolio.maxDrawdownPct || 0);
  const feesPaid = Number(portfolio.feesPaidKrw || 0);
  const realizedPnl = Number(portfolio.realizedPnlKrw || 0);

  els.simulationState.textContent = `${formatKrw(finalEquity)}원`;
  els.simulationState.className = returnPct >= 0 ? "ok" : "critical";
  els.simulationDetail.textContent =
    `수익률 ${formatSignedPercent2(returnPct)}% · MDD ${formatSignedPercent2(maxDrawdownPct)}% · ` +
    `실현 ${formatKrw(realizedPnl)}원 · 수수료 ${formatKrw(feesPaid)}원 · 주문 ${number.format(Number(portfolio.orderCount || 0))}회`;

  els.simulationRange.textContent = `${formatDateShort(range.startKst)} ~ ${formatDateShort(range.endKst)}`;
  const days = Number(payload.periodDays || 0);
  const periodText = Number.isFinite(days) && days > 0 ? `${percent2.format(days)}일` : "기간 확인 중";
  const marketCount = universe.marketCount || universe.requestedMaxMarkets || 0;
  const driftText = settingsDrift.length ? ` · 파일 설정 ${settingsDrift.length}개 변경됨` : "";
  els.simulationAssumption.textContent =
    `${payload.currentModeLabel || payload.modeLabel || "최근 시뮬레이션"} · ${periodText} · ${marketCount}개 코인 · ` +
    `전체 ${formatRatioPercent(displayAssumptions.maxDeployPct)} · 코인 ${formatRatioPercent(displayAssumptions.maxPositionPct)} · ` +
    `주문 ${formatRatioPercent(displayAssumptions.maxOrderPct)} · 하루 ${number.format(Number(displayAssumptions.maxDailyOrders || 0))}회 · ` +
    `수수료 ${formatRatioPercent(displayAssumptions.feeRate ?? riskNotes.feeRate)} · 호가 ${riskNotes.historicalOrderbookIncluded ? "반영" : "미반영"} · 슬리피지 ${riskNotes.slippageIncluded ? "반영" : "미반영"}${driftText}`;

  if (top) {
    els.simulationTopStrategy.textContent = `${top.displayName || displayMarketCode(top.market)} · ${top.strategyLabel || top.strategy}`;
    els.simulationTopDetail.textContent =
      `단독 수익률 ${formatSignedPercent2(Number(top.totalReturnPct || 0))}% · ` +
      `MDD ${formatSignedPercent2(Number(top.maxDrawdownPct || 0))}% · 주문 ${number.format(Number(top.orderCount || 0))}회`;
  } else {
    els.simulationTopStrategy.textContent = "-";
    els.simulationTopDetail.textContent = "상위 매매기법 없음";
  }
}

function renderSimulationPlayback(payload) {
  playbackPayload = payload;
  playbackFrames = payload.ok && Array.isArray(payload.frames) ? payload.frames : [];
  playbackTrades = payload.ok && Array.isArray(payload.trades) ? payload.trades : [];
  playbackIndex = 0;
  stopSimulationPlayback();

  if (!payload.ok || !playbackFrames.length) {
    if (els.playbackState) {
      els.playbackState.textContent = "결과 없음";
      els.playbackState.className = "waiting";
    }
    if (els.playbackTime) els.playbackTime.textContent = "-";
    if (els.playbackFile) els.playbackFile.textContent = payload.message || "재생할 결과 파일이 없습니다";
    if (els.playbackEquity) els.playbackEquity.textContent = "-";
    if (els.playbackReturn) els.playbackReturn.textContent = "수익률 대기";
    if (els.playbackCash) els.playbackCash.textContent = "-";
    if (els.playbackPositions) els.playbackPositions.textContent = "보유 종목 대기";
    if (els.playbackOrders) els.playbackOrders.textContent = "-";
    if (els.playbackProgressText) els.playbackProgressText.textContent = "진행률 대기";
    if (els.playbackProgress) els.playbackProgress.style.width = "0%";
    renderPlaybackTrades([]);
    return;
  }

  if (els.playbackState) {
    els.playbackState.textContent = "준비";
    els.playbackState.className = "waiting";
  }
  if (els.playbackFile) {
    const universe = payload.universe || {};
    const count = universe.marketCount || universe.requestedMaxMarkets || 0;
    els.playbackFile.textContent = `${payload.fileName || "결과 파일"} · ${count}개 코인`;
  }
  renderPlaybackFrame(0);
}

function startSimulationPlayback() {
  if (!playbackFrames.length) {
    loadSimulationPlayback({ autoplay: true, toast: true });
    return;
  }
  stopSimulationPlayback();
  if (playbackIndex >= playbackFrames.length - 1) playbackIndex = 0;
  if (els.playbackState) {
    els.playbackState.textContent = "재생 중";
    els.playbackState.className = "ok";
  }
  playbackTimer = window.setInterval(() => {
    renderPlaybackFrame(playbackIndex);
    playbackIndex += 1;
    if (playbackIndex >= playbackFrames.length) {
      renderPlaybackFrame(playbackFrames.length - 1);
      stopSimulationPlayback();
      if (els.playbackState) {
        els.playbackState.textContent = "완료";
        els.playbackState.className = "connected";
      }
    }
  }, playbackIntervalMs);
}

function stopSimulationPlayback() {
  window.clearInterval(playbackTimer);
  playbackTimer = 0;
}

function pauseSimulationPlayback() {
  stopSimulationPlayback();
  if (els.playbackState) {
    els.playbackState.textContent = playbackFrames.length ? "일시정지" : "대기";
    els.playbackState.className = "waiting";
  }
}

function renderPlaybackFrame(index) {
  if (!playbackFrames.length) return;
  const safeIndex = Math.max(0, Math.min(index, playbackFrames.length - 1));
  const frame = playbackFrames[safeIndex] || {};
  const portfolio = playbackPayload?.portfolio || {};
  const equity = Number(frame.equityKrw || 0);
  const cash = Number(frame.cashKrw || 0);
  const startEquity = Number(portfolio.startEquityKrw || playbackPayload?.assumptions?.startingCashKrw || 0);
  const returnPct = startEquity > 0 ? ((equity - startEquity) / startEquity) * 100 : Number(portfolio.totalReturnPct || 0);
  const progressPct = playbackFrames.length > 1 ? (safeIndex / (playbackFrames.length - 1)) * 100 : 100;
  const visibleTrades = playbackTradesUntil(frame.time).slice(-8).reverse();

  if (els.playbackTime) els.playbackTime.textContent = formatPlaybackTime(frame.time);
  if (els.playbackEquity) {
    els.playbackEquity.textContent = `${formatKrw(equity)}원`;
    els.playbackEquity.className = returnPct >= 0 ? "positive" : "negative";
  }
  if (els.playbackReturn) {
    els.playbackReturn.textContent = `현재 수익률 ${formatSignedPercent2(returnPct)}%`;
    els.playbackReturn.className = returnPct >= 0 ? "positive" : "negative";
  }
  if (els.playbackCash) els.playbackCash.textContent = `${formatKrw(cash)}원`;
  if (els.playbackPositions) els.playbackPositions.textContent = `보유 ${number.format(Number(frame.openPositions || 0))}개`;
  if (els.playbackOrders) els.playbackOrders.textContent = `${number.format(visibleTrades.length)}/${number.format(playbackTrades.length)}건`;
  if (els.playbackProgressText) {
    els.playbackProgressText.textContent = `${percent2.format(progressPct)}% · ${safeIndex + 1}/${playbackFrames.length} 프레임`;
  }
  if (els.playbackProgress) els.playbackProgress.style.width = `${Math.min(100, Math.max(0, progressPct))}%`;
  renderPlaybackTrades(visibleTrades);
}

function playbackTradesUntil(time) {
  const currentTime = parsePlaybackTime(time);
  if (!Number.isFinite(currentTime)) return [];
  return playbackTrades.filter((trade) => {
    const tradeTime = parsePlaybackTime(trade.time);
    return Number.isFinite(tradeTime) && tradeTime <= currentTime;
  });
}

function renderPlaybackTrades(rows) {
  if (!els.playbackTradeRows) return;
  els.playbackTradeRows.replaceChildren(
    ...(rows.length
      ? rows.map((row) => {
          const tr = document.createElement("tr");
          const side = row.side === "buy" || row.side === "bid" ? "매수" : row.side === "sell" || row.side === "ask" ? "매도" : row.side || "-";
          const amount = Number(row.budgetKrw || 0);
          tr.innerHTML = `
            <td>${escapeHtml(formatPlaybackTime(row.time))}</td>
            <td>${escapeHtml(displayMarketCode(row.market))}</td>
            <td class="${side === "매수" ? "positive" : side === "매도" ? "negative" : ""}">${escapeHtml(side)}</td>
            <td>${formatKrw(Math.abs(amount))}원</td>
            <td>${formatPrice(row.price)}</td>
          `;
          return tr;
        })
      : [emptyPlaybackRow()]),
  );
}

function emptyPlaybackRow() {
  const tr = document.createElement("tr");
  tr.innerHTML = `<td class="empty-cell" colspan="5">아직 이 시점까지 체결된 주문이 없습니다</td>`;
  return tr;
}

function renderOrderbookAnalysis(payload) {
  const analysis = payload.analysis || {};
  const action = analysis.action || "unavailable";
  els.orderbookState.textContent = `${payload.market || selectedMarket} ${analysis.actionLabel || orderbookActionLabel(action)}`;
  els.orderbookState.className = action === "skip" ? "critical" : action === "reduce" || action === "reprice" ? "warning" : "ok";
  const slippage = Number(analysis.recommendedSlippagePct ?? analysis.expectedSlippagePct ?? 0);
  const spread = Number(analysis.spreadPct || 0);
  const depthRatio = Number(analysis.bidAskDepthRatio || 0);
  const price = analysis.recommendedAvgPrice || analysis.expectedAvgPrice || payload.price || 0;
  els.orderbookDetail.textContent =
    `예상 ${formatPrice(price)} · 슬리피지 ${formatSignedPercent2(slippage)}% · 스프레드 ${formatSignedPercent2(spread)}% · 매수/매도벽 ${percent2.format(depthRatio)}배`;
}

function orderbookActionLabel(action) {
  if (action === "use") return "통과";
  if (action === "reprice") return "호가 조정";
  if (action === "reduce") return "수량 축소";
  if (action === "skip") return "주문 제외";
  return "호가 없음";
}

function scheduleLearningPoll() {
  window.clearTimeout(learningPollTimer);
  learningPollTimer = window.setTimeout(async () => {
    await loadLearningStatus();
  }, 3500);
}

function setLearningButtonsBusy(busy) {
  setBusy(els.learnButton, busy);
  setBusy(els.learnAllButton, busy);
}

function setAllocationButtonsBusy(busy) {
  setBusy(els.allocationPreviewButton, busy);
  setBusy(els.allocationRunButton, busy);
}

function setRealtimeDecisionButtonsBusy(busy) {
  setBusy(els.realtimeDecisionPreviewButton, busy);
  setBusy(els.realtimeDecisionRunButton, busy);
}

function scopeLabel(scope) {
  if (scope === "all_krw") return "전체 KRW";
  return "감시 코인";
}

function sortedMarkets(markets) {
  const sorter = marketSorters[marketSortKey] || marketSorters.changeRate;
  const direction = marketSortDirection === "asc" ? 1 : -1;
  return [...markets].sort((a, b) => {
    const valueA = sorter(a);
    const valueB = sorter(b);
    if (typeof valueA === "string" || typeof valueB === "string") {
      return String(valueA).localeCompare(String(valueB), "ko-KR") * direction;
    }
    if (valueA === valueB) return marketLabel(a).localeCompare(marketLabel(b), "ko-KR");
    return (valueA > valueB ? 1 : -1) * direction;
  });
}

function marketLabel(row) {
  const symbol = row.symbol || displayMarketCode(row.market);
  return row.koreanName ? `${row.koreanName} ${symbol}` : symbol;
}

function displayMarketCode(market) {
  return String(market || "").replace(/^KRW-/, "");
}

function renderActiveMarketSummary(row) {
  els.marketName.textContent = marketLabel(row);
  els.marketPrice.textContent = formatPrice(row.price);
  const changeRate = Number(row.changeRate || 0);
  els.marketChange.textContent = `${changeLabel(row.change)} ${formatSignedPercent2(changeRate)}% · 24h ${formatKrw(row.tradeValue24h)}원`;
  els.marketChange.className = row.change === "RISE" ? "rise" : row.change === "FALL" ? "fall" : "";
}

async function openMarketChart(row, visibleRows) {
  selectedMarket = row.market;
  renderActiveMarketSummary(row);
  renderMarkets(visibleRows);
  await loadTradingChart(row.market);
  await loadOrderbookAnalysis(row.market);
  document.querySelector(".market-panel").scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderMarkets(markets) {
  const sorted = sortedMarkets(markets);
  updateSortHeaders();
  els.marketRows.replaceChildren(
    ...sorted.map((row) => {
      const tr = document.createElement("tr");
      tr.className = row.market === selectedMarket ? "selected" : "";
      const changeRate = Number(row.changeRate || 0);
      const unrealized = Number(row.unrealizedPnlKrw || 0);
      const realized = Number(row.realizedPnlKrw || 0);
      const returnPct = Number(row.returnPct || 0);
      tr.innerHTML = `
        <td class="market-jump" title="이 코인 차트 보기">
          <span class="market-symbol">${escapeHtml(marketLabel(row))}</span>
          <small>${escapeHtml(displayMarketCode(row.market))}</small>
        </td>
        <td class="recommend-cell">
          <label class="recommend-check" title="실제 투자 후보로 추천">
            <input type="checkbox" ${row.recommended ? "checked" : ""} aria-label="${escapeHtml(marketLabel(row))} 추천 코인" />
            <span>추천</span>
          </label>
        </td>
        <td class="recommend-cell">
          <label class="recommend-check exclude-check" title="신규 투자 후보에서 제외">
            <input type="checkbox" ${row.excluded ? "checked" : ""} aria-label="${escapeHtml(marketLabel(row))} 비추천 코인" />
            <span>비추천</span>
          </label>
        </td>
        <td>${formatPrice(row.price)}</td>
        <td class="${row.change === "RISE" ? "rise" : row.change === "FALL" ? "fall" : ""}">${formatSignedPercent2(changeRate)}%</td>
        <td>${formatCompactKrw(row.tradeValue24h)}원</td>
        <td>${formatKrw(row.positionValueKrw)}원</td>
        <td class="${returnPct >= 0 ? "positive" : "negative"}">${formatSignedPercent2(returnPct)}%</td>
        <td class="${unrealized >= 0 ? "positive" : "negative"}">${formatKrw(row.unrealizedPnlKrw)}원</td>
        <td class="${realized >= 0 ? "positive" : "negative"}">${formatKrw(row.realizedPnlKrw)}원</td>
        <td>${formatRecentTrade(row)}</td>
        <td><span class="stream-pill ${row.stream === "실시간" ? "live" : ""}">${row.stream}</span></td>
        <td class="${row.status === "보유" ? "holding" : "watching"}">${row.status}</td>
        <td><button class="chart-link" type="button">차트</button></td>
      `;
      const marketCell = tr.querySelector(".market-jump");
      const chartButton = tr.querySelector(".chart-link");
      const recommendCheckbox = tr.querySelector(".recommend-check:not(.exclude-check) input");
      const excludeCheckbox = tr.querySelector(".exclude-check input");
      marketCell.addEventListener("click", () => openMarketChart(row, sorted));
      chartButton.addEventListener("click", (event) => {
        event.stopPropagation();
        openMarketChart(row, sorted);
      });
      recommendCheckbox.addEventListener("click", (event) => event.stopPropagation());
      recommendCheckbox.addEventListener("change", (event) => {
        event.stopPropagation();
        toggleRecommendedMarket(row.market, "recommended", recommendCheckbox.checked, recommendCheckbox);
      });
      excludeCheckbox.addEventListener("click", (event) => event.stopPropagation());
      excludeCheckbox.addEventListener("change", (event) => {
        event.stopPropagation();
        toggleRecommendedMarket(row.market, "excluded", excludeCheckbox.checked, excludeCheckbox);
      });
      return tr;
    }),
  );
}

function updateSortHeaders() {
  document.querySelectorAll(".sort-header").forEach((button) => {
    const active = button.dataset.sort === marketSortKey;
    const indicator = button.querySelector("span");
    button.classList.toggle("active", active);
    button.setAttribute("aria-sort", active ? (marketSortDirection === "desc" ? "descending" : "ascending") : "none");
    if (indicator) {
      indicator.textContent = active ? (marketSortDirection === "desc" ? "↓" : "↑") : "";
    }
  });
}

function setMarketSort(key) {
  if (marketSortKey === key) {
    marketSortDirection = marketSortDirection === "desc" ? "asc" : "desc";
  } else {
    marketSortKey = key;
    marketSortDirection = key === "symbol" ? "asc" : "desc";
  }
  if (latestStatus) renderMarkets(latestStatus.markets);
}

function renderLogs(logs) {
  els.logList.replaceChildren(
    ...logs.map((log) => {
      const item = document.createElement("li");
      item.className = log.level;
      const time = document.createElement("time");
      time.textContent = formatTime(log.time);
      const message = document.createElement("p");
      message.textContent = log.message;
      item.append(time, message);
      return item;
    }),
  );
}

function chartZoomKey(canvas, options = {}) {
  const unit = String(options.unit || (options.portfolio ? portfolioChartUnit : options.compact ? holdingChartUnit : chartUnit));
  if (options.portfolio) return `portfolio:${unit}`;
  if (options.compact) {
    const market = options.market || canvas?.closest(".holding-chart-card")?.dataset.market || "holding";
    return `holding:${market}:${unit}`;
  }
  return `main:${options.market || selectedMarket}:${unit}`;
}

function chartZoomIndex(key) {
  const value = chartZoomState.get(key);
  return Number.isInteger(value) ? Math.max(0, Math.min(chartZoomLevels.length - 1, value)) : 0;
}

function chartZoomScale(key) {
  return chartZoomLevels[chartZoomIndex(key)] || 1;
}

function chartPanOffset(key) {
  return Number(chartPanState.get(key) || 0);
}

function setChartPanOffset(key, value, maxPan = Infinity) {
  const numeric = Number(value || 0);
  const clamped = Math.max(0, Math.min(Number.isFinite(maxPan) ? maxPan : Infinity, numeric));
  if (clamped <= 0.001) chartPanState.delete(key);
  else chartPanState.set(key, clamped);
  return clamped;
}

function chartPanMax(candleCount, plotWidth, candleStep) {
  if (!Number.isFinite(candleStep) || candleStep <= 0) return 0;
  const visibleCandles = plotWidth / candleStep;
  return Math.max(0, candleCount - visibleCandles);
}

function chartPriceWindowCandles(candles, xForIndex, plotLeft, plotRight, candleStep) {
  const windowCandles = candles.filter((_, index) => {
    const x = xForIndex(index);
    return x >= plotLeft - candleStep && x <= plotRight + candleStep;
  });
  return windowCandles.length ? windowCandles : candles;
}

function changeChartZoom(key, action) {
  const currentIndex = chartZoomIndex(key);
  let nextIndex = currentIndex;
  if (action === "in") nextIndex = Math.min(chartZoomLevels.length - 1, currentIndex + 1);
  else if (action === "out") nextIndex = Math.max(0, currentIndex - 1);
  else nextIndex = 0;
  if (nextIndex === currentIndex && action !== "reset") return;
  chartZoomState.set(key, nextIndex);
  if (action === "reset") chartPanState.delete(key);
  redrawChartByZoomKey(key);
}

function chartCanvasByZoomKey(key) {
  if (key.startsWith("main:")) return els.chart;
  if (key.startsWith("portfolio:")) return els.portfolioChart;
  if (key.startsWith("holding:")) {
    const [, market] = key.split(":");
    return els.holdingCharts?.querySelector(`[data-market="${cssEscape(market)}"] .holding-chart`) || null;
  }
  return null;
}

function changeChartPan(key, action) {
  const canvas = chartCanvasByZoomKey(key);
  if (!canvas) return;
  const maxPan = Number(canvas.dataset.chartPanMax || 0);
  if (!Number.isFinite(maxPan) || maxPan <= 0) return;
  const visibleCandles = Number(canvas.dataset.chartVisibleCandles || 0);
  const current = chartPanOffset(key);
  const stepCandles = Math.max(10, Math.round((Number.isFinite(visibleCandles) && visibleCandles > 0 ? visibleCandles : 80) * 0.65));
  let next = current;
  if (action === "older") next = current + stepCandles;
  else if (action === "newer") next = current - stepCandles;
  else if (action === "oldest") next = maxPan;
  else next = 0;
  setChartPanOffset(key, next, maxPan);
  redrawChartByZoomKey(key);
}

function redrawChartByZoomKey(key) {
  if (key.startsWith("main:")) {
    redrawMainChart();
    return;
  }
  if (key.startsWith("portfolio:")) {
    redrawPortfolioChart();
    return;
  }
  const [, market] = key.split(":");
  redrawHoldingChart(market);
}

function redrawMainChart() {
  if (!els.chart) return;
  const row = latestStatus?.markets?.find((item) => item.market === selectedMarket);
  const points = latestChart.length ? latestChart : latestStatus?.chart || [];
  drawTradeChart(points, els.chart, { market: selectedMarket, row, unit: chartUnit });
}

function redrawHoldingChart(market) {
  if (!market || !els.holdingCharts) return;
  const card = els.holdingCharts.querySelector(`[data-market="${cssEscape(market)}"]`);
  const canvas = card?.querySelector(".holding-chart");
  const cached = holdingChartCache.get(`${market}:${holdingChartUnit}`);
  if (!canvas || !cached) return;
  const row = latestStatus?.markets?.find((item) => item.market === market);
  drawTradeChart(cached, canvas, { compact: true, market, row, unit: holdingChartUnit });
}

function bindChartZoom(canvas) {
  if (!canvas || canvas.dataset.zoomBound === "true") return;
  canvas.dataset.zoomBound = "true";
  canvas.addEventListener(
    "wheel",
    (event) => {
      if (!canvas.dataset.chartZoomKey) return;
      event.preventDefault();
      if (event.shiftKey) changeChartPan(canvas.dataset.chartZoomKey, event.deltaY > 0 ? "older" : "newer");
      else changeChartZoom(canvas.dataset.chartZoomKey, event.deltaY < 0 ? "in" : "out");
    },
    { passive: false },
  );
  canvas.addEventListener("dblclick", () => {
    if (canvas.dataset.chartZoomKey) changeChartZoom(canvas.dataset.chartZoomKey, "reset");
  });
  canvas.addEventListener("pointerdown", (event) => {
    if (event.button !== 0 || !canvas.dataset.chartZoomKey) return;
    const step = Number(canvas.dataset.chartStep || 0);
    const maxPan = Number(canvas.dataset.chartPanMax || 0);
    if (!Number.isFinite(step) || step <= 0 || maxPan <= 0) return;
    canvas.dataset.draggingChart = "true";
    canvas.setPointerCapture?.(event.pointerId);
    canvas._chartPanDrag = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startPan: chartPanOffset(canvas.dataset.chartZoomKey),
      step,
      maxPan,
    };
    event.preventDefault();
  });
  canvas.addEventListener("pointermove", (event) => {
    const drag = canvas._chartPanDrag;
    if (!drag || drag.pointerId !== event.pointerId || !canvas.dataset.chartZoomKey) return;
    const nextPan = drag.startPan + (event.clientX - drag.startX) / drag.step;
    setChartPanOffset(canvas.dataset.chartZoomKey, nextPan, drag.maxPan);
    redrawChartByZoomKey(canvas.dataset.chartZoomKey);
    event.preventDefault();
  });
  const endDrag = (event) => {
    const drag = canvas._chartPanDrag;
    if (!drag || drag.pointerId !== event.pointerId) return;
    canvas.releasePointerCapture?.(event.pointerId);
    canvas._chartPanDrag = null;
    delete canvas.dataset.draggingChart;
  };
  canvas.addEventListener("pointerup", endDrag);
  canvas.addEventListener("pointercancel", endDrag);
  canvas.addEventListener("pointerleave", endDrag);
}

function updateChartZoomUi(canvas, key, totalCount, meta = {}) {
  const index = chartZoomIndex(key);
  const zoom = chartZoomScale(key);
  const maxPan = Number(meta.maxPan || 0);
  const panOffset = Number(meta.panOffset || 0);
  const visibleCandles = Number(meta.visibleCandles || 0);
  canvas.dataset.chartZoom = zoom.toFixed(2);
  canvas.dataset.totalCandles = String(totalCount);
  canvas.dataset.chartPanReady = maxPan > 0 ? "true" : "false";
  const disabledOut = index <= 0;
  const disabledIn = index >= chartZoomLevels.length - 1 || totalCount <= 2;

  if (key.startsWith("main:")) {
    if (els.chartZoomLabel) els.chartZoomLabel.textContent = `${zoom.toFixed(1)}x`;
    if (els.chartZoomOutButton) els.chartZoomOutButton.disabled = disabledOut;
    if (els.chartZoomInButton) els.chartZoomInButton.disabled = disabledIn;
    if (els.chartZoomResetButton) els.chartZoomResetButton.disabled = disabledOut && panOffset <= 0.5;
    if (els.chartPanOlderButton) els.chartPanOlderButton.disabled = maxPan <= 0 || panOffset >= maxPan - 0.5;
    if (els.chartPanNewerButton) els.chartPanNewerButton.disabled = maxPan <= 0 || panOffset <= 0.5;
    if (els.chartPanLatestButton) els.chartPanLatestButton.disabled = maxPan <= 0 || panOffset <= 0.5;
    if (els.chartPanLabel) {
      if (maxPan <= 0) els.chartPanLabel.textContent = "이동 없음";
      else if (panOffset <= 0.5) els.chartPanLabel.textContent = `최신 구간 · ${totalCount}개`;
      else {
        const approx = Math.round(panOffset);
        const visible = Number.isFinite(visibleCandles) && visibleCandles > 0 ? ` · 화면 ${Math.round(visibleCandles)}개` : "";
        els.chartPanLabel.textContent = `${approx}개 캔들 전${visible}`;
      }
    }
    return;
  }

  if (key.startsWith("portfolio:")) {
    if (els.portfolioChartZoomLabel) els.portfolioChartZoomLabel.textContent = `${zoom.toFixed(1)}x`;
    if (els.portfolioChartZoomOutButton) els.portfolioChartZoomOutButton.disabled = disabledOut;
    if (els.portfolioChartZoomInButton) els.portfolioChartZoomInButton.disabled = disabledIn;
    if (els.portfolioChartZoomResetButton) els.portfolioChartZoomResetButton.disabled = disabledOut && panOffset <= 0.5;
    return;
  }

  const card = canvas.closest(".holding-chart-card");
  if (!card) return;
  card.querySelectorAll("[data-chart-zoom-action]").forEach((button) => {
    const action = button.dataset.chartZoomAction;
    button.disabled = action === "out" || action === "reset" ? disabledOut : action === "in" ? disabledIn : false;
  });
}

function chartCandleBodyWidth(candleStep, compact) {
  if (!Number.isFinite(candleStep) || candleStep <= 0) return compact ? 2 : 3;
  const target = candleStep * 0.82;
  const minimum = compact ? 2 : 3;
  const maximum = compact ? 18 : 34;
  if (candleStep <= minimum + 1) return Math.max(1, candleStep * 0.88);
  return Math.max(minimum, Math.min(maximum, target));
}

function drawTradeChart(points, canvas = els.chart, options = {}) {
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const compact = options.compact === true;
  const zoomKey = chartZoomKey(canvas, options);
  bindChartZoom(canvas);
  canvas.dataset.chartZoomKey = zoomKey;
  canvas.width = Math.max(1, Math.floor(rect.width * dpr));
  canvas.height = Math.max(1, Math.floor(rect.height * dpr));
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, rect.width, rect.height);

  if (!points || points.length < 2) {
    updateChartZoomUi(canvas, zoomKey, Array.isArray(points) ? points.length : 0);
    ctx.fillStyle = "#64748b";
    ctx.font = compact ? "12px system-ui" : "13px system-ui";
    ctx.fillText("차트 데이터가 부족합니다", 16, 32);
    return;
  }

  const candles = points.map((point) => ({
    time: point.time || point.timestamp || point.date || "",
    open: Number(point.open ?? point.price ?? point.close),
    high: Number(point.high ?? point.price ?? point.close),
    low: Number(point.low ?? point.price ?? point.close),
    close: Number(point.close ?? point.price),
    volume: Number(point.volume || 0),
    maShort: point.maShort === null || point.maShort === undefined ? null : Number(point.maShort),
    maLong: point.maLong === null || point.maLong === undefined ? null : Number(point.maLong),
  }));
  const topPad = compact ? 12 : 18;
  const leftPad = compact ? 12 : 16;
  const rightPad = compact ? 12 : 132;
  const bottomPad = compact ? 12 : 36;
  const volumeHeight = compact ? Math.max(28, rect.height * 0.2) : Math.max(46, rect.height * 0.2);
  const volumeGap = compact ? 4 : 14;
  const volumeBottom = rect.height - bottomPad;
  const volumeTopBase = volumeBottom - volumeHeight;
  const chartBottom = volumeTopBase - volumeGap;
  const chartHeight = Math.max(40, chartBottom - topPad);
  const width = Math.max(1, rect.width - leftPad - rightPad);
  const plotRight = rect.width - rightPad;
  const zoomScale = chartZoomScale(zoomKey);
  const baseVisibleCandles = compact ? 64 : 90;
  const candleStep = (width / baseVisibleCandles) * zoomScale;
  const candleWidth = chartCandleBodyWidth(candleStep, compact);
  const maxPan = chartPanMax(candles.length, width, candleStep);
  const panOffset = setChartPanOffset(zoomKey, chartPanOffset(zoomKey), maxPan);
  const visibleCandles = width / candleStep;
  canvas.dataset.chartStep = String(candleStep);
  canvas.dataset.chartPanMax = String(maxPan);
  canvas.dataset.chartPan = String(panOffset);
  canvas.dataset.chartVisibleCandles = String(visibleCandles);
  const xForIndex = (index) => plotRight - (candles.length - 1 - index - panOffset) * candleStep - candleStep / 2;
  const priceWindowCandles = chartPriceWindowCandles(candles, xForIndex, leftPad, plotRight, candleStep);
  updateChartZoomUi(canvas, zoomKey, candles.length, { maxPan, panOffset, visibleCandles });
  const priceLevels = compact ? [] : chartPriceLevels(candles, options);
  const levelPrices = priceLevels.map((level) => level.price);
  const rawMin = Math.min(...priceWindowCandles.map((point) => point.low), ...levelPrices);
  const rawMax = Math.max(...priceWindowCandles.map((point) => point.high), ...levelPrices);
  const maxVolume = Math.max(...priceWindowCandles.map((point) => point.volume), 1);
  const rawRange = rawMax - rawMin || Math.max(rawMax * 0.01, 1);
  const pricePadding = compact ? rawRange * 0.04 : rawRange * 0.08;
  const min = Math.max(0, rawMin - pricePadding);
  const max = rawMax + pricePadding;
  const range = max - min || 1;

  const yForPrice = (price) => topPad + chartHeight - ((price - min) / range) * chartHeight;

  ctx.strokeStyle = "#d8dee7";
  ctx.lineWidth = 1;
  const tickCount = compact ? 3 : 5;
  for (let i = 0; i < tickCount; i += 1) {
    const ratio = tickCount === 1 ? 0 : i / (tickCount - 1);
    const y = topPad + chartHeight * ratio;
    const price = max - range * ratio;
    ctx.beginPath();
    ctx.moveTo(leftPad, y);
    ctx.lineTo(rect.width - rightPad, y);
    ctx.stroke();
    if (!compact) {
      ctx.fillStyle = "#64748b";
      ctx.font = "11px system-ui";
      ctx.textAlign = "right";
      ctx.fillText(formatPrice(price), rect.width - 8, Math.min(rect.height - bottomPad - 4, y + 4));
    }
  }

  if (!compact) {
    ctx.strokeStyle = "#cbd5e1";
    ctx.beginPath();
    ctx.moveTo(rect.width - rightPad, topPad);
    ctx.lineTo(rect.width - rightPad, volumeBottom);
    ctx.stroke();
  }

  candles.forEach((candle, index) => {
    const x = xForIndex(index);
    if (x < leftPad - candleStep || x > plotRight + candleStep) return;
    const rise = candle.close >= candle.open;
    const color = rise ? chartRiseColor : chartFallColor;
    const highY = yForPrice(candle.high);
    const lowY = yForPrice(candle.low);
    const openY = yForPrice(candle.open);
    const closeY = yForPrice(candle.close);
    const bodyTop = Math.min(openY, closeY);
    const bodyHeight = Math.max(1, Math.abs(closeY - openY));

    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.moveTo(x, highY);
    ctx.lineTo(x, lowY);
    ctx.stroke();
    ctx.fillRect(x - candleWidth / 2, bodyTop, candleWidth, bodyHeight);

    const volumeTop = volumeBottom - (candle.volume / maxVolume) * volumeHeight;
    ctx.globalAlpha = 0.24;
    ctx.fillRect(x - candleWidth / 2, volumeTop, candleWidth, volumeBottom - volumeTop);
    ctx.globalAlpha = 1;
  });

  ctx.save();
  ctx.beginPath();
  ctx.rect(leftPad, topPad, width, Math.max(1, volumeBottom - topPad));
  ctx.clip();
  drawMovingAverage(ctx, candles, "maShort", xForIndex, yForPrice, "#2563eb");
  drawMovingAverage(ctx, candles, "maLong", xForIndex, yForPrice, "#f59e0b");
  ctx.restore();

  if (compact) return;
  drawPriceLevels(ctx, priceLevels, yForPrice, leftPad, plotRight, rect.width);
  drawTimeAxis(ctx, candles, xForIndex, volumeBottom, rect.height, options.unit || chartUnit, leftPad, plotRight);
  const latest = candles.at(-1);
  ctx.fillStyle = "#64748b";
  ctx.font = "12px system-ui";
  ctx.textAlign = "left";
  ctx.fillText(`O ${formatPrice(latest.open)}  H ${formatPrice(latest.high)}  L ${formatPrice(latest.low)}  C ${formatPrice(latest.close)}`, leftPad, rect.height - 6);
}

function drawMovingAverage(ctx, candles, key, xForIndex, yForPrice, color) {
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.8;
  ctx.beginPath();
  let hasPoint = false;
  candles.forEach((candle, index) => {
    if (candle[key] === null || Number.isNaN(candle[key])) return;
    const x = xForIndex(index);
    const y = yForPrice(candle[key]);
    if (!hasPoint) {
      ctx.moveTo(x, y);
      hasPoint = true;
    } else {
      ctx.lineTo(x, y);
    }
  });
  if (hasPoint) ctx.stroke();
}

function chartPriceLevels(candles, options = {}) {
  if (Array.isArray(options.priceLevels)) {
    return options.priceLevels
      .map((level) => ({
        label: level.label || "",
        price: Number(level.price || 0),
        color: level.color || "#111827",
        dashed: Boolean(level.dashed),
      }))
      .filter((level) => level.label && Number.isFinite(level.price) && level.price > 0);
  }
  if (options.showTradeLevels === false) return [];
  const market = options.market || selectedMarket;
  const row = options.row || latestStatus?.markets?.find((item) => item.market === market) || {};
  const latestClose = Number(candles.at(-1)?.close || 0);
  const levels = [];
  const current = Number(row.price || latestClose || 0);
  addChartPriceLevel(levels, "현재가", current, "#111827", false);
  addChartPriceLevel(levels, "매수가", row.avgEntryPrice, chartRiseColor, false);
  addChartPriceLevel(levels, "매도가", row.targetSellPrice, chartRiseColor, false);
  addChartPriceLevel(levels, "손절", row.stopLossPrice, chartFallColor, true);
  if (row.lastTradePrice) {
    const side = row.lastTradeSide === "BID" ? "최근 매수" : row.lastTradeSide === "ASK" ? "최근 매도" : "최근 체결";
    const color = row.lastTradeSide === "ASK" ? chartFallColor : row.lastTradeSide === "BID" ? chartRiseColor : "#64748b";
    addChartPriceLevel(levels, side, row.lastTradePrice, color, true);
  }
  return levels;
}

function addChartPriceLevel(levels, label, value, color, dashed) {
  const price = Number(value || 0);
  if (!Number.isFinite(price) || price <= 0) return;
  if (levels.some((level) => level.label === label && Math.abs(level.price - price) < Math.max(1, price * 0.0001))) return;
  levels.push({ label, price, color, dashed });
}

function drawPriceLevels(ctx, levels, yForPrice, plotLeft, plotRight, canvasWidth) {
  if (!levels.length) return;
  const adjusted = adjustedPriceLabelPositions(levels.map((level) => ({ ...level, y: yForPrice(level.price) })));
  const labelX = plotRight + 6;
  const labelWidth = Math.max(64, canvasWidth - labelX - 6);
  adjusted.forEach((level) => {
    ctx.save();
    ctx.strokeStyle = level.color;
    ctx.fillStyle = level.color;
    ctx.lineWidth = level.label === "현재가" ? 1.6 : 1.2;
    ctx.setLineDash(level.dashed ? [5, 4] : []);
    ctx.beginPath();
    ctx.moveTo(plotLeft, level.y);
    ctx.lineTo(plotRight, level.y);
    ctx.stroke();
    ctx.setLineDash([]);
    const label = `${level.label} ${formatPrice(level.price)}`;
    ctx.font = "11px system-ui";
    const boxX = labelX;
    const boxY = level.labelY - 10;
    ctx.globalAlpha = 0.92;
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(boxX, boxY, labelWidth, 18);
    ctx.globalAlpha = 1;
    ctx.strokeStyle = level.color;
    ctx.strokeRect(boxX, boxY, labelWidth, 18);
    ctx.fillStyle = level.color;
    ctx.textAlign = "left";
    ctx.save();
    ctx.beginPath();
    ctx.rect(boxX + 4, boxY, Math.max(1, labelWidth - 8), 18);
    ctx.clip();
    ctx.fillText(label, boxX + 5, level.labelY + 4);
    ctx.restore();
    ctx.restore();
  });
}

function adjustedPriceLabelPositions(levels) {
  const sorted = [...levels].sort((a, b) => a.y - b.y);
  const minGap = 18;
  sorted.forEach((level, index) => {
    const previous = sorted[index - 1];
    level.labelY = level.y;
    if (previous && level.labelY - previous.labelY < minGap) {
      level.labelY = previous.labelY + minGap;
    }
  });
  for (let index = sorted.length - 2; index >= 0; index -= 1) {
    const next = sorted[index + 1];
    if (next && next.labelY - sorted[index].labelY < minGap) {
      sorted[index].labelY = next.labelY - minGap;
    }
  }
  return sorted;
}

function drawTimeAxis(ctx, candles, xForIndex, volumeBottom, canvasHeight, unit, plotLeft, plotRight) {
  const count = candles.length;
  const visibleIndexes = [];
  for (let index = 0; index < count; index += 1) {
    const x = xForIndex(index);
    if (x >= plotLeft && x <= plotRight) visibleIndexes.push(index);
  }
  if (!visibleIndexes.length) return;
  const pickVisibleIndex = (ratio) => visibleIndexes[Math.floor((visibleIndexes.length - 1) * ratio)];
  const indexes = uniqueAxisIndexes([0, 0.25, 0.5, 0.75, 1].map(pickVisibleIndex));
  ctx.strokeStyle = "#cbd5e1";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(plotLeft, volumeBottom);
  ctx.lineTo(plotRight, volumeBottom);
  ctx.stroke();
  ctx.fillStyle = "#64748b";
  ctx.font = "11px system-ui";
  ctx.textAlign = "center";
  indexes.forEach((index) => {
    const x = xForIndex(index);
    ctx.beginPath();
    ctx.moveTo(x, volumeBottom);
    ctx.lineTo(x, volumeBottom + 4);
    ctx.stroke();
    ctx.fillText(chartTimeLabel(candles[index]?.time, unit), x, canvasHeight - 18);
  });
}

function uniqueAxisIndexes(indexes) {
  return [...new Set(indexes.filter((index) => Number.isFinite(index) && index >= 0))];
}

function chartTimeLabel(value, unit) {
  const text = String(value || "");
  const match = text.match(/(\d{4})-(\d{2})-(\d{2})[T\s](\d{2}):(\d{2})/);
  if (!match) return text.slice(0, 5) || "-";
  const [, year, month, day, hour, minute] = match;
  const key = String(unit || chartUnit);
  if (key === "year") return `${year}.${month}`;
  if (key === "month" || key === "week" || key === "day") return `${month}.${day}`;
  return `${hour}:${minute}`;
}

function formatKrw(value) {
  return money.format(Number(value || 0));
}

function formatSignedKrw(value) {
  const numeric = Number(value || 0);
  const formatted = `${formatKrw(Math.abs(numeric))}원`;
  if (numeric > 0) return `+${formatted}`;
  if (numeric < 0) return `-${formatted}`;
  return formatted;
}

function formatMoneyValue(value, currency = "KRW") {
  const code = String(currency || "KRW").toUpperCase();
  const numeric = Number(value || 0);
  if (code === "USDT" || code === "USD") {
    return `$${formatNumber(numeric, 2)} ${code === "USD" ? "USD" : "USDT"}`;
  }
  return `${formatKrw(numeric)}원`;
}

function formatSignedMoneyValue(value, currency = "KRW") {
  const numeric = Number(value || 0);
  const formatted = formatMoneyValue(Math.abs(numeric), currency);
  if (numeric > 0) return `+${formatted}`;
  if (numeric < 0) return `-${formatted}`;
  return formatted;
}

function formatNumber(value, maximumFractionDigits = 2) {
  return new Intl.NumberFormat("ko-KR", {
    maximumFractionDigits,
  }).format(Number(value || 0));
}

function formatPrice(value) {
  const numeric = Number(value || 0);
  const absolute = Math.abs(numeric);
  let maximumFractionDigits = 0;
  if (absolute > 0 && absolute < 1) maximumFractionDigits = 6;
  else if (absolute < 10) maximumFractionDigits = 3;
  else if (absolute < 100) maximumFractionDigits = 2;
  else if (absolute < 1000) maximumFractionDigits = 1;
  return new Intl.NumberFormat("ko-KR", {
    maximumFractionDigits,
  }).format(numeric);
}

function formatOptionalPrice(value) {
  const numeric = Number(value || 0);
  return numeric > 0 ? formatPrice(numeric) : "-";
}

function formatFuturesPrice(value) {
  const numeric = Number(value || 0);
  const absolute = Math.abs(numeric);
  if (!Number.isFinite(numeric)) return "-";
  let minimumFractionDigits = 0;
  let maximumFractionDigits = 2;
  if (absolute >= 100) {
    minimumFractionDigits = 1;
    maximumFractionDigits = 2;
  } else if (absolute >= 1) {
    maximumFractionDigits = 4;
  } else if (absolute > 0) {
    maximumFractionDigits = 8;
  }
  return new Intl.NumberFormat("ko-KR", {
    minimumFractionDigits,
    maximumFractionDigits,
  }).format(numeric);
}

function formatOptionalFuturesPrice(value) {
  const numeric = Number(value || 0);
  return numeric > 0 ? formatFuturesPrice(numeric) : "-";
}

function formatFlowPrice(value, currency = "KRW") {
  return String(currency || "").toUpperCase() === "USDT" ? formatFuturesPrice(value) : formatPrice(value);
}

function formatFlowOptionalPrice(value, currency = "KRW") {
  return String(currency || "").toUpperCase() === "USDT" ? formatOptionalFuturesPrice(value) : formatOptionalPrice(value);
}

function formatCompactKrw(value) {
  return new Intl.NumberFormat("ko-KR", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(Number(value || 0));
}

function formatCompactUsdt(value) {
  return `$${new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(Number(value || 0))}`;
}

function formatSigned(value) {
  if (value > 0) return `+${number.format(value)}`;
  return number.format(value);
}

function formatSignedPercent2(value) {
  if (value > 0) return `+${percent2.format(value)}`;
  return percent2.format(value);
}

function formatScore(value) {
  if (value === undefined || value === null || value === "") return "-";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return String(value);
  return numeric.toFixed(3);
}

function formatRecentTrade(row) {
  if (!row.lastTradePrice || row.lastTradePrice === "0") return "-";
  const side = row.lastTradeSide === "BID" ? "매수" : row.lastTradeSide === "ASK" ? "매도" : "";
  return `${formatPrice(row.lastTradePrice)} ${side}`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatTime(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function formatDateShort(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("ko-KR", {
    year: "2-digit",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatMonthDay(value) {
  if (!value) return "-";
  const date = new Date(String(value).length === 10 ? `${value}T00:00:00+09:00` : value);
  return new Intl.DateTimeFormat("ko-KR", {
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}

function parsePlaybackTime(value) {
  if (!value) return Number.NaN;
  const text = String(value);
  const normalized = /([zZ]|[+-]\d{2}:\d{2})$/.test(text) ? text : `${text}+09:00`;
  return Date.parse(normalized);
}

function formatPlaybackTime(value) {
  const timestamp = parsePlaybackTime(value);
  if (!Number.isFinite(timestamp)) return "-";
  return new Intl.DateTimeFormat("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(timestamp));
}

function formatRatioPercent(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "-";
  const pct = numeric * 100;
  return `${percent2.format(pct)}%`;
}

function changeLabel(change) {
  if (change === "RISE") return "상승";
  if (change === "FALL") return "하락";
  return "보합";
}

function setBusy(button, busy) {
  if (!button) return;
  button.disabled = busy;
  button.style.opacity = busy ? "0.62" : "";
}

function initializeDashboardSectionDrag() {
  const main = document.querySelector("main");
  if (!main) return;
  main.classList.add("section-drag-enabled");
  dashboardSections().forEach((section, index) => {
    section.classList.add("dashboard-section");
    section.dataset.dashboardSection = section.dataset.dashboardSection || dashboardSectionKey(section, index);
    const meta = dashboardSectionMeta[section.dataset.dashboardSection];
    if (meta) section.dataset.sectionTier = meta.tier;
    addDashboardDragHandle(section);
    section.addEventListener("dragover", handleDashboardSectionDragOver);
    section.addEventListener("dragenter", handleDashboardSectionDragEnter);
    section.addEventListener("dragleave", handleDashboardSectionDragLeave);
    section.addEventListener("drop", handleDashboardSectionDrop);
  });
  applySavedDashboardSectionOrder();
  applyDashboardSectionOrders();
}

function dashboardSections() {
  return Array.from(document.querySelectorAll("main > section"));
}

function dashboardSectionKey(section, index) {
  const knownClass = Object.keys(dashboardSectionLabels).find((className) => section.classList.contains(className));
  return knownClass || `section-${index}`;
}

function dashboardSectionLabel(section) {
  const key = section.dataset.dashboardSection || dashboardSectionKey(section, 0);
  if (dashboardSectionLabels[key]) return dashboardSectionLabels[key];
  const heading = section.querySelector("h2");
  return heading?.textContent?.trim() || "섹션";
}

function addDashboardDragHandle(section) {
  if (section.querySelector(":scope > .section-drag-handle")) return;
  const label = dashboardSectionLabel(section);
  const meta = dashboardSectionMeta[section.dataset.dashboardSection] || {};
  const handle = document.createElement("button");
  handle.className = "section-drag-handle";
  handle.type = "button";
  handle.draggable = false;
  handle.setAttribute("aria-label", `${label} 섹션 위치 이동`);
  handle.title = `${label} 섹션 위치 이동`;
  handle.innerHTML = `
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M8 6h8M8 12h8M8 18h8"></path>
    </svg>
    <span>${escapeHtml(label)}</span>
    <em>${escapeHtml(meta.tierLabel || "섹션")}</em>
  `;
  handle.addEventListener("pointerdown", (event) => handleDashboardSectionPointerDown(event, section));
  section.insertBefore(handle, section.firstElementChild);
}

function applySavedDashboardSectionOrder() {
  const main = document.querySelector("main");
  const savedOrder = loadDashboardSectionOrder();
  const targetOrder = savedOrder.length ? savedOrder : dashboardDefaultSectionOrder;
  if (!main || !targetOrder.length) return;
  const sections = dashboardSections();
  const byKey = new Map(sections.map((section) => [section.dataset.dashboardSection, section]));
  const ordered = targetOrder.map((key) => byKey.get(key)).filter(Boolean);
  const rest = sections.filter((section) => !targetOrder.includes(section.dataset.dashboardSection));
  [...ordered, ...rest].forEach((section) => main.appendChild(section));
}

function loadDashboardSectionOrder() {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(dashboardSectionOrderKey) || "[]");
    return Array.isArray(parsed) ? parsed.filter(Boolean) : [];
  } catch {
    return [];
  }
}

function saveDashboardSectionOrder() {
  const order = dashboardSections().map((section) => section.dataset.dashboardSection);
  window.localStorage.setItem(dashboardSectionOrderKey, JSON.stringify(order));
}

function resetDashboardSectionOrder() {
  window.localStorage.removeItem(dashboardSectionOrderKey);
  applySavedDashboardSectionOrder();
  applyDashboardSectionOrders();
  showToast("핵심 운영 배치로 되돌렸습니다");
}

function dashboardSectionOrderSignature() {
  return dashboardSections().map((section) => section.dataset.dashboardSection).join("|");
}

function applyDashboardSectionOrders() {
  dashboardSections().forEach((section, index) => {
    section.style.order = String(index);
  });
}

function handleDashboardSectionPointerDown(event, section) {
  if (event.button !== 0) return;
  const handle = event.currentTarget;
  dashboardPointerDrag = {
    section,
    handle,
    pointerId: event.pointerId,
    startY: event.clientY,
    startOrder: dashboardSectionOrderSignature(),
    moved: false,
  };
  handle.setPointerCapture?.(event.pointerId);
  window.addEventListener("pointermove", handleDashboardSectionPointerMove);
  window.addEventListener("pointerup", handleDashboardSectionPointerEnd);
  window.addEventListener("pointercancel", handleDashboardSectionPointerEnd);
  event.preventDefault();
}

function handleDashboardSectionPointerMove(event) {
  if (!dashboardPointerDrag) return;
  const { section } = dashboardPointerDrag;
  if (!dashboardPointerDrag.moved) {
    if (Math.abs(event.clientY - dashboardPointerDrag.startY) < 6) return;
    dashboardPointerDrag.moved = true;
    draggedDashboardSection = section;
    section.classList.add("dragging");
    document.querySelector("main")?.classList.add("dragging-sections");
  }
  autoScrollDashboardDrag(event.clientY);
  const target = dashboardSectionAtPoint(event.clientX, event.clientY, section);
  if (!target) {
    clearDashboardDragTarget();
    return;
  }
  moveDashboardSectionToward(section, target, dashboardDropPosition(event, target));
}

function handleDashboardSectionPointerEnd(event) {
  if (!dashboardPointerDrag) return;
  const { section, handle, pointerId, startOrder, moved } = dashboardPointerDrag;
  handle.releasePointerCapture?.(pointerId);
  window.removeEventListener("pointermove", handleDashboardSectionPointerMove);
  window.removeEventListener("pointerup", handleDashboardSectionPointerEnd);
  window.removeEventListener("pointercancel", handleDashboardSectionPointerEnd);
  section.classList.remove("dragging");
  document.querySelector("main")?.classList.remove("dragging-sections");
  clearDashboardDragTarget();
  draggedDashboardSection = null;
  dashboardPointerDrag = null;
  applyDashboardSectionOrders();
  const changed = startOrder !== dashboardSectionOrderSignature();
  if (moved && changed) {
    saveDashboardSectionOrder();
    showToast("섹션 순서를 저장했습니다");
  }
  event.preventDefault();
}

function dashboardSectionAtPoint(clientX, clientY, excludedSection) {
  return document.elementsFromPoint(clientX, clientY)
    .map((element) => element.closest?.("main > section.dashboard-section"))
    .find((section) => section && section !== excludedSection) || null;
}

function moveDashboardSectionToward(section, target, position) {
  clearDashboardDragTarget();
  dragOverDashboardSection = target;
  target.classList.add(position === "before" ? "drag-target-before" : "drag-target-after");
  const main = target.parentElement;
  if (!main) return;
  if (position === "before") main.insertBefore(section, target);
  else main.insertBefore(section, target.nextElementSibling);
  applyDashboardSectionOrders();
}

function autoScrollDashboardDrag(clientY) {
  const edge = 84;
  if (clientY < edge) window.scrollBy(0, -18);
  else if (clientY > window.innerHeight - edge) window.scrollBy(0, 18);
}

function handleDashboardSectionDragStart(event, section) {
  draggedDashboardSection = section;
  section.classList.add("dragging");
  document.querySelector("main")?.classList.add("dragging-sections");
  event.dataTransfer.effectAllowed = "move";
  event.dataTransfer.setData("text/plain", section.dataset.dashboardSection || "");
}

function handleDashboardSectionDragEnter(event) {
  const section = event.currentTarget;
  if (!draggedDashboardSection || section === draggedDashboardSection) return;
  event.preventDefault();
}

function handleDashboardSectionDragOver(event) {
  const section = event.currentTarget;
  if (!draggedDashboardSection || section === draggedDashboardSection) return;
  event.preventDefault();
  event.dataTransfer.dropEffect = "move";
  const position = dashboardDropPosition(event, section);
  moveDashboardSectionToward(draggedDashboardSection, section, position);
}

function handleDashboardSectionDragLeave(event) {
  const section = event.currentTarget;
  if (section.contains(event.relatedTarget)) return;
  section.classList.remove("drag-target-before", "drag-target-after");
  if (dragOverDashboardSection === section) dragOverDashboardSection = null;
}

function handleDashboardSectionDrop(event) {
  if (!draggedDashboardSection) return;
  event.preventDefault();
  clearDashboardDragTarget();
  saveDashboardSectionOrder();
  applyDashboardSectionOrders();
  showToast("섹션 순서를 저장했습니다");
}

function handleDashboardSectionDragEnd() {
  draggedDashboardSection?.classList.remove("dragging");
  document.querySelector("main")?.classList.remove("dragging-sections");
  draggedDashboardSection = null;
  clearDashboardDragTarget();
  saveDashboardSectionOrder();
  applyDashboardSectionOrders();
}

function dashboardDropPosition(event, section) {
  const rect = section.getBoundingClientRect();
  return event.clientY < rect.top + rect.height / 2 ? "before" : "after";
}

function clearDashboardDragTarget() {
  dragOverDashboardSection?.classList.remove("drag-target-before", "drag-target-after");
  dragOverDashboardSection = null;
}

let toastTimer = 0;
function showToast(message) {
  window.clearTimeout(toastTimer);
  els.toast.textContent = message;
  els.toast.classList.add("show");
  toastTimer = window.setTimeout(() => els.toast.classList.remove("show"), 2600);
}

els.refreshButton.addEventListener("click", () => refreshStatus({ loadDetails: true }));
els.strategySelect.addEventListener("change", selectStrategy);
els.strategyAutoToggle.addEventListener("change", toggleAutoStrategy);
els.runOnceButton.addEventListener("click", runOnce);
els.scanButton.addEventListener("click", scanOnce);
els.autoStartButton.addEventListener("click", startAutoRun);
els.autoStopButton.addEventListener("click", stopAutoRun);
els.liveCheckButton.addEventListener("click", checkLiveReadiness);
els.livePreviewButton.addEventListener("click", previewLiveOrder);
els.liveTestOrderButton.addEventListener("click", testLiveOrder);
els.backtestButton.addEventListener("click", runBacktestReport);
els.simulationButton.addEventListener("click", () => loadLatestSimulation({ toast: true }));
els.playbackLoadButton.addEventListener("click", () => loadSimulationPlayback({ toast: true }));
els.playbackStartButton.addEventListener("click", startSimulationPlayback);
els.playbackPauseButton.addEventListener("click", pauseSimulationPlayback);
els.eventsButton.addEventListener("click", loadEventLog);
els.exchangesButton.addEventListener("click", checkExchanges);
els.binancePaperButton.addEventListener("click", runBinanceFuturesPaper);
els.portfolioFlowRows?.addEventListener("pointerdown", handleManualFuturesControlPress, true);
els.portfolioFlowRows?.addEventListener("input", handleManualFuturesSizingInput);
els.exchangeModeButton.addEventListener("click", applyExchangeMode);
els.exchangeModeSelect.addEventListener("change", applyExchangeMode);
els.dbButton.addEventListener("click", checkDatabase);
els.alertsButton.addEventListener("click", checkAlerts);
els.recommendOnlyButton.addEventListener("click", toggleRecommendOnlyMode);
els.recommendAllButton.addEventListener("click", recommendAllMarkets);
els.excludeAllButton.addEventListener("click", excludeAllMarkets);
els.recommendedClearButton.addEventListener("click", clearRecommendedMarkets);
els.learnButton.addEventListener("click", () => runHistoricalLearning("watchlist"));
els.learnAllButton.addEventListener("click", () => runHistoricalLearning("all_krw"));
els.allocationPreviewButton.addEventListener("click", previewAllocation);
els.allocationRunButton.addEventListener("click", runDynamicAllocation);
els.realtimeDecisionPreviewButton.addEventListener("click", previewRealtimeDecision);
els.realtimeDecisionRunButton.addEventListener("click", runRealtimeDecision);
els.pmAnalyzeButton?.addEventListener("click", loadPmAnalysis);
els.pmChatForm?.addEventListener("submit", sendPmChat);
els.pmSchedulerRefreshButton?.addEventListener("click", loadPmScheduler);
els.intelRefreshButton?.addEventListener("click", () => loadMarketIntel({ manual: true }));
els.orderbookButton.addEventListener("click", () => loadOrderbookAnalysis(selectedMarket));
els.chartZoomInButton?.addEventListener("click", () => changeChartZoom(chartZoomKey(els.chart, { market: selectedMarket, unit: chartUnit }), "in"));
els.chartZoomOutButton?.addEventListener("click", () => changeChartZoom(chartZoomKey(els.chart, { market: selectedMarket, unit: chartUnit }), "out"));
els.chartZoomResetButton?.addEventListener("click", () => changeChartZoom(chartZoomKey(els.chart, { market: selectedMarket, unit: chartUnit }), "reset"));
els.chartPanOlderButton?.addEventListener("click", () => changeChartPan(chartZoomKey(els.chart, { market: selectedMarket, unit: chartUnit }), "older"));
els.chartPanNewerButton?.addEventListener("click", () => changeChartPan(chartZoomKey(els.chart, { market: selectedMarket, unit: chartUnit }), "newer"));
els.chartPanLatestButton?.addEventListener("click", () => changeChartPan(chartZoomKey(els.chart, { market: selectedMarket, unit: chartUnit }), "latest"));
els.portfolioChartZoomInButton?.addEventListener("click", () => changeChartZoom(chartZoomKey(els.portfolioChart, { portfolio: true, unit: portfolioChartUnit }), "in"));
els.portfolioChartZoomOutButton?.addEventListener("click", () => changeChartZoom(chartZoomKey(els.portfolioChart, { portfolio: true, unit: portfolioChartUnit }), "out"));
els.portfolioChartZoomResetButton?.addEventListener("click", () => changeChartZoom(chartZoomKey(els.portfolioChart, { portfolio: true, unit: portfolioChartUnit }), "reset"));
els.chartUnitButtons.forEach((button) => {
  button.addEventListener("click", () => setChartUnit(button.dataset.unit));
});
els.holdingChartUnitButtons.forEach((button) => {
  button.addEventListener("click", () => setHoldingChartUnit(button.dataset.unit));
});
els.portfolioChartUnitButtons.forEach((button) => {
  button.addEventListener("click", () => setPortfolioChartUnit(button.dataset.unit));
});
els.holdingCharts?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-chart-zoom-action]");
  if (!button) return;
  event.stopPropagation();
  const card = button.closest(".holding-chart-card");
  const canvas = card?.querySelector(".holding-chart");
  if (!card || !canvas) return;
  const key = canvas.dataset.chartZoomKey || chartZoomKey(canvas, { compact: true, market: card.dataset.market, unit: holdingChartUnit });
  changeChartZoom(key, button.dataset.chartZoomAction);
});
document.querySelectorAll(".sort-header").forEach((button) => {
  button.addEventListener("click", () => setMarketSort(button.dataset.sort));
});
els.stopButton.addEventListener("click", emergencyStop);
els.resumeButton.addEventListener("click", resumePaper);
window.addEventListener("resize", () => {
  const row = latestStatus?.markets?.find((item) => item.market === selectedMarket);
  if (latestChart.length) drawTradeChart(latestChart, els.chart, { market: selectedMarket, row, unit: chartUnit });
  else if (latestStatus) drawTradeChart(latestStatus.chart, els.chart, { market: selectedMarket, row, unit: chartUnit });
  redrawPortfolioChart();
  redrawHoldingCharts();
});

function setActiveDashboardNav(targetKey) {
  document.querySelectorAll("[data-section-target]").forEach((item) => {
    item.classList.toggle("active", item.dataset.sectionTarget === targetKey);
  });
}

function scrollToDashboardSection(targetKey) {
  if (targetKey === "overview-panel") {
    window.scrollTo({ top: 0, behavior: "smooth" });
    setActiveDashboardNav(targetKey);
    return;
  }
  const target = document.querySelector(`main > section.${targetKey}`);
  if (!target) return;
  target.scrollIntoView({ behavior: "smooth", block: "start" });
  setActiveDashboardNav(targetKey);
}

document.querySelectorAll("[data-section-target]").forEach((button) => {
  button.addEventListener("click", () => scrollToDashboardSection(button.dataset.sectionTarget));
});

document.querySelectorAll("[data-reset-section-order]").forEach((button) => {
  button.addEventListener("click", resetDashboardSectionOrder);
});

initializeDashboardSectionDrag();
loadStrategies();
updateChartUnitButtons();
updateHoldingChartUnitButtons();
updatePortfolioChartUnitButtons();
refreshStatus({ loadDetails: true });
loadLearningStatus();
loadLatestSimulation({ setButtonBusy: false });
loadSimulationPlayback({ setButtonBusy: false });
loadAllocationStatus();
loadRealtimeDecisionStatus();
loadPmChat();
loadPmScheduler();
loadMarketIntel();
window.setInterval(() => refreshStatus({ loadDetails: false }), 1000);
window.setInterval(() => {
  if (latestStatus && selectedMarket) loadTradingChart(selectedMarket);
}, 30000);
window.setInterval(() => loadHoldingCharts(), 60000);
window.setInterval(() => loadPortfolioChart(), 15000);
window.setInterval(() => loadPmScheduler(), 60000);
window.setInterval(() => loadMarketIntel(), 60000);
window.setInterval(() => {
  if (latestStatus && selectedMarket) loadOrderbookAnalysis(selectedMarket);
}, 15000);
window.setInterval(() => loadLatestSimulation({ setButtonBusy: false }), 60000);
window.setInterval(loadAllocationStatus, 30000);
window.setInterval(loadRealtimeDecisionStatus, 1000);
