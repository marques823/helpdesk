from threading import local

_thread_locals = local()

class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Armazena o usuário atual na thread local
        _thread_locals.user = getattr(request, 'user', None)
        
        # Processa a view
        response = self.get_response(request)
        
        # Limpa a thread local
        if hasattr(_thread_locals, 'user'):
            delattr(_thread_locals, 'user')
            
        return response 