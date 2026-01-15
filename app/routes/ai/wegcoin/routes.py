# Filepath: app/routes/ai/wegcoin/routes.py
# Wegcoin-related endpoints

from flask import jsonify, session
import logging

from app.models import Tenants
from app.utilities.app_logging_helper import log_with_route
from app.utilities.app_access_login_required import login_required

from app.routes.ai import ai_bp

@ai_bp.route('/tenant/wegcoin_balance', methods=['GET'])
@login_required
def get_wegcoin_balance():
    """Get the tenant's Wegcoin balance"""
    tenant_uuid = session.get('tenant_uuid')
    if not tenant_uuid:
        return jsonify({"error": "No tenant found in session"}), 400
    
    tenant = Tenants.query.get(tenant_uuid)
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404
    
    return jsonify({
        "balance": tenant.available_wegcoins,
        "total_spent": tenant.calculate_total_spent()
    })
