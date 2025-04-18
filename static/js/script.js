document.addEventListener('DOMContentLoaded', function() {
    // Initialize logos based on initial theme
    const body = document.body;
    const lightLogos = document.querySelectorAll('.light-logo');
    const darkLogos = document.querySelectorAll('.dark-logo');

    if (body.classList.contains('dark-mode')) {
        lightLogos.forEach(logo => logo.style.display = 'none');
        darkLogos.forEach(logo => logo.style.display = 'inline-block');
    } else {
        lightLogos.forEach(logo => logo.style.display = 'inline-block');
        darkLogos.forEach(logo => logo.style.display = 'none');
    }
    // DOM Elements
    const getStartedBtn = document.getElementById('get-started-btn');
    const landingPage = document.getElementById('landing');
    const analyzerContainer = document.getElementById('analyzer');
    const articleText = document.getElementById('article-text');
    const articleUrl = document.getElementById('article-url');
    const searchTopic = document.getElementById('search-topic');
    const clearUrlBtn = document.getElementById('clear-url-btn');
    const clearTopicBtn = document.getElementById('clear-topic-btn');
    const analyzeBtns = document.querySelectorAll('.analyze-btn');
    const statusCard = document.querySelector('.status-card');
    const statusMessage = document.querySelector('.status-message');
    const progressBar = document.querySelector('.progress-bar');
    const resultsContainer = document.querySelector('.results-container');
    const sentimentValue = document.querySelector('.sentiment-value');
    const biasValue = document.querySelector('.bias-value');
    const summaryText = document.querySelector('.summary-text');
    const rawOutputToggle = document.getElementById('raw-output-toggle');
    const rawOutput = document.querySelector('.raw-output');
    const rawOutputText = document.querySelector('.raw-output-text');
    const recommendedSearchesList = document.querySelector('.recommended-searches-list');
    const contrastingViewsCard = document.querySelector('.contrasting-views-card');
    const contrastingViewsContainer = document.querySelector('.contrasting-views-container');
    const themeToggle = document.querySelector('.theme-toggle');
    const errorModal = new bootstrap.Modal(document.getElementById('errorModal'));
    const errorMessage = document.getElementById('error-message');
    const exportTxtBtn = document.getElementById('export-txt-btn');
    const exportPdfBtn = document.getElementById('export-pdf-btn');
    const copyBtn = document.querySelector('.copy-btn');

    // Theme Toggle
    themeToggle.addEventListener('click', function() {
        const body = document.body;
        const lightLogos = document.querySelectorAll('.light-logo');
        const darkLogos = document.querySelectorAll('.dark-logo');

        if (body.classList.contains('light-mode')) {
            body.classList.remove('light-mode');
            body.classList.add('dark-mode');
            themeToggle.innerHTML = '<i class="fas fa-sun"></i>';

            // Explicitly handle logo visibility
            lightLogos.forEach(logo => logo.style.display = 'none');
            darkLogos.forEach(logo => logo.style.display = 'inline-block');
        } else {
            body.classList.remove('dark-mode');
            body.classList.add('light-mode');
            themeToggle.innerHTML = '<i class="fas fa-moon"></i>';

            // Explicitly handle logo visibility
            lightLogos.forEach(logo => logo.style.display = 'inline-block');
            darkLogos.forEach(logo => logo.style.display = 'none');
        }
    });

    // Character Counter for Text Input
    articleText.addEventListener('input', function() {
        const charCount = document.querySelector('.char-count');
        charCount.textContent = `${this.value.length}/5000`;
        if (this.value.length > 4800) {
            charCount.style.color = '#f44336';
        } else {
            charCount.style.color = '#6c757d';
        }
    });

    // Clear Buttons
    clearUrlBtn.addEventListener('click', function() {
        articleUrl.value = '';
    });

    clearTopicBtn.addEventListener('click', function() {
        searchTopic.value = '';
    });

    // Get Started Button - Show Analyzer
    getStartedBtn.addEventListener('click', function() {
        landingPage.classList.add('d-none');
        analyzerContainer.classList.remove('d-none');
    });

    // Raw Output Toggle
    rawOutputToggle.addEventListener('change', function() {
        if (this.checked) {
            rawOutput.classList.remove('d-none');
        } else {
            rawOutput.classList.add('d-none');
        }
    });

    // Copy Summary Button
    copyBtn.addEventListener('click', function() {
        const textToCopy = summaryText.textContent;
        navigator.clipboard.writeText(textToCopy)
            .then(() => {
                const originalText = copyBtn.innerHTML;
                copyBtn.innerHTML = '<i class="fas fa-check"></i> Copied!';
                setTimeout(() => {
                    copyBtn.innerHTML = originalText;
                }, 2000);
            })
            .catch(err => {
                console.error('Failed to copy: ', err);
            });
    });

    // Export as Text
    exportTxtBtn.addEventListener('click', function() {
        const currentDate = new Date().toLocaleString();
        let content = `Political Bias & Sentiment Analysis Results\n`;
        content += `Generated on: ${currentDate}\n\n`;
        content += `Sentiment: ${sentimentValue.textContent}\n`;
        content += `Political Bias: ${biasValue.textContent}\n\n`;
        content += `Summary:\n${summaryText.textContent}\n`;

        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'analysis-results.txt';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });

    // Export as PDF is just a placeholder (would need a PDF library in production)
    exportPdfBtn.addEventListener('click', function() {
        alert('PDF export feature would be integrated here with a library like jsPDF.');
    });

    // Analyze Buttons
    analyzeBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const inputType = this.getAttribute('data-input-type');
            let inputValue = '';

            // Get input value based on type
            if (inputType === 'text') {
                inputValue = articleText.value.trim();
                if (inputValue === '') {
                    showError('Please enter some text to analyze.');
                    return;
                }
            } else if (inputType === 'url') {
                inputValue = articleUrl.value.trim();
                if (inputValue === '') {
                    showError('Please enter a URL to analyze.');
                    return;
                }
                // Basic URL validation
                if (!isValidUrl(inputValue)) {
                    showError('Please enter a valid URL starting with http:// or https://');
                    return;
                }
            } else if (inputType === 'topic') {
                inputValue = searchTopic.value.trim();
                if (inputValue === '') {
                    showError('Please enter a topic to search and analyze.');
                    return;
                }
            }

            // Show status card and start progress
            statusCard.classList.remove('d-none');
            updateProgress(0, 'Starting analysis...');

            // Disable analyze buttons during processing
            analyzeBtns.forEach(b => b.disabled = true);

            // API call to backend
            fetch('/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ input_type: inputType, input_value: inputValue }),
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Analysis failed. Please try again.');
                }
                updateProgress(50, 'Processing results...');
                return response.json();
            })
            .then(data => {
                // Update progress to show we're nearly done
                updateProgress(90, 'Rendering results...');

                // Display the results
                displayResults(data, inputType);

                // Complete the progress
                setTimeout(() => {
                    updateProgress(100, 'Analysis complete!');

                    // Hide status card after a delay
                    setTimeout(() => {
                        statusCard.classList.add('d-none');
                        // Re-enable analyze buttons
                        analyzeBtns.forEach(b => b.disabled = false);
                    }, 1000);
                }, 500);
            })
            .catch(error => {
                // Re-enable analyze buttons
                analyzeBtns.forEach(b => b.disabled = false);

                // Hide status card
                statusCard.classList.add('d-none');

                // Show error
                showError(error.message);
            });
        });
    });

    // Function to validate URL
    function isValidUrl(string) {
        try {
            new URL(string);
            return true;
        } catch (_) {
            return false;
        }
    }

    // Function to update progress bar and status message
    function updateProgress(percent, message) {
        progressBar.style.width = `${percent}%`;
        statusMessage.textContent = message;
    }

    // Function to show error in modal
    function showError(message) {
        errorMessage.textContent = message;
        errorModal.show();
    }

    // Function to display analysis results
    function displayResults(data, inputType) {
        // Show results container
        resultsContainer.classList.remove('d-none');

        // Update sentiment and bias badges
        sentimentValue.textContent = data.sentiment;
        biasValue.textContent = data.bias;

        // Update badge colors
        const sentimentBadge = document.querySelector('.sentiment-label .badge');
        const biasBadge = document.querySelector('.bias-label .badge');

        sentimentBadge.className = `badge rounded-pill ${data.sentiment}`;
        biasBadge.className = `badge rounded-pill ${data.bias}`;

        // Update summary
        summaryText.textContent = data.summary;

        // Update raw output
        rawOutputText.textContent = JSON.stringify(data, null, 2);

        // Create charts
        createCharts(data.visualization_data);

        // Update recommended searches
        updateRecommendedSearches(data.recommended_searches);

        // Show contrasting views for topic search
        if (inputType === 'topic' && data.contrasting_views && data.contrasting_views.length > 0) {
            contrastingViewsCard.classList.remove('d-none');
            updateContrastingViews(data.contrasting_views);
        } else {
            contrastingViewsCard.classList.add('d-none');
            contrastingViewsContainer.innerHTML = '';
        }

        // Scroll to results
        resultsContainer.scrollIntoView({ behavior: 'smooth' });
    }

    // Function to create charts
    function createCharts(vizData) {
        // Destroy existing charts if they exist
        if (window.sentimentChart) window.sentimentChart.destroy();
        if (window.biasChart) window.biasChart.destroy();

        // Sentiment Chart
        const sentimentCtx = document.getElementById('sentimentChart').getContext('2d');
        window.sentimentChart = new Chart(sentimentCtx, {
            type: 'bar',
            data: {
                labels: Object.keys(vizData.sentiment_distribution),
                datasets: [{
                    label: 'Sentiment Distribution',
                    data: Object.values(vizData.sentiment_distribution),
                    backgroundColor: [
                        'rgba(76, 175, 80, 0.7)',  // Green for Positive
                        'rgba(255, 183, 77, 0.7)', // Orange for Neutral
                        'rgba(244, 67, 54, 0.7)'   // Red for Negative
                    ],
                    borderColor: [
                        'rgba(76, 175, 80, 1)',
                        'rgba(255, 183, 77, 1)',
                        'rgba(244, 67, 54, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: 'Sentiment Analysis'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });

        // Bias Chart
        const biasCtx = document.getElementById('biasChart').getContext('2d');
        window.biasChart = new Chart(biasCtx, {
            type: 'pie',
            data: {
                labels: Object.keys(vizData.bias_distribution),
                datasets: [{
                    label: 'Political Bias Distribution',
                    data: Object.values(vizData.bias_distribution),
                    backgroundColor: [
                        'rgba(58, 124, 165, 0.7)', // Blue for Left
                        'rgba(242, 204, 80, 0.7)', // Yellow for Center
                        'rgba(214, 73, 51, 0.7)'   // Red for Right
                    ],
                    borderColor: [
                        'rgba(58, 124, 165, 1)',
                        'rgba(242, 204, 80, 1)',
                        'rgba(214, 73, 51, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: 'Political Bias Analysis'
                    }
                }
            }
        });
    }

    // Function to update recommended searches
    function updateRecommendedSearches(searches) {
        recommendedSearchesList.innerHTML = '';
        searches.forEach(search => {
            const item = document.createElement('div');
            item.className = 'recommended-search-item';
            item.innerHTML = `<i class="fas fa-search me-2"></i>${search}`;

            item.addEventListener('click', function() {
                // Fill the search topic input with this search
                document.getElementById('topic-tab').click();
                document.getElementById('search-topic').value = search;
            });

            recommendedSearchesList.appendChild(item);
        });
    }

    // Function to update contrasting views
    function updateContrastingViews(views) {
        contrastingViewsContainer.innerHTML = '';
        views.forEach(view => {
            const viewCard = document.createElement('div');
            viewCard.className = `card view-card ${view.bias} mb-3`;
            viewCard.innerHTML = `
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h6 class="card-title mb-0">${view.title}</h6>
                        <span class="badge ${view.bias}">${view.bias}</span>
                    </div>
                    <p class="card-text text-muted mb-2">Source: ${view.source}</p>
                    <p class="card-text">${view.summary}</p>
                    <div class="text-end">
                        <span class="badge ${view.sentiment}">${view.sentiment}</span>
                    </div>
                </div>
            `;
            contrastingViewsContainer.appendChild(viewCard);
        });
    }
});