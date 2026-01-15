# Filepath: app/tasks/tenant/analyzer.py
from typing import Dict, Any
import logging
import time
import json
from app.models import db, Tenants, TenantMetadata, Devices
from app.tasks.base.analyzer import BaseAnalyzer
from app.utilities.langchain_utils import generate_tool_recommendations, generate_entity_suggestions


class TenantRecommendationsAnalyzer(BaseAnalyzer):
    task_type = "tenant-ai-recommendations"
    
    def __init__(self, tenant_id: str, metadata_id: str):
        self.tenant_id = tenant_id
        self.metadata_id = metadata_id
        
    def get_cost(self) -> int:
        """Get cost for this analysis type"""
        from app.tasks.base.definitions import AnalysisDefinitions
        return AnalysisDefinitions.get_cost(self.task_type)
    
    def validate(self) -> bool:
        """Validate tenant exists and has profile data"""
        tenant = db.session.query(Tenants).get(self.tenant_id)
        return tenant is not None

    def create_prompt(self, data: Dict[str, Any]) -> str:
        """Create prompt for AI recommendations - not used as we call langchain_utils directly"""
        return ""

    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response - not used as we handle response in analyze method"""
        return {"analysis": response, "score": 50}
    
    def bill_tenant(self) -> bool:
        """Bill the tenant for recommendations analysis"""
        try:
            tenant = db.session.query(Tenants).get(self.tenant_id)
            if not tenant:
                logging.error(f"Tenant not found for recommendations analysis {self.tenant_id}")
                return False

            cost = self.get_cost()
            logging.info(f"Billing tenant {tenant.tenantuuid} {cost} wegcoins for {self.task_type}")
            
            return tenant.deduct_wegcoins(cost, f"AI recommendations analysis for {tenant.tenantname}")
            
        except Exception as e:
            logging.error(f"Billing error for tenant {self.tenant_id}: {str(e)}")
            return False
    
    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute recommendations analysis"""
        try:
            # Get tenant and validate
            tenant = db.session.query(Tenants).get(self.tenant_id)
            if not self.validate():
                raise ValueError("Validation failed")

            # Process billing first
            if not self.bill_tenant():
                raise ValueError("Billing failed")

            # Generate AI recommendations
            logging.info(f"Generating AI recommendations for tenant {tenant.tenantname}")
            recommendations = generate_tool_recommendations(self.tenant_id)
            
            if not recommendations:
                raise ValueError("Failed to generate recommendations")

            # Calculate a simple score based on content length and quality
            score = min(100, max(10, len(recommendations) // 50))
            
            # Update metadata with results
            metadata = db.session.query(TenantMetadata).get(self.metadata_id)
            if metadata:
                metadata.ai_analysis = recommendations
                metadata.metalogos = {'recommendations': recommendations}
                metadata.score = str(score)
                metadata.analyzed_at = int(time.time())
                metadata.processing_status = 'processed'
                db.session.commit()
                
                logging.info(f"Completed AI recommendations analysis for tenant {tenant.tenantname} with score {score}")
                
                return {
                    'analysis': recommendations,
                    'score': score,
                    'metadata_id': self.metadata_id
                }
            else:
                raise ValueError("Metadata not found")
                
        except Exception as e:
            logging.error(f"Error in recommendations analysis for tenant {self.tenant_id}: {str(e)}")
            # Update metadata to show error
            try:
                metadata = db.session.query(TenantMetadata).get(self.metadata_id)
                if metadata:
                    metadata.processing_status = 'error'
                    metadata.ai_analysis = f"Analysis failed: {str(e)}"
                    db.session.commit()
            except:
                pass
            raise


class TenantSuggestionsAnalyzer(BaseAnalyzer):
    task_type = "tenant-ai-suggestions"
    
    def __init__(self, tenant_id: str, metadata_id: str):
        self.tenant_id = tenant_id
        self.metadata_id = metadata_id
        
    def get_cost(self) -> int:
        """Get cost for this analysis type"""
        from app.tasks.base.definitions import AnalysisDefinitions
        return AnalysisDefinitions.get_cost(self.task_type)
    
    def validate(self) -> bool:
        """Validate tenant exists"""
        tenant = db.session.query(Tenants).get(self.tenant_id)
        return tenant is not None

    def create_prompt(self, data: Dict[str, Any]) -> str:
        """Create prompt for AI suggestions - not used as we call langchain_utils directly"""
        return ""

    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response - not used as we handle response in analyze method"""
        return {"analysis": response, "score": 50}
    
    def bill_tenant(self) -> bool:
        """Bill the tenant for suggestions analysis"""
        try:
            tenant = db.session.query(Tenants).get(self.tenant_id)
            if not tenant:
                logging.error(f"Tenant not found for suggestions analysis {self.tenant_id}")
                return False

            cost = self.get_cost()
            logging.info(f"Billing tenant {tenant.tenantuuid} {cost} wegcoins for {self.task_type}")
            
            return tenant.deduct_wegcoins(cost, f"AI strategic analysis for {tenant.tenantname}")
            
        except Exception as e:
            logging.error(f"Billing error for tenant {self.tenant_id}: {str(e)}")
            return False
    
    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute strategic suggestions analysis"""
        try:
            # Get tenant and validate
            tenant = db.session.query(Tenants).get(self.tenant_id)
            if not self.validate():
                raise ValueError("Validation failed")

            # Process billing first
            if not self.bill_tenant():
                raise ValueError("Billing failed")

            # Generate AI suggestions
            logging.info(f"Generating strategic analysis for tenant {tenant.tenantname}")
            suggestions = generate_entity_suggestions('tenant', self.tenant_id)
            
            if not suggestions:
                raise ValueError("Failed to generate suggestions")

            # Calculate a simple score based on content length and quality
            score = min(100, max(15, len(suggestions) // 40))
            
            # Update metadata with results
            metadata = db.session.query(TenantMetadata).get(self.metadata_id)
            if metadata:
                metadata.ai_analysis = suggestions
                metadata.metalogos = {
                    'suggestions': suggestions,
                    'generation_timestamp': int(time.time())
                }
                metadata.score = str(score)
                metadata.analyzed_at = int(time.time())
                metadata.processing_status = 'processed'
                db.session.commit()
                
                logging.info(f"Completed strategic analysis for tenant {tenant.tenantname} with score {score}")
                
                return {
                    'analysis': suggestions,
                    'score': score,
                    'metadata_id': self.metadata_id
                }
            else:
                raise ValueError("Metadata not found")
                
        except Exception as e:
            logging.error(f"Error in suggestions analysis for tenant {self.tenant_id}: {str(e)}")
            # Update metadata to show error
            try:
                metadata = db.session.query(TenantMetadata).get(self.metadata_id)
                if metadata:
                    metadata.processing_status = 'error'
                    metadata.ai_analysis = f"Analysis failed: {str(e)}"
                    db.session.commit()
            except:
                pass
            raise
