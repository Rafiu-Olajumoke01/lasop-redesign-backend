import hashlib
import hmac
import requests
from django.conf import settings

PAYSTACK_BASE_URL = "https://api.paystack.co"


class PaystackError(Exception):
    pass


def _headers():
    return {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }


def initialize_transaction(*, reference: str, amount, email: str, callback_url: str = ""):
    """
    Initialize a Paystack transaction.
    Returns authorization_url for the student to complete payment.
    Docs: https://paystack.com/docs/api/transaction/#initialize
    """
    payload = {
        "reference": reference,
        "amount": int(float(amount) * 100),  # Paystack uses kobo
        "email": email,
        "currency": "NGN",
    }

    if callback_url:
        payload["callback_url"] = callback_url

    resp = requests.post(
        f"{PAYSTACK_BASE_URL}/transaction/initialize",
        json=payload,
        headers=_headers(),
        timeout=15,
    )
    data = resp.json()

    if not data.get("status"):
        raise PaystackError(data.get("message", "Failed to initialize transaction"))

    return {
        "authorization_url": data["data"]["authorization_url"],
        "access_code": data["data"]["access_code"],
        "reference": data["data"]["reference"],
    }


def verify_transaction(reference: str):
    """
    Verify a transaction by reference.
    Docs: https://paystack.com/docs/api/transaction/#verify
    """
    resp = requests.get(
        f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}",
        headers=_headers(),
        timeout=15,
    )
    return resp.json()


def verify_webhook_signature(request) -> bool:
    """
    Paystack sends an 'x-paystack-signature' header — HMAC SHA512 of the
    raw request body using your secret key.
    """
    signature = request.headers.get("x-paystack-signature")
    if not signature:
        return False

    secret = settings.PAYSTACK_SECRET_KEY.encode("utf-8")
    body = request.body
    expected = hmac.new(secret, body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(signature, expected)