# Filepath: app/utilities/critical_error_monitor.py
"""
Critical Error Monitoring System
Monitors and alerts on critical application errors to prevent business impact.
"""

import logging
import traceback
import time
from typing import Optional, Dict, Any
from flask import request, has_request_context
from flask_mail import Message
from app import mail
from app.utilities.app_logging_helper import log_with_route

# Make webhook dependency optional
try:
    from app.utilities.webhook_sender import send_n8n_notification
    WEBHOOK_AVAILABLE = True
except ImportError:
    WEBHOOK_AVAILABLE = False
    log_with_route(logging.WARNING, "Webhook sender not available - webhook alerts disabled")


class CriticalErrorMonitor:
    """
    Monitors critical errors and sends immediate alerts via email and webhook.
    Prevents loss of business opportunities due to unnoticed errors.
    """

    # Critical endpoints that should trigger immediate alerts
    CRITICAL_ENDPOINTS = [
        '/register',
        '/login',
        '/devices/delete',
        '/payment',
        '/api/devices/register'
    ]

    # Alert email recipient
    ALERT_EMAIL = 'a.trimbitas@oldforge.tech'

    # Rate limiting to prevent alert spam (seconds between same error alerts)
    RATE_LIMIT = 300  # 5 minutes

    def __init__(self):
        self._last_alert_times = {}

    def should_send_alert(self, error_key: str) -> bool:
        """
        Check if enough time has passed since last alert of this type.
        Prevents alert spam while ensuring critical issues are noticed.
        """
        current_time = time.time()
        last_time = self._last_alert_times.get(error_key, 0)

        if current_time - last_time >= self.RATE_LIMIT:
            self._last_alert_times[error_key] = current_time
            return True
        return False

    def is_critical_error(self, endpoint: str, status_code: int, error: Exception) -> bool:
        """Determine if an error is critical enough to alert."""
        # All 500 errors on critical endpoints are critical
        if status_code >= 500 and any(critical in endpoint for critical in self.CRITICAL_ENDPOINTS):
            return True

        # Module errors (like missing dependencies) are always critical
        if isinstance(error, ModuleNotFoundError):
            return True

        # Import errors are critical
        if isinstance(error, ImportError):
            return True

        return False

    def send_email_alert(
        self,
        error_type: str,
        endpoint: str,
        error_message: str,
        traceback_info: str,
        request_info: Dict[str, Any]
    ) -> bool:
        """Send email alert for critical error."""
        try:
            subject = f"🚨 CRITICAL ERROR on Wegweiser - {error_type}"

            body = f"""
CRITICAL ERROR DETECTED ON WEGWEISER

Error Type: {error_type}
Endpoint: {endpoint}
Time: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}

ERROR DETAILS:
{error_message}

REQUEST INFORMATION:
- Method: {request_info.get('method', 'N/A')}
- URL: {request_info.get('url', 'N/A')}
- IP Address: {request_info.get('ip', 'N/A')}
- User Agent: {request_info.get('user_agent', 'N/A')}

TRACEBACK:
{traceback_info}

ACTION REQUIRED:
This error is affecting a critical user-facing endpoint.
Please investigate immediately to prevent loss of business.

---
Wegweiser Error Monitoring System
"""

            msg = Message(
                subject=subject,
                recipients=[self.ALERT_EMAIL],
                body=body,
                sender=("Wegweiser Monitor", "noreply@wegweiser.tech")
            )

            mail.send(msg)
            log_with_route(logging.INFO, f"Critical error alert sent to {self.ALERT_EMAIL}")
            return True

        except Exception as e:
            log_with_route(logging.ERROR, f"Failed to send email alert: {str(e)}")
            return False

    def send_webhook_alert(
        self,
        error_type: str,
        endpoint: str,
        error_message: str,
        request_info: Dict[str, Any]
    ) -> bool:
        """Send webhook alert to N8N (if webhook support is available)."""
        if not WEBHOOK_AVAILABLE:
            log_with_route(logging.DEBUG, "Webhook alerts not available - skipping webhook send")
            return False

        try:
            data = {
                "alert_type": "critical_error",
                "error_type": error_type,
                "endpoint": endpoint,
                "error_message": error_message,
                "timestamp": time.time(),
                "severity": "CRITICAL",
                "request_method": request_info.get('method', 'N/A'),
                "request_url": request_info.get('url', 'N/A'),
                "client_ip": request_info.get('ip', 'N/A'),
                "user_agent": request_info.get('user_agent', 'N/A')
            }

            result = send_n8n_notification(
                message=f"🚨 CRITICAL: {error_type} on {endpoint}",
                data=data
            )

            return result.get('success', False)

        except Exception as e:
            log_with_route(logging.ERROR, f"Failed to send webhook alert: {str(e)}")
            return False

    def handle_error(
        self,
        error: Exception,
        endpoint: Optional[str] = None,
        status_code: int = 500
    ):
        """
        Main error handling method.
        Call this from Flask error handlers.
        """
        # Get request information if in request context
        request_info = {}
        if has_request_context():
            endpoint = endpoint or request.endpoint or request.path
            request_info = {
                'method': request.method,
                'url': request.url,
                'ip': request.headers.get('X-Real-Ip', request.remote_addr),
                'user_agent': request.headers.get('User-Agent', 'Unknown')
            }
        else:
            endpoint = endpoint or "No endpoint (outside request context)"

        # Check if this is a critical error
        if not self.is_critical_error(endpoint, status_code, error):
            return

        # Generate error details
        error_type = type(error).__name__
        error_message = str(error)
        traceback_info = ''.join(traceback.format_exception(type(error), error, error.__traceback__))

        # Create unique error key for rate limiting
        error_key = f"{endpoint}:{error_type}"

        # Check rate limiting
        if not self.should_send_alert(error_key):
            log_with_route(
                logging.DEBUG,
                f"Skipping alert for {error_key} due to rate limiting"
            )
            return

        # Log the critical error
        log_with_route(
            logging.CRITICAL,
            f"CRITICAL ERROR on {endpoint}: {error_type} - {error_message}"
        )

        # Send alerts (both email and webhook)
        email_sent = self.send_email_alert(
            error_type=error_type,
            endpoint=endpoint,
            error_message=error_message,
            traceback_info=traceback_info,
            request_info=request_info
        )

        webhook_sent = self.send_webhook_alert(
            error_type=error_type,
            endpoint=endpoint,
            error_message=error_message,
            request_info=request_info
        )

        if email_sent or webhook_sent:
            log_with_route(
                logging.INFO,
                f"Critical error alerts sent (Email: {email_sent}, Webhook: {webhook_sent})"
            )


# Global monitor instance
_monitor = None

def get_monitor() -> CriticalErrorMonitor:
    """Get or create the global monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = CriticalErrorMonitor()
    return _monitor


def monitor_error(error: Exception, endpoint: Optional[str] = None, status_code: int = 500):
    """Convenience function to monitor an error."""
    monitor = get_monitor()
    monitor.handle_error(error, endpoint, status_code)
