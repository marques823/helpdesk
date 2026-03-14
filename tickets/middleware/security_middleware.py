import re
from django.http import HttpResponseForbidden, HttpResponseRedirect, JsonResponse
from django.urls import resolve, reverse
from django.contrib import messages
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.views import redirect_to_login
from django.conf import settings
from tickets.models import Funcionario, Ticket, Empresa, APIKey
from django.shortcuts import redirect
import logging


class SecurityMiddleware(MiddlewareMixin):
    """
    Middleware para validação avançada de permissões e segurança da aplicação.
    Realiza validações adicionais além das decorações padrão do Django.
    """
    
    # Rotas que não precisam de validação adicional
    EXEMPT_URLS = [
        r'^/admin/',  # Admin do Django
        r'^/login/',
        r'^/logout/',
        r'^/static/',
        r'^/media/',
        r'^/$',  # Página inicial
        r'^/api/',  # API endpoints (autenticados via JWT ou API Key)
    ]
    
    # Dicionário de rotas que requerem verificações específicas
    # O formato é: 'url_pattern': {'required_permission': 'function_name'}
    PROTECTED_URLS = {
        r'^/tickets/(\d+)/$': {'check_func': 'check_ticket_access'},
        r'^/tickets/editar/(\d+)/$': {'check_func': 'check_ticket_edit_permission'},
        r'^/tickets/atribuir/(\d+)/$': {'check_func': 'check_ticket_assign_permission'},
        r'^/tickets/empresa/': {'check_func': 'check_company_admin_permission'},
        r'^/tickets/categorias/': {'check_func': 'check_category_permission'},
        r'^/tickets/campos/': {'check_func': 'check_custom_field_permission'},
    }
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.async_mode = False
    
    def is_exempt(self, path):
        """Verifica se a URL está isenta de verificação"""
        for exempt_url in self.EXEMPT_URLS:
            if re.match(exempt_url, path):
                return True
        return False
    
    def process_request(self, request):
        """Processa a requisição e verifica permissões"""
        # Se o request estiver marcado como isento pelo LoginExemptMiddleware, ignoramos a verificação
        if hasattr(request, 'exempt') and request.exempt:
            return None
            
        # Ignorar URLs isentas
        if self.is_exempt(request.path):
            return None
            
        # Se o usuário não estiver autenticado, redireciona para login
        if not request.user.is_authenticated:
            return redirect_to_login(request.path)
            
        # Verificar URLs protegidas
        for url_pattern, check_info in self.PROTECTED_URLS.items():
            match = re.match(url_pattern, request.path)
            if match:
                check_func_name = check_info.get('check_func')
                if check_func_name and hasattr(self, check_func_name):
                    check_func = getattr(self, check_func_name)
                    result = check_func(request, *match.groups())
                    if result:
                        return result
        
        return None
    
    def check_ticket_access(self, request, ticket_id):
        """Verifica se o usuário tem permissão para acessar um ticket"""
        # Admins do sistema têm acesso a tudo
        if request.user.is_superuser:
            return None
            
        try:
            ticket = Ticket.objects.get(id=ticket_id)
            funcionario = Funcionario.objects.filter(usuario=request.user).first()
            
            if not funcionario:
                messages.error(request, "Você não tem um perfil de funcionário associado.")
                return HttpResponseRedirect(reverse('logout'))
                
            if not funcionario.pode_ver_ticket(ticket):
                messages.error(request, "Você não tem permissão para acessar este ticket.")
                return HttpResponseRedirect(reverse('tickets:dashboard'))
                
        except Ticket.DoesNotExist:
            # Ticket não existe, retorna 404 padrão do Django
            return None
            
        return None
    
    def check_ticket_edit_permission(self, request, ticket_id):
        """Verifica se o usuário tem permissão para editar um ticket"""
        # Admins do sistema têm acesso a tudo
        if request.user.is_superuser:
            return None
            
        try:
            ticket = Ticket.objects.get(id=ticket_id)
            funcionario = Funcionario.objects.filter(usuario=request.user).first()
            
            if not funcionario:
                messages.error(request, "Você não tem um perfil de funcionário associado.")
                return HttpResponseRedirect(reverse('logout'))
                
            if not funcionario.pode_editar_ticket(ticket):
                messages.error(request, "Você não tem permissão para editar este ticket.")
                return HttpResponseRedirect(reverse('tickets:dashboard'))
                
        except Ticket.DoesNotExist:
            # Ticket não existe, retorna 404 padrão do Django
            return None
            
        return None
    
    def check_ticket_assign_permission(self, request, ticket_id):
        """Verifica se o usuário tem permissão para atribuir um ticket"""
        # Admins do sistema têm acesso a tudo
        if request.user.is_superuser:
            return None
            
        try:
            ticket = Ticket.objects.get(id=ticket_id)
            funcionario = Funcionario.objects.filter(usuario=request.user).first()
            
            if not funcionario:
                messages.error(request, "Você não tem um perfil de funcionário associado.")
                return HttpResponseRedirect(reverse('logout'))
                
            if not funcionario.pode_atribuir_ticket(ticket):
                messages.error(request, "Você não tem permissão para atribuir este ticket.")
                return HttpResponseRedirect(reverse('tickets:dashboard'))
                
        except Ticket.DoesNotExist:
            # Ticket não existe, retorna 404 padrão do Django
            return None
            
        return None
    
    def check_company_admin_permission(self, request):
        """Verifica se o usuário é um administrador de empresa"""
        # Admins do sistema têm acesso a tudo
        if request.user.is_superuser:
            return None
            
        funcionario = Funcionario.objects.filter(usuario=request.user).first()
        
        if not funcionario:
            messages.error(request, "Você não tem um perfil de funcionário associado.")
            return HttpResponseRedirect(reverse('logout'))
            
        if not funcionario.is_admin():
            messages.error(request, "Apenas administradores de empresa podem acessar esta área.")
            return HttpResponseRedirect(reverse('tickets:dashboard'))
            
        return None
    
    def check_category_permission(self, request):
        """Verifica se o usuário tem permissão para gerenciar categorias"""
        # Admins do sistema têm acesso a tudo
        if request.user.is_superuser:
            return None
            
        funcionario = Funcionario.objects.filter(usuario=request.user).first()
        
        if not funcionario:
            messages.error(request, "Você não tem um perfil de funcionário associado.")
            return HttpResponseRedirect(reverse('logout'))
            
        if not funcionario.is_admin():
            messages.error(request, "Apenas administradores de empresa podem gerenciar categorias.")
            return HttpResponseRedirect(reverse('tickets:dashboard'))
            
        # Verificar se a empresa permite criar categorias
        empresa = funcionario.empresas.first()
        if empresa:
            try:
                config = empresa.config
                if not config.pode_criar_categorias:
                    messages.error(request, "Sua empresa não tem permissão para gerenciar categorias.")
                    return HttpResponseRedirect(reverse('tickets:dashboard'))
            except:
                pass
            
        return None
    
    def check_custom_field_permission(self, request):
        """Verifica se o usuário tem permissão para gerenciar campos personalizados"""
        # Admins do sistema têm acesso a tudo
        if request.user.is_superuser:
            return None
            
        funcionario = Funcionario.objects.filter(usuario=request.user).first()
        
        if not funcionario:
            messages.error(request, "Você não tem um perfil de funcionário associado.")
            return HttpResponseRedirect(reverse('logout'))
            
        if not funcionario.is_admin():
            messages.error(request, "Apenas administradores de empresa podem gerenciar campos personalizados.")
            return HttpResponseRedirect(reverse('tickets:dashboard'))
            
        # Verificar se a empresa permite criar campos personalizados
        empresa = funcionario.empresas.first()
        if empresa:
            try:
                config = empresa.config
                if not config.pode_criar_campos_personalizados:
                    messages.error(request, "Sua empresa não tem permissão para gerenciar campos personalizados.")
                    return HttpResponseRedirect(reverse('tickets:dashboard'))
            except:
                pass
            
        return None


