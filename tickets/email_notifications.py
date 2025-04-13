import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.contrib.auth.models import User
from .models import Ticket, Funcionario, HistoricoTicket

logger = logging.getLogger(__name__)

class EmailNotificationService:
    """
    Serviço responsável por enviar notificações por e-mail para usuários
    """
    
    @staticmethod
    def enviar_email(assunto, destinatarios, template_html, contexto, reply_to=None):
        """
        Envia um e-mail HTML com versão em texto puro como fallback
        
        Args:
            assunto: Assunto do e-mail
            destinatarios: Lista de e-mails para enviar
            template_html: Caminho para o template HTML
            contexto: Dicionário com dados para renderizar o template
            reply_to: E-mail para resposta (opcional)
        """
        try:
            # Verificar se os destinatários são válidos
            if not destinatarios:
                logger.warning("Tentativa de envio de e-mail sem destinatários.")
                return False
            
            # Verifica se o e-mail está configurado e habilitado
            if not settings.EMAIL_ENABLED:
                logger.info(f"E-mail desabilitado nas configurações. Não enviando para: {', '.join(destinatarios)}")
                # Se usando o console backend, o método ainda será chamado, mas os e-mails serão exibidos no console
                if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
                    logger.info(f"Enviando para o console: Assunto: {assunto}")
                
            # Renderiza o template HTML com o contexto
            html_content = render_to_string(template_html, contexto)
            # Cria uma versão de texto puro removendo as tags HTML
            text_content = strip_tags(html_content)
            
            # Prepara o e-mail
            from_email = settings.DEFAULT_FROM_EMAIL
            email = EmailMultiAlternatives(
                subject=assunto,
                body=text_content,
                from_email=from_email,
                to=destinatarios
            )
            
            # Adiciona a versão HTML
            email.attach_alternative(html_content, "text/html")
            
            # Adiciona cabeçalho de Reply-To se fornecido
            if reply_to:
                email.headers = {'Reply-To': reply_to}
            
            # Envia o e-mail
            enviado = email.send()
            
            if enviado:
                logger.info(f"E-mail enviado com sucesso para {', '.join(destinatarios)}")
                return True
            else:
                logger.error(f"Falha ao enviar e-mail para {', '.join(destinatarios)}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao enviar e-mail: {str(e)}")
            return False
    
    @classmethod
    def notificar_atribuicao_ticket(cls, ticket, destinatario_user):
        """
        Notifica um usuário quando um ticket é atribuído a ele
        
        Args:
            ticket: Objeto Ticket
            destinatario_user: Objeto User que receberá a notificação
        """
        if not destinatario_user.email:
            logger.warning(f"Usuário {destinatario_user.username} não possui e-mail configurado.")
            return False
        
        assunto = f"[Helpdesk] Ticket #{ticket.id} - {ticket.titulo} foi atribuído a você"
        destinatarios = [destinatario_user.email]
        template_html = "tickets/emails/atribuicao_ticket.html"
        
        contexto = {
            'ticket': ticket,
            'destinatario': destinatario_user,
            'empresa': ticket.empresa
        }
        
        return cls.enviar_email(assunto, destinatarios, template_html, contexto)
    
    @classmethod
    def notificar_alteracao_status(cls, ticket, status_anterior, usuario_alteracao):
        """
        Notifica sobre alteração de status de um ticket
        
        Args:
            ticket: Objeto Ticket
            status_anterior: Status anterior do ticket
            usuario_alteracao: Usuário que alterou o status
        """
        # Determinar os destinatários
        destinatarios = []
        
        # Sempre notificar o criador do ticket
        if ticket.criado_por.email:
            destinatarios.append(ticket.criado_por.email)
        
        # Notificar o atribuído se houver e for diferente do criador
        if ticket.atribuido_a and ticket.atribuido_a.usuario.email:
            if ticket.atribuido_a.usuario.email != ticket.criado_por.email:
                destinatarios.append(ticket.atribuido_a.usuario.email)
        
        if not destinatarios:
            logger.warning(f"Nenhum destinatário encontrado para notificação de alteração de status do ticket #{ticket.id}")
            return False
        
        assunto = f"[Helpdesk] Status do Ticket #{ticket.id} alterado para {ticket.get_status_display()}"
        template_html = "tickets/emails/alteracao_status.html"
        
        status_dict = dict(Ticket.STATUS_CHOICES)
        
        contexto = {
            'ticket': ticket,
            'status_anterior': status_dict.get(status_anterior, status_anterior),
            'status_novo': ticket.get_status_display(),
            'usuario_alteracao': usuario_alteracao,
            'empresa': ticket.empresa
        }
        
        return cls.enviar_email(assunto, destinatarios, template_html, contexto)

# Configurações de usuário para notificações
class ConfiguracaoNotificacao:
    """
    Classe para gerenciar as preferências de notificação de cada usuário
    """
    
    @staticmethod
    def deve_enviar_notificacao(usuario, tipo_notificacao):
        """
        Verifica se deve enviar notificação para um usuário com base nas preferências
        
        Args:
            usuario: Objeto User
            tipo_notificacao: String com o tipo de notificação 
                            ('atribuicao', 'alteracao_status', etc)
        
        Returns:
            bool: True se deve enviar, False caso contrário
        """
        try:
            # Tenta obter a preferência do usuário
            pref = usuario.preferencias_notificacao
            
            # Verificar configuração específica
            if tipo_notificacao == 'atribuicao':
                return pref.notificar_atribuicao
            elif tipo_notificacao == 'alteracao_status':
                return pref.notificar_alteracao_status
            else:
                # Para qualquer outro tipo que não tenha configuração específica
                return pref.notificar_todas
                
        except Exception:
            # Se não existe configuração, assume que deve notificar (default)
            return True 