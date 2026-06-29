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
    Initialize a Paystack transaction — returns an authorization URL
    OR for bank transfer, returns account details.
    Docs: https://paystack.com/docs/api/transaction/#initialize
    """
    payload = {
        "reference": reference,
        "amount": int(float(amount) * 100),  # Paystack uses kobo
        "email": email,
        "currency": "NGN",
        "channels": ["bank_transfer"],  # only bank transfer, no card
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

    return data


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


def create_virtual_account(*, reference: str, amount, email: str, full_name: str):
    """
    Create a dedicated virtual account for bank transfer payment.
    Docs: https://paystack.com/docs/payments/dedicated-virtual-accounts
    """
    # First create a customer
    customer_resp = requests.post(
        f"{PAYSTACK_BASE_URL}/customer",
        json={"email": email, "first_name": full_name.split()[0] if full_name else "", "last_name": " ".join(full_name.split()[1:]) if full_name else ""},
        headers=_headers(),
        timeout=15,
    ).json()

    customer_code = customer_resp.get("data", {}).get("customer_code")

    if not customer_code:
        raise PaystackError("Failed to create customer")

    # Create dedicated virtual account
    dva_resp = requests.post(
        f"{PAYSTACK_BASE_URL}/dedicated_account",
        json={
            "customer": customer_code,
            "preferred_bank": "wema-bank",
        },
        headers=_headers(),
        timeout=15,
    ).json()

    if not dva_resp.get("status"):
        raise PaystackError(dva_resp.get("message", "Failed to create virtual account"))

    data = dva_resp.get("data", {})
    account = data.get("account_details", {}) or data

    return {
        "account_number": account.get("account_number") or data.get("account_number"),
        "bank_name": account.get("bank_name") or data.get("bank", {}).get("name"),
        "reference": reference,
        "raw": dva_resp,
    }


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