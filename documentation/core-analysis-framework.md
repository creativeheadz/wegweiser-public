# Wegweiser Analysis Framework Documentation

## Overview
The Wegweiser Analysis Framework is a modular system for processing and analyzing various types of system data from client machines. The framework uses AI-powered analysis to generate insights, recommendations, and health scores.

## Core Components

### 1. Analyzers
Each type of analysis (e.g., system logs, network configuration, installed programs) has its own dedicated analyzer that:
- Inherits from BaseAnalyzer
- Has a unique task_type identifier
- Processes specific types of metadata
- Generates AI prompts with historical context
- Produces standardized analysis output

### 2. Directory Structure
app/tasks/
├── base/
│   ├── analyzer.py     # Base analyzer class
│   ├── scheduler.py    # Task scheduling and management
│   └── definitions.py  # Analysis configurations
├── [analysis_type]/    # e.g., journal/, network/, storage/
├── init.py
├── analyzer.py     # Specific analyzer implementation
├── definition.py   # Analysis configuration
└── prompts/        # AI prompts
├── init.py
└── base.prompt
### 3. Analysis Process Flow
1. Agent collects data and stores in DeviceMetadata table
2. Celery worker picks up pending analyses
3. Analyzer validates data and billing
4. Historical context is gathered
5. AI analysis is performed
6. Results are stored and health score updated

### 4. Key Features
- Automatic billing via wegcoins
- Historical context tracking
- Standardized health scoring
- Error handling and retries
- Configurable schedules per analysis type

## Implementation Guide

### Adding a New Analyzer
1. Create new directory under app/tasks/
2. Implement analyzer class inheriting from BaseAnalyzer
3. Define configuration in definition.py
4. Create prompt template
5. Register in scheduler.py
6. Add to Celery schedule

Example:
```python
# app/tasks/newtype/analyzer.py
class NewTypeAnalyzer(BaseAnalyzer):
    task_type = 'new-type'
    
    def create_prompt(self, current_data, context):
        # Implementation
        
    def parse_response(self, response):
        # Implementation

ANALYSIS_CONFIG = {
    "type": "analysis-type",
    "description": "Analysis Description",
    "cost": 1,            # Wegcoins per analysis
    "schedule": 3600,     # Seconds between runs
    "input_type": "json", # Expected input format
    "output_format": "html"
}

Billing and Scheduling

Each analysis costs configurable wegcoins
Scheduling is handled by Celery
Default 60-second worker checks for pending analyses
Each analysis type can have different costs/schedules

Error Handling

Database connection retries
AI response validation
JSON parsing error handling
Billing verification
Transaction management

Best Practices

Always include historical context in analysis
Validate input data before processing
Use proper error handling
Keep prompts in separate files
Document configuration changes
Test with various data formats

Common Issues and Solutions

Database connection errors

Solution: Automatic retry with exponential backoff


Invalid metadata format

Solution: Input validation in BaseAnalyzer


AI response parsing

Solution: Standardized response format and error handling



Monitoring and Maintenance

Check celery worker logs for errors
Monitor wegcoin deductions
Review analysis health scores
Check processing queue lengths
Monitor AI response times

Future Improvements

Enhanced metrics and monitoring
Automated retry system for failed analyses
More sophisticated billing options
Enhanced historical trending
Dynamic prompt adjustment based on results