from .email_notifications import EmailNotificationService
from django.core.mail import send_mail
from django.conf import settings
import logging

# Esta é uma camada de compatibilidade para manter o código funcionando
# O EmailNotificationService foi movido para email_notifications.py 

logger = logging.getLogger(__name__)

class EmailService:
    """
    Serviço para envio de emails simples, sem templates
    """
    
    @staticmethod
    def enviar_email(destinatario, assunto, mensagem, html_message=None, from_email=None):
        """
        Envia um email simples para um destinatário
        
        Args:
            destinatario: Email do destinatário (string) ou lista de emails
            assunto: Assunto do email
            mensagem: Conteúdo do email (texto plano)
            html_message: Versão HTML do email (opcional)
            from_email: Email de origem (opcional, usa o padrão das configurações)
            
        Returns:
            bool: True se o email foi enviado com sucesso, False caso contrário
        """
        try:
            # Garante que o destinatário seja uma lista
            destinatarios = [destinatario] if isinstance(destinatario, str) else destinatario
            
            # Verifica se os emails estão verificados (se estiver usando SES)
            if settings.EMAIL_HOST == 'email-smtp.sa-east-1.amazonaws.com':
                destinatarios_verificados = []
                for email in destinatarios:
                    if EmailNotificationService.email_verificado(email):
                        destinatarios_verificados.append(email)
                    else:
                        logger.warning(f"Email não verificado no SES: {email}")
                
                if not destinatarios_verificados:
                    logger.error("Nenhum destinatário está verificado no SES. Email não enviado.")
                    return False
                
                destinatarios = destinatarios_verificados
            
            # Usa o email padrão de origem se não for especificado
            if not from_email:
                from_email = settings.DEFAULT_FROM_EMAIL
            
            # Envia o email
            resultado = send_mail(
                subject=assunto,
                message=mensagem,
                from_email=from_email,
                recipient_list=destinatarios,
                html_message=html_message,
                fail_silently=False
            )
            
            if resultado > 0:
                logger.info(f"Email enviado com sucesso para: {', '.join(destinatarios)}")
                return True
            else:
                logger.warning(f"Falha ao enviar email para: {', '.join(destinatarios)}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao enviar email: {str(e)}")
            return False 