class UserFuncionarioMiddleware(MiddlewareMixin):
    """
    Middleware para adicionar o objeto funcionário ao request para todos os usuários autenticados.
    Isso permite acessar funcionario diretamente nos templates via request.funcionario.
    """
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.async_mode = False
    
    def process_request(self, request):
        """
        Adiciona o objeto funcionário ao request se o usuário estiver autenticado
        """
        if request.user.is_authenticated:
            try:
                funcionario = Funcionario.objects.filter(usuario=request.user).first()
                if funcionario:
                    request.funcionario = funcionario
            except:
                # Se houver algum erro, apenas continua sem adicionar o funcionário
                pass
        
        return None 


class LoginExemptMiddleware(MiddlewareMixin):
    """
    Middleware para isentar URLs específicas da necessidade de autenticação.
    Usa a configuração LOGIN_EXEMPT_URLS definida em settings.py.
    """
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.async_mode = False
    
    def process_request(self, request):
        """
        Verifica se o caminho atual está na lista de URLs isentas.
        """
        # Obter a lista de URLs isentas
        exempt_urls = getattr(settings, 'LOGIN_EXEMPT_URLS', [])
        
        # Cria padrões regex para cada URL isenta
        exempt_patterns = [re.compile(r'^/' + url + '/?$') for url in exempt_urls]
        
        # Adiciona sempre a raiz do site como isenta
        exempt_patterns.append(re.compile(r'^/$'))
        
        # Registra o caminho para depuração
        path = request.path_info
        
        # Se o caminho corresponder a um padrão isento, marca request.exempt = True
        for pattern in exempt_patterns:
            if pattern.match(path):
                request.exempt = True
                break
        
        return None 


