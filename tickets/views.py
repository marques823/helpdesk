from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import Http404
from django.contrib.auth import logout
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.db import connection, models
import logging
from .models import Ticket, Comentario, Empresa, Funcionario, HistoricoTicket
from .forms import TicketForm, ComentarioForm, EmpresaForm, FuncionarioForm, UserForm, AtribuirTicketForm
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
import json

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
    try:
        # Verifica se o usuário tem funcionários associados
        funcionarios = request.user.funcionarios.all()
        if not funcionarios.exists():
            messages.error(request, "Usuário não possui funcionários associados. Por favor, contate o administrador.")
            return redirect('login')
        
        # Pega todas as empresas do funcionário
        empresas_ids = [empresa.id for funcionario in funcionarios for empresa in funcionario.empresas.all()]
        
        # Filtra tickets baseado no tipo de usuário
        if request.user.is_superuser:
            # Superusuário vê todos os tickets
            tickets = Ticket.objects.all().order_by('-criado_em')
        else:
            # Para outros usuários, filtra por empresa e tipo
            tickets = Ticket.objects.filter(empresa_id__in=empresas_ids).order_by('-criado_em')
            
            # Se for cliente, filtra tickets criados por ele ou atribuídos a ele
            if any(funcionario.is_cliente() for funcionario in funcionarios):
                tickets = tickets.filter(
                    models.Q(criado_por=request.user) |
                    models.Q(atribuido_a__in=funcionarios)
                )
        
        # Filtra tickets que o usuário tem permissão para ver
        tickets_permitidos = []
        for ticket in tickets:
            for funcionario in funcionarios:
                if funcionario.pode_ver_ticket(ticket):
                    tickets_permitidos.append(ticket)
                    break
        
        # Calcula estatísticas
        total_tickets = len(tickets_permitidos)
        tickets_abertos = len([t for t in tickets_permitidos if t.status == 'aberto'])
        tickets_fechados = len([t for t in tickets_permitidos if t.status == 'fechado'])
        
        # Paginação
        paginator = Paginator(tickets_permitidos, 10)
        page = request.GET.get('page')
        try:
            tickets = paginator.page(page)
        except PageNotAnInteger:
            tickets = paginator.page(1)
        except EmptyPage:
            tickets = paginator.page(paginator.num_pages)
        
        context = {
            'tickets': tickets,
            'total_tickets': total_tickets,
            'tickets_abertos': tickets_abertos,
            'tickets_fechados': tickets_fechados,
        }
        
        return render(request, 'tickets/dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Erro no dashboard: {str(e)}")
        messages.error(request, "Ocorreu um erro ao carregar o dashboard. Por favor, tente novamente.")
        return redirect('login')

def registrar_historico(ticket, tipo_alteracao, usuario, descricao, dados_anteriores=None, dados_novos=None):
    """Função auxiliar para registrar alterações no histórico do ticket"""
    try:
        HistoricoTicket.objects.create(
            ticket=ticket,
            tipo_alteracao=tipo_alteracao,
            usuario=usuario,
            descricao=descricao,
            dados_anteriores=dados_anteriores,
            dados_novos=dados_novos
        )
    except Exception as e:
        logger.error(f"Erro ao registrar histórico: {str(e)}")

@login_required
def historico_ticket(request, ticket_id):
    try:
        ticket = get_object_or_404(Ticket, id=ticket_id)
        
        # Verificar permissões
        if not request.user.is_superuser:
            funcionario = request.user.funcionarios.first()
            if not funcionario or not funcionario.pode_ver_ticket(ticket):
                messages.error(request, 'Você não tem permissão para ver o histórico deste ticket.')
                return redirect('tickets:dashboard')
        
        return render(request, 'tickets/historico_ticket.html', {
            'ticket': ticket
        })
    except Exception as e:
        logger.error(f"Erro ao carregar histórico do ticket: {str(e)}")
        messages.error(request, 'Erro ao carregar histórico do ticket.')
        return redirect('tickets:dashboard')

@login_required
def criar_ticket(request):
    try:
        if request.method == 'POST':
            form = TicketForm(request.POST, user=request.user)
            if form.is_valid():
                # Verifica se o usuário tem permissão para criar tickets para a empresa selecionada
                funcionario = request.user.funcionarios.first()
                if not funcionario:
                    messages.error(request, 'Usuário não possui funcionário associado.')
                    return redirect('tickets:dashboard')
                
                empresa = form.cleaned_data.get('empresa')
                if not empresa:
                    messages.error(request, 'Empresa não selecionada.')
                    return redirect('tickets:dashboard')
                
                if not funcionario.tem_acesso_empresa(empresa):
                    messages.error(request, 'Você não tem acesso a esta empresa.')
                    return redirect('tickets:dashboard')
                
                if not funcionario.pode_criar_ticket(empresa):
                    messages.error(request, 'Você não tem permissão para criar tickets para esta empresa.')
                    return redirect('tickets:dashboard')
                
                ticket = form.save(commit=False)
                ticket.criado_por = request.user
                ticket.save()
                
                # Registra a criação do ticket no histórico
                registrar_historico(
                    ticket=ticket,
                    tipo_alteracao='criacao',
                    usuario=request.user,
                    descricao=f'Ticket criado por {request.user.get_full_name()}',
                    dados_novos={
                        'titulo': ticket.titulo,
                        'descricao': ticket.descricao,
                        'status': ticket.status,
                        'prioridade': ticket.prioridade,
                        'empresa': ticket.empresa.nome,
                        'atribuido_a': ticket.atribuido_a.usuario.username if ticket.atribuido_a else None
                    }
                )
                
                messages.success(request, 'Ticket criado com sucesso!')
                return redirect('tickets:detalhe_ticket', ticket_id=ticket.id)
        else:
            form = TicketForm(user=request.user)
        
        return render(request, 'tickets/criar_ticket.html', {
            'form': form
        })
    except Exception as e:
        logger.error(f"Erro ao criar ticket: {str(e)}")
        messages.error(request, 'Erro ao criar ticket.')
        return redirect('tickets:dashboard')

@login_required
def detalhe_ticket(request, ticket_id):
    try:
        ticket = get_object_or_404(Ticket, id=ticket_id)
        
        # Verificar permissões
        if not request.user.is_superuser:
            funcionario = request.user.funcionarios.first()
            if not funcionario or not funcionario.pode_ver_ticket(ticket):
                messages.error(request, 'Você não tem permissão para ver este ticket.')
                return redirect('tickets:dashboard')
        
        if request.method == 'POST':
            form = ComentarioForm(request.POST)
            if form.is_valid():
                comentario = form.save(commit=False)
                comentario.ticket = ticket
                comentario.autor = request.user
                comentario.save()
                
                # Registra o comentário no histórico
                registrar_historico(
                    ticket=ticket,
                    tipo_alteracao='comentario',
                    usuario=request.user,
                    descricao=f'Comentário adicionado por {request.user.get_full_name()}',
                    dados_novos={
                        'comentario': comentario.texto
                    }
                )
                
                messages.success(request, 'Comentário adicionado com sucesso!')
                return redirect('tickets:detalhe_ticket', ticket_id=ticket.id)
        else:
            form = ComentarioForm()
        
        context = {
            'ticket': ticket,
            'form': form,
            'user': request.user
        }
        
        return render(request, 'tickets/detalhe_ticket.html', context)
    except Exception as e:
        logger.error(f"Erro ao carregar detalhes do ticket: {str(e)}")
        messages.error(request, 'Erro ao carregar detalhes do ticket.')
        return redirect('tickets:dashboard')

@login_required
def editar_ticket(request, ticket_id):
    try:
        ticket = get_object_or_404(Ticket, id=ticket_id)
        
        # Verificar permissões
        if not request.user.is_superuser:
            funcionario = request.user.funcionarios.first()
            if not funcionario or not funcionario.pode_editar_ticket(ticket):
                messages.error(request, 'Você não tem permissão para editar este ticket.')
                return redirect('tickets:dashboard')
        
        if request.method == 'POST':
            form = TicketForm(request.POST, instance=ticket)
            if form.is_valid():
                # Salva os dados anteriores para o histórico
                dados_anteriores = {
                    'titulo': ticket.titulo,
                    'descricao': ticket.descricao,
                    'status': ticket.status,
                    'prioridade': ticket.prioridade,
                    'empresa': ticket.empresa.nome,
                    'atribuido_a': ticket.atribuido_a.usuario.username if ticket.atribuido_a else None
                }
                
                form.save()
                
                # Registra a edição no histórico
                registrar_historico(
                    ticket=ticket,
                    tipo_alteracao='edicao',
                    usuario=request.user,
                    descricao=f'Ticket editado por {request.user.get_full_name()}',
                    dados_anteriores=dados_anteriores,
                    dados_novos={
                        'titulo': ticket.titulo,
                        'descricao': ticket.descricao,
                        'status': ticket.status,
                        'prioridade': ticket.prioridade,
                        'empresa': ticket.empresa.nome,
                        'atribuido_a': ticket.atribuido_a.usuario.username if ticket.atribuido_a else None
                    }
                )
                
                messages.success(request, 'Ticket atualizado com sucesso!')
                return redirect('tickets:detalhe_ticket', ticket_id=ticket.id)
        else:
            form = TicketForm(instance=ticket)
        
        return render(request, 'tickets/editar_ticket.html', {
            'form': form,
            'ticket': ticket
        })
    except Exception as e:
        logger.error(f"Erro ao editar ticket: {str(e)}")
        messages.error(request, 'Erro ao editar ticket.')
        return redirect('tickets:dashboard')

@login_required
def lista_empresas(request):
    try:
        # Verifica se o usuário tem funcionários associados
        funcionarios = request.user.funcionarios.all()
        if not funcionarios.exists():
            messages.error(request, "Usuário não possui funcionários associados. Por favor, contate o administrador.")
            return redirect('login')
        
        # Pega todas as empresas do funcionário
        empresas_ids = [empresa.id for funcionario in funcionarios for empresa in funcionario.empresas.all()]
        
        # Filtra empresas baseado no tipo de usuário
        if request.user.is_superuser:
            # Superusuário vê todas as empresas
            empresas = Empresa.objects.all().order_by('nome')
        else:
            # Para outros usuários, filtra apenas as empresas às quais têm acesso
            empresas = Empresa.objects.filter(id__in=empresas_ids).order_by('nome')
        
        return render(request, 'tickets/lista_empresas.html', {'empresas': empresas})
    except Exception as e:
        logger.error(f"Erro ao listar empresas: {str(e)}")
        messages.error(request, 'Erro ao listar empresas.')
        return redirect('tickets:dashboard')

@login_required
def criar_empresa(request):
    try:
        # Verifica se o usuário tem permissão para criar empresas
        if not request.user.is_superuser:
            messages.error(request, "Você não tem permissão para criar empresas.")
            return redirect('tickets:lista_empresas')
        
        if request.method == 'POST':
            form = EmpresaForm(request.POST)
            if form.is_valid():
                empresa = form.save()
                messages.success(request, 'Empresa criada com sucesso!')
                return redirect('tickets:lista_empresas')
        else:
            form = EmpresaForm()
        
        return render(request, 'tickets/criar_empresa.html', {'form': form})
    except Exception as e:
        logger.error(f"Erro ao criar empresa: {str(e)}")
        messages.error(request, 'Erro ao criar empresa.')
        return redirect('tickets:lista_empresas')

@login_required
def editar_empresa(request, pk):
    try:
        empresa = get_object_or_404(Empresa, pk=pk)
        
        # Verifica se o usuário tem acesso à empresa
        if not request.user.is_superuser:
            funcionarios = request.user.funcionarios.all()
            empresas_ids = [empresa.id for funcionario in funcionarios for empresa in funcionario.empresas.all()]
            if empresa.id not in empresas_ids:
                messages.error(request, "Você não tem acesso a esta empresa.")
                return redirect('tickets:lista_empresas')
        
        if request.method == 'POST':
            form = EmpresaForm(request.POST, instance=empresa)
            if form.is_valid():
                form.save()
                messages.success(request, 'Empresa atualizada com sucesso!')
                return redirect('tickets:lista_empresas')
        else:
            form = EmpresaForm(instance=empresa)
        
        return render(request, 'tickets/editar_empresa.html', {'form': form, 'empresa': empresa})
    except Exception as e:
        logger.error(f"Erro ao editar empresa: {str(e)}")
        messages.error(request, 'Erro ao editar empresa.')
        return redirect('tickets:lista_empresas')

@login_required
def lista_funcionarios(request):
    try:
        # Verifica se o usuário tem funcionários associados
        funcionarios = request.user.funcionarios.all()
        if not funcionarios.exists():
            messages.error(request, "Usuário não possui funcionários associados. Por favor, contate o administrador.")
            return redirect('login')
        
        # Pega todas as empresas do funcionário
        empresas_ids = [empresa.id for funcionario in funcionarios for empresa in funcionario.empresas.all()]
        
        # Filtra funcionários baseado no tipo de usuário
        if request.user.is_superuser:
            # Superusuário vê todos os funcionários
            funcionarios = Funcionario.objects.select_related('usuario').all().order_by('usuario__first_name')
        else:
            # Para outros usuários, filtra apenas os funcionários das empresas às quais têm acesso
            funcionarios = Funcionario.objects.filter(
                empresas__id__in=empresas_ids
            ).select_related('usuario').distinct().order_by('usuario__first_name')
        
        return render(request, 'tickets/lista_funcionarios.html', {'funcionarios': funcionarios})
    except Exception as e:
        logger.error(f"Erro ao listar funcionários: {str(e)}")
        messages.error(request, 'Erro ao listar funcionários.')
        return redirect('tickets:dashboard')

@login_required
def criar_funcionario(request):
    try:
        # Verifica se o usuário tem permissão para criar funcionários
        if not request.user.is_superuser:
            messages.error(request, "Você não tem permissão para criar funcionários.")
            return redirect('tickets:lista_funcionarios')
        
        if request.method == 'POST':
            user_form = UserForm(request.POST)
            funcionario_form = FuncionarioForm(request.POST, user=request.user)
            if user_form.is_valid() and funcionario_form.is_valid():
                user = user_form.save()
                funcionario = funcionario_form.save(commit=False)
                funcionario.usuario = user
                funcionario.save()
                messages.success(request, 'Funcionário criado com sucesso!')
                return redirect('tickets:lista_funcionarios')
        else:
            user_form = UserForm()
            funcionario_form = FuncionarioForm(user=request.user)
        
        return render(request, 'tickets/criar_funcionario.html', {
            'user_form': user_form,
            'funcionario_form': funcionario_form
        })
    except Exception as e:
        logger.error(f"Erro ao criar funcionário: {str(e)}")
        messages.error(request, 'Erro ao criar funcionário.')
        return redirect('tickets:lista_funcionarios')

@login_required
def editar_funcionario(request, pk):
    try:
        funcionario = get_object_or_404(Funcionario, pk=pk)
        
        # Verifica se o usuário tem acesso ao funcionário
        if not request.user.is_superuser:
            funcionarios = request.user.funcionarios.all()
            empresas_ids = [empresa.id for funcionario in funcionarios for empresa in funcionario.empresas.all()]
            if not funcionario.empresas.filter(id__in=empresas_ids).exists():
                messages.error(request, "Você não tem acesso a este funcionário.")
                return redirect('tickets:lista_funcionarios')
        
        if request.method == 'POST':
            user_form = UserForm(request.POST, instance=funcionario.usuario)
            funcionario_form = FuncionarioForm(request.POST, instance=funcionario, user=request.user)
            if user_form.is_valid() and funcionario_form.is_valid():
                user_form.save()
                funcionario_form.save()
                messages.success(request, 'Funcionário atualizado com sucesso!')
                return redirect('tickets:lista_funcionarios')
        else:
            user_form = UserForm(instance=funcionario.usuario)
            funcionario_form = FuncionarioForm(instance=funcionario, user=request.user)
        
        return render(request, 'tickets/editar_funcionario.html', {
            'user_form': user_form,
            'funcionario_form': funcionario_form,
            'funcionario': funcionario
        })
    except Exception as e:
        logger.error(f"Erro ao editar funcionário: {str(e)}")
        messages.error(request, 'Erro ao editar funcionário.')
        return redirect('tickets:lista_funcionarios')

@login_required
def atribuir_ticket(request, ticket_id):
    try:
        ticket = get_object_or_404(Ticket, id=ticket_id)
        
        # Verificar permissões
        if not request.user.is_superuser:
            funcionario = request.user.funcionarios.first()
            if not funcionario or not funcionario.pode_atribuir_ticket(ticket):
                messages.error(request, 'Você não tem permissão para atribuir este ticket.')
                return redirect('tickets:dashboard')
        
        if request.method == 'POST':
            form = AtribuirTicketForm(request.POST, instance=ticket)
            if form.is_valid():
                # Salva o funcionário anterior para o histórico
                funcionario_anterior = ticket.atribuido_a
                
                form.save()
                
                # Registra a atribuição no histórico
                registrar_historico(
                    ticket=ticket,
                    tipo_alteracao='atribuicao',
                    usuario=request.user,
                    descricao=f'Ticket atribuído por {request.user.get_full_name()}',
                    dados_anteriores={
                        'atribuido_a': funcionario_anterior.usuario.username if funcionario_anterior else None
                    },
                    dados_novos={
                        'atribuido_a': ticket.atribuido_a.usuario.username if ticket.atribuido_a else None
                    }
                )
                
                messages.success(request, 'Ticket atribuído com sucesso!')
                return redirect('tickets:detalhe_ticket', ticket_id=ticket.id)
        else:
            form = AtribuirTicketForm(instance=ticket)
        
        return render(request, 'tickets/atribuir_ticket.html', {
            'form': form,
            'ticket': ticket
        })
    except Exception as e:
        logger.error(f"Erro ao atribuir ticket: {str(e)}")
        messages.error(request, 'Erro ao atribuir ticket.')
        return redirect('tickets:dashboard')

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
