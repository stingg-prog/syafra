import logging
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


def global_context(request):
    """
    Global context processor for common template variables.
    """
    from orders.models import WhatsAppSettings

    whatsapp_enquiry_base_url = ''
    
    try:
        settings_obj = WhatsAppSettings.get_settings()
        if settings_obj and settings_obj.enquiry_whatsapp:
            number = settings_obj.enquiry_whatsapp
            default_msg = getattr(settings_obj, 'default_message', 'Hi, I am interested in your products.')
            message = default_msg.strip()
            whatsapp_enquiry_base_url = f"https://wa.me/{number}?{urlencode({'text': message})}"
    except Exception as e:
        logger.debug(f"Could not load WhatsApp settings: {e}")
    
    return {
        'whatsapp_enquiry_base_url': whatsapp_enquiry_base_url,
    }
