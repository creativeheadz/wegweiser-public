// Import the shared GaugeChart class
// Make sure to include the script file in your HTML before this file
// <script src="/static/js/common/gauge_chart.js"></script>

document.addEventListener('DOMContentLoaded', function () {
    const healthScoreContainer = document.getElementById('healthscoreorg');

    if (healthScoreContainer) {
        // Get health score from the container's data attribute
        const healthScore = parseFloat(healthScoreContainer.dataset.healthScore) || 0;
        
        // Create health score gauge
        const healthScoreGauge = new GaugeChart('healthscoreorg', {
            title: 'Health Score'
        });
        
        // Update with the health score value
        // Last updated is not provided in the original code, so we're leaving it undefined
        healthScoreGauge.update(healthScore);
    }
});
