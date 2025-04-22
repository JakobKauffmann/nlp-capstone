document.addEventListener("DOMContentLoaded", function () {
  // --- DOM Elements ---
  const startAnalyzingBtn = document.getElementById("startAnalyzing");
  const landingPage = document.getElementById("landingPage");
  const analysisPage = document.getElementById("analysisPage");
  const inputTypeBtns = document.querySelectorAll(".input-type-btn");
  const contentInput = document.getElementById("contentInput");
  const charCount = document.getElementById("charCount");
  const charLimit = document.getElementById("charLimit");
  const analyzeButton = document.getElementById("analyzeButton");
  const analyzeButtonText = analyzeButton.querySelector(".button-text");
  const analyzeButtonIcon = analyzeButton.querySelector(".button-icon");
  const analyzeButtonSpinner = analyzeButton.querySelector(".fa-cogs");
  const loadingState = document.getElementById("loadingState");
  const loadingMessage = document.getElementById("loadingMessage");
  const errorState = document.getElementById("errorState");
  const errorMessage = document.getElementById("errorMessage");
  const tryAgainButton = document.getElementById("tryAgainButton");
  const resultsSection = document.getElementById("resultsSection");
  const newAnalysisBtn = document.getElementById("newAnalysisBtn");
  const analysisSource = document.getElementById("analysisSource");

  // Result Display Elements
  const biasLabel = document.getElementById("biasLabel");
  const biasScoreEl = document.getElementById("biasScore");
  const biasIcon = document.getElementById("biasIcon");
  const biasIconBg = document.getElementById("biasIconBg");
  const biasIndicatorNeedle = document.getElementById("biasIndicatorNeedle");

  const sentimentLabel = document.getElementById("sentimentLabel");
  const sentimentScoreEl = document.getElementById("sentimentScore");
  const sentimentIcon = document.getElementById("sentimentIcon");
  const sentimentIconBg = document.getElementById("sentimentIconBg");
  const sentimentIndicatorNeedle = document.getElementById(
    "sentimentIndicatorNeedle",
  );

  // Credibility (Text Only)
  // const credibilityLabel = document.getElementById('credibilityLabel'); // Removed
  // const credibilityIndicator = document.getElementById('credibilityIndicator'); // Removed
  const credibilityAssessmentTextEl = document.getElementById(
    "credibilityAssessmentText",
  ); // Get the text element

  // Tabs & Content Areas
  const analysisTabs = document.querySelectorAll(".analysis-tab");
  const analysisContents = document.querySelectorAll(".analysis-content");
  const summaryTab = document.getElementById("summaryTab");
  const visualsTab = document.getElementById("visualsTab");
  const findingsTab = document.getElementById("findingsTab");
  const summaryContent = document.getElementById("summaryContent");
  const visualsContent = document.getElementById("visualsContent");
  const findingsContent = document.getElementById("findingsContent");

  // Content Elements within Tabs
  const contentSummary = document.getElementById("contentSummary");
  const keyFindingsEl = document.getElementById("keyFindings");
  const biasIndicatorsEl = document.getElementById("biasIndicators");
  const recommendedSearchesEl = document.getElementById("recommendedSearches");

  // Plotly Chart Containers
  const sentimentChartContainer = document.getElementById(
    "sentimentChartContainer",
  );
  const biasChartContainer = document.getElementById("biasChartContainer");

  // --- State ---
  let currentInputType = "url";
  const MAX_CHARS = 8000;

  // --- Initialization ---
  if (charLimit) charLimit.textContent = MAX_CHARS;
  activateTab(summaryTab);

  // --- Functions (updateCharCounter, setAnalyzeButtonLoading, showSection, activateTab, updateBiasDisplay, updateSentimentDisplay, Plotly functions remain the same) ---
  const updateCharCounter = () => {
    const currentLength = contentInput.value.length;
    charCount.textContent = currentLength;
    analyzeButton.disabled = currentLength > MAX_CHARS; // Disable if over limit
    charCount.classList.toggle("text-red-500", currentLength > MAX_CHARS);
    charCount.classList.toggle("font-bold", currentLength > MAX_CHARS);
  };

  const setAnalyzeButtonLoading = (isLoading) => {
    analyzeButton.disabled = isLoading; // Disable button when loading
    analyzeButtonText.textContent = isLoading ? "Analyzing..." : "Analyze";
    analyzeButtonIcon.classList.toggle("hidden", isLoading);
    analyzeButtonSpinner.classList.toggle("hidden", !isLoading);
    // Re-enable based on char count only if NOT loading
    if (!isLoading) {
      updateCharCounter();
    }
  };

  const showSection = (section) => {
    loadingState.classList.add("hidden");
    resultsSection.classList.add("hidden");
    errorState.classList.add("hidden");
    const inputForm = analysisPage.querySelector(
      ".analysis-page-card:not(#loadingState):not(#errorState):not(#resultsSection)",
    ); // More specific selector
    if (inputForm) {
      inputForm.classList.toggle("hidden", section !== "input");
    }
    if (section === "loading") loadingState.classList.remove("hidden");
    else if (section === "results") resultsSection.classList.remove("hidden");
    else if (section === "error") errorState.classList.remove("hidden");
    else if (section === "input" && inputForm)
      inputForm.classList.remove("hidden");
  };

  function activateTab(activeTab) {
    if (!activeTab) return;
    analysisTabs.forEach((tab) => {
      const contentId = tab.id.replace("Tab", "Content");
      const content = document.getElementById(contentId);
      const isActive = tab === activeTab;
      tab.classList.toggle("border-blue-500", isActive); // Use theme accent color for border
      tab.classList.toggle("text-blue-600", isActive);
      tab.classList.toggle("dark:border-blue-400", isActive);
      tab.classList.toggle("dark:text-blue-400", isActive);
      tab.classList.toggle("border-transparent", !isActive);
      tab.classList.toggle("text-gray-500", !isActive);
      tab.classList.toggle("hover:text-gray-700", !isActive);
      tab.classList.toggle("hover:border-gray-300", !isActive);
      tab.classList.toggle("dark:text-gray-400", !isActive);
      tab.classList.toggle("dark:hover:text-gray-200", !isActive);
      tab.classList.toggle("dark:hover:border-gray-500", !isActive);
      tab.setAttribute("aria-current", isActive ? "page" : "false");
      if (content) content.classList.toggle("hidden", !isActive);
    });
    // Resize Plotly charts when their container becomes visible
    setTimeout(() => {
      if (
        typeof Plotly !== "undefined" &&
        visualsContent &&
        !visualsContent.classList.contains("hidden")
      ) {
        try {
          Plotly.Plots.resize(sentimentChartContainer);
        } catch (e) {
          console.warn("Resize error", e);
        }
        try {
          Plotly.Plots.resize(biasChartContainer);
        } catch (e) {
          console.warn("Resize error", e);
        }
      }
    }, 50);
  }

  const updateBiasDisplay = (label = "N/A", score = 0) => {
    let colorClass = "text-gray-700 dark:text-gray-300";
    let iconBgClass = "bg-gray-100 dark:bg-gray-600";
    let iconColorClass = "text-gray-500 dark:text-gray-400";
    let needlePos = 50;
    label = label.toString();
    score = Number(score) || 0;
    if (label === "Left") {
      colorClass = "text-blue-600 dark:text-blue-400";
      iconBgClass = "bg-blue-100 dark:bg-opacity-20";
      iconColorClass = "text-blue-500 dark:text-blue-400";
      needlePos = 5 + (score / 100) * 28;
    } else if (label === "Right") {
      colorClass = "text-red-600 dark:text-red-400";
      iconBgClass = "bg-red-100 dark:bg-opacity-20";
      iconColorClass = "text-red-500 dark:text-red-400";
      needlePos = 67 + (score / 100) * 28;
    } else if (label === "Center") {
      colorClass = "text-yellow-600 dark:text-yellow-400";
      iconBgClass = "bg-yellow-100 dark:bg-opacity-20";
      iconColorClass = "text-yellow-500 dark:text-yellow-400";
      needlePos = 34 + (score / 100) * 32;
    } else if (label === "Error") {
      colorClass = "text-red-600 dark:text-red-400";
      iconBgClass = "bg-red-100 dark:bg-opacity-20";
      iconColorClass = "text-red-500 dark:text-red-400";
      needlePos = 50;
      score = 0;
    }
    biasLabel.textContent = label;
    biasLabel.className = `text-2xl font-semibold mb-1 ${colorClass}`;
    biasScoreEl.textContent =
      label !== "Error" ? `Confidence: ${score}%` : "Analysis Failed";
    biasIconBg.className = `p-2 rounded-full mr-3 ${iconBgClass}`;
    biasIcon.className = `fas fa-balance-scale ${iconColorClass}`;
    biasIndicatorNeedle.style.left = `${Math.max(2, Math.min(98, needlePos))}%`;
  };

  const updateSentimentDisplay = (label = "N/A", score = 0) => {
    let colorClass = "text-gray-700 dark:text-gray-300";
    let iconClass = "fa-meh";
    let iconBgClass = "bg-gray-100 dark:bg-gray-600";
    let iconColorClass = "text-gray-500 dark:text-gray-400";
    let needlePos = 50;
    label = label.toString();
    score = Number(score) || 0;
    if (label === "Positive") {
      colorClass = "text-green-600 dark:text-green-400";
      iconClass = "fa-smile";
      iconBgClass = "bg-green-100 dark:bg-opacity-20";
      iconColorClass = "text-green-500 dark:text-green-400";
      needlePos = 50 + (score / 100) * 48;
    } else if (label === "Negative") {
      colorClass = "text-red-600 dark:text-red-400";
      iconClass = "fa-frown";
      iconBgClass = "bg-red-100 dark:bg-opacity-20";
      iconColorClass = "text-red-500 dark:text-red-400";
      needlePos = 50 - (score / 100) * 48;
    } else if (label === "Neutral") {
      needlePos = 40 + (score / 100) * 20; // Keep neutral centered
    } else if (label === "Error") {
      colorClass = "text-red-600 dark:text-red-400";
      iconClass = "fa-exclamation-circle";
      iconBgClass = "bg-red-100 dark:bg-opacity-20";
      iconColorClass = "text-red-500 dark:text-red-400";
      needlePos = 50;
      score = 0;
    }
    sentimentLabel.textContent = label;
    sentimentLabel.className = `text-2xl font-semibold mb-1 ${colorClass}`;
    sentimentScoreEl.textContent =
      label !== "Error" ? `Confidence: ${score}%` : "Analysis Failed";
    sentimentIconBg.className = `p-2 rounded-full mr-3 ${iconBgClass}`;
    sentimentIcon.className = `fas ${iconClass} ${iconColorClass}`;
    sentimentIndicatorNeedle.style.left = `${Math.max(2, Math.min(98, needlePos))}%`;
  };

  // --- Plotly Functions ---
  const getPlotlyLayout = (title) => {
    const isDark = document.documentElement.classList.contains("dark");
    // Use CSS variables defined in style.css for colors
    const paperColor = isDark
      ? "rgba(49, 50, 68, 0.8)"
      : "rgba(230, 233, 239, 0.8)"; // Surface0 / Mantle with alpha
    const fontColor = isDark ? "#cdd6f4" : "#4c4f69"; // Text
    const gridColor = isDark ? "#45475a" : "#acb0be"; // Surface1 / Overlay0
    const legendBgColor = isDark
      ? "rgba(30, 30, 46, 0.6)"
      : "rgba(239, 241, 245, 0.6)"; // Base with alpha
    const legendBorderColor = isDark ? "#6c7086" : "#9ca0b0"; // Overlay0 / Overlay0(Latte)

    return {
      title: { text: title, font: { color: fontColor, size: 16 } },
      paper_bgcolor: paperColor,
      plot_bgcolor: paperColor, // Match paper or make transparent
      font: { color: fontColor },
      showlegend: true,
      legend: {
        bgcolor: legendBgColor,
        bordercolor: legendBorderColor,
        borderwidth: 1,
        x: 0.5,
        xanchor: "center",
        y: -0.15,
        orientation: "h", // Position below
      },
      margin: { l: 30, r: 30, t: 60, b: 60 }, // Increased bottom margin for legend
      height: 320, // Adjust as needed
    };
  };

  window.updatePlotlyLayoutTheme = () => {
    // Keep this for theme toggling
    if (typeof Plotly !== "undefined") {
      try {
        Plotly.relayout(
          "sentimentChart",
          getPlotlyLayout("Sentiment Distribution"),
        );
      } catch (e) {}
      try {
        Plotly.relayout(
          "biasChart",
          getPlotlyLayout("Political Bias Distribution"),
        );
      } catch (e) {}
    }
  };

  const createPlotlyCharts = (sentimentDist = {}, biasDist = {}) => {
    // --- Sentiment Chart (Pie) ---
    const sentimentLabels = Object.keys(sentimentDist);
    const sentimentValues = Object.values(sentimentDist);
    const filteredSentimentLabels = sentimentLabels.filter(
      (_, i) => sentimentValues[i] > 0,
    );
    const filteredSentimentValues = sentimentValues.filter((v) => v > 0);
    const sentimentColors = filteredSentimentLabels.map((label) => {
      // Catppuccin Mocha colors
      if (label === "Positive") return "#a6e3a1"; // Green
      if (label === "Negative") return "#f38ba8"; // Red
      if (label === "Neutral") return "#9399b2"; // Overlay2
      return "#a6adc8"; // Subtext0 fallback
    });
    const sentimentData = [
      {
        values:
          filteredSentimentValues.length > 0 ? filteredSentimentValues : [1],
        labels:
          filteredSentimentLabels.length > 0
            ? filteredSentimentLabels
            : ["N/A"],
        type: "pie",
        hole: 0.4,
        marker: { colors: sentimentColors },
        hoverinfo: "label+percent",
        textinfo: "none",
        domain: { x: [0, 1], y: [0, 1] },
      },
    ];
    const sentimentLayout = getPlotlyLayout("Sentiment Distribution");
    if (filteredSentimentValues.length === 0) {
      sentimentLayout.annotations = [
        { text: "No data", showarrow: false, font: { size: 14 } },
      ];
    }
    Plotly.newPlot("sentimentChart", sentimentData, sentimentLayout, {
      responsive: true,
      displaylogo: false,
    });

    // --- Bias Chart (Pie) ---
    const biasLabels = Object.keys(biasDist);
    const biasValues = Object.values(biasDist);
    const filteredBiasLabels = biasLabels.filter((_, i) => biasValues[i] > 0);
    const filteredBiasValues = biasValues.filter((v) => v > 0);
    const biasColors = filteredBiasLabels.map((label) => {
      // Catppuccin Mocha colors
      if (label === "Left") return "#89b4fa"; // Blue
      if (label === "Right") return "#f38ba8"; // Red
      if (label === "Center") return "#f9e2af"; // Yellow
      return "#a6adc8"; // Subtext0 fallback
    });
    const biasData = [
      {
        values: filteredBiasValues.length > 0 ? filteredBiasValues : [1],
        labels: filteredBiasLabels.length > 0 ? filteredBiasLabels : ["N/A"],
        type: "pie",
        hole: 0.4,
        marker: { colors: biasColors },
        hoverinfo: "label+percent",
        textinfo: "none",
        domain: { x: [0, 1], y: [0, 1] },
      },
    ];
    const biasLayout = getPlotlyLayout("Political Bias Distribution");
    if (filteredBiasValues.length === 0) {
      biasLayout.annotations = [
        { text: "No data", showarrow: false, font: { size: 14 } },
      ];
    }
    Plotly.newPlot("biasChart", biasData, biasLayout, {
      responsive: true,
      displaylogo: false,
    });
  };

  // --- Update Results Display (Main Function) ---
  const updateResults = (data) => {
    if (!data || typeof data !== "object") {
      console.error("Invalid data received:", data);
      errorMessage.textContent = "Received invalid data structure from server.";
      showSection("error");
      return;
    }
    console.log("Received data for UI update:", data);
    const analysis = data.analysis || {};

    // Update top cards
    updateBiasDisplay(data.bias, data.bias_value);
    updateSentimentDisplay(data.sentiment, data.sentiment_value);

    // Update Credibility Text (No score/bar)
    if (credibilityAssessmentTextEl) {
      credibilityAssessmentTextEl.textContent =
        analysis.credibility_assessment || "N/A";
    }

    // Update source display
    analysisSource.textContent = `Source: ${data.source_display || "N/A"}`;

    // Update summary
    contentSummary.textContent =
      data.summary || analysis.summary || "Summary not available.";
    contentSummary.style.whiteSpace =
      data.summary && data.summary.includes("---\n\n") ? "pre-wrap" : "normal";

    // --- Update Findings & Indicators Tab ---
    keyFindingsEl.innerHTML = "";
    const findings = analysis.key_findings || [];
    if (findings.length > 0) {
      findings.forEach((f) => {
        const li = document.createElement("li");
        li.textContent = f;
        keyFindingsEl.appendChild(li);
      });
    } else {
      keyFindingsEl.innerHTML = "<li>No key findings provided.</li>";
    }

    biasIndicatorsEl.innerHTML = "";
    const indicators = analysis.bias_indicators || []; // Use the correctly named key
    if (indicators.length > 0) {
      indicators.forEach((indicator) => {
        const p = document.createElement("p");
        p.className =
          "p-2 bg-gray-100 dark:bg-gray-700 rounded text-sm italic border-l-4 border-gray-400 dark:border-gray-500 pl-3 mb-2";
        p.textContent = indicator.includes("]")
          ? indicator.split("] ")[1]
          : indicator;
        if (indicator.includes("[")) {
          const prefix = document.createElement("span");
          prefix.className = "text-xs text-gray-500 dark:text-gray-400 mr-1";
          prefix.textContent = indicator.split("]")[0] + "]";
          p.prepend(prefix);
        }
        biasIndicatorsEl.appendChild(p);
      });
    } else {
      biasIndicatorsEl.innerHTML =
        '<p class="text-gray-500 dark:text-gray-400 text-sm">No specific bias indicators provided.</p>';
    }

    // --- Update Recommended Searches ---
    recommendedSearchesEl.innerHTML = "";
    const searches = analysis.recommended_searches || [];
    if (searches.length > 0) {
      searches.forEach((search) => {
        const span = document.createElement("span");
        // Apply Tailwind classes for styling
        span.className =
          "cursor-pointer px-3 py-1 bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-full text-sm hover:bg-gray-300 dark:hover:bg-gray-500 transition-colors";
        span.textContent = search;
        span.onclick = () => {
          /* ... (same click handler as before) ... */
          document.getElementById("topicButton").click();
          contentInput.value = search;
          updateCharCounter();
          contentInput.focus();
        };
        recommendedSearchesEl.appendChild(span);
      });
    } else {
      recommendedSearchesEl.innerHTML =
        '<span class="text-sm text-gray-500 dark:text-gray-400">No searches recommended.</span>';
    }

    // Create/Update Plotly charts
    createPlotlyCharts(
      data.visualization_data?.sentiment_distribution,
      data.visualization_data?.bias_distribution,
    );

    // Show results section and activate default tab
    showSection("results");
    activateTab(summaryTab);
  };

  // --- Event Listeners (Unchanged from v4, except Export button removed) ---
  contentInput.addEventListener("input", updateCharCounter);
  startAnalyzingBtn.addEventListener("click", () => {
    landingPage.classList.add("hidden");
    analysisPage.classList.remove("hidden");
  });
  inputTypeBtns.forEach((btn) => {
    btn.addEventListener("click", function () {
      /* ... */
      currentInputType = this.getAttribute("data-input-type");
      inputTypeBtns.forEach((b) => {
        b.classList.remove("bg-blue-600", "text-white", "dark:bg-blue-500");
        b.classList.add(
          "bg-gray-200",
          "text-gray-700",
          "dark:bg-gray-700",
          "dark:text-gray-300",
          "hover:bg-gray-300",
          "dark:hover:bg-gray-600",
        );
        b.setAttribute("aria-selected", "false");
      });
      this.classList.add("bg-blue-600", "text-white", "dark:bg-blue-500");
      this.classList.remove(
        "bg-gray-200",
        "text-gray-700",
        "dark:bg-gray-700",
        "dark:text-gray-300",
        "hover:bg-gray-300",
        "dark:hover:bg-gray-600",
      );
      this.setAttribute("aria-selected", "true");
      if (currentInputType === "url")
        contentInput.placeholder =
          "Paste a news article URL (e.g., https://...)";
      else if (currentInputType === "text")
        contentInput.placeholder = `Paste the article text (limit: ${MAX_CHARS} characters)`;
      else
        contentInput.placeholder =
          "Enter a topic to search and analyze (e.g., climate change)";
      contentInput.focus();
    });
  });
  analysisTabs.forEach((tab) => {
    tab.addEventListener("click", function () {
      activateTab(this);
    });
  });
  analyzeButton.addEventListener("click", function () {
    /* ... (Fetch logic same as v4) ... */
    const input = contentInput.value.trim();
    if (!input) {
      alert("Please enter text, a URL, or a topic.");
      return;
    }
    if (input.length > MAX_CHARS) {
      alert(`Input exceeds ${MAX_CHARS} characters.`);
      return;
    }
    if (currentInputType === "url") {
      try {
        new URL(input);
      } catch (_) {
        alert("Please enter a valid URL.");
        return;
      }
    }
    showSection("loading");
    setAnalyzeButtonLoading(true);
    fetch("/analyze", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        input_type: currentInputType,
        input_value: input,
      }),
    })
      .then((response) => {
        if (!response.ok) {
          return response
            .json()
            .catch(() => {
              throw new Error(
                `HTTP error ${response.status}: ${response.statusText}`,
              );
            })
            .then((errData) => {
              throw new Error(errData.error || `HTTP error ${response.status}`);
            });
        }
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.indexOf("application/json") !== -1) {
          return response.json();
        } else {
          throw new Error("Received non-JSON response from server.");
        }
      })
      .then((data) => {
        if (data.error) {
          throw new Error(data.error);
        }
        updateResults(data);
      })
      .catch((error) => {
        console.error("Analysis Fetch/Process Error:", error);
        errorMessage.textContent =
          error.message || "An unknown error occurred.";
        showSection("error");
      })
      .finally(() => {
        if (loadingState.classList.contains("hidden")) {
          setAnalyzeButtonLoading(false);
        }
      });
  });
  tryAgainButton.addEventListener("click", () => {
    showSection("input");
    setAnalyzeButtonLoading(false);
    contentInput.focus();
  });
  newAnalysisBtn.addEventListener("click", function () {
    showSection("input");
    setAnalyzeButtonLoading(false);
    contentInput.value = "";
    updateCharCounter();
    document.getElementById("urlButton").click();
    contentInput.focus();
  });

  // --- Initial Setup ---
  document.getElementById("urlButton").click();
  updateCharCounter();
}); // End DOMContentLoaded
