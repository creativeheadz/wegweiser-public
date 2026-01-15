# Filepath: app/models/tenants.py
import uuid
import time
import logging
from app.utilities.app_logging_helper import log_with_route
from .wegcoin_transaction import WegcoinTransaction
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text
from app.models.tenantmetadata import TenantMetadata
from sqlalchemy.ext.mutable import MutableDict
from typing import Dict, Any, List
from . import db

def get_default_analysis_toggles():
    return {
        # Event Logs
        'journalFiltered': True,
        'authFiltered': True,
        'eventsFiltered-Application': True,
        'eventsFiltered-Security': True,
        'eventsFiltered-System': True,
        'syslogFiltered': True,
        'kernFiltered': True,

        # System Information
        'msinfo-InstalledPrograms': True,
        'msinfo-NetworkConfig': True,
        'msinfo-StorageInfo': True,
        'msinfo-SystemHardwareConfig': True,
        'msinfo-SystemSoftwareConfig': True,

        # Specific Analyses
        'windrivers': True,
        'msinfo-RecentAppCrashes': True,

        # Group Analyses
        'group-health-analysis': True,

        # Organization Analyses
        'organization-health-analysis': True,

        # Tenant Analyses
        'tenant-ai-recommendations': False,
        'tenant-ai-suggestions': False,

        # macOS Analyses
        'macos-hardware-eol-analysis': True,
        'macos-os-version-analysis': True,
        'macos-log-health-analysis': True,

        # Security Audits
        'lynis-audit': False  # Premium feature, disabled by default
    }

