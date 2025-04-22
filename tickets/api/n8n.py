from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
import json
import logging
from ..models import Ticket, Empresa, Funcionario, CategoriaChamado, Comentario

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_tickets(request):
    """
    Retorna a lista de tickets com base nos parâmetros de filtro.
    Usado pelo n8n para obter tickets para processamento.
    """
    try:
        # Parametros de filtro
        empresa_id = request.GET.get('empresa_id')
        status_filter = request.GET.get('status')
        categoria_id = request.GET.get('categoria_id')
        
        # Filtro base de tickets
        tickets = Ticket.objects.all().select_related(
            'empresa', 'categoria', 'criado_por', 'atribuido_a'
        )
        
        # Aplicar filtros
        if empresa_id:
            tickets = tickets.filter(empresa_id=empresa_id)
            
        if status_filter:
            tickets = tickets.filter(status=status_filter)
            
        if categoria_id:
            tickets = tickets.filter(categoria_id=categoria_id)
        
        # Limitar resultados
        limit = int(request.GET.get('limit', 50))
        tickets = tickets[:limit]
        
        # Construir resposta
        data = []
        for ticket in tickets:
            data.append({
                'id': ticket.id,
                'numero_empresa': ticket.numero_empresa,
                'titulo': ticket.titulo,
                'descricao': ticket.descricao,
                'status': ticket.status,
                'prioridade': ticket.prioridade,
                'empresa': {
                    'id': ticket.empresa.id,
                    'nome': ticket.empresa.nome
                } if ticket.empresa else None,
                'categoria': {
                    'id': ticket.categoria.id,
                    'nome': ticket.categoria.nome
                } if ticket.categoria else None,
                'criado_por': {
                    'id': ticket.criado_por.id,
                    'username': ticket.criado_por.username,
                    'email': ticket.criado_por.email,
                    'nome_completo': ticket.criado_por.get_full_name()
                } if ticket.criado_por else None,
                'atribuido_a': {
                    'id': ticket.atribuido_a.id,
                    'usuario': {
                        'id': ticket.atribuido_a.usuario.id,
                        'username': ticket.atribuido_a.usuario.username,
                        'email': ticket.atribuido_a.usuario.email
                    }
                } if ticket.atribuido_a else None,
                'criado_em': ticket.criado_em.isoformat(),
                'atualizado_em': ticket.atualizado_em.isoformat() if ticket.atualizado_em else None
            })
        
        return Response(data)
        
    except Exception as e:
        logger.error(f"Erro ao obter tickets para n8n: {str(e)}", exc_info=True)
        return Response(
            {"error": f"Erro ao obter tickets: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ticket_detail(request, ticket_id):
    """
    Retorna os detalhes de um ticket específico.
    Usado pelo n8n para obter informações detalhadas de um ticket.
    """
    try:
        ticket = Ticket.objects.select_related(
            'empresa', 'categoria', 'criado_por', 'atribuido_a'
        ).get(id=ticket_id)
        
        # Obter comentários do ticket
        comentarios = Comentario.objects.filter(ticket=ticket).select_related('autor')
        comentarios_data = []
        
        for comentario in comentarios:
            comentarios_data.append({
                'id': comentario.id,
                'conteudo': comentario.conteudo,
                'autor': {
                    'id': comentario.autor.id,
                    'username': comentario.autor.username,
                    'email': comentario.autor.email,
                    'nome_completo': comentario.autor.get_full_name()
                } if comentario.autor else None,
                'data_criacao': comentario.data_criacao.isoformat(),
                'publico': comentario.publico
            })
        
        # Dados do ticket
        data = {
            'id': ticket.id,
            'numero_empresa': ticket.numero_empresa,
            'titulo': ticket.titulo,
            'descricao': ticket.descricao,
            'status': ticket.status,
            'prioridade': ticket.prioridade,
            'empresa': {
                'id': ticket.empresa.id,
                'nome': ticket.empresa.nome
            } if ticket.empresa else None,
            'categoria': {
                'id': ticket.categoria.id,
                'nome': ticket.categoria.nome
            } if ticket.categoria else None,
            'criado_por': {
                'id': ticket.criado_por.id,
                'username': ticket.criado_por.username,
                'email': ticket.criado_por.email,
                'nome_completo': ticket.criado_por.get_full_name()
            } if ticket.criado_por else None,
            'atribuido_a': {
                'id': ticket.atribuido_a.id,
                'usuario': {
                    'id': ticket.atribuido_a.usuario.id,
                    'username': ticket.atribuido_a.usuario.username,
                    'email': ticket.atribuido_a.usuario.email
                }
            } if ticket.atribuido_a else None,
            'criado_em': ticket.criado_em.isoformat(),
            'atualizado_em': ticket.atualizado_em.isoformat() if ticket.atualizado_em else None,
            'comentarios': comentarios_data
        }
        
        return Response(data)
        
    except Ticket.DoesNotExist:
        return Response(
            {"error": "Ticket não encontrado"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Erro ao obter detalhes do ticket para n8n: {str(e)}", exc_info=True)
        return Response(
            {"error": f"Erro ao obter detalhes do ticket: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_ticket(request, ticket_id):
    """
    Atualiza um ticket existente.
    Usado pelo n8n para atualizar o status, prioridade ou atribuir um ticket.
    """
    try:
        ticket = Ticket.objects.get(id=ticket_id)
        
        # Dados a atualizar
        data = request.data
        status_anterior = ticket.status
        
        # Atualizar status
        if 'status' in data:
            ticket.status = data['status']
            
        # Atualizar prioridade
        if 'prioridade' in data:
            ticket.prioridade = data['prioridade']
            
        # Atribuir ticket
        if 'atribuido_a_id' in data:
            funcionario_id = data['atribuido_a_id']
            if funcionario_id:
                try:
                    funcionario = Funcionario.objects.get(id=funcionario_id)
                    ticket.atribuido_a = funcionario
                except Funcionario.DoesNotExist:
                    return Response(
                        {"error": "Funcionário não encontrado"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                ticket.atribuido_a = None
                
        # Adicionar comentário se fornecido
        comentario_texto = data.get('comentario')
        
        # Salvar o ticket
        ticket.save()
        
        # Adicionar comentário, se fornecido
        if comentario_texto:
            Comentario.objects.create(
                ticket=ticket,
                autor=request.user,
                conteudo=comentario_texto,
                publico=data.get('comentario_publico', True)
            )
            
        return Response({
            'success': True,
            'message': 'Ticket atualizado com sucesso',
            'ticket_id': ticket.id
        })
        
    except Ticket.DoesNotExist:
        return Response(
            {"error": "Ticket não encontrado"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Erro ao atualizar ticket via n8n: {str(e)}", exc_info=True)
        return Response(
            {"error": f"Erro ao atualizar ticket: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_comment(request, ticket_id):
    """
    Adiciona um comentário a um ticket.
    Usado pelo n8n para adicionar comentários automaticamente.
    """
    try:
        ticket = Ticket.objects.get(id=ticket_id)
        
        # Dados do comentário
        data = request.data
        conteudo = data.get('conteudo')
        
        if not conteudo:
            return Response(
                {"error": "O conteúdo do comentário é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Criar comentário
        comentario = Comentario.objects.create(
            ticket=ticket,
            autor=request.user,
            conteudo=conteudo,
            publico=data.get('publico', True)
        )
        
        return Response({
            'success': True,
            'message': 'Comentário adicionado com sucesso',
            'ticket_id': ticket.id,
            'comentario_id': comentario.id
        })
        
    except Ticket.DoesNotExist:
        return Response(
            {"error": "Ticket não encontrado"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Erro ao adicionar comentário via n8n: {str(e)}", exc_info=True)
        return Response(
            {"error": f"Erro ao adicionar comentário: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_ticket(request):
    """
    Cria um novo ticket.
    Usado pelo n8n para criar tickets automaticamente.
    """
    try:
        data = request.data
        
        # Campos obrigatórios
        if not data.get('titulo') or not data.get('empresa_id'):
            return Response(
                {"error": "Título e ID da empresa são obrigatórios"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Obter empresa
        try:
            empresa = Empresa.objects.get(id=data['empresa_id'])
        except Empresa.DoesNotExist:
            return Response(
                {"error": "Empresa não encontrada"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Obter categoria, se fornecida
        categoria = None
        if data.get('categoria_id'):
            try:
                categoria = CategoriaChamado.objects.get(
                    id=data['categoria_id'],
                    empresa=empresa
                )
            except CategoriaChamado.DoesNotExist:
                return Response(
                    {"error": "Categoria não encontrada"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        # Obter funcionário para atribuição, se fornecido
        funcionario = None
        if data.get('atribuido_a_id'):
            try:
                funcionario = Funcionario.objects.get(id=data['atribuido_a_id'])
                
                # Verificar se o funcionário pertence à empresa
                if not funcionario.empresas.filter(id=empresa.id).exists():
                    return Response(
                        {"error": "Funcionário não pertence à empresa selecionada"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except Funcionario.DoesNotExist:
                return Response(
                    {"error": "Funcionário não encontrado"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Criar o ticket
        ticket = Ticket.objects.create(
            titulo=data['titulo'],
            descricao=data.get('descricao', ''),
            status=data.get('status', 'aberto'),
            prioridade=data.get('prioridade', 'media'),
            empresa=empresa,
            categoria=categoria,
            criado_por=request.user,
            atribuido_a=funcionario
        )
        
        return Response({
            'success': True,
            'message': 'Ticket criado com sucesso',
            'ticket_id': ticket.id,
            'numero_empresa': ticket.numero_empresa
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Erro ao criar ticket via n8n: {str(e)}", exc_info=True)
        return Response(
            {"error": f"Erro ao criar ticket: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) 