"""
URL configuration for helpdesk project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from tickets import views

from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited
from django.http import HttpResponseForbidden, JsonResponse

def handler403(request, exception=None):
    if isinstance(exception, Ratelimited):
        if request.path.startswith('/api/'):
            return JsonResponse({'error': 'Muitas solicitações ("Too Many Requests"). Por favor, tente novamente mais tarde.'}, status=403)
        return HttpResponseForbidden('Muitas solicitações ("Too Many Requests"). Por favor, tente novamente mais tarde.')
        
    if request.path.startswith('/api/'):
        return JsonResponse({'error': 'Acesso negado ("Forbidden").'}, status=403)
    return HttpResponseForbidden('Acesso negado ("Forbidden").')

# Aplicar rate limiting à view de login:
# Limite: 5 tentativas por minuto, baseado na chave "ip". block=True retornará 403.
ratelimited_login = ratelimit(key='ip', rate='5/m', block=True)(auth_views.LoginView.as_view(template_name='registration/login.html'))

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('login/', ratelimited_login, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('logout-success/', views.logout_success, name='logout_success'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('tickets/', include('tickets.urls', namespace='tickets')),
    
    # URLs para API
    path('api/', include('tickets.api.urls')),
    
    # URLs para gerenciamento de empresas
    path('empresas/', views.lista_empresas, name='lista_empresas'),
    path('empresas/criar/', views.criar_empresa, name='criar_empresa'),
    path('empresas/<int:pk>/editar/', views.editar_empresa, name='editar_empresa'),
    
    # URLs para gerenciamento de funcionários
    path('funcionarios/', views.lista_funcionarios, name='lista_funcionarios'),
    path('funcionarios/criar/', views.criar_funcionario, name='criar_funcionario'),
    path('funcionarios/<int:pk>/editar/', views.editar_funcionario, name='editar_funcionario'),
]
