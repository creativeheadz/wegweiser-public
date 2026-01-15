# Filepath: app/tasks/utils.py
"""
Shared utilities for AI analysis tasks
"""

import bleach
import logging
import json
import jsonschema
from datetime import datetime
from typing import Dict, Any

# JSON Schema for validating AI responses
ANALYSIS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "analysis": {
            "type": "string",
            "minLength": 50,
            "maxLength": 10000
        },
        "score": {
            "type": "integer",
            "minimum": 1,
            "maximum": 100
        }
    },
    "required": ["analysis", "score"],
    "additionalProperties": False
}


def parse_ai_response(response: str, allowed_tags: list = None) -> Dict[str, Any]:
    """
    Parse AI response into structured format - JSON ONLY

    Args:
        response: Raw AI response text
        allowed_tags: List of allowed HTML tags for sanitization

    Returns:
        Dict containing parsed analysis, score, and timestamp

    Raises:
        ValueError: If response is not valid JSON or doesn't match schema
    """
    return _parse_json_response(response, allowed_tags)

def _parse_json_response(response: str, allowed_tags: list = None) -> Dict[str, Any]:
    """Parse JSON response with schema validation"""
    # Clean response (remove any markdown artifacts)
    cleaned_response = response.strip()
    if cleaned_response.startswith('```json'):
        cleaned_response = cleaned_response[7:]
    if cleaned_response.startswith('```'):
        cleaned_response = cleaned_response[3:]
    if cleaned_response.endswith('```'):
        cleaned_response = cleaned_response[:-3]
    cleaned_response = cleaned_response.strip()

    # Parse JSON
    result = json.loads(cleaned_response)

    # Validate against schema
    jsonschema.validate(result, ANALYSIS_RESPONSE_SCHEMA)

    # Default allowed tags if not specified
    if allowed_tags is None:
        allowed_tags = ['p', 'br', 'ul', 'li', 'strong', 'em', 'h4', 'h5', 'table', 'tr', 'td', 'th']

    # Sanitize HTML in analysis
    sanitized_analysis = bleach.clean(
        result['analysis'],
        tags=allowed_tags,
        attributes={},
        strip=True
    )

    logging.info(f"JSON parsing successful - Score: {result['score']}, Analysis length: {len(sanitized_analysis)}")

    return {
        'analysis': sanitized_analysis,
        'score': int(result['score']),
        'timestamp': datetime.utcnow().isoformat(),
        'parsing_method': 'json_success'
    }


