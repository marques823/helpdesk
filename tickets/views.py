from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import Http404, HttpResponse, JsonResponse, HttpResponseRedirect
from django.contrib.auth import logout
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.db import connection, models
from django.db.models import Q, Avg, F, ExpressionWrapper, DurationField
from django.db.models.functions import Concat, Cast, TruncDate
import logging
from .models import Ticket, Comentario, Empresa, Funcionario, HistoricoTicket, CampoPersonalizado, ValorCampoPersonalizado, NotaTecnica, AtribuicaoTicket, PerfilCompartilhamento, CampoPerfilCompartilhamento, CategoriaChamado, EmpresaConfig, PreferenciasNotificacao, CategoriaPermissao, DetalheHistoricoTicket
from .forms import (TicketForm, ComentarioForm, EmpresaForm, FuncionarioForm, UserForm, 
                   AtribuirTicketForm, CampoPersonalizadoForm, ValorCampoPersonalizadoForm, 
                   NotaTecnicaForm, MultiAtribuirTicketForm, PerfilCompartilhamentoForm, 
                   CampoPerfilCompartilhamentoForm, CompartilharTicketForm, CategoriaChamadoForm, 
                   PreferenciasNotificacaoForm)
from django.core.exceptions import ObjectDoesNotExist
import json
from datetime import datetime
from django.urls import reverse
from django.template.loader import render_to_string
import weasyprint
from weasyprint import HTML
from django.conf import settings
import tempfile
import os
from io import BytesIO
from django.db.models import Count
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db.models import Prefetch
from .middleware.security_decorators import admin_permission_required

# Configuração do logger
logger = logging.getLogger(__name__)

def is_admin(user):
    return user.is_superuser

def pode_visualizar_ticket(user, ticket):
    """Verifica se o usuário pode visualizar o ticket"""
    if user.is_superuser:
        return True
    
    try:
        funcionario = user.funcionarios.first()
        if funcionario:
            return funcionario.pode_ver_ticket(ticket)
    except:
        pass
    
    return False

def is_suporte(user):
    return user.is_staff and not user.is_superuser

def home(request):
    has_admin_access = False
    
    if request.user.is_authenticated:
        if request.user.is_superuser:
            has_admin_access = True
        else:
            funcionario = Funcionario.objects.filter(usuario=request.user).first()
            if funcionario and funcionario.is_admin():
                has_admin_access = True
                
    context = {
        'has_admin_access': has_admin_access
    }
    
    return render(request, 'tickets/home.html', context)

@login_required
def dashboard(request):
    """View que renderiza o dashboard de chamados, com melhorias de desempenho e organização."""
    try:
        # Inicializando o contexto
        context = {
            'show_tickets': False,
            'show_status_filters': False
        }
        
        # Verificando o usuário
        if not hasattr(request.user, 'funcionarios'):
            funcionario = Funcionario.objects.filter(usuario=request.user).first()
            if not funcionario:
                logout(request)
                messages.error(request, 'Sua conta não está associada a nenhum funcionário.')
                return redirect('login')
        else:
            funcionario = request.user.funcionarios.first()

        # Verifica permissões administrativas
        has_admin_access = request.user.is_superuser or (funcionario and funcionario.is_admin())
        
        # Obtém os filtros da query string
        termo_pesquisa = request.GET.get('q', '')
        status_filter = request.GET.get('status', '')
        prioridade_filter = request.GET.get('prioridade', '')
        empresa_filter = request.GET.get('empresa', '')
        categoria_filter = request.GET.get('categoria', '')
        order_by = request.GET.get('order_by', '-criado_em')
        
        # Determina se deve mostrar a visualização por categorias ou a lista de tickets
        show_tickets = request.GET.get('show_tickets', '') == 'true'
        show_status_filters = request.GET.get('show_status', '') == 'true'
        selected_category = request.GET.get('selected_category', '')
        selected_status = request.GET.get('selected_status', '')

        # Aplica os filtros de acordo com as permissões do usuário
        if request.user.is_superuser:
            tickets = Ticket.objects.all()
            empresas = Empresa.objects.all()
        else:
            # Obtém as empresas associadas ao funcionário
            empresas = funcionario.empresas.all()
            
            if funcionario.is_admin() or funcionario.is_suporte():
                # Admins e suporte veem tickets das empresas deles
                tickets = Ticket.objects.filter(empresa__in=empresas)
            else:
                # Clientes veem apenas seus próprios tickets
                tickets = Ticket.objects.filter(
                    Q(criado_por=request.user) | 
                    Q(atribuido_a=funcionario) |
                    Q(atribuicoes__funcionario=funcionario)
                ).filter(empresa__in=empresas).distinct()
        
        # Prepara as categorias para a visualização de categorias
        # Se a empresa estiver filtrada, mostra apenas categorias dessa empresa
        if empresa_filter:
            empresa_obj = get_object_or_404(Empresa, id=empresa_filter)
            # Verifica se o funcionário tem permissão para ver categorias específicas
            if request.user.is_superuser or funcionario.is_admin() or funcionario.is_suporte():
                categorias = CategoriaChamado.objects.filter(
                    empresa=empresa_obj,
                    ativo=True
                ).order_by('ordem', 'nome')
            else:
                # Clientes só veem categorias permitidas
                categorias = funcionario.get_categorias_permitidas(empresa=empresa_obj)
        else:
            # Sem filtro de empresa, considera todas as empresas a que o funcionário tem acesso
            if request.user.is_superuser:
                categorias = CategoriaChamado.objects.filter(
                    empresa__in=empresas,
                    ativo=True
                ).order_by('ordem', 'nome')
            else:
                categorias = funcionario.get_categorias_permitidas()
        
        # Prepara a contagem de tickets por categoria
        categoria_counts = {}
        for categoria in categorias:
            categoria_counts[categoria.id] = tickets.filter(categoria=categoria).count()
        
        # Se temos uma categoria selecionada e estamos mostrando status
        if selected_category and show_status_filters:
            # Filtrar tickets apenas pela categoria selecionada
            categoria_obj = get_object_or_404(CategoriaChamado, id=selected_category)
            filtered_tickets = tickets.filter(categoria=categoria_obj)
            
            # Preparar contagens por status
            status_counts = {}
            for status_code, status_name in Ticket.STATUS_CHOICES:
                status_counts[status_code] = filtered_tickets.filter(status=status_code).count()
        else:
            status_counts = None
            categoria_obj = None
        
        # Aplicar filtros de categoria e status se fornecidos
        if selected_category:
            tickets = tickets.filter(categoria_id=selected_category)
        
        if selected_status:
            tickets = tickets.filter(status=selected_status)

        # Aplica os filtros de pesquisa
        if termo_pesquisa:
            # Tenta converter para número para busca por ID
            try:
                ticket_id = int(termo_pesquisa)
                id_query = Q(id=ticket_id)
            except (ValueError, TypeError):
                id_query = Q()
            
            tickets = tickets.filter(
                id_query |
                Q(titulo__icontains=termo_pesquisa) |
                Q(descricao__icontains=termo_pesquisa) |
                Q(empresa__nome__icontains=termo_pesquisa) |
                Q(criado_por__username__icontains=termo_pesquisa) |
                Q(valores_campos_personalizados__valor__icontains=termo_pesquisa)
            ).distinct()
        
        # Aplica filtros de status, prioridade e empresa
        if status_filter:
            tickets = tickets.filter(status=status_filter)
        
        if prioridade_filter:
            tickets = tickets.filter(prioridade=prioridade_filter)
        
        if empresa_filter:
            tickets = tickets.filter(empresa_id=empresa_filter)
            
        if categoria_filter:
            tickets = tickets.filter(categoria_id=categoria_filter)
        
        # Ordenação
        tickets = tickets.order_by(order_by)
        
        # Obter as alterações recentes para exibir no dashboard
        if has_admin_access or funcionario.is_suporte():
            if funcionario.is_admin():
                # Admin vê alterações apenas da sua empresa
                historico_recente = HistoricoTicket.objects.filter(
                    ticket__empresa__in=empresas
                ).select_related('ticket', 'usuario', 'ticket__empresa').order_by('-data_alteracao')[:10]
            else:
                # Suporte vê todas as alterações
                historico_recente = HistoricoTicket.objects.filter(
                    ticket__empresa__in=empresas
                ).select_related('ticket', 'usuario', 'ticket__empresa').order_by('-data_alteracao')[:10]
        else:
            historico_recente = HistoricoTicket.objects.none()
        
        # Paginação - Apenas se estiver mostrando tickets
        if show_tickets:
            paginator = Paginator(tickets, 20)  # 20 tickets por página
            page = request.GET.get('page')
            
            try:
                tickets = paginator.page(page)
            except PageNotAnInteger:
                tickets = paginator.page(1)
            except EmptyPage:
                tickets = paginator.page(paginator.num_pages)
        
        # Prepara os contextos para os templates
        status_choices = Ticket.STATUS_CHOICES
        prioridade_choices = Ticket.PRIORIDADE_CHOICES
        
        # Atualiza o contexto com todas as variáveis necessárias
        context.update({
            'tickets': tickets,
            'termo_pesquisa': termo_pesquisa,
            'status_filter': status_filter,
            'prioridade_filter': prioridade_filter,
            'empresa_filter': empresa_filter,
            'categoria_filter': categoria_filter,
            'order_by': order_by,
            'status_choices': status_choices,
            'prioridade_choices': prioridade_choices,
            'empresas': empresas,
            'categorias': categorias,
            'funcionario': funcionario,
            'show_tickets': show_tickets,
            'show_status_filters': show_status_filters,
            'selected_category': selected_category,
            'selected_status': selected_status,
            'categoria_counts': categoria_counts,
            'status_counts': status_counts,
            'categoria_obj': categoria_obj,
            'has_admin_access': has_admin_access,
            'modificacoes_recentes': historico_recente
        })
        
        return render(request, 'tickets/dashboard.html', context)
    except Exception as e:
        logger.error(f"Erro ao acessar dashboard: {str(e)}")
        messages.error(request, "Ocorreu um erro ao carregar o dashboard. Por favor, tente novamente.")
        return redirect('login')

def registrar_historico(ticket, tipo_alteracao, usuario, descricao, dados_anteriores=None, dados_novos=None):
    """Função auxiliar para registrar alterações no histórico do ticket"""
    try:
        # Criar o registro de histórico principal
        historico = HistoricoTicket.objects.create(
            ticket=ticket,
            tipo_alteracao=tipo_alteracao,
            usuario=usuario,
            descricao=descricao
        )
        
        # Log para debug
        logger.debug(f"Registrando histórico tipo {tipo_alteracao} para ticket {ticket.id}")
        
        # Adicionar os detalhes anteriores, se existirem
        if dados_anteriores:
            for chave, valor in dados_anteriores.items():
                # Se o valor for um dicionário ou lista, converte para string
                if isinstance(valor, (dict, list)):
                    valor = json.dumps(valor)
                elif valor is None:
                    valor = "None"
                else:
                    valor = str(valor)
                
                DetalheHistoricoTicket.objects.create(
                    historico=historico,
                    tipo='anterior',
                    chave=chave,
                    valor=valor
                )
                logger.debug(f"Registrado dado anterior: {chave} = {valor[:50]}...")
        
        # Adicionar os detalhes novos, se existirem
        if dados_novos:
            for chave, valor in dados_novos.items():
                # Se o valor for um dicionário ou lista, converte para string
                if isinstance(valor, (dict, list)):
                    valor = json.dumps(valor)
                elif valor is None:
                    valor = "None"
                else:
                    valor = str(valor)
                    
                DetalheHistoricoTicket.objects.create(
                    historico=historico,
                    tipo='novo',
                    chave=chave,
                    valor=valor
                )
                logger.debug(f"Registrado dado novo: {chave} = {valor[:50]}...")
        
        return historico
    except Exception as e:
        logger.error(f"Erro ao registrar histórico: {str(e)}")
        return None

@login_required
def historico_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    
    # Verifica permissão
    if not request.user.is_superuser:
        try:
            funcionario = Funcionario.objects.get(usuario=request.user)
            if not funcionario.pode_ver_ticket(ticket):
                messages.error(request, 'Você não tem permissão para visualizar este ticket.')
                return redirect('tickets:dashboard')
        except Funcionario.DoesNotExist:
            messages.error(request, 'Você não possui um perfil de funcionário.')
            return redirect('tickets:dashboard')
    
    historico = ticket.historico.all().order_by('-data_alteracao')
    return render(request, 'tickets/historico_ticket.html', {
        'ticket': ticket,
        'historico': historico
    })

