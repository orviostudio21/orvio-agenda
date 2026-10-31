import hashlib
from django.core.cache import cache
from django.http import HttpResponse

class AuthThrottleMiddleware:
    """Basic single-process guard. Use a shared rate limiter at the proxy for replicas."""
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        key = None
        if request.method == 'POST' and request.path in ('/login/', '/signup/'):
            address = request.META.get('REMOTE_ADDR', 'unknown')
            key = 'auth-attempts:' + hashlib.sha256(address.encode()).hexdigest()
            if cache.get(key, 0) >= 20:
                return HttpResponse('Muitas tentativas. Aguarde 10 minutos e tente novamente.', status=429, content_type='text/plain; charset=utf-8')
            if not cache.add(key, 1, 600):
                try:
                    cache.incr(key)
                except ValueError:
                    cache.set(key, 1, 600)
        response = self.get_response(request)
        if key and response.status_code == 302:
            cache.delete(key)
        return response
