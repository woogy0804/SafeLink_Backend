const form = document.querySelector("#scan-form");
const input = document.querySelector("#url-input");
const button = document.querySelector("#scan-button");
const formMessage = document.querySelector("#form-message");
const resultPanel = document.querySelector("#result-panel");
const resultTitle = document.querySelector("#result-title");
const resultUrl = document.querySelector("#result-url");
const resultMessage = document.querySelector("#result-message");
const resultIcon = document.querySelector("#result-icon");
const scoreValue = document.querySelector("#score-value");
const scoreRing = document.querySelector("#score-ring");
const modelUsed = document.querySelector("#model-used");
const grayZone = document.querySelector("#gray-zone");
const featureToggle = document.querySelector("#feature-toggle");
const featureGrid = document.querySelector("#feature-grid");

const defaultMessage = "URL은 서버에서 안전하게 분석되며 별도로 저장하지 않습니다.";

const riskPresentation = {
  safe: {
    title: "안전한 링크입니다",
    icon: "✓",
    color: "#74f0b1",
  },
  suspicious: {
    title: "주의가 필요한 링크입니다",
    icon: "!",
    color: "#f4c96b",
  },
  phishing: {
    title: "피싱 위험이 높습니다",
    icon: "×",
    color: "#ff6b6b",
  },
};

const featureNames = {
  SSLfinal_State: "SSL 인증서",
  URL_of_Anchor: "앵커 링크",
  web_traffic: "웹 트래픽",
  Prefix_Suffix: "도메인 하이픈",
  having_Sub_Domain: "서브도메인",
  Links_in_tags: "태그 외부 링크",
  Links_pointing_to_page: "백링크",
  Request_URL: "리소스 요청",
  SFH: "폼 전송 경로",
  age_of_domain: "도메인 생성일",
  Domain_registeration_length: "도메인 계약 기간",
  having_IP_Address: "IP 주소 사용",
};

const modelNames = {
  logistic_regression_v1: "Logistic Regression",
  random_forest_v1: "Random Forest",
  temporary_rule: "기본 판별 규칙",
};

function normalizeUrl(value) {
  const trimmed = value.trim();
  if (!trimmed) return "";
  if (!/^https?:\/\//i.test(trimmed)) {
    return `https://${trimmed}`;
  }
  return trimmed;
}

function setLoading(isLoading) {
  button.disabled = isLoading;
  button.classList.toggle("is-loading", isLoading);
  input.disabled = isLoading;
  document.querySelector(".button-label").textContent = isLoading
    ? "분석 중"
    : "URL 검사";
}

function setFormMessage(message, isError = false) {
  formMessage.textContent = message;
  formMessage.classList.toggle("is-error", isError);
}

function featureState(value) {
  if (value === 1) {
    return { className: "safe", symbol: "✓", label: "정상" };
  }
  if (value === -1) {
    return { className: "danger", symbol: "!", label: "위험" };
  }
  return { className: "suspicious", symbol: "·", label: "확인 필요" };
}

function renderFeatures(features = {}) {
  featureGrid.replaceChildren();

  Object.entries(features).forEach(([key, value]) => {
    const state = featureState(value);
    const item = document.createElement("div");
    item.className = "feature-item";

    const badge = document.createElement("span");
    badge.className = `feature-state ${state.className}`;
    badge.textContent = state.symbol;

    const copy = document.createElement("div");
    const name = document.createElement("strong");
    const status = document.createElement("small");
    name.textContent = featureNames[key] || key;
    status.textContent = state.label;
    copy.append(name, status);
    item.append(badge, copy);
    featureGrid.append(item);
  });
}

function showResult(data) {
  const presentation = riskPresentation[data.risk] || riskPresentation.suspicious;
  const score = Math.max(0, Math.min(1, Number(data.score) || 0));
  const scorePercent = Math.round(score * 100);

  resultPanel.style.setProperty("--result-color", presentation.color);
  resultTitle.textContent = presentation.title;
  resultUrl.textContent = data.url;
  resultUrl.title = data.url;
  resultMessage.textContent = data.message || "분석 결과를 확인해 주세요.";
  resultIcon.textContent = presentation.icon;
  scoreValue.textContent = `${scorePercent}%`;
  scoreRing.style.setProperty("--score", `${scorePercent * 3.6}deg`);
  modelUsed.textContent = modelNames[data.model_used] || data.model_used || "AI 모델";
  grayZone.hidden = !data.gray_zone;
  renderFeatures(data.features);

  featureToggle.setAttribute("aria-expanded", "false");
  featureGrid.hidden = true;
  document.querySelector(".toggle-icon").textContent = "+";
  resultPanel.hidden = false;
  resultPanel.scrollIntoView({ behavior: "smooth", block: "center" });
}

featureToggle.addEventListener("click", () => {
  const isExpanded = featureToggle.getAttribute("aria-expanded") === "true";
  featureToggle.setAttribute("aria-expanded", String(!isExpanded));
  featureGrid.hidden = isExpanded;
  document.querySelector(".toggle-icon").textContent = isExpanded ? "+" : "−";
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const url = normalizeUrl(input.value);

  if (!url) {
    setFormMessage("검사할 URL을 입력해 주세요.", true);
    input.focus();
    return;
  }

  input.value = url;
  setLoading(true);
  setFormMessage("도메인과 페이지의 보안 신호를 분석하고 있습니다.");
  resultPanel.hidden = true;

  try {
    const response = await fetch("/detect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error?.message || "URL 검사에 실패했습니다.");
    }

    showResult(data);
    setFormMessage(defaultMessage);
  } catch (error) {
    setFormMessage(
      error instanceof Error
        ? error.message
        : "서버와 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.",
      true,
    );
  } finally {
    setLoading(false);
  }
});
