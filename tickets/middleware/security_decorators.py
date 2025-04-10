from functools import wraps
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from tickets.models import Funcionario, Ticket, Empresa, CategoriaChamado, CampoPersonalizado


def funcionario_required(view_func):
    """
    Decorador que verifica se o usuário está autenticado e tem um perfil
    de funcionário associado.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
            
        try:
            funcionario = Funcionario.objects.get(usuario=request.user)
            request.funcionario = funcionario  # Adiciona o funcionário ao request para facilitar o acesso
            return view_func(request, *args, **kwargs)
        except Funcionario.DoesNotExist:
            messages.error(request, "Seu usuário não tem um perfil de funcionário associado.")
            return HttpResponseRedirect(reverse('logout'))
            
    return _wrapped_view


def admin_empresa_required(view_func):
    """
    Decorador que verifica se o usuário é administrador de empresa.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
            
        try:
            funcionario = Funcionario.objects.get(usuario=request.user)
            if not funcionario.is_admin():
                messages.error(request, "Apenas administradores de empresa podem acessar esta área.")
                return HttpResponseRedirect(reverse('tickets:dashboard'))
                
            request.funcionario = funcionario  # Adiciona o funcionário ao request para facilitar o acesso
            return view_func(request, *args, **kwargs)
        except Funcionario.DoesNotExist:
            messages.error(request, "Seu usuário não tem um perfil de funcionário associado.")
            return HttpResponseRedirect(reverse('logout'))
            
    return _wrapped_view


def suporte_required(view_func):
    """
    Decorador que verifica se o usuário é de suporte ou administrador.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
            
        try:
            funcionario = Funcionario.objects.get(usuario=request.user)
            if not (funcionario.is_admin() or funcionario.is_suporte()):
                messages.error(request, "Apenas equipe de suporte ou administradores podem acessar esta área.")
                return HttpResponseRedirect(reverse('tickets:dashboard'))
                
            request.funcionario = funcionario  # Adiciona o funcionário ao request para facilitar o acesso
            return view_func(request, *args, **kwargs)
        except Funcionario.DoesNotExist:
            messages.error(request, "Seu usuário não tem um perfil de funcionário associado.")
            return HttpResponseRedirect(reverse('logout'))
            
    return _wrapped_view


def ticket_access_required(view_func):
    """
    Decorador que verifica se o usuário tem acesso a um ticket específico.
    Deve ser usado em views que recebem o ticket_id como parâmetro.
    """
    @wraps(view_func)
    def _wrapped_view(request, ticket_id, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, ticket_id, *args, **kwargs)
            
        try:
            ticket = Ticket.objects.get(id=ticket_id)
            funcionario = Funcionario.objects.get(usuario=request.user)
            
            if not funcionario.pode_ver_ticket(ticket):
                messages.error(request, "Você não tem permissão para acessar este ticket.")
                return HttpResponseRedirect(reverse('tickets:dashboard'))
                
            request.funcionario = funcionario  # Adiciona o funcionário ao request para facilitar o acesso
            return view_func(request, ticket_id, *args, **kwargs)
        except Ticket.DoesNotExist:
            messages.error(request, "O ticket solicitado não existe.")
            return HttpResponseRedirect(reverse('tickets:dashboard'))
        except Funcionario.DoesNotExist:
            messages.error(request, "Seu usuário não tem um perfil de funcionário associado.")
            return HttpResponseRedirect(reverse('logout'))
            
    return _wrapped_view


def ticket_edit_permission_required(view_func):
    """
    Decorador que verifica se o usuário tem permissão para editar um ticket.
    Deve ser usado em views que recebem o ticket_id como parâmetro.
    """
    @wraps(view_func)
    def _wrapped_view(request, ticket_id, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, ticket_id, *args, **kwargs)
            
        try:
            ticket = Ticket.objects.get(id=ticket_id)
            funcionario = Funcionario.objects.get(usuario=request.user)
            
            if not funcionario.pode_editar_ticket(ticket):
                messages.error(request, "Você não tem permissão para editar este ticket.")
                return HttpResponseRedirect(reverse('tickets:dashboard'))
                
            request.funcionario = funcionario  # Adiciona o funcionário ao request para facilitar o acesso
            return view_func(request, ticket_id, *args, **kwargs)
        except Ticket.DoesNotExist:
            messages.error(request, "O ticket solicitado não existe.")
            return HttpResponseRedirect(reverse('tickets:dashboard'))
        except Funcionario.DoesNotExist:
            messages.error(request, "Seu usuário não tem um perfil de funcionário associado.")
            return HttpResponseRedirect(reverse('logout'))
            
    return _wrapped_view


def ticket_assign_permission_required(view_func):
    """
    Decorador que verifica se o usuário tem permissão para atribuir um ticket.
    Deve ser usado em views que recebem o ticket_id como parâmetro.
    """
    @wraps(view_func)
    def _wrapped_view(request, ticket_id, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, ticket_id, *args, **kwargs)
            
        try:
            ticket = Ticket.objects.get(id=ticket_id)
            funcionario = Funcionario.objects.get(usuario=request.user)
            
            if not funcionario.pode_atribuir_ticket(ticket):
                messages.error(request, "Você não tem permissão para atribuir este ticket.")
                return HttpResponseRedirect(reverse('tickets:dashboard'))
                
            request.funcionario = funcionario  # Adiciona o funcionário ao request para facilitar o acesso
            return view_func(request, ticket_id, *args, **kwargs)
        except Ticket.DoesNotExist:
            messages.error(request, "O ticket solicitado não existe.")
            return HttpResponseRedirect(reverse('tickets:dashboard'))
        except Funcionario.DoesNotExist:
            messages.error(request, "Seu usuário não tem um perfil de funcionário associado.")
            return HttpResponseRedirect(reverse('logout'))
            
    return _wrapped_view


def categoria_permission_required(view_func):
    """
    Decorador que verifica se o usuário tem permissão para gerenciar categorias.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
            
        try:
            funcionario = Funcionario.objects.get(usuario=request.user)
            
            # Verificar se é admin
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
                
            request.funcionario = funcionario  # Adiciona o funcionário ao request para facilitar o acesso
            return view_func(request, *args, **kwargs)
        except Funcionario.DoesNotExist:
            messages.error(request, "Seu usuário não tem um perfil de funcionário associado.")
            return HttpResponseRedirect(reverse('logout'))
            
    return _wrapped_view