class APIKeyAuthMiddleware(MiddlewareMixin):
    """
    Middleware para autenticar requisições de API usando chaves API.
    """
    
    # Prefixos de URL que requerem autenticação por API key
    API_URL_PATTERNS = [
        r'^/api/n8n/',  # URLs da API n8n
    ]
    
    def __init__(self, get_response=None):
        self.get_response = get_response
        self.logger = logging.getLogger(__name__)
        self.async_mode = False
    
    def __call__(self, request):
        # Verificar se a URL requer autenticação por API key
        path = request.path
        
        # Verificar se a URL corresponde a algum padrão protegido
        requires_api_key = any(re.match(pattern, path) for pattern in self.API_URL_PATTERNS)
        
        if requires_api_key:
            # Verificar a chave API no cabeçalho
            api_key = request.headers.get('X-API-Key')
            
            if not api_key:
                self.logger.warning(f"Tentativa de acesso à API sem chave: {path}")
                return JsonResponse({'error': 'API key não fornecida'}, status=401)
            
            # Verificar se a chave API existe e está ativa
            try:
                # Verificamos apenas se a chave existe - o campo active será verificado se existir
                key_obj = APIKey.objects.get(key=api_key)
                
                # Verificar se a chave está ativa, se o modelo tiver esse campo
                if hasattr(key_obj, 'active') and not key_obj.active:
                    self.logger.warning(f"Tentativa de acesso à API com chave inativa: {path}")
                    return JsonResponse({'error': 'API key inativa'}, status=401)
                
                # Registrar o uso da chave
                if hasattr(key_obj, 'mark_used') and callable(key_obj.mark_used):
                    key_obj.mark_used()
                else:
                    # Método alternativo se mark_used não existir
                    if hasattr(key_obj, 'last_used'):
                        from django.utils import timezone
                        key_obj.last_used = timezone.now()
                        key_obj.save(update_fields=['last_used'])
                
                # Adicionar informações da chave API ao request para uso nas views
                request.api_key = key_obj
                
            except APIKey.DoesNotExist:
                self.logger.warning(f"Tentativa de acesso à API com chave inválida: {path}")
                return JsonResponse({'error': 'API key inválida ou inativa'}, status=401)
        
        # Continuar com o próximo middleware/view
        return self.get_response(request)
    
    # Mantém o método process_request para compatibilidade, mas ele não será chamado
    def process_request(self, request):
        return None 