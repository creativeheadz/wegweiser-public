# Filepath: tools/sendNotification.py
import requests
import json

# Configuration
API_URL = "https://app.wegweiser.tech/messages/script"
API_KEY = "1f9d9e8b7e6a9d6b3c4a2f1e8d9b7e6a9d6b3c4a2f1e8d9b7e6a9d6b3c4a2f1e"
HEADERS = {
    "Content-Type": "application/json",
    "x-api-key": API_KEY
}

# Message Data
message_data = {
    "title": "Test Message",
    "content": "https://lemonparty.org/",
    "tenantuuid": "d7f55679-f0ad-402b-a0bb-dc8f870d1c5d"  # Provided tenant UUID for testing
}

# Send POST request to create a message
response = requests.post(API_URL, headers=HEADERS, data=json.dumps(message_data))

# Check the response
if response.status_code == 201:
    print("Message posted successfully:", response.json())
else:
    print("Failed to post message:", response.json())
