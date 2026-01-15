# Filepath: app/routes/api/analysis_config.py
"""
API routes for analysis configuration management.

Handles:
- Tenant-level prompt customization (criteria, density)
- Hierarchical exclusions (tenant/org/group/device level)
"""

import logging
import time
from flask import Blueprint, request, jsonify, session
from app.utilities.app_access_login_required import login_required
from app.utilities.app_logging_helper import log_with_route
from app.models import (
    db, Devices, Groups, Organisations, Tenants, Accounts,
    TenantAnalysisPrompt, AnalysisExclusion, EntityType
)
from app.tasks.base.definitions import AnalysisDefinitions

analysis_config_bp = Blueprint('analysis_config_bp', __name__, url_prefix='/api/analysis-config')

# Maximum length for exclusion/priority text
MAX_EXCLUSION_LENGTH = 500


def get_current_user():
    """Get current authenticated user"""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return db.session.get(Accounts, user_id)


def get_user_tenant_id():
    """Get tenant ID for current user"""
    user = get_current_user()
    if not user:
        return None
    return user.tenantuuid


def validate_analysis_type(analysis_type: str) -> bool:
    """Validate that analysis type exists"""
    try:
        config = AnalysisDefinitions.get_config(analysis_type)
        return config is not None
    except Exception:
        return False


def validate_entity_access(entity_type: EntityType, entity_id: str) -> bool:
    """Validate user has access to the entity"""
    user_tenant_id = get_user_tenant_id()
    if not user_tenant_id:
        return False
    
    try:
        if entity_type == EntityType.TENANT:
            return str(user_tenant_id) == entity_id
        elif entity_type == EntityType.ORGANISATION:
            org = db.session.get(Organisations, entity_id)
            return org and str(org.tenantuuid) == str(user_tenant_id)
        elif entity_type == EntityType.GROUP:
            group = db.session.get(Groups, entity_id)
            return group and str(group.tenantuuid) == str(user_tenant_id)
        elif entity_type == EntityType.DEVICE:
            device = db.session.get(Devices, entity_id)
            return device and str(device.tenantuuid) == str(user_tenant_id)
    except Exception as e:
        logging.error(f"Entity access validation error: {e}")
    
    return False


# ============================================================================
# Tenant Prompt Configuration (Criteria + Density)
# ============================================================================

@analysis_config_bp.route('/tenant/<tenant_id>/prompts', methods=['GET'])
@login_required
def get_tenant_prompts(tenant_id: str):
    """Get all prompt configurations for a tenant"""
    try:
        if not validate_entity_access(EntityType.TENANT, tenant_id):
            return jsonify({'error': 'Access denied'}), 403
        
        prompts = TenantAnalysisPrompt.query.filter_by(tenant_id=tenant_id).all()
        
        return jsonify({
            'success': True,
            'prompts': [p.to_dict() for p in prompts]
        })
    
    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting tenant prompts: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@analysis_config_bp.route('/tenant/<tenant_id>/prompts/<analysis_type>', methods=['GET'])
@login_required
def get_tenant_prompt(tenant_id: str, analysis_type: str):
    """Get prompt configuration for a specific analysis type"""
    try:
        if not validate_entity_access(EntityType.TENANT, tenant_id):
            return jsonify({'error': 'Access denied'}), 403
        
        if not validate_analysis_type(analysis_type):
            return jsonify({'error': 'Invalid analysis type'}), 400
        
        prompt = TenantAnalysisPrompt.query.filter_by(
            tenant_id=tenant_id,
            analysis_type=analysis_type
        ).first()
        
        if not prompt:
            # Return defaults
            from app.models.analysis_config import get_default_density_config
            return jsonify({
                'success': True,
                'prompt': {
                    'tenant_id': tenant_id,
                    'analysis_type': analysis_type,
                    'criteria_prompt': None,
                    'density_config': get_default_density_config(),
                    'is_default': True
                }
            })
        
        return jsonify({
            'success': True,
            'prompt': prompt.to_dict()
        })
    
    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting tenant prompt: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@analysis_config_bp.route('/tenant/<tenant_id>/prompts/<analysis_type>', methods=['PUT'])
