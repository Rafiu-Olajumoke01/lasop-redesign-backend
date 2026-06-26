"""
payments/flutterwave.py

Thin wrapper around Flutterwave's API. Uses requests directly rather than
their SDK so we have full control and no extra dependency.

ENV VARS NEEDED (add to your .env / settings):
    FLUTTERWAVE_SECRET_KEY   -> from your Flutterwave dashboard (test or live)
    FLUTTERWAVE_WEBHOOK_HASH -> a secret string YOU set in Flutterwave dashboard
                                 under Settings > Webhooks > "Secret Hash"
                                 (used to verify webhook requests are genuine)

Until you have real keys, set these to placeholder strings in your .env:
    FLUTTERWAVE_SECRET_KEY=FLWSECK_TEST-placeholder
    FLUTTERWAVE_WEBHOOK_HASH=change-this-to-a-random-string
"""
import requests
from django.conf import settings

FLW_BASE_URL = "https://api.flutterwave.com/v3"


class FlutterwaveError(Exception):
    pass


def _headers():
    return {
        "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
        "Content-Type": "application/json",
    }


def create_virtual_account(*, tx_ref: str, amount, email: str, full_name: str, phone: str = ""):
    """
    Creates a unique, temporary virtual account number for this transaction.
    Docs: https://developer.flutterwave.com/docs/collecting-payments/bank-transfers
    """
    payload = {
        "tx_ref": tx_ref,
        "amount": str(amount),
        "email": email,
        "currency": "NGN",
        "phonenumber": phone,
        "is_permanent": False,  # one-time account, tied to this exact amount/transaction
        "narration": f"LASOP - {full_name}",
    }

    resp = requests.post(
        f"{FLW_BASE_URL}/charges?type=bank_transfer",
        json=payload,
        headers=_headers(),
        timeout=15,
    )
    data = resp.json()

    if data.get("status") != "success":
        raise FlutterwaveError(data.get("message", "Failed to create virtual account"))

    meta = data["data"].get("meta", {}).get("authorization", {})
    return {
        "account_number": meta.get("transfer_account"),
        "bank_name": meta.get("transfer_bank"),
        "flw_ref": data["data"].get("flw_ref"),
        "raw": data,
    }


def verify_transaction(transaction_id: str):
    """
    Server-to-server verification — ALWAYS call this from the webhook handler
    before trusting a webhook payload, rather than trusting the webhook body alone.
    Docs: https://developer.flutterwave.com/docs/verifying-transactions
    """
    resp = requests.get(
        f"{FLW_BASE_URL}/transactions/{transaction_id}/verify",
        headers=_headers(),
        timeout=15,
    )
    return resp.json()


def verify_webhook_signature(request) -> bool:
    """
    Flutterwave sends a 'verif-hash' header that should match the secret hash
    you configured in your dashboard. Reject anything that doesn't match —
    this stops anyone from forging a fake "payment successful" webhook.
    """
    signature = request.headers.get("verif-hash")
    expected = settings.FLUTTERWAVE_WEBHOOK_HASH
    return bool(signature) and signature == expected