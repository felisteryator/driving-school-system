import base64
import json
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from django.conf import settings


class MpesaConfigurationError(Exception):
    """Raised when required sandbox configuration is missing or invalid."""


class MpesaAPIError(Exception):
    """Raised when Daraja cannot accept or process an API request."""

    def __init__(self, message, *, outcome_unknown=False):
        super().__init__(message)
        self.outcome_unknown = outcome_unknown


def _provider_error_message(body):
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ""

    if isinstance(data, dict):
        return str(
            data.get("errorMessage")
            or data.get("ResponseDescription")
            or data.get("CustomerMessage")
            or ""
        )[:300]
    return ""


def _request_json(request):
    try:
        with urlopen(request, timeout=15) as response:
            body = response.read()
    except HTTPError as exc:
        detail = _provider_error_message(exc.read())
        message = f"Daraja returned HTTP {exc.code}."
        if detail:
            message = f"{message} {detail}"
        raise MpesaAPIError(message, outcome_unknown=exc.code >= 500) from exc
    except (URLError, TimeoutError) as exc:
        raise MpesaAPIError(
            "The connection ended before the payment result could be confirmed.",
            outcome_unknown=True,
        ) from exc

    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MpesaAPIError(
            "Daraja returned an unreadable response.", outcome_unknown=True
        ) from exc

    if not isinstance(data, dict):
        raise MpesaAPIError("Daraja returned an unexpected response.")
    return data


def _get_access_token():
    credentials = f"{settings.MPESA_CONSUMER_KEY}:{settings.MPESA_CONSUMER_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("ascii")
    url = (
        f"{settings.MPESA_BASE_URL}/oauth/v1/generate?"
        f"{urlencode({'grant_type': 'client_credentials'})}"
    )
    request = Request(
        url,
        headers={"Authorization": f"Basic {encoded_credentials}"},
        method="GET",
    )
    response = _request_json(request)
    access_token = response.get("access_token")
    if not access_token:
        raise MpesaAPIError("Daraja did not return an access token.")
    return access_token


def initiate_stk_push(payment_attempt):
    required_settings = {
        "MPESA_CONSUMER_KEY": settings.MPESA_CONSUMER_KEY,
        "MPESA_CONSUMER_SECRET": settings.MPESA_CONSUMER_SECRET,
        "MPESA_SHORTCODE": settings.MPESA_SHORTCODE,
        "MPESA_PASSKEY": settings.MPESA_PASSKEY,
        "MPESA_CALLBACK_URL": settings.MPESA_CALLBACK_URL,
    }
    missing = [name for name, value in required_settings.items() if not value]
    if missing:
        raise MpesaConfigurationError(
            "Daraja sandbox configuration is incomplete. Set: " + ", ".join(missing)
        )

    if not settings.MPESA_CALLBACK_URL.startswith("https://"):
        raise MpesaConfigurationError(
            "MPESA_CALLBACK_URL must be a publicly reachable HTTPS URL."
        )

    timestamp = datetime.now(ZoneInfo("Africa/Nairobi")).strftime("%Y%m%d%H%M%S")
    password_source = f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}"
    password = base64.b64encode(password_source.encode("utf-8")).decode("ascii")
    account_reference = payment_attempt.order.reference.hex[:12].upper()

    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": settings.MPESA_TRANSACTION_TYPE,
        "Amount": payment_attempt.amount_kes,
        "PartyA": payment_attempt.phone_number,
        "PartyB": settings.MPESA_SHORTCODE,
        "PhoneNumber": payment_attempt.phone_number,
        "CallBackURL": settings.MPESA_CALLBACK_URL,
        "AccountReference": account_reference,
        "TransactionDesc": "Course fee",
    }

    request = Request(
        f"{settings.MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {_get_access_token()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    return _request_json(request)
