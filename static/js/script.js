document.addEventListener('DOMContentLoaded', function() {
    // --- DOM Elements ---
    const startAnalyzingBtn = document.getElementById('startAnalyzing');
    const landingPage = document.getElementById('landingPage');
    const analysisPage = document.getElementById('analysisPage');
    const inputTypeBtns = document.querySelectorAll('.input-type-btn');
    const contentInput = document.getElementById('contentInput');
    const charCount = document.getElementById('charCount');
    const charLimit = document.getElementById('charLimit'); // Assuming you add this span
    const analyzeButton = document.getElementById('analyzeButton');
    const analyzeButtonText = analyzeButton.querySelector('.button-text');
    const analyzeButtonIcon = analyzeButton.querySelector('.button-icon');
    const analyzeButtonSpinner = analyzeButton.querySelector('.fa-cogs');
    const loadingState = document.getElementById('loadingState');
    const loadingMessage = document.getElementById('loadingMessage');
    const errorState = document.getElementById('errorState');
    const errorMessage = document.getElementById('errorMessage');
    const tryAgainButton = document.getElementById('tryAgainButton');
    const resultsSection = document.getElementById('resultsSection');
    const newAnalysisBtn = document.getElementById('newAnalysisBtn');
    const analysisSource = document.getElementById('analysisSource');

    // Result Display Elements
    const biasLabel = document.getElementById('biasLabel');
    const biasScore = document.getElementById('biasScore');
    const biasIcon = document.getElementById('biasIcon');
    const biasIconBg = document.getElementById('biasIconBg');
    const biasIndicatorNeedle = document.getElementById('biasIndicatorNeedle');

    const sentimentLabel = document.getElementById('sentimentLabel');
    const sentimentScore = document.getElementById('sentimentScore');
    const sentimentIcon = document.getElementById('sentimentIcon');
    const sentimentIconBg = document.getElementById('sentimentIconBg');
    const sentimentIndicatorNeedle = document.getElementById('sentimentIndicatorNeedle');

    const credibilityLabel = document.getElementById('credibilityLabel');
    const credibilityIndicator = document.getElementById('credibilityIndicator');

    const contentSummary = document.getElementById('contentSummary');
    const keyFindingsEl = document.getElementById('keyFindings');
    const biasIndicatorsEl = document.getElementById('biasIndicators');

    // Tabs
    const analysisTabs = document.querySelectorAll('.analysis-tab');
    const analysisContents = document.querySelectorAll('.analysis-content');
    const summaryTab = document.getElementById('summaryTab'); // Default tab

    // Plotly Chart Containers
    const sentimentChartContainer = document.getElementById('sentimentChartContainer');
    const biasChartContainer = document.getElementById('biasChartContainer');

    // --- State ---
    let currentInputType = 'url'; // Default input type
    const MAX_CHARS = 5000; // Set character limit

    // --- Initialization ---
    if (charLimit) charLimit.textContent = MAX_CHARS;
    activateTab(summaryTab); // Activate summary tab by default

    // --- Functions ---

    // Update Character Counter
    const updateCharCounter = () => {
        const currentLength = contentInput.value.length;
        charCount.textContent = currentLength;
        if (currentLength > MAX_CHARS) {
            charCount.classList.add('text-red-500', 'font-bold');
            analyzeButton.disabled = true; // Disable analyze if over limit
        } else {
            charCount.classList.remove('text-red-500', 'font-bold');
            analyzeButton.disabled = false;
        }
    };

    // Set Button State (Loading/Idle)
    const setAnalyzeButtonLoading = (isLoading) => {
        if (isLoading) {
            analyzeButton.disabled = true;
            analyzeButtonText.textContent = 'Analyzing...';
            analyzeButtonIcon.classList.add('hidden');
            analyzeButtonSpinner.classList.remove('hidden');
        } else {
            analyzeButton.disabled = false;
            analyzeButtonText.textContent = 'Analyze';
            analyzeButtonIcon.classList.remove('hidden');
            analyzeButtonSpinner.classList.add('hidden');
            updateCharCounter(); // Re-check char limit when loading finishes
        }
    };

    // Show/Hide Sections
    const showSection = (section) => {
        loadingState.classList.add('hidden');
        resultsSection.classList.add('hidden');
        errorState.classList.add('hidden');
        // Hide input form only when loading or showing results/error
        const inputForm = analysisPage.querySelector('.bg-white'); // Adjust selector if needed
        if (inputForm) {
             inputForm.classList.toggle('hidden', section !== 'input');
        }


        if (section === 'loading') loadingState.classList.remove('hidden');
        else if (section === 'results') resultsSection.classList.remove('hidden');
        else if (section === 'error') errorState.classList.remove('hidden');
        else if (section === 'input') { // Ensure input form is visible
             if (inputForm) inputForm.classList.remove('hidden');
        }
    };

    // Activate Tab
    function activateTab(activeTab) {
        if (!activeTab) return;
        analysisTabs.forEach(tab => {
            const contentId = tab.id.replace('Tab', 'Content');
            const content = document.getElementById(contentId);
            if (tab === activeTab) {
                tab.classList.add('border-blue-500', 'text-blue-600', 'dark:border-blue-400', 'dark:text-blue-400');
                tab.classList.remove('border-transparent', 'text-gray-500', 'hover:text-gray-700', 'hover:border-gray-300', 'dark:text-gray-400', 'dark:hover:text-gray-200', 'dark:hover:border-gray-500');
                tab.setAttribute('aria-current', 'page');
                if (content) content.classList.remove('hidden');
            } else {
                tab.classList.remove('border-blue-500', 'text-blue-600', 'dark:border-blue-400', 'dark:text-blue-400');
                tab.classList.add('border-transparent', 'text-gray-500', 'hover:text-gray-700', 'hover:border-gray-300', 'dark:text-gray-400', 'dark:hover:text-gray-200', 'dark:hover:border-gray-500');
                tab.removeAttribute('aria-current');
                if (content) content.classList.add('hidden');
            }
        });
         // Ensure Plotly charts resize correctly when their container becomes visible
         setTimeout(() => {
            if (typeof Plotly !== 'undefined') {
                Plotly.Plots.resize(sentimentChartContainer);
                Plotly.Plots.resize(biasChartContainer);
            }
         }, 50); // Small delay might be needed
    }

    // Update Bias Display
    const updateBiasDisplay = (label, score) => {
        let colorClass = 'text-gray-700 dark:text-gray-300';
        let iconBgClass = 'bg-gray-100 dark:bg-gray-600';
        let iconColorClass = 'text-gray-500 dark:text-gray-400';
        let needlePos = 50; // Center default

        if (label === 'Left') {
            colorClass = 'text-blue-600 dark:text-blue-400';
            iconBgClass = 'bg-blue-100 dark:bg-blue-900';
            iconColorClass = 'text-blue-500 dark:text-blue-300';
            // Position needle towards left (0-33% range approx)
            needlePos = 15 + (score / 100) * 15; // Scale within the left third based on score? Or just fixed left? Let's use score.
        } else if (label === 'Right') {
            colorClass = 'text-red-600 dark:text-red-400';
            iconBgClass = 'bg-red-100 dark:bg-red-900';
            iconColorClass = 'text-red-500 dark:text-red-300';
            // Position needle towards right (66-100% range approx)
            needlePos = 70 + (score / 100) * 15; // Scale within the right third
        } else if (label === 'Center') {
            colorClass = 'text-yellow-600 dark:text-yellow-400';
            iconBgClass = 'bg-yellow-100 dark:bg-yellow-900';
            iconColorClass = 'text-yellow-500 dark:text-yellow-300';
             // Position needle near center (33-66% range approx)
             needlePos = 40 + (score / 100) * 15; // Scale within the center third
        }

        biasLabel.textContent = label;
        biasLabel.className = `text-2xl font-semibold mb-1 ${colorClass}`; // Apply color class
        biasScore.textContent = `Score: ${score}%`;
        biasIconBg.className = `p-2 rounded-full mr-3 ${iconBgClass}`;
        biasIcon.className = `fas fa-balance-scale ${iconColorClass}`;
        biasIndicatorNeedle.style.left = `${Math.max(2, Math.min(98, needlePos))}%`; // Clamp position
    };

    // Update Sentiment Display
    const updateSentimentDisplay = (label, score) => {
        let colorClass = 'text-gray-700 dark:text-gray-300';
        let iconClass = 'fa-meh'; // Neutral icon default
        let iconBgClass = 'bg-gray-100 dark:bg-gray-600';
        let iconColorClass = 'text-gray-500 dark:text-gray-400';
        let needlePos = 50; // Center default (Neutral)

        if (label === 'Positive') {
            colorClass = 'text-green-600 dark:text-green-400';
            iconClass = 'fa-smile';
            iconBgClass = 'bg-green-100 dark:bg-green-900';
            iconColorClass = 'text-green-500 dark:text-green-300';
            needlePos = 50 + (score / 100) * 50; // 50-100% range
        } else if (label === 'Negative') {
            colorClass = 'text-red-600 dark:text-red-400';
            iconClass = 'fa-frown';
            iconBgClass = 'bg-red-100 dark:bg-red-900';
            iconColorClass = 'text-red-500 dark:text-red-300';
            needlePos = 50 - (score / 100) * 50; // 0-50% range (inverted score?) - Let's assume score is intensity (0-100), so higher score means more negative.
             needlePos = 50 - (score / 100) * 48; // Map score to 0-50 range
        } else { // Neutral
             needlePos = 40 + (score / 100) * 20; // Map score to 40-60 range for neutral
        }


        sentimentLabel.textContent = label;
        sentimentLabel.className = `text-2xl font-semibold mb-1 ${colorClass}`;
        sentimentScore.textContent = `Score: ${score}%`;
        sentimentIconBg.className = `p-2 rounded-full mr-3 ${iconBgClass}`;
        sentimentIcon.className = `fas ${iconClass} ${iconColorClass}`;
        sentimentIndicatorNeedle.style.left = `${Math.max(2, Math.min(98, needlePos))}%`; // Clamp position
    };

    // Plotly Chart Theming
    const getPlotlyLayout = (title) => {
        const isDark = document.documentElement.classList.contains('dark');
        return {
            title: {
                text: title,
                font: {
                    color: isDark ? '#e5e7eb' : '#1f2937', // gray-200 / gray-800
                    size: 16
                }
            },
            paper_bgcolor: isDark ? '#374151' : '#ffffff', // gray-700 / white
            plot_bgcolor: isDark ? '#374151' : '#ffffff',
            font: {
                color: isDark ? '#d1d5db' : '#374151' // gray-300 / gray-700
            },
            showlegend: true,
            legend: {
                bgcolor: isDark ? 'rgba(55, 65, 81, 0.5)' : 'rgba(255, 255, 255, 0.5)', // gray-700 with alpha / white with alpha
                bordercolor: isDark ? '#4b5563' : '#e5e7eb', // gray-600 / gray-200
                borderwidth: 1
            },
            margin: { l: 40, r: 40, t: 50, b: 40 }, // Adjust margins as needed
            height: 320 // Match container height or make responsive
        };
    };

    // Update Plotly Chart Theme (call on theme change)
    window.updatePlotlyLayoutTheme = () => {
        if (typeof Plotly !== 'undefined') {
            try {
                Plotly.relayout('sentimentChart', getPlotlyLayout('Sentiment Distribution'));
            } catch (e) { console.warn("Could not update sentiment chart theme."); }
            try {
                 Plotly.relayout('biasChart', getPlotlyLayout('Political Bias Distribution'));
            } catch (e) { console.warn("Could not update bias chart theme."); }
        }
    };


    // Create/Update Plotly Charts
    const createPlotlyCharts = (sentimentDist, biasDist) => {
        // --- Sentiment Chart (Pie) ---
        const sentimentLabels = Object.keys(sentimentDist);
        const sentimentValues = Object.values(sentimentDist);
        const sentimentColors = sentimentLabels.map(label => {
            if (label === 'Positive') return '#10B981'; // green-500
            if (label === 'Negative') return '#EF4444'; // red-500
            if (label === 'Neutral') return '#6B7280'; // gray-500
            return '#9CA3AF'; // gray-400 fallback
        });

        const sentimentData = [{
            values: sentimentValues,
            labels: sentimentLabels,
            type: 'pie',
            hole: .4, // Make it a donut chart
            marker: { colors: sentimentColors },
            hoverinfo: 'label+percent',
            textinfo: 'none' // Avoid text clutter on slices
        }];
        Plotly.newPlot('sentimentChart', sentimentData, getPlotlyLayout('Sentiment Distribution'), {responsive: true});

        // --- Bias Chart (Pie) ---
        const biasLabels = Object.keys(biasDist);
        const biasValues = Object.values(biasDist);
        const biasColors = biasLabels.map(label => {
            if (label === 'Left') return '#3B82F6'; // blue-500
            if (label === 'Right') return '#EF4444'; // red-500
            if (label === 'Center') return '#F59E0B'; // amber-500 (yellow was hard to see)
            return '#9CA3AF'; // gray-400 fallback
        });

        const biasData = [{
            values: biasValues,
            labels: biasLabels,
            type: 'pie',
            hole: .4,
            marker: { colors: biasColors },
            hoverinfo: 'label+percent',
            textinfo: 'none'
        }];
        Plotly.newPlot('biasChart', biasData, getPlotlyLayout('Political Bias Distribution'), {responsive: true});
    };


    // Update Results Display
    const updateResults = (data) => {
        if (!data) {
            console.error("No data received to update results.");
            errorMessage.textContent = "Received invalid data from server.";
            showSection('error');
            return;
        }

        console.log("Received data:", data);

        // Update top cards
        updateBiasDisplay(data.bias || 'N/A', data.bias_value || 0);
        updateSentimentDisplay(data.sentiment || 'N/A', data.sentiment_value || 0);
        credibilityLabel.textContent = data.credibility_label || 'Moderate'; // Assuming a label exists
        credibilityIndicator.style.width = `${data.credibility_value || 50}%`;

        // Update source display
        analysisSource.textContent = `Source: ${data.source_display || 'N/A'}`;

        // Update summary
        contentSummary.textContent = data.summary || 'Summary not available.';

        // Update key findings (Placeholder data)
        keyFindingsEl.innerHTML = ''; // Clear previous
        if (data.key_findings && data.key_findings.length > 0) {
            data.key_findings.forEach(finding => {
                const li = document.createElement('li');
                li.textContent = finding;
                keyFindingsEl.appendChild(li);
            });
        } else {
            keyFindingsEl.innerHTML = '<li>No key findings generated.</li>';
        }

        // Update bias indicators (Placeholder data)
        biasIndicatorsEl.innerHTML = ''; // Clear previous
        if (data.indicators && data.indicators.length > 0) {
            data.indicators.forEach(indicator => {
                const div = document.createElement('div');
                // Simple display for placeholder indicators
                div.className = 'flex justify-between items-center p-2 bg-gray-100 dark:bg-gray-700 rounded';
                div.innerHTML = `
                    <span>${indicator.name || 'Indicator'}</span>
                    <span class="font-medium text-sm">${indicator.value || 0}%</span>
                `;
                biasIndicatorsEl.appendChild(div);
            });
        } else {
            biasIndicatorsEl.innerHTML = '<p class="text-gray-500 dark:text-gray-400">No specific bias indicators generated.</p>';
        }

        // Create Plotly charts
        createPlotlyCharts(
            data.visualization_data?.sentiment_distribution || {},
            data.visualization_data?.bias_distribution || {}
        );

        // Show results section and activate default tab
        showSection('results');
        activateTab(summaryTab); // Ensure summary tab is active first
    };

    // --- Event Listeners ---

    // Character Counter
    contentInput.addEventListener('input', updateCharCounter);

    // Switch from landing page to analysis page
    startAnalyzingBtn.addEventListener('click', () => {
        landingPage.classList.add('hidden');
        analysisPage.classList.remove('hidden');
    });

    // Input Type Selection
    inputTypeBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            // Update state
            currentInputType = this.getAttribute('data-input-type');

            // Update button styles
            inputTypeBtns.forEach(b => {
                b.classList.remove('bg-blue-600', 'text-white', 'dark:bg-blue-500');
                b.classList.add('bg-gray-200', 'text-gray-700', 'dark:bg-gray-700', 'dark:text-gray-300', 'hover:bg-gray-300', 'dark:hover:bg-gray-600');
                b.setAttribute('aria-selected', 'false');
            });
            this.classList.add('bg-blue-600', 'text-white', 'dark:bg-blue-500');
            this.classList.remove('bg-gray-200', 'text-gray-700', 'dark:bg-gray-700', 'dark:text-gray-300', 'hover:bg-gray-300', 'dark:hover:bg-gray-600');
            this.setAttribute('aria-selected', 'true');


            // Update placeholder
            if (currentInputType === 'url') {
                contentInput.placeholder = 'Paste a news article URL (e.g., https://...)';
            } else if (currentInputType === 'text') {
                contentInput.placeholder = `Paste the article text (limit: ${MAX_CHARS} characters)`;
            } else { // topic
                contentInput.placeholder = 'Enter a topic to search and analyze (e.g., climate change)';
            }
            contentInput.focus(); // Focus input after type change
        });
    });

    // Analysis Tabs
    analysisTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            activateTab(this);
        });
    });

    // Analyze Button
    analyzeButton.addEventListener('click', function() {
        const input = contentInput.value.trim();

        // Basic validation
        if (!input) {
            alert('Please enter text, a URL, or a topic to analyze.'); // Replace with better modal later
            contentInput.focus();
            return;
        }
        if (input.length > MAX_CHARS) {
             alert(`Input exceeds the maximum character limit of ${MAX_CHARS}.`);
             return;
        }
        // Simple URL validation for URL type
        if (currentInputType === 'url') {
            try {
                new URL(input);
            } catch (_) {
                alert('Please enter a valid URL (e.g., starting with http:// or https://).');
                return;
            }
        }


        // Show loading state
        showSection('loading');
        setAnalyzeButtonLoading(true);

        // API call
        fetch('/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ input_type: currentInputType, input_value: input }),
        })
        .then(response => {
            if (!response.ok) {
                // Try to get error message from response body
                return response.json().then(errData => {
                    throw new Error(errData.error || `HTTP error ${response.status}`);
                }).catch(() => {
                    // If body isn't JSON or doesn't have 'error'
                     throw new Error(`HTTP error ${response.status}`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.error) { // Handle errors returned in a 200 response's JSON
                throw new Error(data.error);
            }
            // Success: Update results display
            updateResults(data);
        })
        .catch(error => {
            console.error('Analysis Error:', error);
            errorMessage.textContent = error.message || 'An unknown error occurred during analysis.';
            showSection('error');
        })
        .finally(() => {
            // Ensure button state is reset unless results are shown
            if (resultsSection.classList.contains('hidden') && errorState.classList.contains('hidden')) {
                 setAnalyzeButtonLoading(false);
            } else {
                 // Keep loading state until results/error shown, then reset
                 setTimeout(() => setAnalyzeButtonLoading(false), 100);
            }
        });
    });

    // Try Again Button (from error state)
    tryAgainButton.addEventListener('click', () => {
        showSection('input'); // Go back to input form
        contentInput.focus();
    });


    // New Analysis Button
    newAnalysisBtn.addEventListener('click', function() {
        showSection('input');
        contentInput.value = '';
        updateCharCounter();
        // Optionally reset to default input type
        document.getElementById('urlButton').click();
        contentInput.focus();
    });

    // --- Initial Setup ---
    document.getElementById('urlButton').click(); // Set default input type on load
    updateCharCounter(); // Initial check

}); // End DOMContentLoaded

