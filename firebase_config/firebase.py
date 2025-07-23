import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
import os
import logging

logger = logging.getLogger(__name__)

firebase_app = None

def initialize_firebase():
    global firebase_app
    if not firebase_admin._apps:
        cred_path = getattr(settings, "FIREBASE_CRED_PATH", None)
        if not cred_path:
            logger.error("FIREBASE_CRED_PATH is not set in settings.")
            return None
        if not os.path.exists(cred_path):
            logger.error(f"Firebase credential file not found at: {cred_path}")
            return None
        try:
            cred = credentials.Certificate(cred_path)
            firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase app initialized successfully.")
            return firebase_app
        except Exception as e:
            logger.error(f"Failed to initialize Firebase app: {e}")
            return None
    else:
        firebase_app = firebase_admin.get_app()
        return firebase_app

# Initialize app at import time
initialize_firebase()

def send_firebase_notification(token: str, title: str, body: str, data: dict = None):
    """
    Send a Firebase Cloud Messaging push notification.
    """
    if firebase_app is None:
        error_msg = "Firebase app is not initialized. Cannot send notification."
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

    try:
        message = messaging.Message(
            token=token,
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
        )
        response = messaging.send(message)
        logger.info(f"Notification sent successfully: {response}")
        return {"success": True, "response": response}
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        return {"success": False, "error": str(e)}
