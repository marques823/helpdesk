from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from tickets.models import PreferenciasNotificacao
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Cria preferências de notificação para usuários existentes'

    def handle(self, *args, **options):
        count = 0
        error_count = 0
        
        # Obter todos os usuários que não têm preferências de notificação
        users = User.objects.filter(preferencias_notificacao__isnull=True)
        
        total_users = users.count()
        self.stdout.write(f"Encontrados {total_users} usuários sem preferências de notificação configuradas.")
        
        # Criar preferências para cada usuário
        for user in users:
            try:
                PreferenciasNotificacao.objects.create(usuario=user)
                count += 1
                self.stdout.write(f"Preferências criadas para o usuário {user.username}")
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f"Erro ao criar preferências para {user.username}: {str(e)}"))
                logger.error(f"Erro ao criar preferências para {user.username}: {str(e)}")
        
        # Resumo final
        self.stdout.write(self.style.SUCCESS(
            f"Processamento concluído. {count} preferências criadas, {error_count} erros."
        )) 