class Tenants(db.Model):
    __tablename__ = 'tenants'
    tenantuuid = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenantname = db.Column(db.String(100), unique=True, nullable=True)
    address = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    logo_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.BigInteger, nullable=False, default=lambda: int(time.time()))
    last_active = db.Column(db.BigInteger, nullable=True)
    rmm_type = db.Column(db.String(50), nullable=True)
    industry = db.Column(db.String(100), nullable=True)
    company_size = db.Column(db.String(50), nullable=True)
    primary_focus = db.Column(db.String(100), nullable=True)
    service_areas = db.Column(JSONB, nullable=True)
    specializations = db.Column(JSONB, nullable=True)
    customer_industries = db.Column(JSONB, nullable=True)
    monitoring_preferences = db.Column(JSONB, nullable=True)
    sla_details = db.Column(JSONB, nullable=True)
    preferred_communication_style = db.Column(db.String(20))
    health_score = db.Column(db.Float, nullable=True)
    last_ai_interaction = db.Column(db.BigInteger, nullable=True)
    ai_context = db.Column(JSONB, nullable=True)
    available_wegcoins = db.Column(db.Integer, default=0)
    recurring_analyses_enabled = db.Column(db.Boolean, default=True)
    profile_data = db.Column(JSONB, nullable=True)
    analysis_toggles = db.Column(MutableDict.as_mutable(JSONB), default=get_default_analysis_toggles)
    analysis_costs = db.Column(JSONB, nullable=True)

    # Relationships
    wegcoin_transactions = relationship("WegcoinTransaction", back_populates="tenant")
    organisations = relationship("Organisations", cascade="all, delete-orphan", passive_deletes=True)
    groups = relationship("Groups", cascade="all, delete-orphan", passive_deletes=True)
    messages = relationship('Messages', back_populates='tenant', cascade="all, delete-orphan")
    conversations = relationship("Conversations", back_populates="tenant")
    contexts = relationship("Context", back_populates="tenant")
    ai_memories = relationship('AIMemory', back_populates='tenant')
    devices = relationship("Devices", back_populates="tenant")

    def update_profile(self, data):
        if self.profile_data is None:
            self.profile_data = {}
        self.profile_data.update(data)
        db.session.commit()

    def get_profile_data(self, key, default=None):
        return self.profile_data.get(key, default) if self.profile_data else default

    def get_uuid(self):
        return self.tenantuuid

    def update_health_score(self):
        device_scores = [device.health_score for device in self.devices if device.health_score is not None]
        if device_scores:
            self.health_score = sum(device_scores) / len(device_scores)
        else:
            self.health_score = None
        db.session.commit()

    def update_ai_context(self, new_context):
        if self.ai_context is None:
            self.ai_context = {}
        self.ai_context.update(new_context)
        self.last_ai_interaction = int(time.time())
        db.session.commit()

    def get_overview(self):
        query = text("""
        SELECT t.tenantuuid, t.tenantname, t.health_score, t.available_wegcoins,
            COUNT(DISTINCT o.orguuid) AS org_count,
            COUNT(DISTINCT g.groupuuid) AS group_count,
            COUNT(DISTINCT d.deviceuuid) AS device_count,
            JSON_AGG(DISTINCT jsonb_build_object(
                'groupname', g.groupname,
                'groupuuid', g.groupuuid,
                'device_count', (SELECT COUNT(*) FROM public.devices WHERE groupuuid = g.groupuuid)
            )) AS group_details,
            JSON_AGG(DISTINCT jsonb_build_object(
                'orgname', o.orgname,
                'orguuid', o.orguuid,
                'group_count', (SELECT COUNT(*) FROM public.groups WHERE orguuid = o.orguuid)
            )) AS org_details
        FROM public.tenants t
        LEFT JOIN public.organisations o ON t.tenantuuid = o.tenantuuid
        LEFT JOIN public.groups g ON t.tenantuuid = g.tenantuuid
        LEFT JOIN public.devices d ON t.tenantuuid = d.tenantuuid
        WHERE t.tenantuuid = :tenant_uuid
        GROUP BY t.tenantuuid, t.tenantname, t.health_score, t.available_wegcoins
        """)

        result = db.session.execute(query, {'tenant_uuid': self.tenantuuid})
        row = result.fetchone()
        if not row:
            return None

        return {
            'tenantuuid': str(row.tenantuuid),
            'tenantname': row.tenantname,
            'health_score': row.health_score,
            'available_wegcoins': row.available_wegcoins,
            'org_count': row.org_count,
            'group_count': row.group_count,
            'device_count': row.device_count,
            'group_details': row.group_details,
            'org_details': row.org_details
        }

    def deduct_wegcoins(self, amount=1, description="AI analysis usage"):
        """
        Deduct wegcoins from tenant balance
        
        Args:
            amount: Number of wegcoins to deduct
            description: Optional description for the transaction
            
        Returns:
            bool: True if deduction successful, False if insufficient balance
        """
        if self.available_wegcoins < amount:
            return False
            
        try:
            from app.models import WegcoinTransaction
            
            # Create transaction record
            transaction = WegcoinTransaction(
                tenantuuid=self.tenantuuid,
                amount=-amount,  # Negative for deduction
                transaction_type='usage',
                description=description or 'AI usage'
            )
            
            # Update tenant balance
            self.available_wegcoins -= amount
            
            # Save changes
            db.session.add(transaction)
            db.session.add(self)
            db.session.commit()
            
            return True
        except Exception as e:
            db.session.rollback()
            return False

    def calculate_total_spent(self):
        """Calculate total Wegcoins spent by tenant"""
        from app.models import WegcoinTransaction
        
        spent = db.session.query(db.func.sum(WegcoinTransaction.amount)).filter(
            WegcoinTransaction.tenantuuid == self.tenantuuid,
            WegcoinTransaction.amount < 0  # Only count negative amounts (spent)
        ).scalar()
        
        return abs(spent) if spent else 0

    def add_wegcoins(self, amount, transaction_type='purchase', description="Wegcoin purchase"):
        self.available_wegcoins += amount
        transaction = WegcoinTransaction(
            tenantuuid=self.tenantuuid,
            amount=amount,
            transaction_type=transaction_type,
            description=description
        )
        db.session.add(transaction)
        db.session.add(self)  # Add the updated tenant object to the session
        db.session.commit()

    def get_wegcoin_balance(self):
        return self.available_wegcoins

    def get_wegcoin_transaction_history(self, limit=50):
        return WegcoinTransaction.query.filter_by(tenantuuid=self.tenantuuid).order_by(WegcoinTransaction.created_at.desc()).limit(limit).all()

    def toggle_recurring_analyses(self):
        """Toggle the recurring analyses enabled/disabled for the tenant."""
        self.recurring_analyses_enabled = not self.recurring_analyses_enabled
        db.session.commit()
        return self.recurring_analyses_enabled

    def is_analysis_enabled(self, analysis_type: str) -> bool:
        """Check if specific analysis type is enabled"""
        if not self.recurring_analyses_enabled:
            return False
            
        if self.analysis_toggles is None:
            self.analysis_toggles = get_default_analysis_toggles()
            
        return self.analysis_toggles.get(analysis_type, True)

    def get_analysis_cost(self, analysis_type: str) -> int:
        """Get cost for analysis type, allowing for tenant-specific pricing"""
        if self.analysis_costs and analysis_type in self.analysis_costs:
            return self.analysis_costs[analysis_type]
            
        from app.tasks.base.definitions import AnalysisDefinitions
        return AnalysisDefinitions.get_cost(analysis_type)

    def get_enabled_analyses(self) -> Dict[str, bool]:
        """Get dictionary of all analyses and their enabled status"""
        if self.analysis_toggles is None:
            self.analysis_toggles = get_default_analysis_toggles()
            
        return {
            analysis_type: self.is_analysis_enabled(analysis_type)
            for analysis_type in get_default_analysis_toggles().keys()
        }

    def enable_all_analyses(self) -> None:
        """Enable all analyses"""
        self.recurring_analyses_enabled = True
        self.analysis_toggles = get_default_analysis_toggles()
        log_with_route(logging.INFO, f"Enable all - New toggles: {self.analysis_toggles}")
        db.session.add(self)  # Explicitly add changes
    
    # Add this method to your Tenants class 

    def get_customer_sla(self, orguuid):
        """
        Get SLA information for a specific customer organization.
        
        Args:
            orguuid: The UUID of the organization
            
        Returns:
            dict: SLA information including type, response time, etc.
        """
        # Default SLA information
        sla_info = {
            "type": "Standard",
            "response_time": "24 hours",
            "support_hours": "Business hours",
            "priority_levels": ["Low", "Medium", "High", "Critical"]
        }
        
        # Try to find organization-specific SLA in metadata
        # Instead of using reference_id, look for org_uuid in the metalogos JSON field
        org_metadata = TenantMetadata.query.filter_by(
            tenantuuid=self.tenantuuid,
            metalogos_type='org_sla'
        ).all()
        
        # Check each metadata entry to find the one for this organization
        for metadata in org_metadata:
            if metadata.metalogos and isinstance(metadata.metalogos, dict):
                # Check if this metadata entry refers to our organization
                if metadata.metalogos.get('org_uuid') == str(orguuid):
                    # Found the right metadata, update SLA info
                    sla_data = metadata.metalogos.get('sla_data', {})
                    sla_info.update(sla_data)
                    break
        
        return sla_info

    def disable_all_analyses(self) -> None:
        """Disable all analyses"""
        self.recurring_analyses_enabled = False
        if self.analysis_toggles is None:
            self.analysis_toggles = get_default_analysis_toggles()
        for key in self.analysis_toggles:
            self.analysis_toggles[key] = False
        log_with_route(logging.INFO, f"Disable all - New toggles: {self.analysis_toggles}")
        db.session.add(self)  # Explicitly add changes

    def set_analysis_enabled(self, analysis_type: str, enabled: bool) -> None:
        """Enable/disable specific analysis type"""
        if self.analysis_toggles is None:
            self.analysis_toggles = get_default_analysis_toggles()
        
        if analysis_type in self.analysis_toggles:
            log_with_route(logging.INFO, f"Before update - {analysis_type}: {self.analysis_toggles.get(analysis_type)}")
            self.analysis_toggles[analysis_type] = enabled
            log_with_route(logging.INFO, f"After update - {analysis_type}: {self.analysis_toggles.get(analysis_type)}")
            db.session.add(self)  # Just add to session, let caller handle commit
        else:
            log_with_route(logging.ERROR, f"Invalid analysis type: {analysis_type}")
            raise ValueError(f"Invalid analysis type: {analysis_type}")

    def get_analysis_groups(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get analyses grouped by type for UI display"""
        enabled_analyses = self.get_enabled_analyses()

        # Import here to avoid circular imports
        from app.tasks.base.definitions import AnalysisDefinitions

        def get_analysis_info(analysis_type: str, name: str) -> Dict[str, Any]:
            """Helper to get analysis info with description from definitions"""
            config = AnalysisDefinitions.get_config(analysis_type)
            return {
                'type': analysis_type,
                'name': name,
                'enabled': enabled_analyses[analysis_type],
                'description': config.get('description', '')
            }

        return {
            'Event Logs': [
                get_analysis_info('journalFiltered', 'Journal Logs'),
                get_analysis_info('authFiltered', 'Authentication Logs'),
                get_analysis_info('eventsFiltered-Application', 'Application Events'),
                get_analysis_info('eventsFiltered-Security', 'Security Events'),
                get_analysis_info('eventsFiltered-System', 'System Events'),
                get_analysis_info('syslogFiltered', 'System Logs'),
                get_analysis_info('kernFiltered', 'Kernel Logs'),
            ],
            'System Information': [
                get_analysis_info('msinfo-InstalledPrograms', 'Installed Programs'),
                get_analysis_info('msinfo-NetworkConfig', 'Network Configuration'),
                get_analysis_info('msinfo-StorageInfo', 'Storage Information'),
                get_analysis_info('msinfo-SystemHardwareConfig', 'Hardware Configuration'),
                get_analysis_info('msinfo-SystemSoftwareConfig', 'Software Configuration'),
            ],
            'Specific Analyses': [
                get_analysis_info('windrivers', 'Driver Analysis'),
                get_analysis_info('msinfo-RecentAppCrashes', 'Application Crashes'),
            ],
            'Group Analyses': [
                get_analysis_info('group-health-analysis', 'Group Health Analysis'),
            ],
            'Organization Analyses': [
                get_analysis_info('organization-health-analysis', 'Organization Health Analysis'),
            ],
            'macOS Analyses': [
                get_analysis_info('macos-hardware-eol-analysis', 'macOS Hardware End-of-Life Analysis'),
                get_analysis_info('macos-os-version-analysis', 'macOS Version Analysis'),
                get_analysis_info('macos-log-health-analysis', 'macOS Log Health Analysis'),
            ],
            'Security Audits': [
                get_analysis_info('lynis-audit', 'Lynis Security Audit'),
            ],
            'Tenant Analyses': [
                get_analysis_info('tenant-ai-recommendations', 'AI Tool Recommendations'),
                get_analysis_info('tenant-ai-suggestions', 'Strategic Analysis Report'),
            ]
        }

    def __repr__(self):
        return f'<Tenant {self.tenantname}>'