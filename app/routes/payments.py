# Filepath: app/routes/payments.py
from flask import Blueprint, jsonify, request, url_for, current_app, render_template, session
import stripe
from app.models import db, Tenants, Accounts
from app.utilities.app_access_login_required import login_required

from app.utilities.guided_tour_manager import get_tour_for_page

payments_bp = Blueprint('payments_bp', __name__)


def init_stripe():
    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']

@payments_bp.route('/create-checkout-session/<int:amount>', methods=['POST'])
@login_required
def create_checkout_session(amount):
    init_stripe()
    try:
        tenant_uuid = session.get('tenant_uuid')
        if not tenant_uuid:
            return jsonify({"error": "Tenant UUID not found in session"}), 400

        tenant = Tenants.query.get(tenant_uuid)
        if not tenant:
            return jsonify({"error": "Tenant not found"}), 404

        price = request.json.get('price')
        if not price:
            return jsonify({"error": "Price not provided"}), 400

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'{amount} Wegweiser Credits',
                    },
                    'unit_amount': int(float(price) * 100),  # Convert to cents
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=url_for('payments_bp.success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('payments_bp.cancel', _external=True),
            client_reference_id=str(tenant_uuid),
            metadata={'wegcoin_amount': amount}
        )
        return jsonify({"id": checkout_session.id})
    except Exception as e:
        return jsonify({"error": str(e)}), 403



@payments_bp.route('/cancel')
def cancel():
    return "Payment cancelled."

@payments_bp.route('/payment')
@login_required
def payment():
    tenant_uuid = session.get('tenant_uuid')
    # Guided tour data for Wegcoins page (use dummy when none exists)
    tour_data = get_tour_for_page('wegcoins', session.get('user_id')) or {
        'is_active': True,
        'page_identifier': 'wegcoins',
        'tour_name': 'Quick Tour',
        'tour_config': {},
        'steps': [
            {'id': 'welcome', 'title': 'Welcome', 'text': 'This is a placeholder tour. Configure it in Administration > Tours.'}
        ],
        'user_progress': {'completed_steps': [], 'is_completed': False}
    }
    return render_template('wegcoins/index.html', tenant_uuid=tenant_uuid, tour_data=tour_data)

from flask import request, jsonify, current_app
import stripe
from app.models import db, Tenants, WegcoinTransaction
from app.utilities.app_logging_helper import log_with_route
import logging

@payments_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, current_app.config['STRIPE_WEBHOOK_SECRET']
        )
    except ValueError as e:
        log_with_route(logging.ERROR, f"Invalid payload: {e}", source_type="Stripe Webhook")
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        log_with_route(logging.ERROR, f"Invalid signature: {e}", source_type="Stripe Webhook")
        return 'Invalid signature', 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        log_with_route(logging.INFO, f"Payment successful for session: {session['id']}", source_type="Stripe Webhook")
        handle_successful_payment(session)
    else:
        log_with_route(logging.INFO, f"Unhandled event type: {event['type']}", source_type="Stripe Webhook")

    return jsonify(success=True)

def handle_successful_payment(session):
    tenant_uuid = session['client_reference_id']
    wegcoin_amount = int(session['metadata']['wegcoin_amount'])

    log_with_route(logging.INFO, f"Processing payment for tenant: {tenant_uuid}, amount: {wegcoin_amount}", source_type="Payment Handler")

    try:
        tenant = Tenants.query.get(tenant_uuid)
        if tenant:
            # Create a new WegcoinTransaction
            transaction = WegcoinTransaction(
                tenantuuid=tenant_uuid,
                amount=wegcoin_amount,
                transaction_type='purchase',
                description=f'Purchase of {wegcoin_amount} Wegcoins'
            )
            db.session.add(transaction)

            # Update tenant's available Wegcoins
            tenant.available_wegcoins += wegcoin_amount

            db.session.commit()
            log_with_route(logging.INFO, f"Successfully updated balance for tenant {tenant_uuid}. New balance: {tenant.available_wegcoins}", source_type="Payment Handler")
        else:
            log_with_route(logging.ERROR, f"Tenant not found: {tenant_uuid}", source_type="Payment Handler")
    except Exception as e:
        log_with_route(logging.ERROR, f"Error processing payment: {str(e)}", source_type="Payment Handler", exc_info=True)
        db.session.rollback()

@payments_bp.route('/success')
@login_required
def success():
    session_id = request.args.get('session_id')
    if not session_id:
        return redirect(url_for('dashboard_bp.dashboard'))

    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        amount = session.amount_total / 100  # Convert cents to dollars
        wegcoin_amount = int(session.metadata.get('wegcoin_amount', 0))

        return render_template('wegcoins/payment_success.html',
                               amount=amount,
                               wegcoin_amount=wegcoin_amount,
                               order_id=session.payment_intent)
    except Exception as e:
        current_app.logger.error(f"Error retrieving session: {str(e)}")
        return redirect(url_for('dashboard_bp.dashboard'))