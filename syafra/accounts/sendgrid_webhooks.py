import base64
import json
import logging
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from sendgrid.helpers.eventwebhook import EventWebhook

from .email_tracking import apply_sendgrid_webhook_event

logger = logging.getLogger("syafra.email")


def _request_body_text(body):
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("Webhook payload is not valid UTF-8.")


def _signature_is_recent(timestamp_value):
    try:
        timestamp_int = int(timestamp_value)
    except (TypeError, ValueError):
        return False
    max_age = max(getattr(settings, "SENDGRID_EVENT_WEBHOOK_MAX_AGE_SECONDS", 300), 1)
    return abs(int(time.time()) - timestamp_int) <= max_age


def _verify_sendgrid_signature(request, payload_bytes):
    public_key = (getattr(settings, "SENDGRID_EVENT_WEBHOOK_PUBLIC_KEY", "") or "").strip()
    require_signature = bool(getattr(settings, "SENDGRID_EVENT_WEBHOOK_REQUIRE_SIGNATURE", False))
    if not public_key:
        if require_signature:
            logger.error("SendGrid webhook rejected because signature verification is required and no public key is configured.")
            return False
        logger.warning("SendGrid webhook signature verification is disabled because no public key is configured.")
        return True

    signature = (request.headers.get("X-Twilio-Email-Event-Webhook-Signature") or "").strip()
    timestamp = (request.headers.get("X-Twilio-Email-Event-Webhook-Timestamp") or "").strip()
    if not signature or not timestamp:
        logger.warning("SendGrid webhook missing signature headers.")
        return False
    if not _signature_is_recent(timestamp):
        logger.warning("SendGrid webhook signature timestamp is stale.")
        return False

    verifier = EventWebhook(public_key=public_key)
    signed_payload = timestamp.encode("utf-8") + payload_bytes
    try:
        verifier.public_key.verify(
            base64.b64decode(signature),
            signed_payload,
            ec.ECDSA(hashes.SHA256()),
        )
        return True
    except (InvalidSignature, ValueError):
        logger.warning("SendGrid webhook signature verification failed.")
        return False


@csrf_exempt
@require_POST
def sendgrid_event_webhook(request):
    payload_bytes = request.body or b""
    try:
        payload_text = _request_body_text(payload_bytes)
    except ValueError as exc:
        logger.warning("Invalid SendGrid webhook payload encoding: %s", exc)
        return HttpResponse(status=400)

    if not _verify_sendgrid_signature(request, payload_bytes):
        return HttpResponse(status=400)

    try:
        events = json.loads(payload_text or "[]")
    except json.JSONDecodeError as exc:
        logger.warning("Invalid SendGrid webhook JSON: %s", exc)
        return HttpResponse(status=400)

    if not isinstance(events, list):
        logger.warning("SendGrid webhook payload must be a list of events.")
        return HttpResponse(status=400)

    processed = 0
    duplicates = 0
    unresolved = 0

    for event in events:
        if not isinstance(event, dict):
            continue
        email_log, webhook_event, created = apply_sendgrid_webhook_event(event)
        if created:
            processed += 1
        else:
            duplicates += 1
        if email_log is None:
            unresolved += 1

    logger.info(
        "SendGrid webhook processed | processed=%s | duplicates=%s | unresolved=%s",
        processed,
        duplicates,
        unresolved,
    )
    return JsonResponse(
        {
            "ok": True,
            "processed": processed,
            "duplicates": duplicates,
            "unresolved": unresolved,
        }
    )
