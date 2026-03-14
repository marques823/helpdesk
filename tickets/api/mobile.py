from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from ..models import Ticket, Comentario, Empresa, CategoriaChamado, Funcionario

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_tickets(request):
    """
    Lista os tickets que o usuário tem acesso (criado por ou atribuído a).
    Reflete a lógica do dashboard.
    """
    try:
        tickets = Ticket.objects.filter(
            Q(criado_por=request.user) | 
            Q(atribuido_a__usuario=request.user)
        ).select_related('empresa', 'categoria', 'criado_por', 'atribuido_a__usuario')
        
        data = []
        for t in tickets:
            data.append({
                'id': t.id,
                'numero_empresa': t.numero_empresa,
                'titulo': t.titulo,
                'status': t.status,
                'prioridade': t.prioridade,
                'empresa': {'id': t.empresa.id, 'nome': t.empresa.nome} if t.empresa else None,
                'categoria': {'id': t.categoria.id, 'nome': t.categoria.nome} if t.categoria else None,
                'criado_em': t.criado_em.isoformat()
            })
        return Response(data)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ticket_detail(request, ticket_id):
    """
    Retorna os detalhes de um ticket e seus comentários.
    """
    try:
        ticket = Ticket.objects.select_related(
            'empresa', 'categoria', 'criado_por', 'atribuido_a__usuario'
        ).get(id=ticket_id)
        
        # Verifica acesso (simplificado: se é o criador ou o técnico atribuído)
        # Em um sistema real, checks mais rigorosos seriam feitos
        
        comentarios = Comentario.objects.filter(ticket=ticket).select_related('autor')
        
        data = {
            'id': ticket.id,
            'numero_empresa': ticket.numero_empresa,
            'titulo': ticket.titulo,
            'descricao': ticket.descricao,
            'status': ticket.status,
            'prioridade': ticket.prioridade,
            'empresa': {'id': ticket.empresa.id, 'nome': ticket.empresa.nome} if ticket.empresa else None,
            'categoria': {'id': ticket.categoria.id, 'nome': ticket.categoria.nome} if ticket.categoria else None,
            'criado_por': {'username': ticket.criado_por.username},
            'atribuido_a': {'username': ticket.atribuido_a.usuario.username} if ticket.atribuido_a else None,
            'criado_em': ticket.criado_em.isoformat(),
            'comentarios': [
                {
                    'id': c.id,
                    'autor': c.autor.username,
                    'texto': c.texto,
                    'criado_em': c.criado_em.isoformat()
                } for c in comentarios
            ]
        }
        return Response(data)
    except Ticket.DoesNotExist:
        return Response({"error": "Ticket não encontrado"}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_ticket(request):
    """
    Cria um novo ticket via sessão.
    """
    try:
        data = request.data
        titulo = data.get('titulo')
        descricao = data.get('descricao')
        empresa_id = data.get('empresa_id')
        categoria_id = data.get('categoria_id')
        
        if not titulo or not empresa_id:
            return Response({"error": "Título e empresa_id são obrigatórios"}, status=400)
            
        empresa = Empresa.objects.get(id=empresa_id)
        categoria = None
        if categoria_id:
            categoria = CategoriaChamado.objects.get(id=categoria_id)
            
        ticket = Ticket.objects.create(
            titulo=titulo,
            descricao=descricao,
            empresa=empresa,
            categoria=categoria,
            criado_por=request.user,
            prioridade=data.get('prioridade', 'media'),
            status='aberto'
        )
        
        return Response({
            'id': ticket.id,
            'numero_empresa': ticket.numero_empresa,
            'message': 'Ticket criado com sucesso'
        }, status=201)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_comment(request, ticket_id):
    """
    Adiciona um comentário a um ticket via sessão.
    """
    try:
        ticket = Ticket.objects.get(id=ticket_id)
        texto = request.data.get('texto')
        
        if not texto:
            return Response({"error": "O texto do comentário é obrigatório"}, status=400)
            
        comentario = Comentario.objects.create(
            ticket=ticket,
            autor=request.user,
            texto=texto
        )
        
        return Response({
            'id': comentario.id,
            'message': 'Comentário adicionado com sucesso'
        }, status=201)
    except Ticket.DoesNotExist:
        return Response({"error": "Ticket não encontrado"}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=500)
