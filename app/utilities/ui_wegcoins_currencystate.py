# Filepath: app/utilities/ui_wegcoins_currencystate.py
from app.models import db, WegcoinTransaction, Tenants
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import func

def get_tenant_wegcoin_balance(tenant_uuid):
    try:
        # Fetch the tenant and available Wegcoins
        tenant = db.session.query(Tenants).filter_by(tenantuuid=tenant_uuid).one()
        
        # Fetch the total Wegcoins spent
        total_spent = db.session.query(func.sum(WegcoinTransaction.amount)).filter(
            WegcoinTransaction.tenantuuid == tenant_uuid,
            WegcoinTransaction.amount < 0  # Only consider negative amounts (spending)
        ).scalar() or 0

        return {
            'tenantname': tenant.tenantname,
            'wegcoin_count': tenant.available_wegcoins,
            'total_wegcoins_spent': abs(total_spent)  # Return as positive value for clarity
        }
    except NoResultFound:
        return {
            'tenantname': None,
            'wegcoin_count': 0,
            'total_wegcoins_spent': 0
        }
    except Exception as e:
        # Log the exception if necessary
        return {
            'tenantname': None,
            'wegcoin_count': 0,
            'total_wegcoins_spent': 0,
            'error': str(e)
        }