@login_required
def listar_notas_tecnicas(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    
    # Verifica permissão
    if not request.user.is_superuser:
        try:
            funcionario = Funcionario.objects.get(usuario=request.user)
            if not funcionario.pode_ver_ticket(ticket):
                messages.error(request, 'Você não tem permissão para visualizar este ticket.')
                return redirect('tickets:dashboard')
            if not funcionario.is_suporte() and not funcionario.is_admin():
                messages.error(request, 'Apenas técnicos e administradores podem acessar as notas técnicas.')
                return redirect('tickets:detalhe_ticket', ticket_id=ticket_id)
        except Funcionario.DoesNotExist:
            messages.error(request, 'Você não possui um perfil de funcionário.')
            return redirect('tickets:dashboard')
    
    notas = ticket.notas_tecnicas.all().order_by('-criado_em')
    return render(request, 'tickets/listar_notas_tecnicas.html', {
        'ticket': ticket,
        'notas': notas
    })

@login_required
def adicionar_nota_tecnica(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    
    # Verifica permissão
    if not request.user.is_superuser:
        try:
            funcionario = Funcionario.objects.get(usuario=request.user)
            if not funcionario.pode_ver_ticket(ticket):
                messages.error(request, 'Você não tem permissão para visualizar este ticket.')
                return redirect('tickets:dashboard')
            if not funcionario.is_suporte() and not funcionario.is_admin():
                messages.error(request, 'Apenas técnicos e administradores podem adicionar notas técnicas.')
                return redirect('tickets:detalhe_ticket', ticket_id=ticket_id)
        except Funcionario.DoesNotExist:
            messages.error(request, 'Você não possui um perfil de funcionário.')
            return redirect('tickets:dashboard')
    else:
        # Para superusuários, precisamos obter um funcionário válido
        try:
            funcionario = Funcionario.objects.filter(
                usuario=request.user,
                tipo__in=['admin', 'suporte']
            ).first()
            if not funcionario:
                messages.error(request, 'Você precisa ter um perfil de técnico ou administrador para adicionar notas técnicas.')
                return redirect('tickets:detalhe_ticket', ticket_id=ticket_id)
        except Exception:
            messages.error(request, 'Erro ao verificar seu perfil de funcionário.')
            return redirect('tickets:detalhe_ticket', ticket_id=ticket_id)
    
    if request.method == 'POST':
        form = NotaTecnicaForm(request.POST, ticket=ticket, tecnico=funcionario)
        if form.is_valid():
            nota = form.save()
            
            # Registrar no histórico
            HistoricoTicket.objects.create(
                ticket=ticket,
                tipo_alteracao='nota_tecnica',
                usuario=request.user,
                descricao=f'Nota técnica adicionada por {funcionario.usuario.get_full_name() or funcionario.usuario.username}',
                dados_novos={
                    'nota_id': nota.id,
                    'acao': 'adicao',
                    'equipamento': nota.equipamento if nota.equipamento else 'Não especificado'
                }
            )
            
            messages.success(request, 'Nota técnica adicionada com sucesso!')
            return redirect('tickets:listar_notas_tecnicas', ticket_id=ticket_id)
    else:
        form = NotaTecnicaForm(ticket=ticket, tecnico=funcionario)
    
    return render(request, 'tickets/adicionar_nota_tecnica.html', {
        'ticket': ticket,
        'form': form
    })

@login_required
def editar_nota_tecnica(request, nota_id):
    nota = get_object_or_404(NotaTecnica, pk=nota_id)
    ticket = nota.ticket
    
    # Verifica permissão
    if not request.user.is_superuser:
        try:
            funcionario = Funcionario.objects.get(usuario=request.user)
            if not funcionario.pode_ver_ticket(ticket):
                messages.error(request, 'Você não tem permissão para visualizar este ticket.')
                return redirect('tickets:dashboard')
            # Apenas o técnico que criou a nota ou um admin pode editar
            if not funcionario.is_admin() and funcionario != nota.tecnico:
                messages.error(request, 'Você não tem permissão para editar esta nota técnica.')
                return redirect('tickets:listar_notas_tecnicas', ticket_id=ticket.id)
        except Funcionario.DoesNotExist:
            messages.error(request, 'Você não possui um perfil de funcionário.')
            return redirect('tickets:dashboard')
    
    if request.method == 'POST':
        form = NotaTecnicaForm(request.POST, instance=nota)
        if form.is_valid():
            form.save()
            
            # Registrar no histórico
            HistoricoTicket.objects.create(
                ticket=ticket,
                tipo_alteracao='nota_tecnica',
                usuario=request.user,
                descricao=f'Nota técnica #{nota.id} editada por {request.user.get_full_name() or request.user.username}',
                dados_novos={
                    'nota_id': nota.id,
                    'acao': 'edicao',
                    'equipamento': nota.equipamento if nota.equipamento else 'Não especificado'
                }
            )
            
            messages.success(request, 'Nota técnica atualizada com sucesso!')
            return redirect('tickets:listar_notas_tecnicas', ticket_id=ticket.id)
    else:
        form = NotaTecnicaForm(instance=nota)
    
    return render(request, 'tickets/editar_nota_tecnica.html', {
        'ticket': ticket,
        'nota': nota,
        'form': form
    })

@login_required
def excluir_nota_tecnica(request, nota_id):
    nota = get_object_or_404(NotaTecnica, pk=nota_id)
    ticket = nota.ticket
    
    # Verifica permissão
    if not request.user.is_superuser:
        try:
            funcionario = Funcionario.objects.get(usuario=request.user)
            if not funcionario.pode_ver_ticket(ticket):
                messages.error(request, 'Você não tem permissão para visualizar este ticket.')
                return redirect('tickets:dashboard')
            # Apenas o técnico que criou a nota ou um admin pode excluir
            if not funcionario.is_admin() and funcionario != nota.tecnico:
                messages.error(request, 'Você não tem permissão para excluir esta nota técnica.')
                return redirect('tickets:listar_notas_tecnicas', ticket_id=ticket.id)
        except Funcionario.DoesNotExist:
            messages.error(request, 'Você não possui um perfil de funcionário.')
            return redirect('tickets:dashboard')
    
    if request.method == 'POST':
        nota_id = nota.id
        nota.delete()
        
        # Registrar no histórico
        HistoricoTicket.objects.create(
            ticket=ticket,
            tipo_alteracao='nota_tecnica',
            usuario=request.user,
            descricao=f'Nota técnica #{nota_id} excluída por {request.user.get_full_name() or request.user.username}',
            dados_novos={
                'nota_id': nota_id,
                'acao': 'exclusao'
            }
        )
        
        messages.success(request, 'Nota técnica excluída com sucesso!')
        return redirect('tickets:listar_notas_tecnicas', ticket_id=ticket.id)
    
    return render(request, 'tickets/excluir_nota_tecnica.html', {
        'ticket': ticket,
        'nota': nota
    })

@login_required
def criar_ticket(request):
    try:
        # Verifica se o usuário tem permissão para criar tickets
        funcionario = request.user.funcionarios.first()
        if not funcionario and not request.user.is_superuser:
            messages.error(request, 'Você não tem permissão para criar tickets.')
            return redirect('tickets:dashboard')

        # Obtém as empresas associadas ao usuário
        if request.user.is_superuser:
            empresas = Empresa.objects.all()
        else:
            empresas = funcionario.empresas.all()
            if not empresas.exists():
                messages.error(request, 'Você não está associado a nenhuma empresa.')
                return redirect('tickets:dashboard')

        # Automaticamente seleciona a empresa se o usuário tiver apenas uma
        initial_data = {}
        if funcionario and empresas.count() == 1:
            initial_data['empresa'] = empresas.first().id
            empresa_id = str(empresas.first().id)
        else:
            # Obtém a empresa selecionada do formulário POST ou da query string
            empresa_id = request.POST.get('empresa') if request.method == 'POST' else request.GET.get('empresa')
        
        # Verifica se há uma categoria específica selecionada
        categoria_id = request.POST.get('categoria') if request.method == 'POST' else request.GET.get('categoria')
        if categoria_id:
            initial_data['categoria'] = categoria_id

        # Obtém os campos personalizados da empresa selecionada
        campos_personalizados = None
        if empresa_id:
            try:
                empresa = Empresa.objects.get(id=empresa_id)
                campos_personalizados = CampoPersonalizado.objects.filter(
                    empresa=empresa,
                    ativo=True
                ).order_by('ordem')
            except Empresa.DoesNotExist:
                empresa_id = None
        
        # Se estamos na etapa de seleção de categoria
        categorias = None
        if empresa_id and not categoria_id and request.method != 'POST':
            try:
                empresa = Empresa.objects.get(id=empresa_id)
                
                # Obter as categorias permitidas para o funcionário atual
                if funcionario:
                    categorias = funcionario.get_categorias_permitidas(empresa)
                else:
                    # Se for um superusuário, mostrar todas as categorias ativas
                    categorias = CategoriaChamado.objects.filter(
                        empresa=empresa,
                        ativo=True
                    ).order_by('ordem', 'nome')
                
                # Se temos apenas uma categoria ou nenhuma, continue para o formulário
                if categorias.count() <= 1:
                    if categorias.count() == 1:
                        initial_data['categoria'] = categorias.first().id
                        categoria_id = str(categorias.first().id)
                    categorias = None
                else:
                    # Mostra a tela de seleção de categoria
                    return render(request, 'tickets/selecionar_categoria.html', {
                        'empresa': empresa,
                        'categorias': categorias
                    })
            except Empresa.DoesNotExist:
                pass

        if request.method == 'POST':
            form = TicketForm(request.POST, usuario=request.user, initial=initial_data)
            if form.is_valid():
                ticket = form.save(commit=False)
                ticket.criado_por = request.user
                
                # Verifica se é um cliente criando o ticket e não foi atribuído a ninguém
                if not ticket.atribuido_a:
                    funcionario_atual = Funcionario.objects.filter(usuario=request.user).first()
                    if funcionario_atual and funcionario_atual.is_cliente():
                        # Procura por um funcionário admin ou suporte da mesma empresa para atribuir o ticket
                        atribuido_a = Funcionario.objects.filter(
                            empresas=ticket.empresa,
                            tipo__in=['admin', 'suporte']
                        ).order_by('?').first()  # Ordem aleatória para distribuir os tickets
                        
                        if atribuido_a:
                            ticket.atribuido_a = atribuido_a
                
                ticket.save()

                # Salva os valores dos campos personalizados
                if campos_personalizados:
                    for campo in campos_personalizados:
                        campo_valor = request.POST.get(f'campo_{campo.id}')
                        if campo_valor or campo.tipo == 'booleano':
                            # Para campos booleanos, verifica se o checkbox foi marcado
                            if campo.tipo == 'booleano':
                                valor = 'true' if campo_valor == 'true' else 'false'
                            else:
                                valor = campo_valor or ''
                                
                            # Só salva se o valor não estiver vazio ou se for um campo booleano
                            if valor or campo.tipo == 'booleano':
                                ValorCampoPersonalizado.objects.create(
                                    ticket=ticket,
                                    campo=campo,
                                    valor=valor
                                )

                messages.success(request, 'Chamado criado com sucesso!')
                return redirect('tickets:detalhe_ticket', ticket.id)
        else:
            form = TicketForm(usuario=request.user, initial=initial_data)

        context = {
            'form': form,
            'campos_personalizados': campos_personalizados,
            'empresas': empresas,
            'empresa_id': empresa_id,
            'categoria_id': categoria_id
        }
        return render(request, 'tickets/criar_ticket.html', context)
    except Exception as e:
        logger.error(f"Erro ao criar ticket: {str(e)}")
        messages.error(request, f"Erro ao criar ticket: {str(e)}")
        return redirect('tickets:dashboard')

@login_required
def detalhe_ticket(request, ticket_id):
    try:
        logger.info(f"Tentando acessar ticket {ticket_id} para usuário {request.user.username}")
        ticket = get_object_or_404(Ticket, id=ticket_id)
        
        # Verifica se o usuário tem permissão para ver o ticket
        if not request.user.is_superuser:
            funcionario = request.user.funcionarios.first()
            if not funcionario:
                logger.warning(f"Usuário {request.user.username} não tem funcionário associado")
                messages.error(request, 'Você não tem permissão para visualizar este ticket.')
                return redirect('tickets:dashboard')
            
            # Verifica se o funcionário tem acesso à empresa do ticket
            if not funcionario.empresas.filter(id=ticket.empresa.id).exists():
                logger.warning(f"Usuário {request.user.username} não tem acesso à empresa {ticket.empresa.id}")
                messages.error(request, 'Você não tem acesso a esta empresa.')
                return redirect('tickets:dashboard')
            
            # Verifica se o funcionário tem permissão para ver o ticket
            if not funcionario.pode_ver_ticket(ticket):
                logger.warning(f"Usuário {request.user.username} não tem permissão para ver o ticket {ticket.id}")
                messages.error(request, 'Você não tem permissão para visualizar este ticket.')
                return redirect('tickets:dashboard')
        
        # Processa o formulário de comentário se for POST
        if request.method == 'POST':
            action = request.POST.get('action')
            
            if action == 'comentario':
                funcionario = request.user.funcionarios.first()
                if not funcionario or not funcionario.pode_comentar_ticket_especifico(ticket):
                    logger.warning(f"Usuário {request.user.username} não tem permissão para comentar no ticket {ticket.id}")
                    messages.error(request, 'Você não tem permissão para adicionar comentários.')
                    return redirect('tickets:detalhe_ticket', ticket_id=ticket.id)
                
                texto = request.POST.get('texto')
                if texto:
                    comentario = Comentario.objects.create(
                        ticket=ticket,
                        autor=request.user,
                        texto=texto
                    )
                    
                    # Registra o comentário no histórico
                    registrar_historico(
                        ticket=ticket,
                        tipo_alteracao='comentario',
                        usuario=request.user,
                        descricao=f'Comentário adicionado por {request.user.get_full_name()}',
                        dados_novos={'comentario': texto}
                    )
                    
                    messages.success(request, 'Comentário adicionado com sucesso!')
                else:
                    messages.error(request, 'O comentário não pode estar vazio.')
            
            elif action == 'status':
                if not request.user.is_superuser:
                    funcionario = request.user.funcionarios.first()
                    if not funcionario or not funcionario.pode_editar_ticket(ticket):
                        logger.warning(f"Usuário {request.user.username} não tem permissão para alterar status do ticket {ticket.id}")
                        messages.error(request, 'Você não tem permissão para alterar o status deste ticket.')
                        return redirect('tickets:detalhe_ticket', ticket_id=ticket.id)
                
                novo_status = request.POST.get('novo_status')
                if novo_status in [choice[0] for choice in Ticket.STATUS_CHOICES]:
                    # Salva o status anterior para o histórico
                    status_anterior = ticket.status
                    
                    # Atualiza o status
                    ticket.status = novo_status
                    ticket.save()
                    
                    # Registra a alteração no histórico
                    registrar_historico(
                        ticket=ticket,
                        tipo_alteracao='status',
                        usuario=request.user,
                        descricao=f'Status alterado por {request.user.get_full_name()}',
                        dados_anteriores={'status': status_anterior},
                        dados_novos={'status': novo_status}
                    )
                    
                    messages.success(request, 'Status atualizado com sucesso!')
                else:
                    messages.error(request, 'Status inválido.')
            
            elif action == 'prioridade':
                if not request.user.is_superuser:
                    funcionario = request.user.funcionarios.first()
                    if not funcionario or not funcionario.pode_editar_ticket(ticket):
                        logger.warning(f"Usuário {request.user.username} não tem permissão para alterar prioridade do ticket {ticket.id}")
                        messages.error(request, 'Você não tem permissão para alterar a prioridade deste ticket.')
                        return redirect('tickets:detalhe_ticket', ticket_id=ticket.id)
                
                nova_prioridade = request.POST.get('nova_prioridade')
                if nova_prioridade in [choice[0] for choice in Ticket.PRIORIDADE_CHOICES]:
                    # Salva a prioridade anterior para o histórico
                    prioridade_anterior = ticket.prioridade
                    
                    # Atualiza a prioridade
                    ticket.prioridade = nova_prioridade
                    ticket.save()
                    
                    # Registra a alteração no histórico
                    registrar_historico(
                        ticket=ticket,
                        tipo_alteracao='prioridade',
                        usuario=request.user,
                        descricao=f'Prioridade alterada por {request.user.get_full_name()}',
                        dados_anteriores={'prioridade': prioridade_anterior},
                        dados_novos={'prioridade': nova_prioridade}
                    )
                    
                    messages.success(request, 'Prioridade atualizada com sucesso!')
                else:
                    messages.error(request, 'Prioridade inválida.')
            
            return redirect('tickets:detalhe_ticket', ticket_id=ticket.id)
        
        # Obtém os filtros da URL
        status = request.GET.get('status', '')
        prioridade = request.GET.get('prioridade', '')
        empresa = request.GET.get('empresa', '')
        order_by = request.GET.get('order_by', '-criado_em')
        
        # Obtém os tickets filtrados
        if request.user.is_superuser:
            tickets = Ticket.objects.all()
        else:
            funcionario = request.user.funcionarios.first()
            tickets = Ticket.objects.filter(
                Q(empresa__in=funcionario.empresas.all()) |
                Q(atribuido_a=funcionario)
            )
        
        # Aplica os filtros específicos
        if status:
            tickets = tickets.filter(status=status)
        if prioridade:
            tickets = tickets.filter(prioridade=prioridade)
        if empresa:
            tickets = tickets.filter(empresa_id=empresa)
        
        # Aplica a ordenação
        tickets = tickets.order_by(order_by)
        
        # Obtém o ticket anterior e próximo
        ticket_anterior = None
        ticket_proximo = None
        tickets_list = list(tickets)
        for i, t in enumerate(tickets_list):
            if t.id == ticket.id:
                if i > 0:
                    ticket_anterior = tickets_list[i-1]
                if i < len(tickets_list) - 1:
                    ticket_proximo = tickets_list[i+1]
                break
        
        # Obtém os comentários do ticket
        comentarios = Comentario.objects.filter(ticket=ticket).order_by('criado_em')
        
        # Obtém os valores dos campos personalizados
        valores_campos = ValorCampoPersonalizado.objects.filter(ticket=ticket)
        
        # Obtém o funcionário do usuário
        funcionario = request.user.funcionarios.first()
        
        # Verifica as permissões do funcionário
        pode_editar = funcionario and funcionario.pode_editar_ticket(ticket) if funcionario else False
        pode_atribuir = funcionario and funcionario.pode_atribuir_ticket(ticket) if funcionario else False
        
        # Verifica se é técnico de suporte
        is_suporte = funcionario.is_suporte() if funcionario else False
        is_admin = funcionario.is_admin() if funcionario else False
        
        context = {
            'ticket': ticket,
            'comentarios': comentarios,
            'ticket_anterior': ticket_anterior,
            'ticket_proximo': ticket_proximo,
            'status': status,
            'prioridade': prioridade,
            'empresa': empresa,
            'order_by': order_by,
            'campos_personalizados': valores_campos,
            'funcionario': funcionario,
            'pode_editar': pode_editar,
            'pode_atribuir': pode_atribuir,
            'is_suporte': is_suporte,
            'is_admin': is_admin
        }
        
        logger.info(f"Chamado {ticket_id} carregado com sucesso para usuário {request.user.username}")
        return render(request, 'tickets/detalhe_ticket.html', context)
        
    except Exception as e:
        logger.error(f"Erro ao carregar detalhes do ticket {ticket_id}: {str(e)}", exc_info=True)
        messages.error(request, 'Ocorreu um erro ao carregar os detalhes do ticket.')
        return redirect('tickets:dashboard')

@login_required
def editar_ticket(request, ticket_id):
    try:
        ticket = get_object_or_404(Ticket, id=ticket_id)
        
        # Verificar permissões
        is_admin = False
        if not request.user.is_superuser:
            funcionario = request.user.funcionarios.first()
            if not funcionario or not funcionario.pode_editar_ticket(ticket):
                messages.error(request, 'Você não tem permissão para editar este ticket.')
                return redirect('tickets:dashboard')
            
            # Verifica se o funcionário tem acesso à empresa do ticket
            if not funcionario.empresas.filter(id=ticket.empresa.id).exists():
                messages.error(request, 'Você não tem acesso a esta empresa.')
                return redirect('tickets:dashboard')
                
            # Verifica se o funcionário é admin
            is_admin = funcionario.is_admin()
        else:
            is_admin = True
        
        # Carrega os valores dos campos personalizados existentes
        valores_campos = ValorCampoPersonalizado.objects.filter(ticket=ticket).select_related('campo')
        
        # Obtém as empresas e funcionários disponíveis
        if request.user.is_superuser:
            empresas = Empresa.objects.all()
            funcionarios = Funcionario.objects.all()
        else:
            funcionario = request.user.funcionarios.first()
            empresas = funcionario.empresas.all()
            funcionarios = Funcionario.objects.filter(empresas__in=empresas).distinct()
        
        if request.method == 'POST':
            form = TicketForm(request.POST, instance=ticket, usuario=request.user)
            if form.is_valid():
                # Salva os dados anteriores para o histórico
                dados_anteriores = {
                    'titulo': ticket.titulo,
                    'descricao': ticket.descricao,
                    'status': ticket.status,
                    'prioridade': ticket.prioridade,
                    'empresa': ticket.empresa.nome,
                }
                
                # Adiciona atribuido_a aos dados anteriores se existir
                if ticket.atribuido_a:
                    dados_anteriores['atribuido_a'] = ticket.atribuido_a.usuario.username
                
                ticket_salvo = form.save()
                
                # Processa os valores dos campos personalizados
                campos_alterados = []
                for valor in valores_campos:
                    # Só processa os campos editáveis
                    if valor.campo.editavel:
                        campo_id = valor.campo.id
                        campo_valor = request.POST.get(f'campo_{campo_id}')
                        
                        # Processa o valor de acordo com o tipo do campo
                        if valor.campo.tipo == 'booleano':
                            novo_valor = 'true' if campo_valor == 'true' else 'false'
                        else:
                            novo_valor = campo_valor or ''
                        
                        # Se o valor mudou, atualiza e registra no histórico
                        if novo_valor != valor.valor:
                            # Registra a alteração para o histórico
                            campos_alterados.append({
                                'campo': valor.campo.nome,
                                'valor_anterior': valor.valor,
                                'valor_novo': novo_valor
                            })
                            
                            # Atualiza o valor do campo
                            valor.valor = novo_valor
                            valor.save()
                
                # Registra a edição no histórico
                dados_novos = {
                    'titulo': ticket_salvo.titulo,
                    'descricao': ticket_salvo.descricao,
                    'status': ticket_salvo.status,
                    'prioridade': ticket_salvo.prioridade,
                    'empresa': ticket_salvo.empresa.nome,
                }
                
                # Adiciona atribuido_a aos dados novos se existir
                if ticket_salvo.atribuido_a:
                    dados_novos['atribuido_a'] = ticket_salvo.atribuido_a.usuario.username
                
                # Adiciona os campos personalizados alterados aos dados do histórico
                if campos_alterados:
                    dados_anteriores['campos_personalizados'] = {item['campo']: item['valor_anterior'] for item in campos_alterados}
                    dados_novos['campos_personalizados'] = {item['campo']: item['valor_novo'] for item in campos_alterados}
                
                # Sempre registrar o histórico quando o formulário é salvo
                historico = registrar_historico(
                    ticket=ticket_salvo,
                    tipo_alteracao='edicao',
                    usuario=request.user,
                    descricao=f'Chamado editado por {request.user.get_full_name() or request.user.username}',
                    dados_anteriores=dados_anteriores,
                    dados_novos=dados_novos
                )
                logger.info(f"Histórico registrado com ID {historico.id if historico else 'None'} para o ticket {ticket_salvo.id}")
                
                messages.success(request, 'Chamado atualizado com sucesso!')
                return redirect('tickets:detalhe_ticket', ticket_id=ticket.id)
        else:
            form = TicketForm(instance=ticket, usuario=request.user)
        
        # Atualiza as opções do formulário
        form.fields['empresa'].queryset = empresas
        # Verifica se o campo atribuido_a existe antes de tentar atualizá-lo
        if 'atribuido_a' in form.fields:
            form.fields['atribuido_a'].queryset = funcionarios
        
        return render(request, 'tickets/editar_ticket.html', {
            'form': form,
            'ticket': ticket,
            'campos_personalizados': valores_campos,
            'is_admin': is_admin
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
            form = AtribuirTicketForm(request.POST, instance=ticket, user=request.user)
            if form.is_valid():
                # Salva o funcionário anterior para o histórico
                funcionario_anterior = ticket.atribuido_a
                
                form.save()
                
                # Registra a atribuição no histórico
                registrar_historico(
                    ticket=ticket,
                    tipo_alteracao='atribuicao',
                    usuario=request.user,
                    descricao=f'Chamado atribuído por {request.user.get_full_name()}',
                    dados_anteriores={
                        'atribuido_a': funcionario_anterior.usuario.username if funcionario_anterior else None
                    },
                    dados_novos={
                        'atribuido_a': ticket.atribuido_a.usuario.username if ticket.atribuido_a else None
                    }
                )
                
                # Cria ou atualiza a atribuição para manter a compatibilidade
                if ticket.atribuido_a:
                    AtribuicaoTicket.objects.update_or_create(
                        ticket=ticket,
                        funcionario=ticket.atribuido_a,
                        defaults={'principal': True}
                    )
                
                messages.success(request, 'Chamado atribuído com sucesso!')
                return redirect('tickets:detalhe_ticket', ticket_id=ticket.id)
        else:
            form = AtribuirTicketForm(instance=ticket, user=request.user)
        
        return render(request, 'tickets/atribuir_ticket.html', {
            'form': form,
            'ticket': ticket
        })
    except Exception as e:
        logger.error(f"Erro ao atribuir ticket: {str(e)}")
        messages.error(request, 'Erro ao atribuir ticket.')
        return redirect('tickets:dashboard')

@login_required
def multi_atribuir_ticket(request, ticket_id):
    try:
        ticket = get_object_or_404(Ticket, id=ticket_id)
        
        # Verificar permissões
        if not request.user.is_superuser:
            funcionario = request.user.funcionarios.first()
            if not funcionario or not funcionario.pode_atribuir_ticket(ticket):
                messages.error(request, 'Você não tem permissão para atribuir este ticket.')
                return redirect('tickets:dashboard')
        
        # Obter as atribuições atuais para exibir no formulário
        atribuicoes_atuais = AtribuicaoTicket.objects.filter(ticket=ticket).select_related('funcionario')
        
        if request.method == 'POST':
            form = MultiAtribuirTicketForm(request.POST, ticket=ticket, empresa=ticket.empresa, user=request.user)
            if form.is_valid():
                # Obter os funcionários selecionados antes de salvar
                funcionarios_anteriores = [
                    atribuicao.funcionario.usuario.username 
                    for atribuicao in ticket.atribuicoes.all()
                ]
                
                # Salvar as novas atribuições
                form.save()
                
                # Obter os funcionários novos após salvar
                funcionarios_novos = [
                    atribuicao.funcionario.usuario.username 
                    for atribuicao in ticket.atribuicoes.all()
                ]
                
                # Registra a atribuição no histórico
                registrar_historico(
                    ticket=ticket,
                    tipo_alteracao='atribuicao',
                    usuario=request.user,
                    descricao=f'Múltiplas atribuições atualizadas por {request.user.get_full_name()}',
                    dados_anteriores={
                        'atribuidos_a': funcionarios_anteriores,
                        'atribuido_principal': ticket.atribuido_a.usuario.username if ticket.atribuido_a else None
                    },
                    dados_novos={
                        'atribuidos_a': funcionarios_novos,
                        'atribuido_principal': ticket.atribuido_a.usuario.username if ticket.atribuido_a else None
                    }
                )
                
                messages.success(request, 'Chamado atribuído com sucesso!')
                return redirect('tickets:detalhe_ticket', ticket_id=ticket.id)
        else:
            form = MultiAtribuirTicketForm(ticket=ticket, empresa=ticket.empresa, user=request.user)
        
        # Obter a lista de funcionários disponíveis para a empresa do ticket
        # considerando as permissões do usuário atual
        if not request.user.is_superuser:
            funcionario_atual = request.user.funcionarios.first()
            if funcionario_atual:
                funcionarios_disponiveis = Funcionario.objects.filter(
                    empresas=ticket.empresa,
                    tipo__in=['admin', 'suporte'],
                    empresas__in=funcionario_atual.empresas.all()
                ).select_related('usuario').distinct()
            else:
                funcionarios_disponiveis = Funcionario.objects.none()
        else:
            funcionarios_disponiveis = Funcionario.objects.filter(
                empresas=ticket.empresa,
                tipo__in=['admin', 'suporte']
            ).select_related('usuario').distinct()
        
        return render(request, 'tickets/multi_atribuir_ticket.html', {
            'form': form,
            'ticket': ticket,
            'atribuicoes_atuais': atribuicoes_atuais,
            'funcionarios_disponiveis': funcionarios_disponiveis
        })
    except Exception as e:
        logger.error(f"Erro ao atribuir múltiplos funcionários ao ticket: {str(e)}")
        messages.error(request, f'Erro ao atribuir múltiplos funcionários: {str(e)}')
        return redirect('tickets:dashboard')

@never_cache
def logout_view(request):
    """
    Realiza o logout do usuário e direciona para a página de logout bem-sucedido.
    Implementação simplificada que não depende do sistema de redirecionamento do Django.
    """
    try:
        # Registrar o nome do usuário antes de fazer logout
        username = request.user.username if request.user.is_authenticated else 'Usuário não autenticado'
        logger.info(f"Logout iniciado para o usuário: {username}")
        
        # Realizar o logout
        logout(request)
        
        # Mensagem de sucesso no log
        logger.info("Logout concluído com sucesso")
        
        # Redirecionar diretamente para a página de logout success
        # Usando o caminho absoluto em vez do nome da URL
        return HttpResponseRedirect('/logout-success/')
    except Exception as e:
        # Logar qualquer erro que ocorra
        logger.error(f"Erro durante o logout: {str(e)}", exc_info=True)
        # Redirecionar para home em caso de erro
        return HttpResponseRedirect('/')

@login_required
@admin_permission_required
def gerenciar_campos_personalizados(request, empresa_id):
    try:
        empresa = get_object_or_404(Empresa, id=empresa_id)
        
        if request.method == 'POST':
            form = CampoPersonalizadoForm(request.POST)
            if form.is_valid():
                campo = form.save(commit=False)
                campo.empresa = empresa
                campo.save()
                messages.success(request, 'Campo personalizado criado com sucesso!')
                return redirect('tickets:gerenciar_campos_personalizados', empresa_id=empresa.id)
        else:
            form = CampoPersonalizadoForm()
        
        campos = CampoPersonalizado.objects.filter(empresa=empresa).order_by('ordem', 'nome')
        
        return render(request, 'tickets/gerenciar_campos_personalizados.html', {
            'empresa': empresa,
            'form': form,
            'campos': campos
        })
    except Exception as e:
        logger.error(f"Erro ao gerenciar campos personalizados: {str(e)}")
        messages.error(request, 'Erro ao gerenciar campos personalizados.')
        return redirect('tickets:lista_empresas')

@login_required
@admin_permission_required
def editar_campo_personalizado(request, campo_id):
    try:
        campo = get_object_or_404(CampoPersonalizado, id=campo_id)
        
        if request.method == 'POST':
            form = CampoPersonalizadoForm(request.POST, instance=campo)
            if form.is_valid():
                form.save()
                messages.success(request, 'Campo personalizado atualizado com sucesso!')
                return redirect('tickets:gerenciar_campos_personalizados', empresa_id=campo.empresa.id)
        else:
            form = CampoPersonalizadoForm(instance=campo)
        
        return render(request, 'tickets/editar_campo_personalizado.html', {
            'form': form,
            'campo': campo
        })
    except Exception as e:
        logger.error(f"Erro ao editar campo personalizado: {str(e)}")
        messages.error(request, 'Erro ao editar campo personalizado.')
        return redirect('tickets:lista_empresas')

@login_required
@admin_permission_required
def excluir_campo_personalizado(request, campo_id):
    try:
        campo = get_object_or_404(CampoPersonalizado, id=campo_id)
        empresa_id = campo.empresa.id
        campo.delete()
        messages.success(request, 'Campo personalizado excluído com sucesso!')
        return redirect('tickets:gerenciar_campos_personalizados', empresa_id=empresa_id)
    except Exception as e:
        logger.error(f"Erro ao excluir campo personalizado: {str(e)}")
        messages.error(request, 'Erro ao excluir campo personalizado.')
        return redirect('tickets:lista_empresas')

# Views para Relatórios

@login_required
def relatorios_menu(request):
    """
    Menu principal de relatórios
    """
    return render(request, 'tickets/relatorios_menu.html')

@login_required
def relatorio_tickets(request):
    """
    Relatório detalhado de tickets com filtros
    """
    # Obtém o funcionário logado
    funcionario = get_object_or_404(Funcionario, usuario=request.user)
    
    # Lista de empresas que o funcionário tem acesso
    empresas = funcionario.empresas.all()
    
    # Lista de técnicos (funcionários de suporte) 
    tecnicos = Funcionario.objects.filter(
        tipo__in=['admin', 'suporte'],
        empresas__in=empresas
    ).distinct()
    
    # Aplicar filtros
    filtro_empresa = request.GET.get('empresa')
    filtro_status = request.GET.get('status')
    filtro_prioridade = request.GET.get('prioridade')
    filtro_tecnico = request.GET.get('tecnico')
    filtro_data_inicial = request.GET.get('data_inicial')
    filtro_data_final = request.GET.get('data_final')
    filtro_search = request.GET.get('search')
    
    # Base query - agora com verificação de permissões
    if funcionario.is_admin() or funcionario.is_suporte():
        # Admins e suporte podem ver todos os tickets das empresas que têm acesso
        tickets_query = Ticket.objects.filter(empresa__in=empresas)
    else:
        # Clientes só podem ver seus próprios tickets
        tickets_query = Ticket.objects.filter(
            Q(empresa__in=empresas) & 
            (Q(criado_por=request.user) | Q(atribuido_a=funcionario) | Q(atribuicoes__funcionario=funcionario))
        ).distinct()
    
    # Aplicar filtros se fornecidos
    if filtro_empresa:
        if funcionario.tem_acesso_empresa(get_object_or_404(Empresa, id=filtro_empresa)):
            tickets_query = tickets_query.filter(empresa_id=filtro_empresa)
    
    if filtro_status:
        tickets_query = tickets_query.filter(status=filtro_status)
    
    if filtro_prioridade:
        tickets_query = tickets_query.filter(prioridade=filtro_prioridade)
    
    if filtro_tecnico:
        tickets_query = tickets_query.filter(atribuido_a_id=filtro_tecnico)
    
    if filtro_data_inicial:
        data_inicial = datetime.strptime(filtro_data_inicial, '%Y-%m-%d').date()
        tickets_query = tickets_query.filter(criado_em__date__gte=data_inicial)
    
    if filtro_data_final:
        data_final = datetime.strptime(filtro_data_final, '%Y-%m-%d').date()
        tickets_query = tickets_query.filter(criado_em__date__lte=data_final)
    
    if filtro_search:
        tickets_query = tickets_query.filter(
            Q(titulo__icontains=filtro_search) | 
            Q(descricao__icontains=filtro_search)
        )
    
    # Ordenação
    tickets_query = tickets_query.order_by('-criado_em')
    
    # Paginação
    paginator = Paginator(tickets_query, 25)  # 25 tickets por página
    page = request.GET.get('page')
    
    try:
        tickets = paginator.page(page)
    except PageNotAnInteger:
        tickets = paginator.page(1)
    except EmptyPage:
        tickets = paginator.page(paginator.num_pages)
    
    # Cálculo das estatísticas
    total_tickets = tickets_query.count()
    abertos = tickets_query.filter(status='aberto').count()
    em_andamento = tickets_query.filter(status='em_andamento').count()
    pendentes = tickets_query.filter(status='pendente').count()
    resolvidos = tickets_query.filter(status='resolvido').count()
    fechados = tickets_query.filter(status='fechado').count()
    
    # Estatísticas por prioridade
    baixa_prioridade = tickets_query.filter(prioridade='baixa').count()
    media_prioridade = tickets_query.filter(prioridade='media').count()
    alta_prioridade = tickets_query.filter(prioridade='alta').count()
    urgente_prioridade = tickets_query.filter(prioridade='urgente').count()
    
    # Cálculo de porcentagens
    porcentagem_abertos = round((abertos / total_tickets * 100) if total_tickets > 0 else 0, 1)
    porcentagem_em_andamento = round((em_andamento / total_tickets * 100) if total_tickets > 0 else 0, 1)
    porcentagem_resolvidos = round((resolvidos / total_tickets * 100) if total_tickets > 0 else 0, 1)
    
    # Tempo médio de resolução (em dias)
    # Modificando para evitar o uso de contains lookup em JSON que não é suportado pelo SQLite
    tempo_medio = tickets_query.filter(
        status__in=['resolvido', 'fechado']
    ).annotate(
        tempo_resolucao=ExpressionWrapper(
            F('atualizado_em') - F('criado_em'),
            output_field=DurationField()
        )
    ).aggregate(media=Avg('tempo_resolucao'))
    
    tempo_medio_resolucao = '0'
    if tempo_medio['media']:
        tempo_medio_resolucao = round(tempo_medio['media'].total_seconds() / (3600 * 24), 1)  # Conversão para dias
    
    context = {
        'tickets': tickets,
        'empresas': empresas,
        'tecnicos': tecnicos,
        'status_choices': Ticket.STATUS_CHOICES,
        'prioridade_choices': Ticket.PRIORIDADE_CHOICES,
        'total_tickets': total_tickets,
        'abertos': abertos,
        'em_andamento': em_andamento,
        'pendentes': pendentes,
        'resolvidos': resolvidos,
        'fechados': fechados,
        'baixa_prioridade': baixa_prioridade,
        'media_prioridade': media_prioridade,
        'alta_prioridade': alta_prioridade,
        'urgente_prioridade': urgente_prioridade,
        'porcentagem_abertos': porcentagem_abertos,
        'porcentagem_em_andamento': porcentagem_em_andamento,
        'porcentagem_resolvidos': porcentagem_resolvidos,
        'tempo_medio_resolucao': tempo_medio_resolucao,
    }
    
    return render(request, 'tickets/relatorio_tickets.html', context)

@login_required
def relatorio_empresas(request):
    """
    Relatório por empresa
    """
    # Implementar relatório por empresa
    return render(request, 'tickets/relatorio_empresas.html')

@login_required
def relatorio_tecnicos(request):
    """
    Relatório de desempenho dos técnicos
    """
    # Implementar relatório de técnicos
    return render(request, 'tickets/relatorio_tecnicos.html')

@login_required
def exportar_relatorio(request, tipo):
    """
    Exporta um relatório para PDF, Excel ou CSV
    """
    try:
        from io import BytesIO
        from django.http import HttpResponse
        import csv
        import xlsxwriter
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        
        # Verificar se o formato está no GET corretamente
        formato = request.GET.get('format', 'csv')
        
        # Selecionar o tipo de relatório a ser exportado
        if tipo == 'tickets':
            # Obter filtros
            filtro_empresa = request.GET.get('empresa')
            filtro_status = request.GET.get('status')
            filtro_prioridade = request.GET.get('prioridade')
            filtro_tecnico = request.GET.get('tecnico')
            filtro_data_inicial = request.GET.get('data_inicial')
            filtro_data_final = request.GET.get('data_final')
            filtro_search = request.GET.get('search')
            
            # Obter funcionário logado
            funcionario = get_object_or_404(Funcionario, usuario=request.user)
            
            # Lista de empresas que o funcionário tem acesso
            empresas = funcionario.empresas.all()
            
            # Base query com restrições de permissão
            if funcionario.is_admin() or funcionario.is_suporte():
                # Admins e suporte podem ver todos os tickets das empresas que têm acesso
                tickets_query = Ticket.objects.filter(empresa__in=empresas)
            else:
                # Clientes só podem ver seus próprios tickets
                tickets_query = Ticket.objects.filter(
                    Q(empresa__in=empresas) & 
                    (Q(criado_por=request.user) | Q(atribuido_a=funcionario) | Q(atribuicoes__funcionario=funcionario))
                ).distinct()
            
            # Aplicar filtros se fornecidos
            if filtro_empresa:
                if funcionario.tem_acesso_empresa(get_object_or_404(Empresa, id=filtro_empresa)):
                    tickets_query = tickets_query.filter(empresa_id=filtro_empresa)
            
            if filtro_status:
                tickets_query = tickets_query.filter(status=filtro_status)
            
            if filtro_prioridade:
                tickets_query = tickets_query.filter(prioridade=filtro_prioridade)
            
            if filtro_tecnico:
                tickets_query = tickets_query.filter(atribuido_a_id=filtro_tecnico)
            
            if filtro_data_inicial:
                try:
                    data_inicial = datetime.strptime(filtro_data_inicial, '%Y-%m-%d').date()
                    tickets_query = tickets_query.filter(criado_em__date__gte=data_inicial)
                except ValueError:
                    pass  # Ignorar data inválida
            
            if filtro_data_final:
                try:
                    data_final = datetime.strptime(filtro_data_final, '%Y-%m-%d').date()
                    tickets_query = tickets_query.filter(criado_em__date__lte=data_final)
                except ValueError:
                    pass  # Ignorar data inválida
            
            if filtro_search:
                tickets_query = tickets_query.filter(
                    Q(titulo__icontains=filtro_search) | 
                    Q(descricao__icontains=filtro_search)
                )
            
            # Ordenação
            tickets_query = tickets_query.order_by('-criado_em')
            
            # Preparar dados para o relatório
            dados = []
            cabecalho = ['ID', 'Título', 'Empresa', 'Status', 'Prioridade', 'Atribuído Para', 'Criado Em', 'Atualizado Em']
            dados.append(cabecalho)
            
            # Função para obter o nome formatado de status e prioridade
            def get_status_nome(status):
                return dict(Ticket.STATUS_CHOICES).get(status, status)
            
            def get_prioridade_nome(prioridade):
                return dict(Ticket.PRIORIDADE_CHOICES).get(prioridade, prioridade)
            
            # Adicionar dados de tickets
            for ticket in tickets_query:
                atribuido_para = ''
                if ticket.atribuido_a:
                    atribuido_para = f"{ticket.atribuido_a.usuario.first_name} {ticket.atribuido_a.usuario.last_name}"
                
                linha = [
                    ticket.id,
                    ticket.titulo,
                    ticket.empresa.nome,
                    get_status_nome(ticket.status),
                    get_prioridade_nome(ticket.prioridade),
                    atribuido_para,
                    ticket.criado_em.strftime('%d/%m/%Y %H:%M'),
                    ticket.atualizado_em.strftime('%d/%m/%Y %H:%M')
                ]
                dados.append(linha)
            
            # Exportar baseado no formato solicitado
            if formato == 'csv':
                # Exportar para CSV
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename="relatorio_tickets.csv"'
                
                writer = csv.writer(response)
                for linha in dados:
                    writer.writerow(linha)
                
                return response
            
            elif formato == 'excel':
                try:
                    # Exportar para Excel
                    output = BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    worksheet = workbook.add_worksheet()
                    
                    # Formatar cabeçalho
                    header_format = workbook.add_format({
                        'bold': True,
                        'bg_color': '#343a40',
                        'font_color': 'white',  # Usando font_color em vez de color
                        'align': 'center',
                        'valign': 'vcenter',
                        'border': 1
                    })
                    
                    # Formatar células de dados
                    cell_format = workbook.add_format({
                        'border': 1
                    })
                    
                    # Escrever dados
                    for i, linha in enumerate(dados):
                        for j, valor in enumerate(linha):
                            if i == 0:  # Cabeçalho
                                worksheet.write(i, j, valor, header_format)
                            else:  # Dados
                                worksheet.write(i, j, valor, cell_format)
                    
                    # Ajustar largura das colunas
                    worksheet.set_column(0, 0, 5)   # ID
                    worksheet.set_column(1, 1, 40)  # Título
                    worksheet.set_column(2, 2, 20)  # Empresa
                    worksheet.set_column(3, 4, 15)  # Status, Prioridade
                    worksheet.set_column(5, 5, 25)  # Atribuído Para
                    worksheet.set_column(6, 7, 20)  # Datas
                    
                    workbook.close()
                    
                    # Preparar a resposta
                    output.seek(0)
                    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename="relatorio_tickets.xlsx"'
                    
                    return response
                except Exception as e:
                    # Em caso de erro, voltar para CSV como fallback
                    return HttpResponse(f"Erro ao gerar Excel: {str(e)}. Tente exportar como CSV.")
            
            elif formato == 'pdf':
                try:
                    # Exportar para PDF
                    response = HttpResponse(content_type='application/pdf')
                    response['Content-Disposition'] = 'attachment; filename="relatorio_tickets.pdf"'
                    
                    # Criar documento PDF
                    buffer = BytesIO()
                    doc = SimpleDocTemplate(buffer, pagesize=letter)
                    elements = []
                    
                    # Definir estilos
                    styles = getSampleStyleSheet()
                    title_style = styles['Heading1']
                    
                    # Adicionar título
                    elements.append(Paragraph("Relatório de Tickets", title_style))
                    elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
                    elements.append(Paragraph(" ", styles['Normal']))  # Espaço
                    
                    # Criar tabela
                    tabela = Table(dados)
                    
                    # Estilo da tabela
                    estilo_tabela = TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('ALIGN', (0, 0), (0, -1), 'CENTER'),  # ID centralizado
                        ('ALIGN', (3, 1), (4, -1), 'CENTER'),  # Status e Prioridade centralizados
                        ('ALIGN', (6, 1), (7, -1), 'CENTER'),  # Datas centralizadas
                        ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ])
                    
                    tabela.setStyle(estilo_tabela)
                    elements.append(tabela)
                    
                    # Construir PDF
                    doc.build(elements)
                    
                    # Retornar PDF
                    pdf = buffer.getvalue()
                    buffer.close()
                    response.write(pdf)
                    
                    return response
                except Exception as e:
                    # Em caso de erro, voltar para CSV como fallback
                    return HttpResponse(f"Erro ao gerar PDF: {str(e)}. Tente exportar como CSV.")
            
            # Formato inválido - usar CSV como padrão
            return HttpResponse("Formato não suportado. Use 'csv', 'excel', ou 'pdf'.")
        
        # Tipo de relatório não implementado
        return HttpResponse("Tipo de relatório não suportado")
        
    except Exception as e:
        # Capturar qualquer exceção e exibir uma mensagem de erro
        import traceback
        return HttpResponse(f"Erro ao gerar relatório: {str(e)}<br><pre>{traceback.format_exc()}</pre>")

# Views para gerenciamento de perfis de compartilhamento
@login_required
def perfis_compartilhamento_list(request):
    """Lista todos os perfis de compartilhamento disponíveis para o usuário."""
    user = request.user
    
    if user.is_superuser:
        perfis = PerfilCompartilhamento.objects.all()
    else:
        # Para usuários normais, mostrar apenas perfis de empresas às quais eles têm acesso
        funcionario = Funcionario.objects.filter(usuario=user).first()
        if funcionario:
            empresas = funcionario.empresas.all()
            perfis = PerfilCompartilhamento.objects.filter(empresa__in=empresas)
        else:
            perfis = PerfilCompartilhamento.objects.none()
    
    return render(request, 'tickets/perfis_compartilhamento_list.html', {'perfis': perfis})

@login_required
def perfil_compartilhamento_novo(request):
    """Cria um novo perfil de compartilhamento."""
    if request.method == 'POST':
        form = PerfilCompartilhamentoForm(request.POST, user=request.user)
        if form.is_valid():
            perfil = form.save(commit=False)
            perfil.criado_por = request.user
            perfil.save()
            messages.success(request, 'Perfil de compartilhamento criado com sucesso!')
            return redirect('tickets:perfis_compartilhamento_list')
    else:
        form = PerfilCompartilhamentoForm(user=request.user)
    
    return render(request, 'tickets/perfil_compartilhamento_form.html', {'form': form})

@login_required
def perfil_compartilhamento_editar(request, pk):
    """Edita um perfil de compartilhamento existente."""
    perfil = get_object_or_404(PerfilCompartilhamento, pk=pk)
    
    # Verificar permissões
    if not request.user.is_superuser:
        funcionario = Funcionario.objects.filter(usuario=request.user).first()
        if not funcionario or not funcionario.empresas.filter(id=perfil.empresa.id).exists():
            messages.error(request, 'Você não tem permissão para editar este perfil.')
            return redirect('tickets:perfis_compartilhamento_list')
    
    if request.method == 'POST':
        form = PerfilCompartilhamentoForm(request.POST, instance=perfil, user=request.user)
        if form.is_valid():
            perfil = form.save(commit=False)
            perfil.atualizado_por = request.user
            perfil.save()
            messages.success(request, 'Perfil de compartilhamento atualizado com sucesso!')
            return redirect('tickets:perfis_compartilhamento_list')
    else:
        form = PerfilCompartilhamentoForm(instance=perfil, user=request.user)
    
    return render(request, 'tickets/perfil_compartilhamento_form.html', {'form': form})

@login_required
def perfil_compartilhamento_excluir(request, pk):
    """Exclui um perfil de compartilhamento."""
    perfil = get_object_or_404(PerfilCompartilhamento, pk=pk)
    
    # Verificar permissões
    if not request.user.is_superuser:
        funcionario = Funcionario.objects.filter(usuario=request.user).first()
        if not funcionario or not funcionario.empresas.filter(id=perfil.empresa.id).exists():
            messages.error(request, 'Você não tem permissão para excluir este perfil.')
            return redirect('tickets:perfis_compartilhamento_list')
    
    if request.method == 'POST':
        perfil.delete()
        messages.success(request, 'Perfil de compartilhamento excluído com sucesso!')
        return redirect('tickets:perfis_compartilhamento_list')
    
    return render(request, 'tickets/perfil_compartilhamento_confirm_delete.html', {'perfil': perfil})

@login_required
def campos_perfil_compartilhamento_list(request, perfil_id):
    """Lista todos os campos de um perfil de compartilhamento."""
    perfil = get_object_or_404(PerfilCompartilhamento, pk=perfil_id)
    
    # Verificar permissões
    if not request.user.is_superuser:
        funcionario = Funcionario.objects.filter(usuario=request.user).first()
        if not funcionario or not funcionario.empresas.filter(id=perfil.empresa.id).exists():
            messages.error(request, 'Você não tem permissão para visualizar este perfil.')
            return redirect('tickets:perfis_compartilhamento_list')
    
    campos = CampoPerfilCompartilhamento.objects.filter(perfil=perfil).order_by('ordem')
    
    return render(request, 'tickets/campos_perfil_compartilhamento_list.html', {
        'perfil': perfil,
        'campos': campos
    })

@login_required
def campo_perfil_compartilhamento_novo(request, perfil_id):
    """Adiciona um novo campo a um perfil de compartilhamento."""
    perfil = get_object_or_404(PerfilCompartilhamento, pk=perfil_id)
    
    # Verificar permissões
    if not request.user.is_superuser:
        funcionario = Funcionario.objects.filter(usuario=request.user).first()
        if not funcionario or not funcionario.empresas.filter(id=perfil.empresa.id).exists():
            messages.error(request, 'Você não tem permissão para editar este perfil.')
            return redirect('tickets:perfis_compartilhamento_list')
    
    if request.method == 'POST':
        form = CampoPerfilCompartilhamentoForm(request.POST, user=request.user)
        if form.is_valid():
            campo = form.save(commit=False)
            campo.perfil = perfil
            campo.save()
            messages.success(request, 'Campo adicionado com sucesso!')
            return redirect('tickets:campos_perfil_compartilhamento_list', perfil_id=perfil.id)
    else:
        form = CampoPerfilCompartilhamentoForm(
            user=request.user,
            initial={'perfil': perfil}
        )
        # Definir queryset de campo_personalizado para mostrar apenas os da empresa do perfil
        form.fields['campo_personalizado'].queryset = CampoPersonalizado.objects.filter(empresa=perfil.empresa)
    
    return render(request, 'tickets/campo_perfil_compartilhamento_form.html', {
        'form': form,
        'perfil': perfil
    })

@login_required
def campo_perfil_compartilhamento_editar(request, pk):
    """Edita um campo de um perfil de compartilhamento."""
    campo = get_object_or_404(CampoPerfilCompartilhamento, pk=pk)
    perfil = campo.perfil
    
    # Verificar permissões
    if not request.user.is_superuser:
        funcionario = Funcionario.objects.filter(usuario=request.user).first()
        if not funcionario or not funcionario.empresas.filter(id=perfil.empresa.id).exists():
            messages.error(request, 'Você não tem permissão para editar este campo.')
            return redirect('tickets:perfis_compartilhamento_list')
    
    if request.method == 'POST':
        form = CampoPerfilCompartilhamentoForm(request.POST, instance=campo, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Campo atualizado com sucesso!')
            return redirect('tickets:campos_perfil_compartilhamento_list', perfil_id=perfil.id)
    else:
        form = CampoPerfilCompartilhamentoForm(instance=campo, user=request.user)
        # Definir queryset de campo_personalizado para mostrar apenas os da empresa do perfil
        form.fields['campo_personalizado'].queryset = CampoPersonalizado.objects.filter(empresa=perfil.empresa)
    
    return render(request, 'tickets/campo_perfil_compartilhamento_form.html', {
        'form': form,
        'perfil': perfil
    })

@login_required
def campo_perfil_compartilhamento_excluir(request, pk):
    """Exclui um campo de um perfil de compartilhamento."""
    campo = get_object_or_404(CampoPerfilCompartilhamento, pk=pk)
    perfil = campo.perfil
    
    # Verificar permissões
    if not request.user.is_superuser:
        funcionario = Funcionario.objects.filter(usuario=request.user).first()
        if not funcionario or not funcionario.empresas.filter(id=perfil.empresa.id).exists():
            messages.error(request, 'Você não tem permissão para excluir este campo.')
            return redirect('tickets:perfis_compartilhamento_list')
    
    if request.method == 'POST':
        campo.delete()
        messages.success(request, 'Campo excluído com sucesso!')
        return redirect('tickets:campos_perfil_compartilhamento_list', perfil_id=perfil.id)
    
    return render(request, 'tickets/campo_perfil_compartilhamento_confirm_delete.html', {
        'campo': campo,
        'perfil': perfil
    })

@login_required
def compartilhar_ticket_pdf(request, ticket_id):
    """Compartilha um ticket em formato PDF."""
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    
    # Verificar permissões
    if not pode_visualizar_ticket(request.user, ticket):
        messages.error(request, 'Você não tem permissão para visualizar este ticket.')
        return redirect('tickets:dashboard')
    
    if request.method == 'POST':
        form = CompartilharTicketForm(request.POST, ticket=ticket, user=request.user)
        if form.is_valid():
            perfil = form.cleaned_data['perfil']
            
            # Gerar PDF
            return gerar_pdf_ticket(request, ticket.id, perfil.id)
    else:
        form = CompartilharTicketForm(ticket=ticket, user=request.user)
    
    return render(request, 'tickets/compartilhar_ticket_form.html', {
        'form': form,
        'ticket': ticket
    })

@login_required
def gerar_pdf_ticket(request, ticket_id, perfil_id=None):
    """Gera um PDF com as informações do chamado de acordo com o perfil de compartilhamento."""
    try:
        ticket = Ticket.objects.get(id=ticket_id)
        if not pode_visualizar_ticket(request.user, ticket):
            messages.error(request, 'Você não tem permissão para visualizar este chamado.')
            return redirect('tickets:dashboard')
        
        empresa = ticket.empresa
        
        # Se perfil_id foi fornecido, busca o perfil
        if perfil_id:
            try:
                perfil = PerfilCompartilhamento.objects.get(id=perfil_id, empresa=empresa)
            except PerfilCompartilhamento.DoesNotExist:
                messages.error(request, 'Perfil de compartilhamento não encontrado.')
                return redirect('tickets:detalhe_ticket', ticket_id=ticket_id)
        else:
            # Perfil padrão (mostra tudo)
            perfil = None
        
        # Obter dados do chamado
        context = {
            'ticket': ticket,
            'empresa': empresa,
        }
        
        # Comentários
        if not perfil or perfil.incluir_comentarios:
            context['comentarios'] = ticket.comentarios.all().order_by('-criado_em')
        
        # Notas Técnicas
        if not perfil or perfil.incluir_notas_tecnicas:
            context['notas_tecnicas'] = ticket.notas_tecnicas.all().order_by('-criado_em')
        
        # Campos personalizados
        campos_personalizados = ValorCampoPersonalizado.objects.filter(ticket=ticket)
        context['campos_personalizados'] = campos_personalizados
        
        # Se tem perfil, filtra os campos conforme o perfil
        if perfil:
            context['campos_perfil'] = perfil.campos.all()
        else:
            # Lista todos os campos padrão + personalizados
            campos_padrao = [
                {'tipo_campo': 'titulo', 'nome_campo': 'Título'},
                {'tipo_campo': 'descricao', 'nome_campo': 'Descrição'},
                {'tipo_campo': 'status', 'nome_campo': 'Status'},
                {'tipo_campo': 'prioridade', 'nome_campo': 'Prioridade'},
                {'tipo_campo': 'categoria', 'nome_campo': 'Categoria'},
                {'tipo_campo': 'cliente', 'nome_campo': 'Cliente'},
                {'tipo_campo': 'atribuido_a', 'nome_campo': 'Atribuído a'},
                {'tipo_campo': 'criado_em', 'nome_campo': 'Criado em'},
                {'tipo_campo': 'atualizado_em', 'nome_campo': 'Atualizado em'},
            ]
            for campo in empresa.campospersonalizados.all():
                campos_padrao.append({
                    'tipo_campo': 'personalizado',
                    'nome_campo': campo.nome,
                    'campo_personalizado': campo
                })
            context['campos_perfil'] = campos_padrao
        
        # Histórico
        if not perfil or perfil.incluir_historico:
            context['historico'] = ticket.historico.all().order_by('-data_alteracao')
        
        # Renderiza o HTML
        html = render_to_string('tickets/chamado_pdf_template.html', context)
        
        # Gera o PDF
        pdf = HTML(string=html).write_pdf()
        
        # Retorna o PDF como resposta HTTP
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="chamado_{ticket.id}.pdf"'
        return response
    
    except Exception as e:
        messages.error(request, f'Erro ao gerar PDF: {str(e)}')
        return redirect('tickets:detalhe_ticket', ticket_id=ticket_id)

@login_required
def get_campos_personalizados(request):
    """AJAX view para obter campos personalizados de uma empresa."""
    empresa_id = request.GET.get('empresa_id')
    if empresa_id:
        campos = CampoPersonalizado.objects.filter(empresa_id=empresa_id).values('id', 'nome')
        return JsonResponse(list(campos), safe=False)
    return JsonResponse([], safe=False)

@login_required
def get_categorias_por_empresa(request):
    """API para obter categorias por empresa"""
    empresa_id = request.GET.get('empresa_id')
    categorias = []
    
    if empresa_id:
        try:
            # Verifica permissão
            if request.user.is_superuser:
                # Superusuários veem todas as categorias
                categorias = list(CategoriaChamado.objects.filter(
                    empresa_id=empresa_id,
                    ativo=True
                ).order_by('ordem', 'nome').values('id', 'nome', 'descricao', 'cor', 'icone'))
            else:
                funcionario = request.user.funcionarios.first()
                if not funcionario or not funcionario.empresas.filter(id=empresa_id).exists():
                    return JsonResponse({"error": "Você não tem acesso a esta empresa"}, status=403)
                
                # Obtém a empresa
                empresa = get_object_or_404(Empresa, id=empresa_id)
                
                # Obtém categorias permitidas de acordo com o tipo de funcionário
                categorias_permitidas = funcionario.get_categorias_permitidas(empresa=empresa)
                
                categorias = list(categorias_permitidas.values('id', 'nome', 'descricao', 'cor', 'icone'))
                
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    return JsonResponse({"categorias": categorias})

@login_required
def get_estatisticas_categorias(request):
    """API para obter estatísticas de tickets por categoria"""
    empresa_id = request.GET.get('empresa_id')
    estatisticas = []
    
    if empresa_id:
        try:
            # Verifica permissão
            if not request.user.is_superuser:
                funcionario = request.user.funcionarios.first()
                if not funcionario or not funcionario.empresas.filter(id=empresa_id).exists():
                    return JsonResponse({"error": "Você não tem acesso a esta empresa"}, status=403)
            
            # Obtém todas as categorias da empresa
            categorias = CategoriaChamado.objects.filter(
                empresa_id=empresa_id,
                ativo=True
            ).order_by('ordem', 'nome')
            
            # Para cada categoria, obtém estatísticas dos tickets
            for categoria in categorias:
                # Tickets totais da categoria
                total_tickets = Ticket.objects.filter(categoria=categoria).count()
                
                # Tickets em aberto (status = aberto ou em_andamento ou pendente)
                tickets_abertos = Ticket.objects.filter(
                    categoria=categoria,
                    status__in=['aberto', 'em_andamento', 'pendente']
                ).count()
                
                # Tickets fechados (status = resolvido ou fechado)
                tickets_fechados = Ticket.objects.filter(
                    categoria=categoria,
                    status__in=['resolvido', 'fechado']
                ).count()
                
                estatisticas.append({
                    'id': categoria.id,
                    'nome': categoria.nome,
                    'cor': categoria.cor,
                    'icone': categoria.icone,
                    'total': total_tickets,
                    'abertos': tickets_abertos,
                    'fechados': tickets_fechados,
                    'porcentagem_fechados': round((tickets_fechados / total_tickets) * 100) if total_tickets > 0 else 0
                })
                
            # Adiciona estatística para "Sem categoria"
            tickets_sem_categoria = Ticket.objects.filter(
                empresa_id=empresa_id,
                categoria__isnull=True
            )
            
            total_sem_categoria = tickets_sem_categoria.count()
            
            if total_sem_categoria > 0:
                tickets_abertos_sem_categoria = tickets_sem_categoria.filter(
                    status__in=['aberto', 'em_andamento', 'pendente']
                ).count()
                
                tickets_fechados_sem_categoria = tickets_sem_categoria.filter(
                    status__in=['resolvido', 'fechado']
                ).count()
                
                estatisticas.append({
                    'id': None,
                    'nome': 'Sem categoria',
                    'cor': 'secondary',
                    'icone': 'fa-question-circle',
                    'total': total_sem_categoria,
                    'abertos': tickets_abertos_sem_categoria,
                    'fechados': tickets_fechados_sem_categoria,
                    'porcentagem_fechados': round((tickets_fechados_sem_categoria / total_sem_categoria) * 100) if total_sem_categoria > 0 else 0
                })
                
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    return JsonResponse({"estatisticas": estatisticas})

def logout_success(request):
    """
    Exibe uma página de logout bem-sucedido.
    Esta view não requer autenticação e deve funcionar
    mesmo após o usuário ter feito logout.
    """
    # Log para debug
    logger.info("Página de logout_success acessada")
    
    # HTML direto para evitar quaisquer problemas de template
    html_content = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Logout Realizado</title>
        <!-- Script para aplicar o tema antes do carregamento da página -->
        <script>
            // Aplicar tema imediatamente para evitar piscar
            (function() {
                const savedTheme = localStorage.getItem('theme');
                const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
                const theme = savedTheme || (prefersDark ? 'dark' : 'light');
                
                // Aplicar ao documento antes mesmo de carregar
                document.documentElement.setAttribute('data-bs-theme', theme);
                
                // Definir estilo inicial para o body
                if (theme === 'dark') {
                    document.documentElement.style.backgroundColor = '#212529';
                    document.documentElement.style.color = '#dee2e6';
                }
            })();
        </script>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
        <style>
            body {
                transition: background-color 0.3s ease, color 0.3s ease;
                /* Definir cores iniciais baseadas no tema para evitar piscar */
                background-color: var(--bs-body-bg);
                color: var(--bs-body-color);
            }
        </style>
    </head>
    <body>
        <div class="container mt-5">
            <div class="row justify-content-center">
                <div class="col-md-6">
                    <div class="card shadow-lg border-0">
                        <div class="card-body text-center p-5">
                            <div class="mb-4">
                                <i class="fas fa-check-circle text-success" style="font-size: 4rem;"></i>
                            </div>
                            <h2 class="mb-4">Você saiu do sistema com sucesso!</h2>
                            <p class="lead mb-4">Obrigado por utilizar os serviços da Técnico Litoral Central de Suporte.</p>
                            <div class="d-grid gap-2 col-md-8 mx-auto">
                                <a href="/" class="btn btn-primary btn-lg">
                                    <i class="fas fa-home me-2"></i> Página Inicial
                                </a>
                                <a href="/login/" class="btn btn-outline-primary btn-lg">
                                    <i class="fas fa-sign-in-alt me-2"></i> Entrar Novamente
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """
    
    return HttpResponse(html_content)

# ----- Views Painel Administrativo de Empresas -----

@login_required
def empresa_admin_dashboard(request):
    """Dashboard administrativo para empresas"""
    try:
        # Verificar se o usuário é admin de uma empresa
        funcionario = get_object_or_404(Funcionario, usuario=request.user)
        if not funcionario.is_admin():
            messages.error(request, "Você não tem permissão para acessar esta área.")
            return redirect('tickets:dashboard')
        
        # Pegar a empresa do funcionário (assumindo que um admin gerencia apenas uma empresa)
        empresas = funcionario.empresas.all()
        if not empresas.exists():
            messages.error(request, "Você não está associado a nenhuma empresa.")
            return redirect('tickets:dashboard')
        
        empresa = empresas.first()  # Pega a primeira empresa associada
        
        # Obter configurações da empresa
        try:
            config = EmpresaConfig.objects.get(empresa=empresa)
        except EmpresaConfig.DoesNotExist:
            # Criar configuração padrão se não existir
            config = EmpresaConfig(empresa=empresa)
            config.save()
        
        # Estatísticas para o dashboard
        total_usuarios = funcionario.empresas.first().funcionarios.count()
        limite_usuarios = config.limite_usuarios
        porcentagem_usuarios = (total_usuarios / limite_usuarios) * 100 if limite_usuarios > 0 else 0
        
        total_tickets = Ticket.objects.filter(empresa=empresa).count()
        tickets_abertos = Ticket.objects.filter(empresa=empresa, status__in=['aberto', 'em_andamento', 'pendente']).count()
        tickets_fechados = Ticket.objects.filter(empresa=empresa, status__in=['resolvido', 'fechado']).count()
        
        context = {
            'empresa': empresa,
            'config': config,
            'total_usuarios': total_usuarios,
            'limite_usuarios': limite_usuarios,
            'porcentagem_usuarios': porcentagem_usuarios,
            'total_tickets': total_tickets,
            'tickets_abertos': tickets_abertos,
            'tickets_fechados': tickets_fechados,
            'pode_criar_mais': config.pode_criar_mais_usuarios(),
        }
        
        return render(request, 'tickets/empresa_admin/dashboard.html', context)
    
    except Exception as e:
        logger.error(f"Erro no dashboard administrativo: {str(e)}")
        messages.error(request, "Ocorreu um erro ao carregar o dashboard administrativo.")
        return redirect('tickets:dashboard')

@login_required
def empresa_admin_usuarios(request):
    """Gerenciamento de usuários para administradores de empresa"""
    try:
        # Verificar se o usuário é admin de uma empresa
        funcionario = get_object_or_404(Funcionario, usuario=request.user)
        if not funcionario.is_admin():
            messages.error(request, "Você não tem permissão para acessar esta área.")
            return redirect('tickets:dashboard')
        
        # Pegar a empresa do funcionário (assumindo que um admin gerencia apenas uma empresa)
        empresas = funcionario.empresas.all()
        if not empresas.exists():
            messages.error(request, "Você não está associado a nenhuma empresa.")
            return redirect('tickets:dashboard')
        
        empresa = empresas.first()  # Pega a primeira empresa associada
        
        # Obter configurações da empresa
        try:
            config = EmpresaConfig.objects.get(empresa=empresa)
        except EmpresaConfig.DoesNotExist:
            # Criar configuração padrão se não existir
            config = EmpresaConfig(empresa=empresa)
            config.save()
        
        # Obter todos os funcionários da empresa
        funcionarios = Funcionario.objects.filter(empresas=empresa).order_by('-tipo', 'usuario__username')
        
        context = {
            'empresa': empresa,
            'config': config,
            'funcionarios': funcionarios,
            'total_usuarios': funcionarios.count(),
            'limite_usuarios': config.limite_usuarios,
            'pode_criar_mais': config.pode_criar_mais_usuarios(),
        }
        
        return render(request, 'tickets/empresa_admin/usuarios.html', context)
    
    except Exception as e:
        logger.error(f"Erro no gerenciamento de usuários da empresa: {str(e)}")
        messages.error(request, "Ocorreu um erro ao carregar a lista de usuários.")
        return redirect('tickets:dashboard')

@login_required
def empresa_admin_criar_usuario(request):
    # Check if user is company admin
    try:
        funcionario = Funcionario.objects.filter(
            usuario=request.user,
            tipo='admin'
        ).first()
        
        if not funcionario:
            messages.error(request, 'Você não tem permissão para acessar esta página.')
            return redirect('tickets:dashboard')
        
        # Get company associated with the admin
        empresa = funcionario.empresas.first()
        
        if not empresa:
            messages.error(request, 'Você não está associado a nenhuma empresa como administrador.')
            return redirect('tickets:dashboard')
        
        # Check if company can create more users
        try:
            config = EmpresaConfig.objects.get(empresa=empresa)
            usuarios_atuais = Funcionario.objects.filter(empresas=empresa).count()
            pode_criar_mais = usuarios_atuais < config.limite_usuarios
            config.pode_criar_mais_usuarios = pode_criar_mais
            
            if not pode_criar_mais:
                messages.warning(request, f'Sua empresa atingiu o limite de {config.limite_usuarios} usuários. Entre em contato com o administrador do sistema para aumentar seu limite.')
                return redirect('tickets:empresa_admin_usuarios')
        except EmpresaConfig.DoesNotExist:
            config = None
            messages.warning(request, 'Configuração da empresa não encontrada.')
        
        if request.method == 'POST':
            # Use UserCreationForm to handle password validation
            user_form = UserForm(request.POST)
            funcionario_form = FuncionarioForm(request.POST, user=request.user, criacao_usuario=True)
            
            # Explicitly set the initial queryset to only allow the admin's company
            funcionario_form.fields['empresas'].queryset = Empresa.objects.filter(pk=empresa.pk)
            funcionario_form.fields['empresas'].initial = [empresa]
            funcionario_form.fields['empresas'].disabled = True
            
            if user_form.is_valid() and funcionario_form.is_valid():
                try:
                    # Create the user
                    novo_usuario = user_form.save(commit=True)
                    
                    # Create the employee associating with the company
                    novo_funcionario = funcionario_form.save(commit=False)
                    novo_funcionario.usuario = novo_usuario
                    novo_funcionario.save()
                    
                    # Clear and add only the admin's company to the employee
                    novo_funcionario.empresas.clear()
                    novo_funcionario.empresas.add(empresa)
                    
                    # Create default notification preferences for the new user
                    try:
                        PreferenciasNotificacao.objects.create(usuario=novo_usuario)
                    except Exception as e:
                        logger.warning(f"Erro ao criar preferências de notificação para o usuário {novo_usuario.username}: {str(e)}")
                    
                    messages.success(request, f'Usuário {novo_usuario.username} criado com sucesso!')
                    return redirect('tickets:empresa_admin_usuarios')
                except Exception as e:
                    messages.error(request, f'Erro ao criar usuário: {str(e)}')
                    logger.error(f'Error creating user: {str(e)}')
                    return redirect('tickets:empresa_admin_usuarios')
            else:
                # Add form errors to messages for better visibility
                for field, errors in user_form.errors.items():
                    for error in errors:
                        messages.error(request, f'Erro em {field}: {error}')
                
                for field, errors in funcionario_form.errors.items():
                    for error in errors:
                        messages.error(request, f'Erro em {field}: {error}')
        else:
            user_form = UserForm()
            funcionario_form = FuncionarioForm(user=request.user, criacao_usuario=True)
            
            # Explicitly set the queryset to only allow the admin's company
            funcionario_form.fields['empresas'].queryset = Empresa.objects.filter(pk=empresa.pk)
            funcionario_form.fields['empresas'].initial = [empresa]
            funcionario_form.fields['empresas'].disabled = True
        
        context = {
            'user_form': user_form,
            'funcionario_form': funcionario_form,
            'empresa': empresa,
            'config': config,
        }
        
        return render(request, 'tickets/empresa_admin/criar_usuario.html', context)
        
    except Exception as e:
        messages.error(request, f'Erro ao acessar a página: {str(e)}')
        logger.error(f'Error accessing empresa_admin_criar_usuario: {str(e)}')
        return redirect('tickets:dashboard')

@login_required
def empresa_admin_editar_usuario(request, funcionario_id):
    """Editar usuário existente da empresa"""
    try:
        # Verificar se o usuário é admin de uma empresa
        admin_funcionario = get_object_or_404(Funcionario, usuario=request.user)
        if not admin_funcionario.is_admin():
            messages.error(request, "Você não tem permissão para acessar esta área.")
            return redirect('tickets:dashboard')
        
        # Pegar a empresa do funcionário admin
        empresa = admin_funcionario.empresas.first()
        
        # Verificar se o funcionário a ser editado pertence à empresa
        funcionario = get_object_or_404(Funcionario, id=funcionario_id, empresas=empresa)
        usuario = funcionario.usuario
        
        if request.method == 'POST':
            # Não permitimos alterar a senha aqui
            from django import forms as django_forms
            
            class UserEditForm(django_forms.ModelForm):
                class Meta:
                    model = User
                    fields = ['first_name', 'last_name', 'email']
            
            usuario_form = UserEditForm(request.POST, instance=usuario)
            
            # Usamos criacao_usuario=False para manter o campo usuario no formulário
            # e passamos o instance para que o campo seja preenchido automaticamente
            funcionario_form = FuncionarioForm(
                request.POST, 
                instance=funcionario, 
                user=request.user,
                criacao_usuario=False  # Não é criação, é edição
            )
            
            # Limitar visibilidade apenas à empresa do admin ao processar o formulário
            funcionario_form.fields['empresas'].queryset = admin_funcionario.empresas.all()
            funcionario_form.fields['empresas'].disabled = True  # Desativar a edição do campo
            
            # Definir explicitamente o usuário no campo, já que conhecemos o usuário associado
            funcionario_form.fields['usuario'].initial = usuario.id
            funcionario_form.fields['usuario'].disabled = True  # Desativar edição do usuário
            
            if usuario_form.is_valid() and funcionario_form.is_valid():
                try:
                    usuario = usuario_form.save()
                    
                    funcionario = funcionario_form.save(commit=False)
                    funcionario.usuario = usuario  # Garantir que o usuário seja mantido
                    funcionario.save()
                    
                    # Garantir que a empresa do admin esteja associada ao funcionário
                    if not funcionario.empresas.filter(id=empresa.id).exists():
                        funcionario.empresas.add(empresa)
                    
                    messages.success(request, f"Usuário {usuario.username} atualizado com sucesso!")
                    return redirect('tickets:empresa_admin_usuarios')
                except Exception as e:
                    logger.error(f"Erro ao salvar usuário: {str(e)}")
                    messages.error(request, f"Erro ao salvar usuário: {str(e)}")
            else:
                # Adicionar erros dos formulários às mensagens para melhor visibilidade
                for field, errors in usuario_form.errors.items():
                    for error in errors:
                        messages.error(request, f'Erro em {field}: {error}')
                
                for field, errors in funcionario_form.errors.items():
                    for error in errors:
                        messages.error(request, f'Erro em {field}: {error}')
        else:
            # Formulário para edição de usuário
            from django import forms as django_forms
            
            class UserEditForm(django_forms.ModelForm):
                class Meta:
                    model = User
                    fields = ['first_name', 'last_name', 'email']
            
            usuario_form = UserEditForm(instance=usuario)
            
            # Na edição, precisamos manter o campo usuário e pré-selecioná-lo
            funcionario_form = FuncionarioForm(
                instance=funcionario, 
                user=request.user, 
                criacao_usuario=False  # Não é criação, é edição
            )
            
            # Definir explicitamente o usuário no campo, já que conhecemos o usuário associado
            funcionario_form.fields['usuario'].initial = usuario.id
            funcionario_form.fields['usuario'].disabled = True  # Desativar edição do usuário
            
            # Limitar visibilidade apenas à empresa do admin
            funcionario_form.fields['empresas'].queryset = admin_funcionario.empresas.all()
            funcionario_form.fields['empresas'].disabled = True  # Desativar a edição do campo
        
        context = {
            'empresa': empresa,
            'usuario_form': usuario_form,
            'funcionario_form': funcionario_form,
            'funcionario': funcionario,
            'usuario': usuario,
        }
        
        return render(request, 'tickets/empresa_admin/editar_usuario.html', context)
    
    except Exception as e:
        logger.error(f"Erro ao editar usuário da empresa: {str(e)}")
        messages.error(request, "Ocorreu um erro ao editar o usuário.")
        return redirect('tickets:empresa_admin_usuarios')

@login_required
def empresa_admin_config(request):
    """Configurações da empresa para administradores"""
    try:
        # Verificar se o usuário é admin de uma empresa
        funcionario = get_object_or_404(Funcionario, usuario=request.user)
        if not funcionario.is_admin():
            messages.error(request, "Você não tem permissão para acessar esta área.")
            return redirect('tickets:dashboard')
        
        # Pegar a empresa do funcionário
        empresa = funcionario.empresas.first()
        
        # Obter configurações da empresa
        try:
            config = EmpresaConfig.objects.get(empresa=empresa)
        except EmpresaConfig.DoesNotExist:
            # Criar configuração padrão se não existir
            config = EmpresaConfig(empresa=empresa)
            config.save()
        
        # Contar o número de usuários da empresa
        usuarios_criados = Funcionario.objects.filter(empresas=empresa).count()
        config.usuarios_criados = usuarios_criados
        
        # Calcular o percentual de usuários (evita usar os filtros mul e div no template)
        if config.limite_usuarios > 0:
            config.percentual_usuarios = (usuarios_criados * 100) / config.limite_usuarios
        else:
            config.percentual_usuarios = 0
        
        # Se há um formulário de empresa sendo enviado
        if request.method == 'POST':
            # Manter os valores originais do nome e cnpj no POST
            post_data = request.POST.copy()
            post_data['nome'] = empresa.nome
            post_data['cnpj'] = empresa.cnpj
            
            empresa_form = EmpresaForm(post_data, instance=empresa)
            if empresa_form.is_valid():
                empresa_form.save()
                messages.success(request, "Informações da empresa atualizadas com sucesso!")
                return redirect('tickets:empresa_admin_config')
        else:
            empresa_form = EmpresaForm(instance=empresa)
            
        # Tornar os campos somente leitura em vez de desativados
        empresa_form.fields['nome'].widget.attrs['readonly'] = True
        empresa_form.fields['cnpj'].widget.attrs['readonly'] = True
        
        context = {
            'empresa': empresa,
            'config': config,
            'empresa_form': empresa_form,
        }
        
        return render(request, 'tickets/empresa_admin/configuracoes.html', context)
    
    except Exception as e:
        logger.error(f"Erro nas configurações da empresa: {str(e)}")
        messages.error(request, "Ocorreu um erro ao carregar as configurações.")
        return redirect('tickets:dashboard')

# ----- Views para Gerenciar Categorias -----

@login_required
def empresa_admin_categorias(request):
    """Listar categorias de chamados da empresa"""
    try:
        # Verificar se o usuário é admin de uma empresa
        funcionario = get_object_or_404(Funcionario, usuario=request.user)
        if not funcionario.is_admin():
            messages.error(request, "Você não tem permissão para acessar esta área.")
            return redirect('tickets:dashboard')
        
        # Pegar a empresa do funcionário
        empresa = funcionario.empresas.first()
        
        # Obter configurações da empresa
        try:
            config = EmpresaConfig.objects.get(empresa=empresa)
        except EmpresaConfig.DoesNotExist:
            # Criar configuração padrão se não existir
            config = EmpresaConfig(empresa=empresa)
            config.save()
        
        # Verificar se a empresa pode criar categorias
        if not config.pode_criar_categorias:
            messages.error(request, "Sua empresa não tem permissão para gerenciar categorias de chamados.")
            return redirect('tickets:empresa_admin_dashboard')
        
        # Obter todas as categorias da empresa
        categorias = CategoriaChamado.objects.filter(
            empresa=empresa
        ).order_by('ordem', 'nome')
        
        context = {
            'empresa': empresa,
            'config': config,
            'categorias': categorias,
        }
        
        return render(request, 'tickets/empresa_admin/categorias_list.html', context)
    
    except Exception as e:
        logger.error(f"Erro ao listar categorias: {str(e)}")
        messages.error(request, "Ocorreu um erro ao listar as categorias.")
        return redirect('tickets:empresa_admin_dashboard')

@login_required
def empresa_admin_criar_categoria(request):
    """Criar nova categoria de chamados"""
    try:
        # Verificar se o usuário é admin de uma empresa
        funcionario = get_object_or_404(Funcionario, usuario=request.user)
        if not funcionario.is_admin():
            messages.error(request, "Você não tem permissão para acessar esta área.")
            return redirect('tickets:dashboard')
        
        # Pegar a empresa do funcionário
        empresa = funcionario.empresas.first()
        
        # Obter configurações da empresa
        try:
            config = EmpresaConfig.objects.get(empresa=empresa)
        except EmpresaConfig.DoesNotExist:
            # Criar configuração padrão se não existir
            config = EmpresaConfig(empresa=empresa)
            config.save()
        
        # Verificar se a empresa pode criar categorias
        if not config.pode_criar_categorias:
            messages.error(request, "Sua empresa não tem permissão para criar categorias de chamados.")
            return redirect('tickets:empresa_admin_categorias')
        
        if request.method == 'POST':
            form = CategoriaChamadoForm(request.POST)
            if form.is_valid():
                categoria = form.save(commit=False)
                categoria.empresa = empresa
                
                # Garantir que os campos estejam preenchidos
                if not categoria.cor:
                    categoria.cor = 'primary'
                
                # O campo icone já está tratado no clean_icone do CategoriaChamadoForm
                
                categoria.save()
                messages.success(request, f"Categoria '{categoria.nome}' criada com sucesso!")
                return redirect('tickets:empresa_admin_categorias')
        else:
            # Valores padrão para o formulário inicial
            form = CategoriaChamadoForm(initial={
                'cor': 'primary',
                'icone': 'fa-ticket-alt',
                'ordem': 0,
                'ativo': True
            })
        
        context = {
            'empresa': empresa,
            'form': form,
            'config': config,
        }
        
        return render(request, 'tickets/empresa_admin/categoria_form.html', context)
    
    except Exception as e:
        logger.error(f"Erro ao criar categoria: {str(e)}")
        messages.error(request, "Ocorreu um erro ao criar a categoria.")
        return redirect('tickets:empresa_admin_categorias')

@login_required
def empresa_admin_editar_categoria(request, categoria_id):
    """Editar categoria de chamados"""
    try:
        # Verificar se o usuário é admin de uma empresa
        funcionario = get_object_or_404(Funcionario, usuario=request.user)
        if not funcionario.is_admin():
            messages.error(request, "Você não tem permissão para acessar esta área.")
            return redirect('tickets:dashboard')
        
        # Pegar a empresa do funcionário
        empresa = funcionario.empresas.first()
        
        # Obter configurações da empresa
        try:
            config = EmpresaConfig.objects.get(empresa=empresa)
        except EmpresaConfig.DoesNotExist:
            # Criar configuração padrão se não existir
            config = EmpresaConfig(empresa=empresa)
            config.save()
        
        # Verificar se a empresa pode criar categorias
        if not config.pode_criar_categorias:
            messages.error(request, "Sua empresa não tem permissão para editar categorias de chamados.")
            return redirect('tickets:empresa_admin_categorias')
        
        # Obter a categoria e verificar se pertence à empresa do usuário
        categoria = get_object_or_404(CategoriaChamado, id=categoria_id)
        if categoria.empresa != empresa:
            messages.error(request, "Você não tem permissão para editar esta categoria.")
            return redirect('tickets:empresa_admin_categorias')
        
        if request.method == 'POST':
            form = CategoriaChamadoForm(request.POST, instance=categoria)
            if form.is_valid():
                categoria_atualizada = form.save(commit=False)
                
                # Garantir que os campos estejam preenchidos
                if not categoria_atualizada.cor:
                    categoria_atualizada.cor = 'primary'
                
                # O campo icone já está tratado no clean_icone do CategoriaChamadoForm
                
                categoria_atualizada.save()
                messages.success(request, f"Categoria '{categoria.nome}' atualizada com sucesso!")
                return redirect('tickets:empresa_admin_categorias')
        else:
            # Preparar dados iniciais se o ícone não estiver formatado corretamente
            if categoria.icone and not categoria.icone.startswith('fa-'):
                categoria.icone = f"fa-{categoria.icone}"
            elif not categoria.icone:
                categoria.icone = "fa-ticket-alt"
                
            form = CategoriaChamadoForm(instance=categoria)
        
        context = {
            'empresa': empresa,
            'form': form,
            'categoria': categoria,
            'config': config,
            'editando': True,
        }
        
        return render(request, 'tickets/empresa_admin/categoria_form.html', context)
    
    except Exception as e:
        logger.error(f"Erro ao editar categoria: {str(e)}")
        messages.error(request, "Ocorreu um erro ao editar a categoria.")
        return redirect('tickets:empresa_admin_categorias')

@login_required
def empresa_admin_excluir_categoria(request, categoria_id):
    """Excluir categoria de chamados"""
    try:
        # Verificar se o usuário é admin de uma empresa
        funcionario = get_object_or_404(Funcionario, usuario=request.user)
        if not funcionario.is_admin():
            messages.error(request, "Você não tem permissão para acessar esta área.")
            return redirect('tickets:dashboard')
        
        # Pegar a empresa do funcionário
        empresa = funcionario.empresas.first()
        
        # Obter configurações da empresa
        try:
            config = EmpresaConfig.objects.get(empresa=empresa)
        except EmpresaConfig.DoesNotExist:
            # Criar configuração padrão se não existir
            config = EmpresaConfig(empresa=empresa)
            config.save()
        
        # Verificar se a empresa pode criar categorias
        if not config.pode_criar_categorias:
            messages.error(request, "Sua empresa não tem permissão para excluir categorias de chamados.")
            return redirect('tickets:empresa_admin_categorias')
        
        # Obter a categoria e verificar se pertence à empresa do usuário
        categoria = get_object_or_404(CategoriaChamado, id=categoria_id)
        if categoria.empresa != empresa:
            messages.error(request, "Você não tem permissão para excluir esta categoria.")
            return redirect('tickets:empresa_admin_categorias')
        
        # Verificar se existem tickets vinculados a esta categoria
        tickets_count = Ticket.objects.filter(categoria=categoria).count()
        
        if request.method == 'POST':
            nome_categoria = categoria.nome
            
            if tickets_count > 0 and 'confirm_delete' in request.POST:
                # Atualizar tickets para remover a referência à categoria
                Ticket.objects.filter(categoria=categoria).update(categoria=None)
                categoria.delete()
                messages.success(request, f"Categoria '{nome_categoria}' excluída com sucesso! {tickets_count} chamados foram desvinculados da categoria.")
                return redirect('tickets:empresa_admin_categorias')
            elif tickets_count == 0:
                categoria.delete()
                messages.success(request, f"Categoria '{nome_categoria}' excluída com sucesso!")
                return redirect('tickets:empresa_admin_categorias')
        
        context = {
            'empresa': empresa,
            'categoria': categoria,
            'tickets_count': tickets_count,
            'config': config,
        }
        
        return render(request, 'tickets/empresa_admin/categoria_excluir.html', context)
    
    except Exception as e:
        logger.error(f"Erro ao excluir categoria: {str(e)}")
        messages.error(request, "Ocorreu um erro ao excluir a categoria.")
        return redirect('tickets:empresa_admin_categorias')

@login_required
def gerenciar_notificacoes(request):
    """
    Permite ao usuário gerenciar suas preferências de notificação
    """
    try:
        # Tenta obter as preferências do usuário
        preferencias, created = PreferenciasNotificacao.objects.get_or_create(usuario=request.user)
        
        if request.method == 'POST':
            form = PreferenciasNotificacaoForm(request.POST, instance=preferencias)
            if form.is_valid():
                form.save()
                messages.success(request, 'Suas preferências de notificação foram atualizadas com sucesso!')
                return redirect('tickets:dashboard')
        else:
            form = PreferenciasNotificacaoForm(instance=preferencias)
            
        context = {
            'form': form,
            'title': 'Gerenciar Notificações',
        }
        
        return render(request, 'tickets/gerenciar_notificacoes.html', context)
    except Exception as e:
        messages.error(request, f'Ocorreu um erro ao gerenciar suas notificações: {str(e)}')
        return redirect('tickets:dashboard')

@login_required
def excluir_ticket(request, ticket_id):
    """Excluir um ticket (apenas para administradores)"""
    try:
        ticket = get_object_or_404(Ticket, id=ticket_id)
        
        # Verificar permissões (apenas superuser ou admin)
        is_admin = False
        if not request.user.is_superuser:
            funcionario = Funcionario.objects.filter(usuario=request.user, tipo='admin').first()
            if not funcionario:
                messages.error(request, 'Apenas administradores podem excluir chamados.')
                return redirect('tickets:detalhe_ticket', ticket_id=ticket_id)
            
            # Verificar se o funcionário admin tem acesso à empresa do ticket
            if not funcionario.empresas.filter(id=ticket.empresa.id).exists():
                messages.error(request, 'Você não tem acesso a esta empresa.')
                return redirect('tickets:dashboard')
            
            is_admin = True
        
        # Verificar método da requisição (apenas POST para segurança)
        if request.method != 'POST':
            messages.error(request, 'Método não permitido.')
            return redirect('tickets:detalhe_ticket', ticket_id=ticket_id)
            
        # Registrar informações para histórico antes de excluir
        ticket_info = {
            'id': ticket.id,
            'titulo': ticket.titulo,
            'empresa': ticket.empresa.nome,
            'categoria': ticket.categoria.nome if ticket.categoria else 'Sem categoria',
            'status': ticket.status,
            'prioridade': ticket.prioridade,
            'data_criacao': ticket.criado_em.strftime('%d/%m/%Y %H:%M'),
            'criado_por': ticket.criado_por.get_full_name() or ticket.criado_por.username
        }
        
        # Criar uma cópia do registro de histórico em outra tabela ou arquivo para futura referência
        # Idealmente, em sistemas reais, os tickets seriam apenas marcados como "excluídos" 
        # mas manteriam as informações no banco de dados para referência
        try:
            # Registrar a exclusão no histórico do sistema (log global)
            logger.info(f"Ticket #{ticket.id} excluído por {request.user.username} - {json.dumps(ticket_info)}")
            
            # Se você tiver uma tabela de logs global, poderia registrar aqui
            # LogSistema.objects.create(...)
            
            messages.success(request, f'Chamado #{ticket.id} excluído com sucesso!')
            
            # Excluir o ticket
            ticket.delete()
            
            return redirect('tickets:dashboard')
        except Exception as e:
            logger.error(f"Erro ao excluir ticket: {str(e)}")
            messages.error(request, f'Erro ao excluir chamado: {str(e)}')
            return redirect('tickets:detalhe_ticket', ticket_id=ticket_id)
            
    except Exception as e:
        logger.error(f"Erro ao acessar exclusão de ticket: {str(e)}")
        messages.error(request, 'Ocorreu um erro ao tentar excluir o chamado.')
        return redirect('tickets:dashboard')

# ----- Views para Gerenciar Permissões de Categorias -----

@login_required
@admin_permission_required
def gerenciar_permissoes_categoria(request):
    """
    View para gerenciar as permissões de categorias dos funcionários.
    Apenas usuários administradores podem acessar esta página.
    """
    logger.info("**** INÍCIO FUNÇÃO gerenciar_permissoes_categoria (CORRIGIDA FINAL) ****")
    
    try:
        # Obtém apenas as empresas às quais o usuário tem acesso
        if request.user.is_superuser:
            # Superusuários veem todas as empresas
            empresas = Empresa.objects.all().order_by('nome')
        else:
            # Funcionários administrativos veem apenas as empresas associadas a eles
            funcionario = Funcionario.objects.filter(usuario=request.user).first()
            if funcionario and funcionario.is_admin():
                empresas = funcionario.empresas.all().order_by('nome')
            else:
                empresas = Empresa.objects.none()
        
        empresa_id = request.GET.get('empresa')
        empresa_selecionada = None
        funcionarios_dados = []
        
        # Se houver apenas uma empresa, seleciona-a automaticamente
        if not empresa_id and empresas.count() == 1:
            empresa_id = str(empresas.first().id)
        
        # Se uma empresa foi selecionada
        if empresa_id:
            # Para superusuários, permite acessar qualquer empresa
            if request.user.is_superuser:
                empresa_selecionada = get_object_or_404(Empresa, id=empresa_id)
            else:
                # Para funcionários normais, verifica se tem acesso à empresa
                empresa_selecionada = get_object_or_404(empresas, id=empresa_id)
            
            # Usa SQL direto para garantir que todos os funcionários são carregados
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        f.id, f.tipo, 
                        u.username, u.first_name, u.last_name, u.email
                    FROM 
                        tickets_funcionario f
                    JOIN 
                        auth_user u ON f.usuario_id = u.id
                    JOIN 
                        tickets_funcionario_empresas fe ON f.id = fe.funcionario_id
                    WHERE 
                        fe.empresa_id = %s
                    ORDER BY
                        u.username
                """, [empresa_selecionada.id])
                
                funcionarios_raw = cursor.fetchall()
            
            # Para cada funcionário, preparar os dados para exibição
            for func_row in funcionarios_raw:
                func_id, tipo, username, first_name, last_name, email = func_row
                
                # Contar categorias permitidas
                categorias_count = CategoriaPermissao.objects.filter(
                    funcionario_id=func_id,
                    categoria__empresa=empresa_selecionada
                ).count()
                
                # Criar dados do funcionário para exibição
                funcionario_data = {
                    'id': func_id,
                    'tipo': tipo,
                    'tipo_display': dict(Funcionario.TIPO_CHOICES).get(tipo, tipo),
                    'username': username,
                    'first_name': first_name or '',
                    'last_name': last_name or '',
                    'email': email or '',
                    'categorias_count': categorias_count
                }
                
                funcionarios_dados.append(funcionario_data)
        
        context = {
            'empresas': empresas,
            'empresa_selecionada': empresa_selecionada,
            'funcionarios_dados': funcionarios_dados,
        }
        
        return render(request, 'tickets/admin/permissoes_categoria.html', context)
        
    except Exception as e:
        logger.exception(f"Erro ao gerenciar permissões de categoria: {str(e)}")
        messages.error(request, f"Ocorreu um erro ao gerenciar permissões: {str(e)}")
        return redirect('tickets:dashboard')

@login_required
@admin_permission_required
def editar_permissoes_usuario(request, funcionario_id):
    """
    View para editar as permissões de categorias de um funcionário específico.
    Apenas usuários administradores podem acessar esta página.
    """
    try:
        # Obter o funcionário
        funcionario = get_object_or_404(Funcionario, id=funcionario_id)
        
        # Obter a empresa selecionada
        empresa_id = request.GET.get('empresa')
        if not empresa_id:
            messages.error(request, 'É necessário selecionar uma empresa.')
            return redirect('tickets:gerenciar_permissoes_categoria')
        
        # Obtém apenas as empresas às quais o usuário tem acesso
        if request.user.is_superuser:
            # Superusuários veem todas as empresas
            empresas = Empresa.objects.all()
            empresa_selecionada = get_object_or_404(Empresa, id=empresa_id)
        else:
            # Funcionários administrativos veem apenas as empresas associadas a eles
            funcionario_logado = request.user.funcionarios.first()
            empresas = funcionario_logado.empresas.all()
            try:
                # Verifica se a empresa selecionada está entre as empresas permitidas
                empresa_selecionada = empresas.get(id=empresa_id)
            except Empresa.DoesNotExist:
                messages.error(request, 'Você não tem permissão para gerenciar esta empresa.')
                return redirect('tickets:gerenciar_permissoes_categoria')
        
        # Verificar se o funcionário tem acesso à empresa selecionada
        if not funcionario.empresas.filter(id=empresa_selecionada.id).exists():
            messages.error(request, 'Este funcionário não pertence à empresa selecionada.')
            return redirect('tickets:gerenciar_permissoes_categoria')
        
        # Obter todas as categorias da empresa
        categorias = CategoriaChamado.objects.filter(empresa=empresa_selecionada)
        
        # Obter as categorias permitidas para o funcionário nesta empresa
        categorias_permitidas = CategoriaPermissao.objects.filter(
            funcionario=funcionario,
            categoria__empresa=empresa_selecionada
        )
        categorias_permitidas_ids = [cp.categoria.id for cp in categorias_permitidas]
        
        if request.method == 'POST':
            # Recebe os IDs das categorias enviadas no formulário
            categoria_ids = request.POST.getlist('categorias')
            
            # Remove todas as permissões existentes para esta empresa
            CategoriaPermissao.objects.filter(
                funcionario=funcionario,
                categoria__empresa=empresa_selecionada
            ).delete()
            
            # Adiciona as novas permissões selecionadas
            if categoria_ids:
                for cat_id in categoria_ids:
                    try:
                        categoria = CategoriaChamado.objects.get(id=cat_id, empresa=empresa_selecionada)
                        CategoriaPermissao.objects.create(
                            funcionario=funcionario,
                            categoria=categoria
                        )
                    except Exception as e:
                        logger.error(f"Erro ao adicionar categoria {cat_id}: {str(e)}")
            
            messages.success(request, f'Permissões de {funcionario.usuario.get_full_name() or funcionario.usuario.username} atualizadas com sucesso.')
            return redirect('tickets:gerenciar_permissoes_categoria')
        
        context = {
            'funcionario': funcionario,
            'empresas': empresas,
            'empresa_selecionada': empresa_selecionada,
            'categorias': categorias,
            'categorias_permitidas_ids': categorias_permitidas_ids,
        }
        
        return render(request, 'tickets/admin/editar_permissoes_usuario.html', context)
        
    except Exception as e:
        logger.error(f"Erro ao editar permissões de usuário: {str(e)}")
        messages.error(request, f"Ocorreu um erro ao editar permissões: {str(e)}")
        return redirect('tickets:gerenciar_permissoes_categoria')
