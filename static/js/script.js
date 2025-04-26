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

  // Credibility Elements
  const credibilityLevelDisplay = document.getElementById(
    "credibilityLevelDisplay",
  ); // Container div
  const credibilityAssessmentTextEl = document.getElementById(
    "credibilityAssessmentText",
  ); // Detail text

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
  if (summaryTab) activateTab(summaryTab);

  // --- Functions ---

  // updateCharCounter is defined globally in base.html

  const setAnalyzeButtonLoading = (isLoading) => {
    if (!analyzeButton) return;
    analyzeButton.disabled = isLoading;
    if (analyzeButtonText)
      analyzeButtonText.textContent = isLoading ? "Analyzing..." : "Analyze";
    if (analyzeButtonIcon)
      analyzeButtonIcon.classList.toggle("hidden", isLoading);
    if (analyzeButtonSpinner)
      analyzeButtonSpinner.classList.toggle("hidden", !isLoading);
    if (!isLoading && typeof window.updateCharCounter === "function") {
      window.updateCharCounter();
    }
  };

  const showSection = (section) => {
    if (loadingState) loadingState.classList.add("hidden");
    if (resultsSection) resultsSection.classList.add("hidden");
    if (errorState) errorState.classList.add("hidden");
    const inputForm = analysisPage?.querySelector(
      ".analysis-page-card:not(#loadingState):not(#errorState):not(#resultsSection)",
    );
    if (inputForm) {
      inputForm.classList.toggle("hidden", section !== "input");
    }
    if (section === "loading" && loadingState)
      loadingState.classList.remove("hidden");
    else if (section === "results" && resultsSection)
      resultsSection.classList.remove("hidden");
    else if (section === "error" && errorState)
      errorState.classList.remove("hidden");
    else if (section === "input" && inputForm)
      inputForm.classList.remove("hidden");
  };

  function activateTab(activeTab) {
    if (!activeTab || !analysisTabs.length) return;
    analysisTabs.forEach((tab) => {
      const contentId = tab.id.replace("Tab", "Content");
      const content = document.getElementById(contentId);
      const isActive = tab === activeTab;
      tab.setAttribute("aria-current", isActive ? "page" : "false");
      if (content) content.classList.toggle("hidden", !isActive);
      // Visual state handled by CSS based on [aria-current="page"]
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

  // --- Display Update Functions ---

  const updateBiasDisplay = (label = "N/A", score = 0) => {
    let colorClass = "";
    let iconBgClass = "";
    let iconColorClass = "";
    let needlePos = 50;
    label = label.toString();
    score = Number(score) || 0;
    switch (label) {
      case "Left":
        colorClass = "text-blue-600 dark:text-blue-400";
        iconBgClass = "bg-blue-100 dark:bg-opacity-20";
        iconColorClass = "text-blue-500 dark:text-blue-400";
        needlePos = 5 + (score / 100) * 28;
        break;
      case "Right":
        colorClass = "text-red-600 dark:text-red-400";
        iconBgClass = "bg-red-100 dark:bg-opacity-20";
        iconColorClass = "text-red-500 dark:text-red-400";
        needlePos = 67 + (score / 100) * 28;
        break;
      case "Center":
        colorClass = "text-yellow-600 dark:text-yellow-400";
        iconBgClass = "bg-yellow-100 dark:bg-opacity-20";
        iconColorClass = "text-yellow-500 dark:text-yellow-400";
        needlePos = 34 + (score / 100) * 32;
        break;
      case "Error":
        colorClass = "text-red-600 dark:text-red-400";
        iconBgClass = "bg-red-100 dark:bg-opacity-20";
        iconColorClass = "text-red-500 dark:text-red-400";
        needlePos = 50;
        score = 0;
        break;
      default:
        colorClass = "text-gray-700 dark:text-gray-300";
        iconBgClass = "bg-gray-100 dark:bg-gray-600";
        iconColorClass = "text-gray-500 dark:text-gray-400";
        needlePos = 50;
        break;
    }
    if (biasLabel) {
      biasLabel.textContent = label;
      biasLabel.className = `text-2xl font-semibold mb-1 ${colorClass}`;
    }
    if (biasScoreEl)
      biasScoreEl.textContent =
        label !== "Error" ? `Confidence: ${score}%` : "Analysis Failed";
    if (biasIconBg)
      biasIconBg.className = `p-2 rounded-full mr-3 ${iconBgClass}`;
    if (biasIcon) biasIcon.className = `fas fa-balance-scale ${iconColorClass}`;
    if (biasIndicatorNeedle)
      biasIndicatorNeedle.style.left = `${Math.max(2, Math.min(98, needlePos))}%`;
  };

  const updateSentimentDisplay = (label = "N/A", score = 0) => {
    let colorClass = "";
    let iconClass = "fa-meh";
    let iconBgClass = "";
    let iconColorClass = "";
    let needlePos = 50;
    label = label.toString();
    score = Number(score) || 0;
    switch (label) {
      case "Positive":
        colorClass = "text-green-600 dark:text-green-400";
        iconClass = "fa-smile";
        iconBgClass = "bg-green-100 dark:bg-opacity-20";
        iconColorClass = "text-green-500 dark:text-green-400";
        needlePos = 98;
        break;
      case "Negative":
        colorClass = "text-red-600 dark:text-red-400";
        iconClass = "fa-frown";
        iconBgClass = "bg-red-100 dark:bg-opacity-20";
        iconColorClass = "text-red-500 dark:text-red-400";
        needlePos = 2;
        break;
      case "Error":
        colorClass = "text-red-600 dark:text-red-400";
        iconClass = "fa-exclamation-circle";
        iconBgClass = "bg-red-100 dark:bg-opacity-20";
        iconColorClass = "text-red-500 dark:text-red-400";
        needlePos = 50;
        break;
      default:
        colorClass = "text-gray-700 dark:text-gray-300";
        iconClass = "fa-meh";
        iconBgClass = "bg-gray-100 dark:bg-gray-600";
        iconColorClass = "text-gray-500 dark:text-gray-400";
        needlePos = 50;
        break;
    }
    if (sentimentLabel) {
      sentimentLabel.textContent = label;
      sentimentLabel.className = `text-2xl font-semibold mb-1 ${colorClass}`;
    }
    if (sentimentScoreEl) sentimentScoreEl.classList.add("hidden");
    if (sentimentIconBg)
      sentimentIconBg.className = `p-2 rounded-full mr-3 ${iconBgClass}`;
    if (sentimentIcon)
      sentimentIcon.className = `fas ${iconClass} ${iconColorClass}`;
    if (sentimentIndicatorNeedle)
      sentimentIndicatorNeedle.style.left = `${needlePos}%`;
  };

  // --- Plotly Functions ---
  const getPlotlyLayout = (title) => {
    const isDark = document.documentElement.classList.contains("dark");
    const paperColor = getComputedStyle(document.documentElement)
      .getPropertyValue(isDark ? "--card-bg" : "--card-bg")
      .trim();
    const fontColor = getComputedStyle(document.documentElement)
      .getPropertyValue("--text")
      .trim();
    const gridColor = getComputedStyle(document.documentElement)
      .getPropertyValue("--border")
      .trim();
    const legendBgColor = getComputedStyle(document.documentElement)
      .getPropertyValue("--bg")
      .trim();
    const legendBorderColor = getComputedStyle(document.documentElement)
      .getPropertyValue("--border")
      .trim();
    return {
      title: { text: title, font: { color: fontColor, size: 16 } },
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      font: { color: fontColor },
      showlegend: true,
      legend: {
        bgcolor: legendBgColor + "aa",
        bordercolor: legendBorderColor,
        borderwidth: 1,
        x: 0.5,
        xanchor: "center",
        y: -0.15,
        orientation: "h",
      },
      margin: { l: 30, r: 30, t: 60, b: 60 },
      height: 300,
    };
  };
  window.updatePlotlyLayoutTheme = () => {
    if (typeof Plotly !== "undefined") {
      try {
        Plotly.relayout(
          "sentimentChart",
          getPlotlyLayout("Sentiment Distribution (Binary)"),
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
    // Sentiment Chart
    const filteredSentimentDist = Object.fromEntries(
      Object.entries(sentimentDist).filter(([key]) => key !== "Neutral"),
    );
    const sentimentLabels = Object.keys(filteredSentimentDist);
    const sentimentValues = Object.values(filteredSentimentDist);
    const filteredSentimentLabels = sentimentLabels.filter(
      (_, i) => sentimentValues[i] > 0,
    );
    const filteredSentimentValues = sentimentValues.filter((v) => v > 0);
    const sentimentColors = filteredSentimentLabels.map((label) => {
      if (label === "Positive")
        return getComputedStyle(document.documentElement).getPropertyValue(
          "--ctp-mocha-green",
        );
      if (label === "Negative")
        return getComputedStyle(document.documentElement).getPropertyValue(
          "--ctp-mocha-red",
        );
      return getComputedStyle(document.documentElement).getPropertyValue(
        "--ctp-mocha-subtext0",
      );
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
    const sentimentLayout = getPlotlyLayout("Sentiment Distribution (Binary)");
    if (filteredSentimentValues.length === 0) {
      sentimentLayout.annotations = [
        { text: "No data", showarrow: false, font: { size: 14 } },
      ];
    }
    if (sentimentChartContainer)
      Plotly.newPlot("sentimentChart", sentimentData, sentimentLayout, {
        responsive: true,
        displaylogo: false,
      });

    // Bias Chart
    const biasLabels = Object.keys(biasDist);
    const biasValues = Object.values(biasDist);
    const filteredBiasLabels = biasLabels.filter((_, i) => biasValues[i] > 0);
    const filteredBiasValues = biasValues.filter((v) => v > 0);
    const biasColors = filteredBiasLabels.map((label) => {
      if (label === "Left")
        return getComputedStyle(document.documentElement).getPropertyValue(
          "--ctp-mocha-blue",
        );
      if (label === "Right")
        return getComputedStyle(document.documentElement).getPropertyValue(
          "--ctp-mocha-red",
        );
      if (label === "Center")
        return getComputedStyle(document.documentElement).getPropertyValue(
          "--ctp-mocha-yellow",
        );
      return getComputedStyle(document.documentElement).getPropertyValue(
        "--ctp-mocha-subtext0",
      );
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
    if (biasChartContainer)
      Plotly.newPlot("biasChart", biasData, biasLayout, {
        responsive: true,
        displaylogo: false,
      });
  };

  // --- Update Results Display (Main Function) ---
  const updateResults = (data) => {
    if (!data || typeof data !== "object") {
      console.error("Invalid data received:", data);
      if (errorMessage)
        errorMessage.textContent = "Received invalid data structure.";
      showSection("error");
      return;
    }
    console.log("Received data for UI update:", data);
    const analysis = data.analysis || {};

    // Update top cards
    updateBiasDisplay(data.bias, data.bias_value);
    updateSentimentDisplay(data.sentiment, data.sentiment_value);

    // --- Update Credibility Display --- (FIXED VERSION)
    const credLevel = analysis.credibility_level || "Medium"; // Default to Medium
    const credText = analysis.credibility_assessment || "N/A";
    let credEmoji = "🤔"; // Medium emoji
    let credColorClass = "cred-medium"; // CSS class for color

    if (credLevel === "High") {
      credEmoji = "👍";
      credColorClass = "cred-high";
    } else if (credLevel === "Low") {
      credEmoji = "👎";
      credColorClass = "cred-low";
    }

    if (credibilityLevelDisplay) {
      // Use safer DOM manipulation to prevent "High" text bug
      // First, clear all existing content
      while (credibilityLevelDisplay.firstChild) {
        credibilityLevelDisplay.removeChild(credibilityLevelDisplay.firstChild);
      }

      // Remove old color classes
      credibilityLevelDisplay.classList.remove(
        "cred-high",
        "cred-medium",
        "cred-low",
      );

      // Add new color class
      credibilityLevelDisplay.classList.add(credColorClass);

      // Create and append level-text span
      const levelTextSpan = document.createElement("span");
      levelTextSpan.className = "level-text";
      levelTextSpan.textContent = credLevel;
      credibilityLevelDisplay.appendChild(levelTextSpan);

      // Create and append level-emoji span
      const levelEmojiSpan = document.createElement("span");
      levelEmojiSpan.className = "level-emoji ml-1";
      levelEmojiSpan.textContent = credEmoji;
      credibilityLevelDisplay.appendChild(levelEmojiSpan);
    }

    // Update the assessment text element separately
    if (credibilityAssessmentTextEl) {
      credibilityAssessmentTextEl.textContent = credText;
    } // --- End Credibility Update ---

    if (analysisSource)
      analysisSource.textContent = `Source: ${data.source_display || "N/A"}`;
    if (contentSummary) {
      contentSummary.textContent = data.summary || analysis.summary || "N/A";
      contentSummary.style.whiteSpace =
        data.summary && data.summary.includes("---\n\n")
          ? "pre-wrap"
          : "normal";
    }

    // Update Findings & Indicators Tab
    if (keyFindingsEl) {
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
    }
    if (biasIndicatorsEl) {
      biasIndicatorsEl.innerHTML = "";
      const indicators = analysis.bias_indicators || [];
      if (indicators.length > 0) {
        indicators.forEach((indicator) => {
          const p = document.createElement("p");
          p.className =
            "p-2 bg-gray-100 dark:bg-slate-700 rounded text-sm italic border-l-4 border-gray-400 dark:border-slate-500 pl-3 mb-2";
          p.textContent = indicator.includes("]")
            ? indicator.split("] ")[1]
            : indicator;
          if (indicator.includes("[")) {
            const prefix = document.createElement("span");
            prefix.className = "text-xs mr-1 text-gray-500 dark:text-slate-400";
            prefix.textContent = indicator.split("]")[0] + "]";
            p.prepend(prefix);
          }
          biasIndicatorsEl.appendChild(p);
        });
      } else {
        biasIndicatorsEl.innerHTML =
          '<p class="text-sm text-gray-500 dark:text-slate-400">No specific bias indicators provided.</p>';
      }
    }

    // Update Recommended Searches
    if (recommendedSearchesEl) {
      recommendedSearchesEl.innerHTML = "";
      const searches = analysis.recommended_searches || [];
      if (searches.length > 0) {
        searches.forEach((search) => {
          const span = document.createElement("span");
          span.className =
            "cursor-pointer px-3 py-1 rounded-full text-sm hover:bg-slate-300 dark:hover:bg-slate-600 transition-colors";
          span.textContent = search;
          span.onclick = () => {
            if (document.getElementById("topicButton"))
              document.getElementById("topicButton").click();
            if (contentInput) contentInput.value = search;
            if (typeof window.updateCharCounter === "function")
              window.updateCharCounter();
            if (contentInput) contentInput.focus();
          };
          recommendedSearchesEl.appendChild(span);
        });
      } else {
        recommendedSearchesEl.innerHTML =
          '<span class="text-sm text-gray-500 dark:text-slate-400">No searches recommended.</span>';
      }
    }

    // Create/Update Plotly charts
    createPlotlyCharts(
      data.visualization_data?.sentiment_distribution,
      data.visualization_data?.bias_distribution,
    );

    showSection("results");
    if (summaryTab) activateTab(summaryTab);
  };

  // --- Event Listeners ---
  if (contentInput)
    contentInput.addEventListener("input", () => {
      if (typeof window.updateCharCounter === "function")
        window.updateCharCounter();
    });
  if (startAnalyzingBtn)
    startAnalyzingBtn.addEventListener("click", () => {
      if (landingPage) landingPage.classList.add("hidden");
      if (analysisPage) analysisPage.classList.remove("hidden");
    });
  inputTypeBtns.forEach((btn) => {
    btn.addEventListener("click", function () {
      /* ... update state, placeholder, focus ... */
      currentInputType = this.getAttribute("data-input-type");
      inputTypeBtns.forEach((b) => b.setAttribute("aria-selected", "false"));
      this.setAttribute("aria-selected", "true");
      if (contentInput) {
        if (currentInputType === "url")
          contentInput.placeholder =
            "Paste a news article URL (e.g., https://...)";
        else if (currentInputType === "text")
          contentInput.placeholder = `Paste the article text (limit: ${MAX_CHARS} characters)`;
        else
          contentInput.placeholder =
            "Enter a topic to search and analyze (e.g., climate change)";
        contentInput.focus();
      }
    });
  });
  analysisTabs.forEach((tab) => {
    tab.addEventListener("click", function () {
      activateTab(this);
    });
  });
  if (analyzeButton)
    analyzeButton.addEventListener("click", function () {
      /* ... Fetch logic ... */
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
                throw new Error(
                  errData.error || `HTTP error ${response.status}`,
                );
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
          if (errorMessage)
            errorMessage.textContent =
              error.message || "An unknown error occurred.";
          showSection("error");
        })
        .finally(() => {
          if (loadingState && loadingState.classList.contains("hidden")) {
            setAnalyzeButtonLoading(false);
          }
        });
    });
  if (tryAgainButton)
    tryAgainButton.addEventListener("click", () => {
      showSection("input");
      setAnalyzeButtonLoading(false);
      if (contentInput) contentInput.focus();
    });
  if (newAnalysisBtn)
    newAnalysisBtn.addEventListener("click", function () {
      showSection("input");
      setAnalyzeButtonLoading(false);
      if (contentInput) contentInput.value = "";
      if (typeof window.updateCharCounter === "function")
        window.updateCharCounter();
      if (document.getElementById("urlButton"))
        document.getElementById("urlButton").click();
      if (contentInput) contentInput.focus();
    });

  // --- Initial Setup ---
  if (document.getElementById("urlButton"))
    document.getElementById("urlButton").click();
  if (typeof window.updateCharCounter === "function")
    window.updateCharCounter();
}); // End DOMContentLoaded
