# Filepath: app/tasks/base/prompt.py
# app/tasks/base/prompt.py
from typing import Dict, Any
from datetime import datetime
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class AnalysisConfig:
    """Configuration for analysis type"""
    source_type: str              # Type of data in metalogos
    data_format: str             # Expected format (json/array)
    consolidation_window: int    # Days of history to maintain
    output_format: str          # Required output format
    baseline_cost: int          # Wegcoins for baseline
    delta_cost: int            # Wegcoins for delta analysis

class PromptTemplate(ABC):
    """Base class for analysis prompts"""
    
    @abstractmethod
    def baseline_prompt(self, data: Dict[str, Any]) -> str:
        """Generate baseline analysis prompt"""
        pass

    @abstractmethod
    def delta_prompt(self, 
                    delta: Dict[str, Any], 
                    context: Dict[str, Any]) -> str:
        """Generate delta analysis prompt"""
        pass

    @abstractmethod
    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response into standard format"""
        pass

# Example implementation
class JournalPromptTemplate(PromptTemplate):
    def baseline_prompt(self, data: Dict[str, Any]) -> str:
        return f"""Analyze these Linux journal logs to establish a baseline.
        
System Health Assessment:
- Overall patterns
- Critical issues and impacts
- Recurring problems
- Performance metrics
- Security concerns

Format as HTML with proper tags (<p>, <ul>, <li>).
Include a health score from 1-100

Data: {data}"""

    def delta_prompt(self, delta: Dict[str, Any], context: Dict[str, Any]) -> str:
        return f"""Analyze new journal logs in context of previous findings.

Previous Analysis:
{context['latest_analysis']}
Previous Health Score: {context['health_score']}

New Data:
{delta}

Focus on:
1. Changes since last analysis
2. Improvement/degradation
3. New issues
4. Updated recommendations

Format as HTML. Include updated health score from 1-100"""

    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response - JSON ONLY"""
        import bleach
        import json
        import jsonschema

        # JSON schema for validation
        schema = {
            "type": "object",
            "properties": {
                "analysis": {"type": "string"},
                "score": {"type": "integer", "minimum": 1, "maximum": 100}
            },
            "required": ["analysis", "score"]
        }

        try:
            # Parse JSON
            result = json.loads(response.strip())

            # Validate schema
            jsonschema.validate(result, schema)

            # Sanitize HTML
            allowed_tags = ['p', 'br', 'ul', 'li', 'strong', 'em']
            sanitized_analysis = bleach.clean(
                result['analysis'],
                tags=allowed_tags,
                attributes={},
                strip=True
            )

            return {
                'analysis': sanitized_analysis,
                'score': int(result['score']),
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as e:
            raise ValueError(f"AI response must be valid JSON: {e}")