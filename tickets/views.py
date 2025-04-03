from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import Http404
from django.contrib.auth import logout
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.db import connection
import logging
from .models import Ticket, Comentario, Empresa, Funcionario
from .forms import TicketForm, ComentarioForm, EmpresaForm, FuncionarioForm, UserForm
from django.core.exceptions import ObjectDoesNotExist

# Configuração do logger
logger = logging.getLogger(__name__)

def is_admin(user):
    return user.is_superuser

def is_suporte(user):
    return user.is_staff and not user.is_superuser

def home(request):
    return render(request, 'tickets/home.html')

@login_required
def dashboard(request):
    logger.info(f"Iniciando carregamento do dashboard para usuário: {request.user.username}")
    try:
        # 1. Determina o tipo de usuário e suas permissões
        is_admin_user = request.user.is_superuser
        is_support_user = request.user.is_staff and not is_admin_user
        
        logger.info(f"Tipo de usuário - Admin: {is_admin_user}, Suporte: {is_support_user}")

        # 2. Obtém as empresas do usuário (se não for admin)
        empresas = None
        if not is_admin_user:
            try:
                funcionario = Funcionario.objects.select_related('usuario').get(usuario=request.user)
                empresas = funcionario.empresas.all()
                logger.info(f"Empresas do usuário encontradas: {[e.nome for e in empresas]}")
            except Funcionario.DoesNotExist:
                logger.error(f"Funcionário não encontrado para o usuário {request.user.username}")
                messages.error(request, 'Erro: Usuário não possui um funcionário associado. Por favor, contate o administrador.')
                return redirect('home')
            except Exception as e:
                logger.error(f"Erro ao buscar funcionário: {str(e)}", exc_info=True)
                messages.error(request, 'Erro ao buscar informações do funcionário. Por favor, contate o administrador.')
                return redirect('home')

        # 3. Define a query base
        try:
            if is_admin_user:
                logger.info("Buscando todos os tickets (admin)")
                tickets = Ticket.objects.all()
            elif is_support_user:
                logger.info(f"Buscando tickets das empresas {[e.nome for e in empresas]}")
                tickets = Ticket.objects.filter(empresa__in=empresas)
            else:
                logger.info("Buscando tickets do usuário (cliente)")
                tickets = Ticket.objects.filter(
                    empresa__in=empresas,
                    criado_por=request.user
                )

            # 4. Otimiza a query
            tickets = tickets.select_related('criado_por', 'empresa').order_by('-criado_em')
            
            # 5. Calcula estatísticas
            total = tickets.count()
            abertos = tickets.filter(status='aberto').count()
            fechados = tickets.filter(status='fechado').count()
            
            logger.info(f"Estatísticas - Total: {total}, Abertos: {abertos}, Fechados: {fechados}")

            context = {
                'total_tickets': total,
                'tickets_abertos': abertos,
                'tickets_fechados': fechados,
            }

            # 6. Paginação
            paginator = Paginator(tickets, 10)
            page = request.GET.get('page', 1)
            try:
                context['tickets'] = paginator.page(page)
                logger.info(f"Página {page} carregada com sucesso")
            except PageNotAnInteger:
                context['tickets'] = paginator.page(1)
                logger.info("Redirecionado para primeira página")
            except EmptyPage:
                context['tickets'] = paginator.page(paginator.num_pages)
                logger.info("Redirecionado para última página")

            return render(request, 'tickets/dashboard.html', context)

        except Exception as e:
            logger.error(f"Erro ao processar tickets: {str(e)}", exc_info=True)
            messages.error(request, f'Erro ao processar tickets: {str(e)}')
            return redirect('home')

    except Exception as e:
        logger.error(f"Erro geral no dashboard: {str(e)}", exc_info=True)
        messages.error(request, f'Erro ao carregar o dashboard: {str(e)}')
        return redirect('home')

@login_required
def criar_ticket(request):
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.criado_por = request.user
            
            # Se o usuário não for admin, usa a primeira empresa do funcionário
            if not request.user.is_superuser:
                funcionario = Funcionario.objects.get(usuario=request.user)
                empresas = funcionario.empresas.all()
                if empresas.exists():
                    ticket.empresa = empresas.first()
                else:
                    messages.error(request, 'Erro: Usuário não possui empresas atribuídas.')
                    return redirect('dashboard')
            
            ticket.save()
            messages.success(request, 'Ticket criado com sucesso!')
            return redirect('detalhe_ticket', pk=ticket.pk)
    else:
        form = TicketForm()
        # Remove o campo empresa do formulário para clientes
        if not request.user.is_superuser:
            form.fields.pop('empresa', None)
            form.fields.pop('atribuido_para', None)
            
            # Se o usuário tiver apenas uma empresa, preenche automaticamente
            funcionario = Funcionario.objects.get(usuario=request.user)
            empresas = funcionario.empresas.all()
            if empresas.count() == 1:
                form.initial['empresa'] = empresas.first()
    
    return render(request, 'tickets/criar_ticket.html', {'form': form})

