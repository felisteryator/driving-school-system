import json
import logging
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import CourseOrder, PaymentAttempt

logger = logging.getLogger(__name__)


def _acknowledge():
    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted."})


@csrf_exempt
@require_POST
def mpesa_callback(request):
    """Process an STK Push callback and acknowledge Daraja's delivery."""
    if len(request.body) > 64 * 1024:
        return JsonResponse({"ResultCode": 1, "ResultDesc": "Payload too large."}, status=413)

    try:
        payload = json.loads(request.body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({"ResultCode": 1, "ResultDesc": "Invalid JSON."}, status=400)

    body = payload.get("Body") if isinstance(payload, dict) else None
    callback = body.get("stkCallback") if isinstance(body, dict) else None
    if not isinstance(callback, dict):
        return JsonResponse({"ResultCode": 1, "ResultDesc": "Invalid callback."}, status=400)

    checkout_request_id = callback.get("CheckoutRequestID")
    try:
        result_code = int(callback["ResultCode"])
    except (KeyError, TypeError, ValueError):
        return JsonResponse({"ResultCode": 1, "ResultDesc": "Invalid callback result."}, status=400)
    if not isinstance(checkout_request_id, str) or not checkout_request_id:
        return JsonResponse({"ResultCode": 1, "ResultDesc": "Missing checkout reference."}, status=400)

    callback_metadata = callback.get("CallbackMetadata", {})
    metadata_items = callback_metadata.get("Item", []) if isinstance(callback_metadata, dict) else []
    metadata = {
        item["Name"]: item.get("Value")
        for item in metadata_items
        if isinstance(item, dict) and isinstance(item.get("Name"), str)
    } if isinstance(metadata_items, list) else {}

    # Daraja retries callbacks. Acknowledge unknown references to avoid endless
    # retries, but never change a payment unless its request ID is matched.
    with transaction.atomic():
        attempt = (
            PaymentAttempt.objects.select_for_update()
            .select_related("order")
            .filter(checkout_request_id=checkout_request_id)
            .first()
        )
        if attempt is None:
            logger.warning("Ignoring M-PESA callback for unknown checkout request %s", checkout_request_id)
            return _acknowledge()

        callback_merchant_id = callback.get("MerchantRequestID")
        if (
            attempt.merchant_request_id
            and callback_merchant_id != attempt.merchant_request_id
        ):
            logger.warning("Ignoring M-PESA callback with mismatched merchant request ID")
            return _acknowledge()

        # Duplicate callbacks and late failures must not undo a successful payment.
        if attempt.status == PaymentAttempt.Status.SUCCEEDED:
            return _acknowledge()

        now = timezone.now()
        attempt.result_code = str(result_code)
        attempt.result_description = str(callback.get("ResultDesc", ""))[:2000]
        attempt.completed_at = now

        if result_code == 0:
            try:
                callback_amount = Decimal(str(metadata["Amount"]))
                receipt_number = str(metadata["MpesaReceiptNumber"])
            except (KeyError, InvalidOperation, TypeError, ValueError):
                callback_amount = None
                receipt_number = ""

            if (
                callback_amount != Decimal(attempt.amount_kes)
                or not receipt_number
                or len(receipt_number) > 30
            ):
                attempt.status = PaymentAttempt.Status.UNKNOWN
                attempt.result_description = (
                    "Daraja reported success, but the callback amount or receipt was missing "
                    "or did not match this payment. Check the sandbox transaction."
                )
                attempt.save(
                    update_fields=["status", "result_code", "result_description", "completed_at", "updated_at"]
                )
                logger.error("M-PESA success callback failed amount/receipt validation for attempt %s", attempt.pk)
                return _acknowledge()

            callback_phone = metadata.get("PhoneNumber")
            if callback_phone is not None and str(callback_phone) != attempt.phone_number:
                attempt.status = PaymentAttempt.Status.UNKNOWN
                attempt.result_description = "Daraja callback phone number did not match this payment."
                attempt.save(
                    update_fields=["status", "result_code", "result_description", "completed_at", "updated_at"]
                )
                logger.error("M-PESA callback phone mismatch for attempt %s", attempt.pk)
                return _acknowledge()

            duplicate_receipt = PaymentAttempt.objects.filter(
                mpesa_receipt_number=receipt_number
            ).exclude(pk=attempt.pk).exists()
            if duplicate_receipt:
                attempt.status = PaymentAttempt.Status.UNKNOWN
                attempt.result_description = "Daraja receipt number is already attached to another payment."
                attempt.save(
                    update_fields=["status", "result_code", "result_description", "completed_at", "updated_at"]
                )
                logger.error("Duplicate M-PESA receipt number received for attempt %s", attempt.pk)
                return _acknowledge()

            attempt.status = PaymentAttempt.Status.SUCCEEDED
            attempt.mpesa_receipt_number = receipt_number
            attempt.save(
                update_fields=[
                    "status", "result_code", "result_description", "mpesa_receipt_number",
                    "completed_at", "updated_at",
                ]
            )
            order = attempt.order
            if order.status != CourseOrder.Status.PAID:
                order.status = CourseOrder.Status.PAID
                order.paid_at = now
                order.save(update_fields=["status", "paid_at", "updated_at"])
        else:
            if result_code == 1032:
                attempt.status = PaymentAttempt.Status.CANCELLED
            elif result_code == 1037:
                attempt.status = PaymentAttempt.Status.TIMED_OUT
            else:
                attempt.status = PaymentAttempt.Status.FAILED
            attempt.save(
                update_fields=["status", "result_code", "result_description", "completed_at", "updated_at"]
            )

    return _acknowledge()
