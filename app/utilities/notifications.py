# Filepath: app/utilities/notifications.py
from flask import render_template_string, get_flashed_messages

def get_notification_icon(category):
    """Get the appropriate icon for each notification category"""
    icons = {
        'success': 'fas fa-check-circle',
        'danger': 'fas fa-exclamation-triangle',
        'error': 'fas fa-exclamation-triangle',
        'warning': 'fas fa-exclamation-triangle',
        'info': 'fas fa-info-circle',
        'primary': 'fas fa-info-circle',
        'secondary': 'fas fa-bell',
        'light': 'fas fa-bell',
        'dark': 'fas fa-bell'
    }
    return icons.get(category, 'fas fa-bell')

def get_notification_title(category):
    """Get the appropriate title for each notification category"""
    titles = {
        'success': 'Success',
        'danger': 'Error',
        'error': 'Error',
        'warning': 'Warning',
        'info': 'Information',
        'primary': 'Notice',
        'secondary': 'Notice',
        'light': 'Notice',
        'dark': 'Notice'
    }
    return titles.get(category, 'Notice')

def create_notification(message, category, image_url=None, actions=None):
    icon = get_notification_icon(category)
    title = get_notification_title(category)

    # Process actions if provided
    action_buttons = ""
    if actions:
        action_buttons = '<div class="notification-actions">'
        for action in actions:
            btn_class = action.get('class', 'btn-outline-primary')
            btn_text = action.get('text', 'Action')
            btn_onclick = action.get('onclick', '')
            btn_href = action.get('href', '#')

            if btn_onclick:
                action_buttons += f'<button type="button" class="btn btn-sm {btn_class}" onclick="{btn_onclick}">{btn_text}</button>'
            else:
                action_buttons += f'<a href="{btn_href}" class="btn btn-sm {btn_class}">{btn_text}</a>'
        action_buttons += '</div>'

    html = render_template_string("""
    <div class="alert alert-{{ category }} alert-dismissible fade show notification-enhanced" role="alert" data-auto-dismiss="{{ auto_dismiss }}">
        <div class="notification-header">
            <div class="notification-icon">
                <i class="{{ icon }}"></i>
            </div>
            <div class="notification-content">
                {% if image_url %}
                <img src="{{ image_url }}" alt="Notification Image" class="notification-image">
                {% endif %}
                <div class="notification-text">
                    <strong class="notification-title">{{ title }}</strong>
                    <p class="notification-message">{{ message }}</p>
                    {% if action_buttons %}
                    {{ action_buttons|safe }}
                    {% endif %}
                </div>
            </div>
        </div>
        <button type="button" class="btn-close notification-close" data-bs-dismiss="alert" aria-label="Close"></button>
    </div>
    """,
    message=message,
    category=category,
    image_url=image_url,
    icon=icon,
    title=title,
    action_buttons=action_buttons,
    auto_dismiss='false' if actions else 'true'  # Don't auto-dismiss if there are actions
    )
    return html

def get_all_notifications():
    notifications = []
    flashed_messages = get_flashed_messages(with_categories=True)
    for category, message in flashed_messages:
        notifications.append(create_notification(message, category))
    return notifications