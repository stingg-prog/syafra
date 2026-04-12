import base64
import binascii
import json
import logging
import time
from functools import lru_cache

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicKey
from cryptography.hazmat.primitives.serialization import load_der_public_key
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .email_tracking import apply_sendgrid_webhook_event

logger = logging.getLogger("syafra.email")

SENDGRID_SIGNATURE_HEADER = "X-Twilio-Email-Event-Webhook-Signature"
SENDGRID_TIMESTAMP_HEADER = "X-Twilio-Email-Event-Webhook-Timestamp"


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


def _clean_base64_value(value):
    return "".join((value or "").split())


@lru_cache(maxsize=4)
def _load_sendgrid_verification_key(verification_key):
    key_bytes = base64.b64decode(_clean_base64_value(verification_key), validate=True)
    public_key = load_der_public_key(key_bytes)
    if not isinstance(public_key, EllipticCurvePublicKey):
        raise ValueError("SendGrid verification key is not an ECDSA public key.")
    return public_key


def verify_sendgrid_signature(request):
    verification_key = (getattr(settings, "SENDGRID_EVENT_WEBHOOK_VERIFICATION_KEY", "") or "").strip()
    require_signature = bool(getattr(settings, "SENDGRID_EVENT_WEBHOOK_REQUIRE_SIGNATURE", True))
    if not verification_key:
        if require_signature:
            logger.error(
                "SendGrid webhook rejected because signature verification is required "
                "and SENDGRID_EVENT_WEBHOOK_VERIFICATION_KEY is not configured."
            )
            return False
        logger.warning("SendGrid webhook signature verification is disabled because no verification key is configured.")
        return True

    signature = (request.headers.get(SENDGRID_SIGNATURE_HEADER) or "").strip()
    timestamp = (request.headers.get(SENDGRID_TIMESTAMP_HEADER) or "").strip()
    if not signature or not timestamp:
        logger.warning("SendGrid webhook missing signature headers.")
        return False
    if not _signature_is_recent(timestamp):
        logger.warning("SendGrid webhook signature timestamp is stale.")
        return False

    signed_payload = timestamp.encode("utf-8") + (request.body or b"")
    try:
        public_key = _load_sendgrid_verification_key(verification_key)
        signature_bytes = base64.b64decode(_clean_base64_value(signature), validate=True)
        public_key.verify(signature_bytes, signed_payload, ec.ECDSA(hashes.SHA256()))
        return True
    except InvalidSignature:
        logger.warning("SendGrid webhook signature verification failed.")
        return False
    except (binascii.Error, TypeError, ValueError, UnsupportedAlgorithm) as exc:
        logger.error("SendGrid webhook signature verification could not be performed: %s", exc)
        return False


@csrf_exempt
@require_POST
def sendgrid_webhook(request):
    payload_bytes = request.body or b""
    try:
        payload_text = _request_body_text(payload_bytes)
    except ValueError as exc:
        logger.warning("Invalid SendGrid webhook payload encoding: %s", exc)
        return HttpResponse(status=400)

    if not verify_sendgrid_signature(request):
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
        logger.info(
            "SendGrid webhook event recorded | event=%s | email_log_id=%s | duplicate=%s",
            (event.get("event") or "unknown"),
            getattr(email_log, "id", None),
            not created,
        )
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


sendgrid_event_webhook = sendgrid_webhook