def campo_personalizado_permission_required(view_func):
    """
    Decorador que verifica se o usuário tem permissão para gerenciar campos personalizados.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
            
        try:
            funcionario = Funcionario.objects.get(usuario=request.user)
            
            # Verificar se é admin
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
                
            request.funcionario = funcionario  # Adiciona o funcionário ao request para facilitar o acesso
            return view_func(request, *args, **kwargs)
        except Funcionario.DoesNotExist:
            messages.error(request, "Seu usuário não tem um perfil de funcionário associado.")
            return HttpResponseRedirect(reverse('logout'))
            
    return _wrapped_view


def empresa_access_required(view_func):
    """
    Decorador que verifica se o usuário tem acesso a uma empresa específica.
    Deve ser usado em views que recebem o empresa_id como parâmetro.
    """
    @wraps(view_func)
    def _wrapped_view(request, empresa_id, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, empresa_id, *args, **kwargs)
            
        try:
            empresa = Empresa.objects.get(id=empresa_id)
            funcionario = Funcionario.objects.get(usuario=request.user)
            
            if not funcionario.tem_acesso_empresa(empresa):
                messages.error(request, "Você não tem acesso a esta empresa.")
                return HttpResponseRedirect(reverse('tickets:dashboard'))
                
            request.funcionario = funcionario  # Adiciona o funcionário ao request para facilitar o acesso
            return view_func(request, empresa_id, *args, **kwargs)
        except Empresa.DoesNotExist:
            messages.error(request, "A empresa solicitada não existe.")
            return HttpResponseRedirect(reverse('tickets:dashboard'))
        except Funcionario.DoesNotExist:
            messages.error(request, "Seu usuário não tem um perfil de funcionário associado.")
            return HttpResponseRedirect(reverse('logout'))
            
    return _wrapped_view


def admin_permission_required(view_func):
    """
    Decorador que verifica se o usuário é um administrador (superusuário ou tipo admin).
    Redireciona para o dashboard caso não tenha permissão.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Superusuários sempre têm acesso
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
            
        try:
            # Verifica se o usuário é um funcionário administrador
            funcionario = Funcionario.objects.get(usuario=request.user)
            
            # Verificar se é admin
            if funcionario.is_admin():
                return view_func(request, *args, **kwargs)
            
            # Se não é admin, redireciona com mensagem
            messages.error(request, "Apenas administradores podem acessar esta página.")
            return HttpResponseRedirect(reverse('tickets:dashboard'))
            
        except Funcionario.DoesNotExist:
            messages.error(request, "Seu usuário não tem um perfil de funcionário associado.")
            return HttpResponseRedirect(reverse('tickets:dashboard'))
            
    return _wrapped_view 