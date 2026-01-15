# Filepath: app/tasks/base/billing.py
# app/tasks/base/billing.py
from typing import Dict, Any
from abc import abstractmethod
from app.models import db, WegcoinTransaction, Tenants, Devices
from datetime import datetime

class AnalysisBilling:
    """Handles analysis billing"""
    
    def __init__(self, tenant_id: str, task_type: str):
        self.tenant_id = tenant_id
        self.task_type = task_type

    def bill(self, amount: int, description: str = None) -> bool:
        """Process billing transaction"""
        tenant = Tenants.query.get(self.tenant_id)
        if not tenant or tenant.available_wegcoins < amount:
            return False

        try:
            transaction = WegcoinTransaction(
                tenantuuid=self.tenant_id,
                amount=-amount,
                transaction_type='analysis',
                description=description or f"{self.task_type} analysis"
            )
            tenant.available_wegcoins -= amount
            
            db.session.add(transaction)
            db.session.add(tenant)
            db.session.commit()
            return True

        except Exception:
            db.session.rollback()
            return False

    def get_cost(self, cycle_type: str = 'per_analysis') -> int:
        """Get cost based on cycle type"""
        costs = {
            'per_analysis': 1,
            'daily': 5,
            'monthly': 50
        }
        return costs.get(cycle_type, 1)

# Update BaseAnalyzer
class BaseAnalyzer:
    def __init__(self, device_id: str, metadata_id: str):
        self.device_id = device_id
        self.metadata_id = metadata_id
        self.redis = redis_manager
        self._billing = None

    @property
    def billing(self) -> AnalysisBilling:
        """Lazy load billing handler"""
        if not self._billing:
            device = Devices.query.get(self.device_id)
            self._billing = AnalysisBilling(
                str(device.tenant.tenantuuid),
                self.task_type
            )
        return self._billing

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Handle billing first
        cost = self.billing.get_cost(self.billing_cycle)
        if not self.billing.bill(cost):
            raise ValueError("Billing failed")
            
        # Continue with analysis
        return self._perform_analysis(data)

    @abstractmethod
    def _perform_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Implement actual analysis logic"""
        pass