# Filepath: app/tasks/test_json_analysis.py
"""
Test analyzer for validating JSON response structure from AI
"""
import json
import jsonschema
import logging
import time
from typing import Dict, Any
from datetime import datetime
from app.tasks.base.analyzer import BaseAnalyzer
from app.models import db, DeviceMetadata
import bleach

# JSON Schema for validating AI responses
ANALYSIS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "analysis": {
            "type": "string",
            "minLength": 50,
            "maxLength": 5000
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

class TestJSONAnalyzer(BaseAnalyzer):
    """Test analyzer for JSON response validation"""
    
    task_type = 'test-json-analysis'
    
    def create_prompt(self, current_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Create analysis prompt that requests JSON response"""
        previous = context['analyses'][0] if context['analyses'] else None
        score_trend = context['score_trend']
        trend_text = "No previous scores available"
        
        if score_trend:
            if len(score_trend) > 1:
                if score_trend[0] > score_trend[-1]:
                    trend_text = f"Health score improving: {score_trend[::-1]}"
                elif score_trend[0] < score_trend[-1]:
                    trend_text = f"Health score declining: {score_trend[::-1]}"
                else:
                    trend_text = f"Health score stable: {score_trend[::-1]}"
            else:
                trend_text = f"Single previous score: {score_trend[0]}"

        return f"""You MUST respond with valid JSON only. No other text before or after.

Analyze this test system data and return your response in this exact JSON format:
{{
    "analysis": "HTML formatted analysis with <p>, <ul>, <li> tags",
    "score": 85
}}

Where:
- analysis: Your detailed HTML analysis for display to users (use <p>, <ul>, <li>, <strong>, <em> tags)
- score: Health score from 1-100 (integer only)

Previous Analysis Summary:
Last Health Score: {previous['score'] if previous else 'No previous score'}
Score Trend: {trend_text}

Previous Key Findings:
{previous['analysis'] if previous else 'No previous analysis'}

Test System Data to Analyze:
{json.dumps(current_data, indent=2)}

Analyze this data and provide:
1. Summary of key system metrics
2. Identification of any issues or concerns
3. Overall system health assessment
4. Recommendations for improvement
5. Comparison with previous analysis (if available)

Remember: Respond with ONLY the JSON object, no markdown code blocks, no explanations.
The analysis field should contain properly formatted HTML for web display.
The score should reflect the overall system health based on the data provided."""

    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON response with schema validation and fallback"""
        try:
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
            
            # Sanitize HTML in analysis
            allowed_tags = ['p', 'br', 'ul', 'li', 'strong', 'em', 'h4', 'h5']
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
            
        except json.JSONDecodeError as e:
            logging.error(f"JSON parsing failed: {e}, response: {cleaned_response[:200]}")
            return self._fallback_parse(response, 'json_decode_error')
            
        except jsonschema.ValidationError as e:
            logging.error(f"JSON schema validation failed: {e}, response: {cleaned_response[:200]}")
            return self._fallback_parse(response, 'schema_validation_error')
            
        except Exception as e:
            logging.error(f"Unexpected error parsing JSON: {e}, response: {cleaned_response[:200]}")
            return self._fallback_parse(response, 'unexpected_error')

    def _fallback_parse(self, response: str, error_type: str) -> Dict[str, Any]:
        """Fallback to regex parsing if JSON fails"""
        import re
        
        # Try to extract score using regex (current method)
        match = re.search(r'\|Healthscore (\d+)\|', response)
        score = int(match.group(1)) if match else 50
        
        # Clean HTML
        allowed_tags = ['p', 'br', 'ul', 'li', 'strong', 'em']
        analysis = bleach.clean(
            response,
            tags=allowed_tags,
            attributes={},
            strip=True
        )
        
        logging.warning(f"Used fallback parsing due to: {error_type}")
        
        return {
            'analysis': f'<p>Fallback analysis due to {error_type}</p>{analysis}',
            'score': score,
            'timestamp': datetime.utcnow().isoformat(),
            'parsing_method': f'fallback_{error_type}'
        }

    def get_cost(self) -> int:
        """Test analysis is free"""
        return 0

def create_test_metadata_records(device_uuid: str, num_records: int = 15) -> list:
    """Create test metadata records with varying content"""
    
    test_data_variations = [
        # Short content
        {
            "system_info": {"cpu_usage": 25, "memory_usage": 45, "disk_usage": 60},
            "events": ["System startup", "User login"],
            "status": "normal"
        },
        # Medium content
        {
            "system_info": {"cpu_usage": 85, "memory_usage": 78, "disk_usage": 92},
            "events": ["High CPU usage detected", "Memory warning", "Disk space low", "Service restart"],
            "errors": ["Failed to start service X", "Network timeout"],
            "status": "warning"
        },
        # Long content with many issues
        {
            "system_info": {"cpu_usage": 95, "memory_usage": 89, "disk_usage": 98},
            "events": [
                "Critical system error", "Multiple service failures", "Network connectivity issues",
                "Database connection timeout", "Authentication failures", "Security breach attempt",
                "System overheating", "Hardware malfunction detected"
            ],
            "errors": [
                "CRITICAL: System disk full", "ERROR: Database corruption detected",
                "FATAL: Memory allocation failed", "ERROR: Network interface down",
                "WARNING: High temperature readings", "ERROR: Service dependency failure"
            ],
            "security_events": [
                "Failed login attempts: 15", "Suspicious network activity",
                "Unauthorized access attempt", "Malware signature detected"
            ],
            "performance_metrics": {
                "response_time": 5000, "throughput": 10, "error_rate": 25
            },
            "status": "critical"
        },
        # Minimal content
        {
            "status": "healthy",
            "uptime": "30 days"
        },
        # Complex nested structure
        {
            "hardware": {
                "cpu": {"model": "Intel i7", "cores": 8, "usage": 45},
                "memory": {"total": "16GB", "used": "8GB", "available": "8GB"},
                "storage": [
                    {"drive": "C:", "total": "500GB", "used": "300GB", "type": "SSD"},
                    {"drive": "D:", "total": "1TB", "used": "750GB", "type": "HDD"}
                ]
            },
            "software": {
                "os": "Windows 11", "version": "22H2",
                "installed_programs": 156,
                "updates_pending": 3
            },
            "network": {
                "interfaces": ["Ethernet", "WiFi"],
                "connectivity": "good",
                "bandwidth_usage": "moderate"
            }
        }
    ]
    
    created_records = []
    
    for i in range(num_records):
        # Cycle through test data variations
        test_data = test_data_variations[i % len(test_data_variations)]
        
        # Add some randomization to make each record unique
        if "system_info" in test_data:
            test_data["system_info"]["timestamp"] = int(time.time()) + i
            test_data["system_info"]["record_id"] = i + 1
        
        metadata = DeviceMetadata(
            deviceuuid=device_uuid,
            metalogos_type='test-json-analysis',
            metalogos=test_data,
            processing_status='pending'
        )
        
        db.session.add(metadata)
        created_records.append(metadata)
    
    db.session.commit()
    logging.info(f"Created {len(created_records)} test metadata records")
    return created_records

def run_json_consistency_test(device_uuid: str) -> Dict[str, Any]:
    """Run the JSON consistency test on all pending test records"""
    
    # Get all pending test records for the device
    test_records = db.session.query(DeviceMetadata).filter(
        DeviceMetadata.deviceuuid == device_uuid,
        DeviceMetadata.metalogos_type == 'test-json-analysis',
        DeviceMetadata.processing_status == 'pending'
    ).all()
    
    if not test_records:
        return {"error": "No test records found"}
    
    results = {
        "total_tests": len(test_records),
        "json_success": 0,
        "json_failures": 0,
        "schema_failures": 0,
        "fallback_used": 0,
        "parsing_methods": {},
        "score_distribution": {},
        "test_details": []
    }
    
    analyzer = TestJSONAnalyzer(device_uuid, None)
    
    for record in test_records:
        try:
            # Set the metadata_id for this test
            analyzer.metadata_id = str(record.metadatauuid)
            
            # Run the analysis
            result = analyzer.analyze(record.metalogos)
            
            # Track results
            parsing_method = result.get('parsing_method', 'unknown')
            results['parsing_methods'][parsing_method] = results['parsing_methods'].get(parsing_method, 0) + 1
            
            if parsing_method == 'json_success':
                results['json_success'] += 1
            elif 'fallback' in parsing_method:
                results['fallback_used'] += 1
                if 'schema' in parsing_method:
                    results['schema_failures'] += 1
                else:
                    results['json_failures'] += 1
            
            # Track score distribution
            score_range = f"{(result['score'] // 10) * 10}-{(result['score'] // 10) * 10 + 9}"
            results['score_distribution'][score_range] = results['score_distribution'].get(score_range, 0) + 1
            
            # Store test details
            results['test_details'].append({
                "record_id": str(record.metadatauuid),
                "data_size": len(str(record.metalogos)),
                "parsing_method": parsing_method,
                "score": result['score'],
                "analysis_length": len(result['analysis'])
            })
            
        except Exception as e:
            logging.error(f"Test failed for record {record.metadatauuid}: {e}")
            results['test_details'].append({
                "record_id": str(record.metadatauuid),
                "error": str(e),
                "parsing_method": "test_error"
            })
    
    # Calculate success rate
    results['json_success_rate'] = (results['json_success'] / results['total_tests']) * 100
    results['overall_success_rate'] = ((results['json_success'] + results['fallback_used']) / results['total_tests']) * 100
    
    return results