@login_required
def detalhe_ticket(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Verifica permissão
    if not request.user.is_superuser:
        try:
            funcionario = Funcionario.objects.get(usuario=request.user)
            if ticket.empresa not in funcionario.empresas.all():
                raise Http404
        except Funcionario.DoesNotExist:
            raise Http404
    
    comentarios = ticket.comentarios.all().order_by('-criado_em')
    
    if request.method == 'POST':
        form = ComentarioForm(request.POST)
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.ticket = ticket
            comentario.autor = request.user
            comentario.save()
            messages.success(request, 'Comentário adicionado com sucesso!')
            return redirect('detalhe_ticket', pk=pk)
    else:
        form = ComentarioForm()
    
    return render(request, 'tickets/detalhe_ticket.html', {
        'ticket': ticket,
        'comentarios': comentarios,
        'form': form
    })

@login_required
def editar_ticket(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Verifica permissão
    if not request.user.is_superuser:
        try:
            funcionario = Funcionario.objects.get(usuario=request.user)
            if ticket.empresa not in funcionario.empresas.all():
                raise Http404
        except Funcionario.DoesNotExist:
            raise Http404
    
    if request.method == 'POST':
        form = TicketForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ticket atualizado com sucesso!')
            return redirect('detalhe_ticket', pk=pk)
    else:
        form = TicketForm(instance=ticket)
    return render(request, 'tickets/editar_ticket.html', {'form': form, 'ticket': ticket})

@login_required
@user_passes_test(is_admin)
def lista_empresas(request):
    empresas = Empresa.objects.all().order_by('nome')
    return render(request, 'tickets/lista_empresas.html', {'empresas': empresas})

@login_required
@user_passes_test(is_admin)
def criar_empresa(request):
    if request.method == 'POST':
        form = EmpresaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Empresa criada com sucesso!')
            return redirect('lista_empresas')
    else:
        form = EmpresaForm()
    return render(request, 'tickets/criar_empresa.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def editar_empresa(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    if request.method == 'POST':
        form = EmpresaForm(request.POST, instance=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Empresa atualizada com sucesso!')
            return redirect('lista_empresas')
    else:
        form = EmpresaForm(instance=empresa)
    return render(request, 'tickets/editar_empresa.html', {'form': form, 'empresa': empresa})

@login_required
@user_passes_test(is_admin)
def lista_funcionarios(request):
    funcionarios = Funcionario.objects.select_related('empresa', 'usuario').all().order_by('empresa__nome', 'usuario__first_name')
    return render(request, 'tickets/lista_funcionarios.html', {'funcionarios': funcionarios})

@login_required
@user_passes_test(is_admin)
def criar_funcionario(request):
    if request.method == 'POST':
        user_form = UserForm(request.POST)
        funcionario_form = FuncionarioForm(request.POST)
        if user_form.is_valid() and funcionario_form.is_valid():
            user = user_form.save()
            funcionario = funcionario_form.save(commit=False)
            funcionario.usuario = user
            funcionario.save()
            messages.success(request, 'Funcionário criado com sucesso!')
            return redirect('lista_funcionarios')
    else:
        user_form = UserForm()
        funcionario_form = FuncionarioForm()
    return render(request, 'tickets/criar_funcionario.html', {
        'user_form': user_form,
        'funcionario_form': funcionario_form
    })

@login_required
@user_passes_test(is_admin)
def editar_funcionario(request, pk):
    funcionario = get_object_or_404(Funcionario, pk=pk)
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=funcionario.usuario)
        funcionario_form = FuncionarioForm(request.POST, instance=funcionario)
        if user_form.is_valid() and funcionario_form.is_valid():
            user_form.save()
            funcionario_form.save()
            messages.success(request, 'Funcionário atualizado com sucesso!')
            return redirect('lista_funcionarios')
    else:
        user_form = UserForm(instance=funcionario.usuario)
        funcionario_form = FuncionarioForm(instance=funcionario)
    return render(request, 'tickets/editar_funcionario.html', {
        'user_form': user_form,
        'funcionario_form': funcionario_form,
        'funcionario': funcionario
    })

@never_cache
def logout_view(request):
    try:
        logger.info(f"Logout iniciado para o usuário: {request.user.username}")
        logout(request)
        logger.info("Logout concluído com sucesso")
        messages.success(request, 'Você foi deslogado com sucesso!')
        return redirect('home')
    except Exception as e:
        logger.error(f"Erro durante o logout: {str(e)}", exc_info=True)
        messages.error(request, f'Erro ao fazer logout: {str(e)}')
        return redirect('home')
