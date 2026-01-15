# Filepath: app/models/analysis_config.py
"""
Models for tenant-customizable analysis prompts and hierarchical exclusions.

TenantAnalysisPrompt: Tenant-level prompt configuration (criteria, density)
AnalysisExclusion: Entity-level exclusions (tenant/org/group/device)
"""
import uuid
import time
from enum import Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Enum as SQLEnum, UniqueConstraint, CheckConstraint
from . import db


class EntityType(str, Enum):
    """Entity types for polymorphic exclusion association"""
    TENANT = 'tenant'
    ORGANISATION = 'organisation'
    GROUP = 'group'
    DEVICE = 'device'


def get_default_density_config():
    """Default density configuration for analysis output"""
    return {
        'summary_sentences': 3,
        'detail_bullets': 5,
        'performance_bullets': 4,
        'security_bullets': 3,
        'reliability_bullets': 3,
        'monitoring_bullets': 3
    }


class TenantAnalysisPrompt(db.Model):
    """
    Tenant-level analysis prompt configuration.
    
    Stores the customizable criteria portion of analysis prompts.
    Only tenant admins can view/edit these - not exposed to org/group/device users.
    """
    __tablename__ = 'tenant_analysis_prompts'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(
        UUID(as_uuid=True), 
        db.ForeignKey('tenants.tenantuuid', ondelete='CASCADE'), 
        nullable=False
    )
    analysis_type = db.Column(db.String(100), nullable=False)
    
    # Customizable criteria prompt (the "part1" section)
    criteria_prompt = db.Column(db.Text, nullable=True)
    
    # Output density configuration
    density_config = db.Column(
        JSONB, 
        nullable=False, 
        default=get_default_density_config
    )
    
    # Audit fields
    created_at = db.Column(db.BigInteger, nullable=False, default=lambda: int(time.time()))
    updated_at = db.Column(db.BigInteger, nullable=False, default=lambda: int(time.time()))
    updated_by = db.Column(
        UUID(as_uuid=True), 
        db.ForeignKey('accounts.useruuid', ondelete='SET NULL'),
        nullable=True
    )
    
    # Relationships
    tenant = db.relationship('Tenants', backref=db.backref('analysis_prompts', lazy='dynamic'))
    updated_by_user = db.relationship('Accounts', foreign_keys=[updated_by])
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'analysis_type', name='uq_tenant_analysis_prompt'),
    )
    
    def __repr__(self):
        return f'<TenantAnalysisPrompt {self.analysis_type} for tenant {self.tenant_id}>'
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'tenant_id': str(self.tenant_id),
            'analysis_type': self.analysis_type,
            'criteria_prompt': self.criteria_prompt,
            'density_config': self.density_config,
            'updated_at': self.updated_at,
            'updated_by': str(self.updated_by) if self.updated_by else None
        }


class AnalysisExclusion(db.Model):
    """
    Hierarchical exclusions for analysis scoring.
    
    Exclusions cascade and accumulate through the entity hierarchy:
    Tenant → Organisation → Group → Device
    
    Child exclusions ADD to parent exclusions (they don't replace them).
    """
    __tablename__ = 'analysis_exclusions'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Polymorphic entity association
    entity_type = db.Column(
        SQLEnum(EntityType, name='entity_type_enum', create_type=True),
        nullable=False
    )
    entity_id = db.Column(UUID(as_uuid=True), nullable=False)
    
    # Analysis type this exclusion applies to
    analysis_type = db.Column(db.String(100), nullable=False)
    
    # Freeform exclusion text (max 500 chars enforced at API level)
    # "Ignore these when calculating health score"
    exclusions = db.Column(db.Text, nullable=True)
    
    # Freeform priority text (max 500 chars enforced at API level)
    # "Weight these higher when calculating health score"
    priorities = db.Column(db.Text, nullable=True)
    
    # Audit fields
    created_at = db.Column(db.BigInteger, nullable=False, default=lambda: int(time.time()))
    updated_at = db.Column(db.BigInteger, nullable=False, default=lambda: int(time.time()))
    updated_by = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('accounts.useruuid', ondelete='SET NULL'),
        nullable=True
    )
    
    # Relationship to user who updated
    updated_by_user = db.relationship('Accounts', foreign_keys=[updated_by])
    
    __table_args__ = (
        UniqueConstraint('entity_type', 'entity_id', 'analysis_type', name='uq_entity_analysis_exclusion'),
        CheckConstraint(
            "length(exclusions) <= 500 AND length(priorities) <= 500",
            name='ck_exclusion_length'
        ),
    )
    
    def __repr__(self):
        return f'<AnalysisExclusion {self.analysis_type} for {self.entity_type.value}:{self.entity_id}>'
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'entity_type': self.entity_type.value,
            'entity_id': str(self.entity_id),
            'analysis_type': self.analysis_type,
            'exclusions': self.exclusions,
            'priorities': self.priorities,
            'updated_at': self.updated_at,
            'updated_by': str(self.updated_by) if self.updated_by else None
        }
    
    @classmethod
    def get_for_entity(cls, entity_type: EntityType, entity_id: str, analysis_type: str):
        """Get exclusion for a specific entity and analysis type"""
        return cls.query.filter_by(
            entity_type=entity_type,
            entity_id=entity_id,
            analysis_type=analysis_type
        ).first()
    
    @classmethod
    def get_or_create(cls, entity_type: EntityType, entity_id: str, analysis_type: str):
        """Get existing exclusion or create a new one"""
        exclusion = cls.get_for_entity(entity_type, entity_id, analysis_type)
        if not exclusion:
            exclusion = cls(
                entity_type=entity_type,
                entity_id=entity_id,
                analysis_type=analysis_type
            )
            db.session.add(exclusion)
        return exclusion
