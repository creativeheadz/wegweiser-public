# Filepath: app/tasks/base/analyzer.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.models import db, DeviceMetadata, Devices
import logging
import json
import jsonschema
import bleach

from .definitions import AnalysisDefinitions
from .exclusions import build_exclusion_block, get_tenant_prompt_config, get_density_config
from flask import current_app

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

class BaseAnalyzer(ABC):
    """Base class for all analyzers"""

    def __init__(self, device_id: str, metadata_id: str):
        self.device_id = device_id
        self.metadata_id = metadata_id
        self._config = None

    @property
    @abstractmethod
    def task_type(self) -> str:
        """Unique identifier for this analysis type"""
        pass

    @property
    def config(self) -> Dict[str, Any]:
        """Get analyzer configuration from definitions"""
        if not self._config:
            self._config = AnalysisDefinitions.get_config(self.task_type)
        return self._config

    def get_cost(self) -> int:
        """Get cost for this analysis type"""
        return self.config.get('cost', 1)  # Default to 1 if not specified

    def get_exclusion_block(self) -> str:
        """Get the sandboxed exclusion block for this device and analysis type.
        
        Returns empty string if no exclusions are configured.
        Child classes should include this in their prompt assembly.
        """
        if hasattr(self, 'device_id') and self.device_id:
            return build_exclusion_block(self.device_id, self.task_type)
        return ''

    def get_tenant_id(self) -> Optional[str]:
        """Get tenant ID for the current device"""
        if hasattr(self, 'device_id') and self.device_id:
            try:
                device = db.session.get(Devices, self.device_id)
                if device:
                    return str(device.tenantuuid)
            except Exception as e:
                logging.error(f"Error getting tenant ID: {e}")
        return None

    def get_custom_criteria(self, default_criteria: str) -> str:
        """Get tenant's custom criteria prompt or return default.
        
        Args:
            default_criteria: The default criteria text to use if tenant hasn't customized
            
        Returns:
            Tenant's custom criteria if set, otherwise the default
        """
        tenant_id = self.get_tenant_id()
        if tenant_id:
            prompt_config = get_tenant_prompt_config(tenant_id, self.task_type)
            if prompt_config and prompt_config.criteria_prompt:
                return prompt_config.criteria_prompt
        return default_criteria

    def get_density(self) -> Dict[str, int]:
        """Get output density configuration for this analysis type.
        
        Returns tenant's custom config if set, otherwise defaults.
        """
        tenant_id = self.get_tenant_id()
        if tenant_id:
            return get_density_config(tenant_id, self.task_type)
        from app.models.analysis_config import get_default_density_config
        return get_default_density_config()


    def _clean_historical_analysis(self, analysis_text: Optional[str]) -> str:
        """No-op cleaner for historical analysis text.
        Left intentionally minimal now that DB has been cleaned and JSON-only parsing is enforced.
        """
        return analysis_text or ""


    def get_historical_context(self, limit: int = 5) -> Dict[str, Any]:
        """Get historical analyses in chronological order"""
        try:
            previous_analyses = (DeviceMetadata.query
                .filter_by(
                    deviceuuid=self.device_id,
                    metalogos_type=self.task_type,
                    processing_status='processed'
                )
                .order_by(DeviceMetadata.created_at.desc())
                .limit(limit)
                .all())

            if not previous_analyses:
                return {
                    'analyses': [],
                    'score_trend': [],
                    'last_score': None
                }

            return {
                'analyses': [
                    {
                        'timestamp': entry.created_at,
                        'analysis': self._clean_historical_analysis(entry.ai_analysis),
                        'score': entry.score
                    } for entry in previous_analyses
                ],
                'score_trend': [entry.score for entry in previous_analyses],
                'last_score': previous_analyses[0].score
            }

        except Exception as e:
            logging.error(f"Error getting historical context: {str(e)}")
            return {
                'analyses': [],
                'score_trend': [],
                'last_score': None
            }

    @abstractmethod
    def create_prompt(self, current_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Create analysis prompt with historical context"""
        pass

    @abstractmethod
    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response"""
        pass

    def parse_json_response(self, response: str) -> Dict[str, Any]:
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
            raise ValueError(f"AI response is not valid JSON: {e}")

        except jsonschema.ValidationError as e:
            logging.error(f"JSON schema validation failed: {e}, response: {cleaned_response[:200]}")
            raise ValueError(f"AI response does not match required schema: {e}")

        except Exception as e:
            logging.error(f"Unexpected error parsing JSON: {e}, response: {cleaned_response[:200]}")
            raise ValueError(f"Failed to parse AI response: {e}")



    def validate(self) -> bool:
        """Validate input data and billing status"""
        try:
            # Coerce IDs to UUID objects when possible to avoid cast issues
            import uuid as _uuid
            try:
                metadata_pk = _uuid.UUID(str(self.metadata_id))
            except Exception:
                logging.error(f"Invalid metadata_id format: {self.metadata_id}")
                return False

            try:
                device_pk = _uuid.UUID(str(self.device_id))
            except Exception:
                logging.error(f"Invalid device_id format: {self.device_id}")
                return False

            metadata = db.session.get(DeviceMetadata, metadata_pk)
            device = db.session.get(Devices, device_pk)

            if not metadata or not metadata.metalogos:
                logging.error(f"Missing or invalid metadata for {self.metadata_id}")
                return False

            # Check tenant has enough wegcoins
            if not device.tenant.available_wegcoins >= self.get_cost():
                # Disable all analyses for this tenant instead of repeatedly logging
                if device.tenant.recurring_analyses_enabled:
                    device.tenant.disable_all_analyses()
                    db.session.commit()
                    logging.warning(f"Disabled all analyses for tenant {device.tenant.tenantuuid} due to insufficient wegcoins")
                return False

            # Verify device exists and belongs to tenant
            if not device:
                logging.error(f"Device not found: {self.device_id}")
                return False

            # Verify metadata belongs to device
            if str(metadata.deviceuuid) != str(self.device_id):
                logging.error(f"Metadata {self.metadata_id} does not belong to device {self.device_id}")
                return False

            # Verify input type if specified
            if input_type := self.config.get('input_type'):
                if input_type == 'json':
                    if not isinstance(metadata.metalogos, (dict, list)):
                        logging.error(f"Invalid input type for {self.metadata_id}")
                        return False
                elif not isinstance(metadata.metalogos, str):
                    logging.error(f"Invalid input type for {self.metadata_id}")
                    return False

            return True

        except Exception as e:
            logging.error(f"Validation error: {str(e)}")
            return False

    def bill_tenant(self, device: Devices) -> bool:
        """Process billing for the analysis"""
        try:
            cost = self.get_cost()
            tenant = device.tenant
            logging.info(f"Billing tenant {tenant.tenantuuid} {cost} wegcoins for {self.task_type}")

            return tenant.deduct_wegcoins(cost, f"{self.task_type} analysis")

        except Exception as e:
            logging.error(f"Billing error: {str(e)}")
            return False

    def get_ai_client(self):
        """Get configured OpenAI client"""
        from openai import AzureOpenAI
        return AzureOpenAI(
            api_key=current_app.config["AZURE_OPENAI_API_KEY"],
            api_version=current_app.config.get("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            azure_endpoint=current_app.config["AZURE_OPENAI_ENDPOINT"]
        )

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute analysis with historical context"""
        try:
            # Get device and validate before transaction
            import uuid as _uuid
            device = db.session.get(Devices, _uuid.UUID(str(self.device_id)))
            if not self.validate():
                raise ValueError("Validation failed")

            # Process billing first - this handles its own transaction
            if not self.bill_tenant(device):
                raise ValueError("Billing failed")

            # Get historical context
            context = self.get_historical_context()

            # Add device data to context if analyzer has get_data_sources method
            if hasattr(self, 'get_data_sources'):
                context['device_data'] = self.get_data_sources(self.device_id)

            # Create prompt with context
            prompt = self.create_prompt(data, context)

            # Get AI response
            client = self.get_ai_client()
            response = client.chat.completions.create(
                model="wegweiser",
                messages=[
                    {"role": "system", "content": "You are a Linux system analyst."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config.get('max_tokens', 1500),
                temperature=self.config.get('temperature', 0.5)
            )

            # Parse response
            result = self.parse_response(response.choices[0].message.content)

            # Update metadata
            metadata = db.session.get(DeviceMetadata, _uuid.UUID(str(self.metadata_id)))
            metadata.ai_analysis = result['analysis']
            metadata.score = result['score']
            metadata.processing_status = 'processed'
            metadata.analyzed_at = int(datetime.utcnow().timestamp())

            db.session.commit()
            return result

        except Exception as e:
            msg = f"Analysis error for {self.task_type} on device {self.device_id}: {str(e)}"
            if str(e) == "Validation failed":
                logging.info(msg)
            else:
                logging.error(msg)
            # Best-effort mark as failed to avoid stuck 'processing' items
            try:
                import uuid as _uuid
                metadata = db.session.get(DeviceMetadata, _uuid.UUID(str(self.metadata_id)))
                if metadata:
                    metadata.processing_status = 'failed'
                    metadata.ai_analysis = f'<p>Analysis failed: {str(e)}</p>'
                    metadata.score = 0
                    metadata.analyzed_at = int(datetime.utcnow().timestamp())
                    db.session.commit()
                else:
                    db.session.rollback()
            except Exception as _e:
                logging.error(f"Failed to mark metadata as failed: {_e}")
                db.session.rollback()
            return {
                'analysis': f'<p>Analysis failed: {str(e)}</p>',
                'score': 0,
                'timestamp': datetime.utcnow().isoformat()
            }