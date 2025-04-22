import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Ticket, Funcionario, HistoricoTicket, EmailVerificado

logger = logging.getLogger(__name__)

class EmailNotificationService:
    """
    Serviço responsável por enviar notificações por e-mail para usuários
    """
    
    # Lista de domínios verificados no Amazon SES
    DOMINIOS_VERIFICADOS = ['tecnicolitoral.com']
    
    # Lista de emails específicos verificados no Amazon SES
    EMAILS_VERIFICADOS = ['suportetecnicolitoral@gmail.com', 'suporte@tecnicolitoral.com']
    
    @classmethod
    def email_verificado(cls, email):
        """
        Verifica se um email está verificado no Amazon SES
        
        Args:
            email: Endereço de email a verificar
            
        Returns:
            bool: True se o email está verificado, False caso contrário
        """
        if not email:
            return False
        
        # Verifica no banco de dados
        try:
            email_verificado = EmailVerificado.objects.filter(email=email, verificado=True).exists()
            if email_verificado:
                return True
        except Exception as e:
            logger.error(f"Erro ao verificar email no banco de dados: {str(e)}")
            
        # Verifica se é um email específico verificado
        if email in cls.EMAILS_VERIFICADOS:
            return True
            
        # Verifica se o domínio está verificado
        dominio = email.split('@')[-1]
        return dominio in cls.DOMINIOS_VERIFICADOS
    
    @classmethod
    def verificar_email_especifico(cls, email):
        """
        Verifica se um email específico está na lista de emails verificados
        """
        return email in cls.EMAILS_VERIFICADOS
    
    @classmethod
    def verificar_dominio_email(cls, email):
        """
        Verifica se o domínio do email está na lista de domínios verificados
        """
        if not email or '@' not in email:
            return False
        dominio = email.split('@')[-1]
        return dominio in cls.DOMINIOS_VERIFICADOS
    
    @classmethod
    def registrar_email_verificado(cls, email, verificado=True):
        """
        Registra um email no sistema como verificado ou não verificado
        
        Args:
            email: Endereço de email para registrar
            verificado: Boolean indicando se o email está verificado
            
        Returns:
            EmailVerificado: Objeto criado ou atualizado
        """
        try:
            obj, created = EmailVerificado.objects.update_or_create(
                email=email,
                defaults={
                    'verificado': verificado,
                    'data_verificacao': timezone.now() if verificado else None
                }
            )
            if created:
                logger.info(f"Email {email} registrado como {'verificado' if verificado else 'não verificado'}")
            else:
                logger.info(f"Status de verificação de {email} atualizado para {'verificado' if verificado else 'não verificado'}")
            return obj
        except Exception as e:
            logger.error(f"Erro ao registrar email verificado: {str(e)}")
            return None
    
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
            
            # Filtra apenas os destinatários verificados quando usando AWS SES
            if settings.EMAIL_ENABLED and settings.EMAIL_HOST == 'email-smtp.sa-east-1.amazonaws.com':
                destinatarios_verificados = [d for d in destinatarios if EmailNotificationService.email_verificado(d)]
                if not destinatarios_verificados:
                    logger.warning(f"Nenhum destinatário verificado no SES. Pulando envio: {', '.join(destinatarios)}")
                    return False
                destinatarios = destinatarios_verificados
            
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
        
        # Determinar tipo de usuário
        from .models import Funcionario
        tipo_usuario = 'cliente'  # Default
        try:
            if Funcionario.objects.filter(usuario=destinatario_user).exists():
                funcionario = Funcionario.objects.get(usuario=destinatario_user)
                tipo_usuario = funcionario.tipo
        except Exception as e:
            logger.warning(f"Erro ao determinar tipo de usuário para {destinatario_user.username}: {str(e)}")
        
        assunto = f"[Helpdesk] Chamado #{ticket.id} - {ticket.titulo} foi atribuído a você"
        destinatarios = [destinatario_user.email]
        template_html = "tickets/emails/atribuicao_ticket.html"
        
        contexto = {
            'ticket': ticket,
            'destinatario': destinatario_user,
            'empresa': ticket.empresa,
            'url_ticket': f"{settings.SITE_URL}/tickets/ticket/{ticket.id}/" if hasattr(settings, 'SITE_URL') else None,
            'tipo_usuario': tipo_usuario,
            'nome_destinatario': destinatario_user.get_full_name() or destinatario_user.username
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
        destinatarios_info = []
        
        # Tipo de usuário cliente para o criador do ticket
        if ticket.criado_por.email:
            # Verificar preferências de notificação
            if ConfiguracaoNotificacao.deve_enviar_notificacao(ticket.criado_por, 'alteracao_status'):
                # Verificar se é cliente ou funcionário
                from .models import Funcionario
                tipo_usuario = 'cliente'
                try:
                    if Funcionario.objects.filter(usuario=ticket.criado_por).exists():
                        funcionario = Funcionario.objects.get(usuario=ticket.criado_por)
                        tipo_usuario = funcionario.tipo
                except Exception as e:
                    logger.warning(f"Erro ao determinar tipo de usuário para {ticket.criado_por.username}: {str(e)}")
                
                destinatarios_info.append({
                    'email': ticket.criado_por.email,
                    'tipo_usuario': tipo_usuario,
                    'nome': ticket.criado_por.get_full_name() or ticket.criado_por.username
                })
        
        # Notificar o atribuído se houver e for diferente do criador
        if ticket.atribuido_a and ticket.atribuido_a.usuario.email:
            if ticket.atribuido_a.usuario.email != ticket.criado_por.email:
                if ConfiguracaoNotificacao.deve_enviar_notificacao(ticket.atribuido_a.usuario, 'alteracao_status'):
                    destinatarios_info.append({
                        'email': ticket.atribuido_a.usuario.email,
                        'tipo_usuario': ticket.atribuido_a.tipo,
                        'nome': ticket.atribuido_a.usuario.get_full_name() or ticket.atribuido_a.usuario.username
                    })
        
        if not destinatarios_info:
            logger.warning(f"Nenhum destinatário encontrado para notificação de alteração de status do chamado #{ticket.id}")
            return False
        
        assunto = f"[Helpdesk] Status do Chamado #{ticket.id} alterado para {ticket.get_status_display()}"
        template_html = "tickets/emails/alteracao_status.html"
        
        status_dict = dict(Ticket.STATUS_CHOICES)
        
        # Envio individual para cada destinatário com contexto personalizado
        sucessos = 0
        for destinatario in destinatarios_info:
            contexto = {
                'ticket': ticket,
                'status_anterior': status_dict.get(status_anterior, status_anterior),
                'status_novo': ticket.get_status_display(),
                'alterador': usuario_alteracao,
                'empresa': ticket.empresa,
                'url_ticket': f"{settings.SITE_URL}/tickets/ticket/{ticket.id}/" if hasattr(settings, 'SITE_URL') else None,
                'tipo_usuario': destinatario['tipo_usuario'],
                'nome_destinatario': destinatario['nome']
            }
            
            success = cls.enviar_email(
                assunto=assunto,
                destinatarios=[destinatario['email']],
                template_html=template_html,
                contexto=contexto
            )
            if success:
                sucessos += 1
        
        return sucessos > 0  # Retorna True se pelo menos um email foi enviado com sucesso
    
    @classmethod
    def notificar_novo_comentario(cls, comentario):
        """
        Notifica sobre um novo comentário em um ticket
        
        Args:
            comentario: Objeto Comentario
        """
        ticket = comentario.ticket
        autor = comentario.autor
        
        # Determinar os destinatários
        destinatarios_info = []
        
        # Verificar tipo de cada destinatário
        from .models import Funcionario
        
        # Notificar o criador do ticket (se não for o autor do comentário)
        if ticket.criado_por.email and ticket.criado_por != autor:
            # Verificar preferências de notificação
            if ConfiguracaoNotificacao.deve_enviar_notificacao(ticket.criado_por, 'novo_comentario'):
                # Verificar se é cliente ou funcionário
                tipo_usuario = 'cliente'
                try:
                    if Funcionario.objects.filter(usuario=ticket.criado_por).exists():
                        funcionario = Funcionario.objects.get(usuario=ticket.criado_por)
                        tipo_usuario = funcionario.tipo
                except Exception as e:
                    logger.warning(f"Erro ao determinar tipo de usuário para {ticket.criado_por.username}: {str(e)}")
                
                destinatarios_info.append({
                    'email': ticket.criado_por.email,
                    'tipo_usuario': tipo_usuario,
                    'nome': ticket.criado_por.get_full_name() or ticket.criado_por.username
                })
        
        # Notificar o técnico atribuído (se houver e não for o autor do comentário)
        if ticket.atribuido_a and ticket.atribuido_a.usuario.email and ticket.atribuido_a.usuario != autor:
            # Verificar preferências de notificação
            if ConfiguracaoNotificacao.deve_enviar_notificacao(ticket.atribuido_a.usuario, 'novo_comentario'):
                destinatarios_info.append({
                    'email': ticket.atribuido_a.usuario.email,
                    'tipo_usuario': ticket.atribuido_a.tipo,
                    'nome': ticket.atribuido_a.usuario.get_full_name() or ticket.atribuido_a.usuario.username
                })
        
        # Notificar outros técnicos atribuídos
        for atribuicao in ticket.atribuicoes.all():
            if (atribuicao.funcionario != ticket.atribuido_a and 
                atribuicao.funcionario.usuario.email and 
                atribuicao.funcionario.usuario != autor):
                # Verificar preferências de notificação
                if ConfiguracaoNotificacao.deve_enviar_notificacao(atribuicao.funcionario.usuario, 'novo_comentario'):
                    destinatarios_info.append({
                        'email': atribuicao.funcionario.usuario.email,
                        'tipo_usuario': atribuicao.funcionario.tipo,
                        'nome': atribuicao.funcionario.usuario.get_full_name() or atribuicao.funcionario.usuario.username
                    })
        
        if not destinatarios_info:
            logger.info(f"Nenhum destinatário para notificação de novo comentário no chamado #{ticket.id}")
            return False
        
        assunto = f"[Helpdesk] Novo comentário no Chamado #{ticket.id} - {ticket.titulo}"
        template_html = "tickets/emails/novo_comentario.html"
        
        # Envio individual para cada destinatário com contexto personalizado
        sucessos = 0
        for destinatario in destinatarios_info:
            contexto = {
                'ticket': ticket,
                'comentario': comentario,
                'autor': autor,
                'empresa': ticket.empresa,
                'url_ticket': f"{settings.SITE_URL}/tickets/ticket/{ticket.id}/" if hasattr(settings, 'SITE_URL') else None,
                'tipo_usuario': destinatario['tipo_usuario'],
                'nome_destinatario': destinatario['nome']
            }
            
            success = cls.enviar_email(
                assunto=assunto,
                destinatarios=[destinatario['email']],
                template_html=template_html,
                contexto=contexto
            )
            if success:
                sucessos += 1
                
        return sucessos > 0  # Retorna True se pelo menos um email foi enviado com sucesso
    
    @classmethod
    def notificar_criacao_ticket(cls, ticket):
        """
        Notifica sobre a criação de um novo ticket
        
        Args:
            ticket: Objeto Ticket recém-criado
        """
        # Determinar os destinatários (administradores e suporte da empresa)
        from .models import Funcionario
        destinatarios_info = []  # Lista com info de destinatários e seus tipos
        
        # Verificar se o criador é um cliente para notificá-lo também
        tipo_criador = 'cliente'  # Default
        is_criador_cliente = False
        
        try:
            funcionario_criador = Funcionario.objects.filter(usuario=ticket.criado_por).first()
            if funcionario_criador:
                tipo_criador = funcionario_criador.tipo
                is_criador_cliente = funcionario_criador.tipo == 'cliente'
        except Exception as e:
            logger.warning(f"Erro ao determinar tipo do criador {ticket.criado_por.username}: {str(e)}")
        
        # Se o criador for cliente, notificá-lo sobre a abertura do chamado
        if is_criador_cliente and ticket.criado_por.email:
            if ConfiguracaoNotificacao.deve_enviar_notificacao(ticket.criado_por, 'criacao_ticket'):
                destinatarios_info.append({
                    'email': ticket.criado_por.email,
                    'tipo_usuario': tipo_criador,
                    'nome': ticket.criado_por.get_full_name() or ticket.criado_por.username,
                })
        
        # Localizar administradores e suporte da empresa
        funcionarios = Funcionario.objects.filter(
            empresas=ticket.empresa,
            tipo__in=['admin', 'suporte']
        ).select_related('usuario')
        
        for funcionario in funcionarios:
            if funcionario.usuario.email and funcionario.usuario != ticket.criado_por:
                # Verificar preferências de notificação
                if ConfiguracaoNotificacao.deve_enviar_notificacao(funcionario.usuario, 'criacao_ticket'):
                    destinatarios_info.append({
                        'email': funcionario.usuario.email,
                        'tipo_usuario': funcionario.tipo,
                        'nome': funcionario.usuario.get_full_name() or funcionario.usuario.username,
                    })
        
        if not destinatarios_info:
            logger.info(f"Nenhum destinatário para notificação de criação do chamado #{ticket.id}")
            return False
        
        assunto = f"[Helpdesk] Novo chamado criado: #{ticket.id} - {ticket.titulo}"
        template_html = "tickets/emails/novo_ticket.html"
        
        # Envio individual para cada destinatário com contexto personalizado
        sucessos = 0
        for destinatario in destinatarios_info:
            contexto = {
                'ticket': ticket,
                'criador': ticket.criado_por,
                'empresa': ticket.empresa,
                'url_ticket': f"{settings.SITE_URL}/tickets/ticket/{ticket.id}/" if hasattr(settings, 'SITE_URL') else None,
                'tipo_usuario': destinatario['tipo_usuario'],
                'nome_destinatario': destinatario['nome']
            }
            
            success = cls.enviar_email(
                assunto=assunto,
                destinatarios=[destinatario['email']],
                template_html=template_html,
                contexto=contexto
            )
            if success:
                sucessos += 1
                
        return sucessos > 0  # Retorna True se pelo menos um email foi enviado com sucesso

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
                            ('atribuicao', 'alteracao_status', 'novo_comentario', 'criacao_ticket', etc)
        
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
            elif tipo_notificacao == 'novo_comentario':
                return pref.notificar_novo_comentario
            elif tipo_notificacao == 'criacao_ticket':
                return pref.notificar_todas  # Usa a configuração "todas" para notificações de novos tickets
            else:
                # Para qualquer outro tipo que não tenha configuração específica
                return pref.notificar_todas
                
        except Exception as e:
            # Se não existe configuração, assume que deve notificar (default)
            logger.debug(f"Erro ao verificar preferências de notificação para {usuario.username}: {str(e)}")
            return True
            
    @staticmethod
    def criar_preferencias_padrao(usuario):
        """
        Cria preferências de notificação padrão para um usuário caso não existam
        
        Args:
            usuario: Objeto User
            
        Returns:
            PreferenciasNotificacao: Objeto de preferências
        """
        from .models import PreferenciasNotificacao
        try:
            preferencias, criado = PreferenciasNotificacao.objects.get_or_create(
                usuario=usuario,
                defaults={
                    'notificar_todas': True,
                    'notificar_atribuicao': True,
                    'notificar_alteracao_status': True,
                    'notificar_novo_comentario': True,
                    'notificar_prioridade_alterada': True
                }
            )
            
            if criado:
                logger.info(f"Preferências de notificação padrão criadas para {usuario.username}")
                
            return preferencias
        except Exception as e:
            logger.error(f"Erro ao criar preferências de notificação para {usuario.username}: {str(e)}")
            return None 