import logging
import time
from email.utils import parseaddr

import resend
from django.conf import settings

logger = logging.getLogger("syafra.email")


class EmailService:
    _initialized = False
    _resend = None

    @classmethod
    def _ensure_initialized(cls):
        if not cls._initialized:
            api_key = getattr(settings, "RESEND_API_KEY", "").strip()
            if not api_key:
                logger.warning("RESEND_API_KEY is not configured")
            else:
                resend.api_key = api_key
            cls._resend = resend
            cls._initialized = True

    @classmethod
    def send(cls, *, to, subject, text, html=None, from_email=None, tags=None, headers=None):
        cls._ensure_initialized()

        if from_email is None:
            from_email = settings.DEFAULT_FROM_EMAIL

        display_name, email_address = parseaddr(str(from_email or ""))
        if not email_address:
            display_name, email_address = parseaddr(str(settings.DEFAULT_FROM_EMAIL))

        # Defensive: reject any from domain that is not a verified @syafra.com domain
        verified_suffixes = ("@syafra.com",)
        if not email_address.lower().endswith(verified_suffixes):
            logger.critical(
                "BLOCKED unverified from domain | attempted=%s (%s) | falling_back_to=%s",
                from_email, email_address, settings.DEFAULT_FROM_EMAIL,
            )
            display_name, email_address = parseaddr(str(settings.DEFAULT_FROM_EMAIL))

        sender = f"{display_name} <{email_address}>" if display_name else email_address

        logger.info(
            "RESEND API REQUEST | from=%s | to=%s | subject=%s | tags=%s",
            sender, to, subject, tags or [],
        )

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

            return True, elapsed_ms, None, message_id, False
        except cls._resend.exceptions.RateLimitError as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.error(
                "Resend rate limit | recipient=%s | elapsed=%.1fms | error=%s",
                to, elapsed_ms, exc,
            )
            return False, elapsed_ms, str(exc), "", True
        except cls._resend.exceptions.ResendError as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            error_str = str(exc)
            status_code = getattr(exc, "code", 0)
            logger.error(
                "Resend API error | recipient=%s | status=%s | elapsed=%.1fms | error=%s",
                to, status_code, elapsed_ms, error_str,
            )
            return False, elapsed_ms, error_str, "", False
        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.exception(
                "Email send unexpected error | recipient=%s | elapsed=%.1fms",
                to, elapsed_ms,
            )
            return False, elapsed_ms, str(exc), "", True
