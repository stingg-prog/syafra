import logging
import time
from email.utils import parseaddr

from django.conf import settings

logger = logging.getLogger("syafra.email")


class EmailService:
    _initialized = False
    _resend = None

    @classmethod
    def _ensure_initialized(cls):
        if not cls._initialized:
            import resend as _resend_mod

            api_key = getattr(settings, "RESEND_API_KEY", "").strip()
            if not api_key:
                logger.warning("RESEND_API_KEY is not configured")
            else:
                _resend_mod.api_key = api_key
            cls._resend = _resend_mod
            cls._initialized = True

    @classmethod
    def send(cls, *, to, subject, text, html=None, from_email=None, tags=None, headers=None):
        cls._ensure_initialized()

        if from_email is None:
            from_email = settings.DEFAULT_FROM_EMAIL

        display_name, email_address = parseaddr(from_email or "")
        if not email_address:
            email_address = settings.DEFAULT_FROM_EMAIL
        sender = f"{display_name} <{email_address}>" if display_name else email_address

        params = {
            "from": sender,
            "to": [to],
            "subject": subject,
            "text": text,
            "html": html or text.replace("\n", "<br>"),
        }
        if tags:
            params["tags"] = tags
        if headers:
            params["headers"] = headers

        start = time.monotonic()
        try:
            response = cls._resend.Emails.send(params)
            elapsed_ms = (time.monotonic() - start) * 1000

            message_id = ""
            if isinstance(response, dict):
                message_id = response.get("id", "") or ""

            return True, elapsed_ms, None, message_id
        except cls._resend.exceptions.ResendError as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            error_str = str(exc)
            status_code = getattr(exc, "code", 0)
            logger.error(
                "Resend API error | recipient=%s | status=%s | elapsed=%.1fms | error=%s",
                to, status_code, elapsed_ms, error_str,
            )
            return False, elapsed_ms, error_str, ""
        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.exception(
                "Email send unexpected error | recipient=%s | elapsed=%.1fms",
                to, elapsed_ms,
            )
            return False, elapsed_ms, str(exc), ""
