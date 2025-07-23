import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
import os

# Initialize the Firebase app once
cred_path = getattr(settings, "FIREBASE_CRED_PATH", None)

if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

def send_firebase_notification(token, title, body, data=None):
    # Construct the message
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body
        ),
        token=token,
        data=data or {}
    )
    # Send the message via Firebase Admin SDK
    response = messaging.send(message)
    return response  # This returns a message ID string if successful
