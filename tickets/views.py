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
from .models import Ticket, Comentario, Empresa, Funcionario, HistoricoTicket, CampoPersonalizado, ValorCampoPersonalizado, NotaTecnica
from .forms import TicketForm, ComentarioForm, EmpresaForm, FuncionarioForm, UserForm, AtribuirTicketForm, CampoPersonalizadoForm, ValorCampoPersonalizadoForm, NotaTecnicaForm
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
import json
from django.db.models import Q

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
            if request.user.is_superuser:
                # Superusuário não precisa ter funcionário associado
                tickets = Ticket.objects.all()
                empresas = Empresa.objects.all()
            else:
                messages.error(request, "Usuário não possui funcionários associados. Por favor, contate o administrador.")
                return redirect('tickets:home')
        else:
            # Pega todas as empresas do funcionário
            empresas_ids = [empresa.id for funcionario in funcionarios for empresa in funcionario.empresas.all()]
            
            # Filtra tickets baseado no tipo de usuário
            if request.user.is_superuser:
                # Superusuário vê todos os tickets
                tickets = Ticket.objects.all()
                empresas = Empresa.objects.all()
            else:
                # Para outros usuários, filtra por empresa e tipo
                tickets = Ticket.objects.filter(empresa_id__in=empresas_ids)
                
                # Se for cliente, filtra tickets criados por ele ou atribuídos a ele
                if any(funcionario.is_cliente() for funcionario in funcionarios):
                    tickets = tickets.filter(
                        models.Q(criado_por=request.user) |
                        models.Q(atribuido_a__in=funcionarios)
                    )
            
            # Prepara opções de filtro
            empresas = Empresa.objects.filter(id__in=empresas_ids)
        
        # Aplica filtros
        status_filter = request.GET.get('status')
        if status_filter:
            tickets = tickets.filter(status=status_filter)
        
        prioridade_filter = request.GET.get('prioridade')
        if prioridade_filter:
            tickets = tickets.filter(prioridade=prioridade_filter)
        
        empresa_filter = request.GET.get('empresa')
        if empresa_filter:
            tickets = tickets.filter(empresa_id=empresa_filter)
        
        # Aplica ordenação
        order_by = request.GET.get('order_by', '-criado_em')
        tickets = tickets.order_by(order_by)
        
        # Calcula estatísticas
        total_tickets = tickets.count()
        tickets_abertos = tickets.filter(status='aberto').count()
        tickets_fechados = tickets.filter(status='fechado').count()
        
        # Paginação
        paginator = Paginator(tickets, 10)
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
            'empresas': empresas,
            'status_filter': status_filter,
            'prioridade_filter': prioridade_filter,
            'empresa_filter': empresa_filter,
            'order_by': order_by,
            'status_choices': Ticket.STATUS_CHOICES,
            'prioridade_choices': Ticket.PRIORIDADE_CHOICES,
            'funcionario': funcionarios.first() if funcionarios.exists() else None,
        }
        
        return render(request, 'tickets/dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Erro no dashboard: {str(e)}")
        messages.error(request, "Ocorreu um erro ao carregar o dashboard. Por favor, tente novamente.")
        return redirect('tickets:home')

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
                tipo_alteracao='comentario',
                usuario=request.user,
                descricao=f'Nota técnica adicionada por {funcionario.usuario.get_full_name() or funcionario.usuario.username}',
                dados_novos={'nota_id': nota.id}
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
                tipo_alteracao='edicao',
                usuario=request.user,
                descricao=f'Nota técnica #{nota.id} editada por {request.user.get_full_name() or request.user.username}',
                dados_novos={'nota_id': nota.id}
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
            tipo_alteracao='edicao',
            usuario=request.user,
            descricao=f'Nota técnica #{nota_id} excluída por {request.user.get_full_name() or request.user.username}',
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

        # Obtém os campos personalizados da empresa selecionada
        campos_personalizados = None
        if empresa_id:
            try:
                # Verifica se o usuário tem acesso à empresa
                empresa = Empresa.objects.get(id=empresa_id)
                if not request.user.is_superuser and not funcionario.empresas.filter(id=empresa_id).exists():
                    messages.error(request, 'Você não tem acesso a esta empresa.')
                    return redirect('tickets:dashboard')
                
                # Se o usuário está tentando acessar uma empresa que não é dele, redirecione
                if funcionario and funcionario.empresas.count() == 1 and str(funcionario.empresas.first().id) != empresa_id:
                    return redirect('tickets:criar_ticket')
                
                # Busca os campos personalizados ativos para a empresa, ordenados por ordem e nome
                campos_personalizados = CampoPersonalizado.objects.filter(
                    empresa_id=empresa_id,
                    ativo=True
                ).order_by('ordem', 'nome')
                
            except (Empresa.DoesNotExist, ValueError):
                # Se a empresa não existe ou o ID não é válido, limpe o valor
                empresa_id = None
                campos_personalizados = None

        if request.method == 'POST':
            form = TicketForm(request.POST, user=request.user, initial=initial_data)
            if form.is_valid():
                ticket = form.save(commit=False)
                ticket.criado_por = request.user
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

                messages.success(request, 'Ticket criado com sucesso!')
                return redirect('tickets:detalhe_ticket', ticket.id)
        else:
            form = TicketForm(user=request.user, initial=initial_data)

        context = {
            'form': form,
            'campos_personalizados': campos_personalizados,
            'empresas': empresas,
            'empresa_id': empresa_id
        }
        return render(request, 'tickets/novo_ticket.html', context)

    except Exception as e:
        logger.error(f"Erro ao criar ticket: {str(e)}")
        messages.error(request, 'Ocorreu um erro ao criar o ticket. Por favor, tente novamente.')
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
            'pode_atribuir': pode_atribuir
        }
        
        logger.info(f"Ticket {ticket_id} carregado com sucesso para usuário {request.user.username}")
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
        if not request.user.is_superuser:
            funcionario = request.user.funcionarios.first()
            if not funcionario or not funcionario.pode_editar_ticket(ticket):
                messages.error(request, 'Você não tem permissão para editar este ticket.')
                return redirect('tickets:dashboard')
            
            # Verifica se o funcionário tem acesso à empresa do ticket
            if not funcionario.empresas.filter(id=ticket.empresa.id).exists():
                messages.error(request, 'Você não tem acesso a esta empresa.')
                return redirect('tickets:dashboard')
        
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
            form = TicketForm(request.POST, instance=ticket, user=request.user)
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
                    'atribuido_a': ticket_salvo.atribuido_a.usuario.username if ticket_salvo.atribuido_a else None
                }
                
                # Adiciona os campos personalizados alterados aos dados do histórico
                if campos_alterados:
                    dados_anteriores['campos_personalizados'] = {item['campo']: item['valor_anterior'] for item in campos_alterados}
                    dados_novos['campos_personalizados'] = {item['campo']: item['valor_novo'] for item in campos_alterados}
                
                registrar_historico(
                    ticket=ticket_salvo,
                    tipo_alteracao='edicao',
                    usuario=request.user,
                    descricao=f'Ticket editado por {request.user.get_full_name()}',
                    dados_anteriores=dados_anteriores,
                    dados_novos=dados_novos
                )
                
                messages.success(request, 'Ticket atualizado com sucesso!')
                return redirect('tickets:detalhe_ticket', ticket_id=ticket.id)
        else:
            form = TicketForm(instance=ticket, user=request.user)
        
        # Atualiza as opções do formulário
        form.fields['empresa'].queryset = empresas
        form.fields['atribuido_a'].queryset = funcionarios
        
        return render(request, 'tickets/editar_ticket.html', {
            'form': form,
            'ticket': ticket,
            'campos_personalizados': valores_campos
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

@login_required
@user_passes_test(is_admin)
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
@user_passes_test(is_admin)
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
@user_passes_test(is_admin)
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
