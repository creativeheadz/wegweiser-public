/**
 * Guided Tour Manager
 * Reusable JavaScript component for managing Shepherd.js guided tours across the application.
 * Filepath: app/static/js/common/guided-tour.js
 */

class GuidedTourManager {
    constructor() {
        this.tour = null;
        this.tourData = null;
        this.pageIdentifier = null;
        this.isInitialized = false;
    }

    /**
     * Initialize the tour system for a specific page
     * @param {Object} tourData - Tour configuration data from backend
     * @param {string} pageIdentifier - Unique page identifier
     */
    init(tourData, pageIdentifier) {
        if (!tourData || !pageIdentifier) {
            console.warn('GuidedTourManager: Missing tour data or page identifier');
            return false;
        }

        this.tourData = tourData;
        this.pageIdentifier = pageIdentifier;
        this.isInitialized = true;

        // Load Shepherd.js if not already loaded
        this.loadShepherdJS().then(() => {
            this.createTour();
            this.setupEventListeners();
            
            // Auto-start tour if configured and user hasn't completed it
            if (this.shouldAutoStart()) {
                this.startTour();
            }
        }).catch(error => {
            console.error('Failed to load Shepherd.js:', error);
        });

        return true;
    }

    /**
     * Load Shepherd.js library if not already loaded
     */
    async loadShepherdJS() {
        if (window.Shepherd) {
            return Promise.resolve();
        }

        return new Promise((resolve, reject) => {
            // Load CSS
            const cssLink = document.createElement('link');
            cssLink.rel = 'stylesheet';
            cssLink.href = 'https://cdn.jsdelivr.net/npm/shepherd.js@11.1.1/dist/css/shepherd.css';
            document.head.appendChild(cssLink);

            // Load JS
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/shepherd.js@11.1.1/dist/js/shepherd.min.js';
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    /**
     * Create the Shepherd tour instance
     */
    createTour() {
        if (!window.Shepherd) {
            console.error('Shepherd.js not loaded');
            return;
        }

        const defaultConfig = {
            useModalOverlay: true,
            defaultStepOptions: {
                classes: 'shadow-md bg-purple-dark',
                scrollTo: true,
                cancelIcon: {
                    enabled: true
                }
            }
        };

        // Merge with custom configuration
        const config = { ...defaultConfig, ...this.tourData.tour_config };
        this.tour = new Shepherd.Tour(config);

        // Add steps
        this.addSteps();

        // Add tour event listeners
        this.tour.on('complete', () => this.onTourComplete());
        this.tour.on('cancel', () => this.onTourCancel());
    }

    /**
     * Add steps to the tour
     */
    addSteps() {
        if (!this.tourData.steps || !Array.isArray(this.tourData.steps)) {
            console.error('Invalid tour steps data');
            return;
        }

        this.tourData.steps.forEach((stepData, index) => {
            const step = this.createStepConfig(stepData, index);
            this.tour.addStep(step);
        });
    }

    /**
     * Create step configuration for Shepherd
     */
    createStepConfig(stepData, index) {
        const isFirst = index === 0;
        const isLast = index === this.tourData.steps.length - 1;
        
        const step = {
            id: stepData.id,
            text: stepData.text,
            attachTo: stepData.attachTo,
            buttons: this.createStepButtons(isFirst, isLast, stepData.id),
            classes: stepData.classes || '',
            scrollTo: stepData.scrollTo !== false
        };

        // Add optional properties
        if (stepData.title) step.title = stepData.title;
        if (stepData.when) step.when = stepData.when;

        return step;
    }

    /**
     * Create navigation buttons for a step
     */
    createStepButtons(isFirst, isLast, stepId) {
        const buttons = [];

        // Back button (not on first step)
        if (!isFirst) {
            buttons.push({
                text: 'Back',
                action: this.tour.back,
                classes: 'btn btn-secondary'
            });
        }

        // Next/Done button
        if (isLast) {
            buttons.push({
                text: 'Done',
                action: () => {
                    this.markStepComplete(stepId);
                    this.tour.complete();
                },
                classes: 'btn btn-success'
            });
        } else {
            buttons.push({
                text: 'Next',
                action: () => {
                    this.markStepComplete(stepId);
                    this.tour.next();
                },
                classes: 'btn btn-primary'
            });
        }

        return buttons;
    }

    /**
     * Start the tour
     */
    startTour() {
        if (!this.tour) {
            console.error('Tour not initialized');
            return;
        }

        this.tour.start();
        this.markTourStarted();
    }

    /**
     * Check if tour should auto-start
     */
    shouldAutoStart() {
        if (!this.tourData.auto_start) return false;
        
        // Check if user has already completed the tour
        const userProgress = this.tourData.user_progress;
        if (userProgress && userProgress.is_completed) return false;

        // Check if tour was already started in this session
        const sessionKey = `tour_started_${this.pageIdentifier}`;
        if (sessionStorage.getItem(sessionKey)) return false;

        return true;
    }

    /**
     * Mark tour as started in session
     */
    markTourStarted() {
        const sessionKey = `tour_started_${this.pageIdentifier}`;
        sessionStorage.setItem(sessionKey, 'true');
    }

    /**
     * Mark a step as completed
     */
    markStepComplete(stepId) {
        // Send to backend
        fetch('/api/tours/step-complete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({
                page_identifier: this.pageIdentifier,
                step_id: stepId
            })
        }).catch(error => {
            console.error('Failed to mark step complete:', error);
        });
    }

    /**
     * Handle tour completion
     */
    onTourComplete() {
        debug.log('Tour completed for page:', this.pageIdentifier);
        
        // Send completion event to backend
        fetch('/api/tours/complete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({
                page_identifier: this.pageIdentifier
            })
        }).catch(error => {
            console.error('Failed to mark tour complete:', error);
        });

        // Trigger custom event
        window.dispatchEvent(new CustomEvent('tourComplete', {
            detail: { pageIdentifier: this.pageIdentifier }
        }));
    }

    /**
     * Handle tour cancellation
     */
    onTourCancel() {
        debug.log('Tour cancelled for page:', this.pageIdentifier);
    }

    /**
     * Reset tour progress
     */
    resetProgress() {
        fetch('/api/tours/reset', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({
                page_identifier: this.pageIdentifier
            })
        }).then(() => {
            location.reload(); // Reload to reset UI state
        }).catch(error => {
            console.error('Failed to reset tour progress:', error);
        });
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Listen for start tour button clicks
        document.addEventListener('click', (event) => {
            if (event.target.matches('[data-tour-start]') || 
                event.target.closest('[data-tour-start]')) {
                event.preventDefault();
                this.startTour();
            }
        });

        // Listen for reset tour button clicks
        document.addEventListener('click', (event) => {
            if (event.target.matches('[data-tour-reset]') || 
                event.target.closest('[data-tour-reset]')) {
                event.preventDefault();
                if (confirm('Are you sure you want to reset your tour progress?')) {
                    this.resetProgress();
                }
            }
        });
    }

    /**
     * Get CSRF token from meta tag
     */
    getCSRFToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }

    /**
     * Check if tour is available for current page
     */
    isAvailable() {
        return this.isInitialized && this.tour !== null;
    }

    /**
     * Get tour progress information
     */
    getProgress() {
        return this.tourData ? this.tourData.user_progress : null;
    }
}

// Create global instance
window.guidedTourManager = new GuidedTourManager();

// Auto-initialize if tour data is available
document.addEventListener('DOMContentLoaded', function() {
    if (window.tourData && window.pageIdentifier) {
        window.guidedTourManager.init(window.tourData, window.pageIdentifier);
    }
});
