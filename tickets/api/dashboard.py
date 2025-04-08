from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Count, Q
from ..models import Ticket, CategoriaChamado
import logging

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard_stats(request):
    """
    Retorna as estatísticas básicas do dashboard para o usuário autenticado.
    Inicialmente, retorna apenas os números totais.
    """
    try:
        logger.info(f"Requisição recebida para dashboard_stats - User: {request.user.username}")
        logger.debug(f"Headers recebidos: {request.headers}")
        
        # Verifica autenticação
        if not request.user.is_authenticated:
            logger.error(f"Usuário não autenticado tentando acessar dashboard_stats")
            return Response({"error": "Não autenticado"}, status=401)
            
        # Obtém os tickets associados ao usuário (seja como criador ou atribuído)
        user_tickets = Ticket.objects.filter(
            Q(criado_por=request.user) | 
            Q(atribuido_a__usuario=request.user)
        )
        
        # Log do número de tickets encontrados
        logger.info(f"Tickets encontrados para o usuário {request.user.username}: {user_tickets.count()}")
        
        # Contagem total de tickets
        total_tickets = user_tickets.count()
        
        # Contagem de tickets por status
        tickets_abertos = user_tickets.filter(status='aberto').count()
        tickets_resolvidos = user_tickets.filter(status='resolvido').count()
        
        # Contagem de tickets urgentes
        tickets_urgentes = user_tickets.filter(prioridade='urgente').count()
        
        # Estatísticas por prioridade
        prioridade_stats = user_tickets.values('prioridade').annotate(
            count=Count('id')
        ).order_by('prioridade')
        
        prioridade_data = {
            'baixa': {'label': 'Baixa', 'count': 0},
            'media': {'label': 'Média', 'count': 0},
            'alta': {'label': 'Alta', 'count': 0},
            'urgente': {'label': 'Urgente', 'count': 0}
        }
        
        for stat in prioridade_stats:
            if stat['prioridade'] in prioridade_data:
                prioridade_data[stat['prioridade']]['count'] = stat['count']
        
        # Estatísticas por categoria
        categorias = []
        for categoria in CategoriaChamado.objects.all():
            tickets_categoria = user_tickets.filter(categoria=categoria)
            total_categoria = tickets_categoria.count()
            
            if total_categoria > 0:  # Só inclui categorias que têm tickets
                abertos_categoria = tickets_categoria.filter(status='aberto').count()
                fechados_categoria = tickets_categoria.filter(status='resolvido').count()
                
                categorias.append({
                    'id': categoria.id,
                    'nome': categoria.nome,
                    'cor': categoria.cor or 'gray',  # Cor padrão se não definida
                    'icone': categoria.icone or 'fa-ticket',  # Ícone padrão se não definido
                    'total': total_categoria,
                    'abertos': abertos_categoria,
                    'fechados': fechados_categoria,
                    'porcentagem_fechados': int((fechados_categoria / total_categoria) * 100) if total_categoria > 0 else 0
                })
        
        # Lista dos tickets mais recentes (limitado a 5)
        tickets_recentes = user_tickets.select_related(
            'empresa',
            'categoria',
            'criado_por',
            'atribuido_a__usuario'
        ).order_by('-criado_em')[:5]
        
        tickets_data = []
        for ticket in tickets_recentes:
            tickets_data.append({
                'id': ticket.id,
                'titulo': ticket.titulo,
                'status': ticket.status,
                'prioridade': ticket.prioridade,
                'empresa': {'nome': ticket.empresa.nome if ticket.empresa else 'N/A'},
                'categoria': {
                    'nome': ticket.categoria.nome,
                    'cor': ticket.categoria.cor or 'gray',
                    'icone': ticket.categoria.icone or 'fa-ticket'
                } if ticket.categoria else None,
                'criado_por': {'username': ticket.criado_por.username},
                'atribuido_a': {
                    'usuario': {'username': ticket.atribuido_a.usuario.username}
                } if ticket.atribuido_a else None,
                'criado_em': ticket.criado_em.isoformat()
            })
        
        response_data = {
            'total_tickets': total_tickets,
            'tickets_abertos': tickets_abertos,
            'tickets_resolvidos': tickets_resolvidos,
            'tickets_urgentes': tickets_urgentes,
            'prioridade_data': prioridade_data,
            'categorias': categorias,
            'tickets': tickets_data
        }
        
        logger.info(f"Dados do dashboard gerados com sucesso para {request.user.username}")
        return Response(response_data)
        
    except Exception as e:
        logger.error(f"Erro ao gerar dados do dashboard: {str(e)}", exc_info=True)
        return Response(
            {"error": "Erro interno ao processar dados do dashboard"},
            status=500
        ) 