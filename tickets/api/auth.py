from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
import json
from django_ratelimit.decorators import ratelimit

@api_view(['POST'])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='5/m', block=True)
def api_login(request):
    """
    Legado: Login via sessão. 
    Para JWT, use /api/auth/token/
    """
    try:
        data = request.data
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return Response({'error': 'Usuário e senha são obrigatórios'}, status=400)
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return Response({
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser,
                }
            })
        else:
            return Response({'error': 'Credenciais inválidas'}, status=401)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_logout(request):
    try:
        logout(request)
        return Response({'message': 'Logout realizado com sucesso'})
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def api_user(request):
    try:
        user = request.user
        if request.method == 'PUT':
            data = request.data
            user.first_name = data.get('first_name', user.first_name)
            user.last_name = data.get('last_name', user.last_name)
            user.email = data.get('email', user.email)
            user.save()
            
        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
            }
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_save_push_token(request):
    try:
        user = request.user
        token_value = request.data.get('token')
        # Mapeia a plataforma se necessário (Capacitor envia 'ios', 'android' ou 'web')
        platform = (request.data.get('platform') or 'web').lower()
        if platform not in ['android', 'ios', 'web']:
            platform = 'web'

        if not token_value:
            return Response({'error': 'Token é obrigatório'}, status=400)

        from tickets.models import PushToken
        # Remove o token se ele já pertencer a outro usuário para evitar conflitos
        PushToken.objects.filter(token=token_value).exclude(usuario=user).delete()
        
        # Cria ou atualiza o token para o usuário atual
        PushToken.objects.update_or_create(
            usuario=user,
            token=token_value,
            defaults={'plataforma': platform}
        )

        return Response({'success': True, 'message': 'Token salvo com sucesso'})
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def api_notification_settings(request):
    try:
        user = request.user
        from tickets.models import PreferenciasNotificacao
        prefs, created = PreferenciasNotificacao.objects.get_or_create(usuario=user)

        if request.method == 'PUT':
            data = request.data
            prefs.habilitar_push = data.get('push', prefs.habilitar_push)
            prefs.habilitar_email = data.get('email', prefs.habilitar_email)
            prefs.notificar_novos_tickets = data.get('newTickets', prefs.notificar_novos_tickets)
            prefs.notificar_comentarios = data.get('replies', prefs.notificar_comentarios)
            prefs.notificar_mudanca_status = data.get('statusUpdates', prefs.notificar_mudanca_status)
            prefs.notificar_alertas_sistema = data.get('systemAlerts', prefs.notificar_alertas_sistema)
            prefs.save()

        return Response({
            'push': prefs.habilitar_push,
            'email': prefs.habilitar_email,
            'newTickets': prefs.notificar_novos_tickets,
            'replies': prefs.notificar_comentarios,
            'statusUpdates': prefs.notificar_mudanca_status,
            'systemAlerts': prefs.notificar_alertas_sistema,
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)