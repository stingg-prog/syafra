import logging
from .models import Cart

logger = logging.getLogger(__name__)


def cart_context(request):
    """
    Context processor for cart count.
    
    🚀 OPTIMIZATION FIX #1: Cache cart count in session to avoid DB query on every page.
    """
    cart_count = 0
    
    if request.user.is_authenticated:
        session = getattr(request, 'session', None)
        session_key = f'cart_count_{request.user.id}'

        if session is not None:
            cached_count = session.get(session_key)
        else:
            cached_count = None
        
        if cached_count is not None:
            cart_count = cached_count
        else:
            try:
                cart = Cart.get_for_user(request.user)
                cart_count = cart.items.count()
                if session is not None:
                    session[session_key] = cart_count
            except Exception as e:
                logger.error(f"Error getting cart for user {request.user.id}: {e}")
                cart_count = 0
    
    return {'cart_count': cart_count}
