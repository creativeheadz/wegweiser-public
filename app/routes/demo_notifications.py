# Demo route for testing the enhanced notification system
from flask import Blueprint, render_template, flash, redirect, url_for, request
from app.utilities.notifications import create_notification

demo_bp = Blueprint('demo', __name__, url_prefix='/demo')

@demo_bp.route('/notifications')
def notifications_demo():
    """Demo page for testing all notification features"""
    return render_template('demo/notifications.html')

@demo_bp.route('/test-flash/<category>')
def test_flash(category):
    """Test different flash message categories"""
    messages = {
        'success': 'Operation completed successfully! Your data has been saved.',
        'danger': 'An error occurred while processing your request. Please try again.',
        'warning': 'Warning: This action cannot be undone. Please proceed with caution.',
        'info': 'Information: Your session will expire in 5 minutes.',
        'primary': 'Notice: New features are available in your dashboard.'
    }
    
    message = messages.get(category, 'Test notification message')
    flash(message, category)
    return redirect(url_for('demo.notifications_demo'))

@demo_bp.route('/test-actions')
def test_actions():
    """Test notifications with action buttons"""
    # This would be used in a real scenario where you want to provide actions
    # For now, we'll just flash a message that would normally have actions
    flash('Device "Server-001" has been deleted. This action can be undone within 30 seconds.', 'warning')
    return redirect(url_for('demo.notifications_demo'))

@demo_bp.route('/test-image')
def test_image():
    """Test notification with image"""
    flash('Analysis completed for log file "system.log". View the generated insights.', 'success')
    return redirect(url_for('demo.notifications_demo'))
