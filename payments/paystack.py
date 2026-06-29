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
    Docs: https://paystack.com/docs/api/transaction/#initialize
    """
    payload = {
        "reference": reference,
        "amount": int(float(amount) * 100),  # Paystack uses kobo
        "email": email,
        "currency": "NGN",
        "channels": ["bank_transfer"],
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


def _get_or_create_customer(email: str, full_name: str) -> str:
    """
    Create a Paystack customer, or fetch existing one if email already exists.
    Returns the customer_code.
    """
    name_parts = full_name.split() if full_name else []
    first_name = name_parts[0] if name_parts else ""
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

    # Try to create customer
    create_resp = requests.post(
        f"{PAYSTACK_BASE_URL}/customer",
        json={"email": email, "first_name": first_name, "last_name": last_name},
        headers=_headers(),
        timeout=15,
    ).json()

    customer_code = create_resp.get("data", {}).get("customer_code")

    # FIX: If customer already exists, Paystack returns an error — fetch them instead
    if not customer_code:
        fetch_resp = requests.get(
            f"{PAYSTACK_BASE_URL}/customer/{email}",
            headers=_headers(),
            timeout=15,
        ).json()
        customer_code = fetch_resp.get("data", {}).get("customer_code")

    if not customer_code:
        raise PaystackError("Failed to create or fetch Paystack customer")

    return customer_code


def _get_or_create_virtual_account(customer_code: str) -> dict:
    """
    Create a dedicated virtual account for a customer.
    If one already exists (Paystack doesn't allow duplicates), fetch it instead.
    Returns the account dict with account_number and bank_name.
    """
    dva_resp = requests.post(
        f"{PAYSTACK_BASE_URL}/dedicated_account",
        json={
            "customer": customer_code,
            "preferred_bank": "wema-bank",
        },
        headers=_headers(),
        timeout=15,
    ).json()

    # FIX: If DVA already exists for this customer, fetch the existing one
    if not dva_resp.get("status"):
        error_msg = dva_resp.get("message", "").lower()
        if "exist" in error_msg or "already" in error_msg:
            fetch_resp = requests.get(
                f"{PAYSTACK_BASE_URL}/dedicated_account?customer={customer_code}",
                headers=_headers(),
                timeout=15,
            ).json()
            accounts = fetch_resp.get("data", [])
            if accounts:
                dva_resp = {"status": True, "data": accounts[0]}
            else:
                raise PaystackError("Customer has a DVA but could not be fetched")
        else:
            raise PaystackError(dva_resp.get("message", "Failed to create virtual account"))

    data = dva_resp.get("data", {})

    # Paystack DVA response structure can vary — handle both formats
    account_number = (
        data.get("account_number")
        or data.get("account_details", {}).get("account_number")
    )
    bank_name = (
        data.get("bank", {}).get("name")
        or data.get("account_details", {}).get("bank_name")
        or data.get("bank_name")
    )

    return {
        "account_number": account_number,
        "bank_name": bank_name,
        "raw": dva_resp,
    }


def create_virtual_account(*, reference: str, amount, email: str, full_name: str):
    """
    Full flow: create/fetch customer → create/fetch dedicated virtual account.
    Returns account_number, bank_name, and reference.
    Docs: https://paystack.com/docs/payments/dedicated-virtual-accounts
    """
    customer_code = _get_or_create_customer(email, full_name)
    account = _get_or_create_virtual_account(customer_code)

    return {
        "account_number": account["account_number"],
        "bank_name": account["bank_name"],
        "reference": reference,
        "raw": account["raw"],
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

    # Python's hmac module uses hmac.new(key, msg, digestmod)
    expected = hmac.new(secret, body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(signature, expected)