@login_required
def update_tenant_prompt(tenant_id: str, analysis_type: str):
    """Update prompt configuration for a specific analysis type"""
    try:
        if not validate_entity_access(EntityType.TENANT, tenant_id):
            return jsonify({'error': 'Access denied'}), 403
        
        if not validate_analysis_type(analysis_type):
            return jsonify({'error': 'Invalid analysis type'}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        user = get_current_user()
        
        # Get or create prompt config
        prompt = TenantAnalysisPrompt.query.filter_by(
            tenant_id=tenant_id,
            analysis_type=analysis_type
        ).first()
        
        if not prompt:
            prompt = TenantAnalysisPrompt(
                tenant_id=tenant_id,
                analysis_type=analysis_type
            )
            db.session.add(prompt)
        
        # Update fields
        if 'criteria_prompt' in data:
            prompt.criteria_prompt = data['criteria_prompt']
        
        if 'density_config' in data:
            # Validate density config values (must be 1-10)
            density = data['density_config']
            for key, value in density.items():
                if not isinstance(value, int) or value < 1 or value > 10:
                    return jsonify({'error': f'Invalid density value for {key}: must be 1-10'}), 400
            prompt.density_config = density
        
        prompt.updated_at = int(time.time())
        prompt.updated_by = user.useruuid if user else None
        
        db.session.commit()
        
        log_with_route(
            logging.INFO, 
            f"Tenant prompt updated: {analysis_type} for tenant {tenant_id} by user {user.useruuid if user else 'unknown'}"
        )
        
        return jsonify({
            'success': True,
            'prompt': prompt.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Error updating tenant prompt: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# Entity-Level Exclusions (Tenant/Org/Group/Device)
# ============================================================================

@analysis_config_bp.route('/exclusions/<entity_type>/<entity_id>', methods=['GET'])
@login_required
def get_entity_exclusions(entity_type: str, entity_id: str):
    """Get all exclusions for an entity"""
    try:
        # Validate entity type
        try:
            etype = EntityType(entity_type)
        except ValueError:
            return jsonify({'error': 'Invalid entity type'}), 400
        
        if not validate_entity_access(etype, entity_id):
            return jsonify({'error': 'Access denied'}), 403
        
        exclusions = AnalysisExclusion.query.filter_by(
            entity_type=etype,
            entity_id=entity_id
        ).all()
        
        return jsonify({
            'success': True,
            'exclusions': [e.to_dict() for e in exclusions]
        })
    
    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting entity exclusions: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@analysis_config_bp.route('/exclusions/<entity_type>/<entity_id>/<analysis_type>', methods=['GET'])
@login_required
def get_entity_exclusion(entity_type: str, entity_id: str, analysis_type: str):
    """Get exclusion for a specific entity and analysis type"""
    try:
        # Validate entity type
        try:
            etype = EntityType(entity_type)
        except ValueError:
            return jsonify({'error': 'Invalid entity type'}), 400
        
        if not validate_entity_access(etype, entity_id):
            return jsonify({'error': 'Access denied'}), 403
        
        if not validate_analysis_type(analysis_type):
            return jsonify({'error': 'Invalid analysis type'}), 400
        
        exclusion = AnalysisExclusion.get_for_entity(etype, entity_id, analysis_type)
        
        if not exclusion:
            return jsonify({
                'success': True,
                'exclusion': {
                    'entity_type': entity_type,
                    'entity_id': entity_id,
                    'analysis_type': analysis_type,
                    'exclusions': None,
                    'priorities': None,
                    'is_default': True
                }
            })
        
        return jsonify({
            'success': True,
            'exclusion': exclusion.to_dict()
        })
    
    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting entity exclusion: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@analysis_config_bp.route('/exclusions/<entity_type>/<entity_id>/<analysis_type>', methods=['PUT'])
@login_required
def update_entity_exclusion(entity_type: str, entity_id: str, analysis_type: str):
    """Update exclusion for a specific entity and analysis type"""
    try:
        # Validate entity type
        try:
            etype = EntityType(entity_type)
        except ValueError:
            return jsonify({'error': 'Invalid entity type'}), 400
        
        if not validate_entity_access(etype, entity_id):
            return jsonify({'error': 'Access denied'}), 403
        
        if not validate_analysis_type(analysis_type):
            return jsonify({'error': 'Invalid analysis type'}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate length limits
        exclusions_text = data.get('exclusions', '')
        priorities_text = data.get('priorities', '')
        
        if exclusions_text and len(exclusions_text) > MAX_EXCLUSION_LENGTH:
            return jsonify({'error': f'Exclusions text exceeds {MAX_EXCLUSION_LENGTH} character limit'}), 400
        
        if priorities_text and len(priorities_text) > MAX_EXCLUSION_LENGTH:
            return jsonify({'error': f'Priorities text exceeds {MAX_EXCLUSION_LENGTH} character limit'}), 400
        
        user = get_current_user()
        
        # Get or create exclusion
        exclusion = AnalysisExclusion.get_or_create(etype, entity_id, analysis_type)
        
        # Update fields
        exclusion.exclusions = exclusions_text if exclusions_text else None
        exclusion.priorities = priorities_text if priorities_text else None
        exclusion.updated_at = int(time.time())
        exclusion.updated_by = user.useruuid if user else None
        
        db.session.commit()
        
        log_with_route(
            logging.INFO,
            f"Exclusion updated: {analysis_type} for {entity_type}/{entity_id} by user {user.useruuid if user else 'unknown'}"
        )
        
        return jsonify({
            'success': True,
            'exclusion': exclusion.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Error updating entity exclusion: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@analysis_config_bp.route('/exclusions/<entity_type>/<entity_id>/<analysis_type>', methods=['DELETE'])
@login_required
def delete_entity_exclusion(entity_type: str, entity_id: str, analysis_type: str):
    """Delete exclusion for a specific entity and analysis type"""
    try:
        # Validate entity type
        try:
            etype = EntityType(entity_type)
        except ValueError:
            return jsonify({'error': 'Invalid entity type'}), 400
        
        if not validate_entity_access(etype, entity_id):
            return jsonify({'error': 'Access denied'}), 403
        
        exclusion = AnalysisExclusion.get_for_entity(etype, entity_id, analysis_type)
        
        if not exclusion:
            return jsonify({'error': 'Exclusion not found'}), 404
        
        user = get_current_user()
        
        db.session.delete(exclusion)
        db.session.commit()
        
        log_with_route(
            logging.INFO,
            f"Exclusion deleted: {analysis_type} for {entity_type}/{entity_id} by user {user.useruuid if user else 'unknown'}"
        )
        
        return jsonify({'success': True, 'message': 'Exclusion deleted'})
    
    except Exception as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Error deleting entity exclusion: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# Merged Exclusions Preview (for debugging/UI)
# ============================================================================

@analysis_config_bp.route('/exclusions/preview/device/<device_id>/<analysis_type>', methods=['GET'])
@login_required
def preview_merged_exclusions(device_id: str, analysis_type: str):
    """Preview merged exclusions for a device (for debugging/UI)"""
    try:
        if not validate_entity_access(EntityType.DEVICE, device_id):
            return jsonify({'error': 'Access denied'}), 403
        
        from app.tasks.base.exclusions import get_merged_exclusions, build_exclusion_block
        
        merged = get_merged_exclusions(device_id, analysis_type)
        exclusion_block = build_exclusion_block(device_id, analysis_type)
        
        return jsonify({
            'success': True,
            'merged_exclusions': merged['exclusions'],
            'merged_priorities': merged['priorities'],
            'prompt_block': exclusion_block
        })
    
    except Exception as e:
        log_with_route(logging.ERROR, f"Error previewing merged exclusions: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# Analysis Types List (for UI dropdowns)
# ============================================================================

@analysis_config_bp.route('/analysis-types', methods=['GET'])
@login_required
def get_analysis_types():
    """Get list of available analysis types"""
    try:
        from app.tasks.base.definitions import AnalysisDefinitions
        
        configs = AnalysisDefinitions.get_all_configs()
        
        types = []
        for analysis_type, config in configs.items():
            types.append({
                'type': analysis_type,
                'description': config.get('description', ''),
                'cost': config.get('cost', 1)
            })
        
        return jsonify({
            'success': True,
            'analysis_types': types
        })
    
    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting analysis types: {e}")
        return jsonify({'error': 'Internal server error'}), 500
