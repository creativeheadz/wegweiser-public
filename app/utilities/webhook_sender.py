# Filepath: app/utilities/webhook_sender.py
import requests
import json
import logging
from typing import Dict, Any, Optional, Union
from app.utilities.app_logging_helper import log_with_route


class WebhookSender:
    """Central webhook sending utility for consistent webhook handling across the application."""
    
    # Default webhook configurations
    DEFAULT_WEBHOOKS = {
        'n8n_notifications': 'https://datenfluss.oldforge.tech/webhook/7507cccd-0aee-40ad-9b3c-23aa392ca94b',
        # Add more default webhooks here as needed
    }
    
    def __init__(self, default_timeout: int = 10):
        """
        Initialize the webhook sender.
        
        Args:
            default_timeout: Default timeout for webhook requests in seconds
        """
        self.default_timeout = default_timeout
    
    def send_webhook(
        self,
        webhook_url: str,
        data: Dict[str, Any],
        webhook_type: str = "generic",
        timeout: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        log_success: bool = True,
        log_errors: bool = True
    ) -> Dict[str, Any]:
        """
        Send a webhook with comprehensive error handling and logging.
        
        Args:
            webhook_url: The webhook URL to send to
            data: The data payload to send
            webhook_type: Type of webhook for logging purposes
            timeout: Request timeout (uses default if None)
            headers: Additional headers to send
            log_success: Whether to log successful sends
            log_errors: Whether to log errors
            
        Returns:
            Dict containing success status, response data, and any error information
        """
        if timeout is None:
            timeout = self.default_timeout
            
        # Prepare headers
        request_headers = {"Content-Type": "application/json"}
        if headers:
            request_headers.update(headers)
        
        # Prepare response structure
        result = {
            "success": False,
            "status_code": None,
            "response_data": None,
            "error": None,
            "webhook_type": webhook_type,
            "webhook_url": webhook_url
        }
        
        try:
            # Send the webhook
            response = requests.post(
                webhook_url,
                json=data,
                headers=request_headers,
                timeout=timeout
            )
            
            result["status_code"] = response.status_code
            
            # Check if request was successful
            if response.status_code == 200:
                result["success"] = True
                try:
                    result["response_data"] = response.json()
                except json.JSONDecodeError:
                    result["response_data"] = response.text
                
                if log_success:
                    log_with_route(
                        logging.INFO,
                        f"Successfully sent {webhook_type} webhook to {webhook_url}. "
                        f"Status: {response.status_code}"
                    )
            else:
                result["error"] = f"HTTP Error: {response.status_code}"
                result["response_data"] = response.text
                
                if log_errors:
                    log_with_route(
                        logging.WARNING,
                        f"{webhook_type.title()} webhook failed with status {response.status_code} "
                        f"for URL: {webhook_url}. Response: {response.text}"
                    )
                    
        except requests.exceptions.Timeout:
            result["error"] = f"Timeout after {timeout} seconds"
            if log_errors:
                log_with_route(
                    logging.ERROR,
                    f"{webhook_type.title()} webhook timed out after {timeout}s for URL: {webhook_url}"
                )
                
        except requests.exceptions.ConnectionError:
            result["error"] = "Connection error"
            if log_errors:
                log_with_route(
                    logging.ERROR,
                    f"{webhook_type.title()} webhook connection error for URL: {webhook_url}"
                )
                
        except Exception as e:
            result["error"] = str(e)
            if log_errors:
                log_with_route(
                    logging.ERROR,
                    f"Failed to send {webhook_type} webhook to {webhook_url}: {str(e)}",
                    exc_info=True
                )
        
        return result
    
    def send_n8n_notification(
        self,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a notification to N8N with standardized format.
        
        Args:
            message: The main message to send
            data: Additional data to include in the webhook
            webhook_url: Custom webhook URL (uses default if None)
            
        Returns:
            Dict containing webhook send result
        """
        if webhook_url is None:
            webhook_url = self.DEFAULT_WEBHOOKS['n8n_notifications']
        
        # Prepare the payload
        payload = {"message": message}
        if data:
            payload.update(data)
        
        return self.send_webhook(
            webhook_url=webhook_url,
            data=payload,
            webhook_type="n8n_notification"
        )
    
    def send_tenant_registration_notification(
        self,
        companyname: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a tenant registration notification to N8N.
        
        Args:
            companyname: Name of the company that registered
            additional_data: Any additional data to include
            
        Returns:
            Dict containing webhook send result
        """
        payload = {
            "message": "New tenant registered",
            "companyname": companyname,
            "event_type": "tenant_registration"
        }
        
        if additional_data:
            payload.update(additional_data)
        
        return self.send_n8n_notification(
            message="New tenant registered",
            data=payload
        )


# Convenience functions for easy importing
def send_webhook(webhook_url: str, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Convenience function to send a webhook."""
    sender = WebhookSender()
    return sender.send_webhook(webhook_url, data, **kwargs)


def send_n8n_notification(message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Convenience function to send N8N notification."""
    sender = WebhookSender()
    return sender.send_n8n_notification(message, data)


def send_tenant_registration_notification(companyname: str, **kwargs) -> Dict[str, Any]:
    """Convenience function to send tenant registration notification."""
    sender = WebhookSender()
    return sender.send_tenant_registration_notification(companyname, **kwargs)


# Example usage:
"""
# Basic webhook sending
from app.utilities.webhook_sender import send_webhook

result = send_webhook(
    webhook_url="https://your-webhook-url.com/endpoint",
    data={"message": "Something happened", "details": "Additional info"},
    webhook_type="custom_event"
)

if result["success"]:
    print("Webhook sent successfully!")
else:
    print(f"Webhook failed: {result['error']}")

# N8N notification
from app.utilities.webhook_sender import send_n8n_notification

result = send_n8n_notification(
    message="Device went offline",
    data={"device_id": "12345", "timestamp": time.time()}
)

# Tenant registration (already implemented)
from app.utilities.webhook_sender import send_tenant_registration_notification

result = send_tenant_registration_notification(
    companyname="Acme Corp",
    additional_data={"contact_email": "admin@acme.com"}
)

# Using the class directly for more control
from app.utilities.webhook_sender import WebhookSender

sender = WebhookSender(default_timeout=30)  # Custom timeout
result = sender.send_webhook(
    webhook_url="https://api.example.com/webhook",
    data={"event": "user_login", "user_id": 123},
    webhook_type="authentication",
    headers={"Authorization": "Bearer token123"},
    log_success=False  # Don't log successful sends
)
"""
