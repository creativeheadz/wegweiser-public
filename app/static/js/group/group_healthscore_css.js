// CSS-only gauge alternative for maximum performance on MacBook Pro
document.addEventListener('DOMContentLoaded', function () {
    const healthScoreContainer = document.getElementById('healthscoreorg');

    if (healthScoreContainer) {
        const healthScore = parseFloat(healthScoreContainer.dataset.healthScore) || 0;
        
        // Create CSS-only gauge
        function createCSSGauge() {
            healthScoreContainer.innerHTML = `
                <div class="css-gauge" style="--percentage: ${healthScore}">
                    <div class="css-gauge-content">
                        <div class="css-gauge-value">${Math.round(healthScore)}%</div>
                        <div class="css-gauge-label">Health Score</div>
                    </div>
                </div>
            `;
        }

        createCSSGauge();
    }
});
