from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db import transaction

from .models import Ticket, Comentario, HistoricoTicket, AtribuicaoTicket, PreferenciasNotificacao
from .email_notifications import EmailNotificationService, ConfiguracaoNotificacao

import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def criar_preferencias_notificacao(sender, instance, created, **kwargs):
    """
    Cria automaticamente um registro de preferências de notificação para novos usuários
    """
    if created:
        try:
            PreferenciasNotificacao.objects.create(usuario=instance)
            logger.info(f"Preferências de notificação criadas para o usuário {instance.username}")
        except Exception as e:
            logger.error(f"Erro ao criar preferências de notificação para {instance.username}: {str(e)}")

@receiver(pre_save, sender=Ticket)
def detectar_alteracao_status(sender, instance, **kwargs):
    """
    Detecta alterações de status em tickets antes de salvar
    """
    if instance.pk:  # Se não é um novo ticket
        try:
            # Obtém o ticket original do banco de dados
            ticket_antigo = Ticket.objects.get(pk=instance.pk)
            
            # Verifica se o status foi alterado
            if ticket_antigo.status != instance.status:
                # Salva temporariamente o status anterior no objeto para usar no post_save
                instance._status_anterior = ticket_antigo.status
                instance._status_alterado = True
            else:
                instance._status_alterado = False
                
            # Verifica se a atribuição foi alterada
            if ticket_antigo.atribuido_a != instance.atribuido_a and instance.atribuido_a is not None:
                instance._atribuicao_alterada = True
            else:
                instance._atribuicao_alterada = False
                
        except Ticket.DoesNotExist:
            # Caso seja uma criação de ticket via código não através do ORM
            instance._status_alterado = False
            instance._atribuicao_alterada = False
    else:
        # Novo ticket
        instance._status_alterado = False
        instance._atribuicao_alterada = False

@receiver(post_save, sender=Ticket)
def notificar_alteracoes_ticket(sender, instance, created, **kwargs):
    """
    Envia notificações de e-mail quando o status de um ticket é alterado ou quando é atribuído
    """
    # Se foi um novo ticket criado, notifica os administradores e suporte
    if created:
        try:
            # Espera um pouco para garantir que o ticket foi completamente salvo
            transaction.on_commit(lambda: enviar_notificacao_novo_ticket(instance))
            return
        except Exception as e:
            logger.error(f"Erro ao agendar notificação de novo ticket #{instance.id}: {str(e)}")
        
    # Processar alteração de status    
    if hasattr(instance, '_status_alterado') and instance._status_alterado:
        try:
            # Envia notificação de alteração de status
            status_anterior = instance._status_anterior
            
            # Obter o histórico mais recente para este ticket
            try:
                historico_recente = HistoricoTicket.objects.filter(
                    ticket=instance, 
                    tipo_alteracao='status'
                ).order_by('-data_alteracao').first()
                
                if historico_recente and historico_recente.usuario:
                    usuario_alteracao = historico_recente.usuario
                    logger.info(f"Usuário identificado do histórico: {usuario_alteracao.username}")
                else:
                    usuario_alteracao = instance.criado_por
            except Exception as e:
                logger.error(f"Erro ao obter histórico: {str(e)}")
                usuario_alteracao = instance.criado_por
            
            # Envia a notificação
            EmailNotificationService.notificar_alteracao_status(
                ticket=instance,
                status_anterior=status_anterior,
                usuario_alteracao=usuario_alteracao
            )
            logger.info(f"Notificação de alteração de status enviada para o chamado #{instance.id}")
        except Exception as e:
            logger.error(f"Erro ao enviar notificação de alteração de status para o chamado #{instance.id}: {str(e)}")
    
    # Processar alteração de atribuição
    if hasattr(instance, '_atribuicao_alterada') and instance._atribuicao_alterada:
        try:
            # Verifica preferências de notificação do atribuído
            usuario_atribuido = instance.atribuido_a.usuario
            
            if ConfiguracaoNotificacao.deve_enviar_notificacao(usuario_atribuido, 'atribuicao'):
                # Envia notificação de atribuição
                EmailNotificationService.notificar_atribuicao_ticket(
                    ticket=instance,
                    destinatario_user=usuario_atribuido
                )
                logger.info(f"Notificação de atribuição enviada para {usuario_atribuido.username} sobre o ticket #{instance.id}")
            else:
                logger.info(f"Notificação de atribuição desativada para o usuário {usuario_atribuido.username}")
        except Exception as e:
            logger.error(f"Erro ao enviar notificação de atribuição para o ticket #{instance.id}: {str(e)}")

def enviar_notificacao_novo_ticket(ticket):
    """
    Função auxiliar para enviar notificação de novo ticket
    """
    try:
        EmailNotificationService.notificar_criacao_ticket(ticket)
        logger.info(f"Notificação de novo ticket enviada para o ticket #{ticket.id}")
    except Exception as e:
        logger.error(f"Erro ao enviar notificação de novo ticket #{ticket.id}: {str(e)}")

@receiver(post_save, sender=AtribuicaoTicket)
def notificar_atribuicao_multipla(sender, instance, created, **kwargs):
    """
    Envia notificações quando um ticket é atribuído a múltiplos funcionários
    """
    if created:  # Apenas para novas atribuições
        try:
            # Obter o usuário do funcionário atribuído
            usuario_atribuido = instance.funcionario.usuario
            
            # Verificar preferências de notificação
            if ConfiguracaoNotificacao.deve_enviar_notificacao(usuario_atribuido, 'atribuicao'):
                # Enviar notificação
                EmailNotificationService.notificar_atribuicao_ticket(
                    ticket=instance.ticket,
                    destinatario_user=usuario_atribuido
                )
                logger.info(f"Notificação de atribuição múltipla enviada para {usuario_atribuido.username} sobre o ticket #{instance.ticket.id}")
            else:
                logger.info(f"Notificação de atribuição múltipla desativada para o usuário {usuario_atribuido.username}")
        except Exception as e:
            logger.error(f"Erro ao enviar notificação de atribuição múltipla: {str(e)}")

@receiver(post_save, sender=Comentario)
def notificar_novo_comentario(sender, instance, created, **kwargs):
    """
    Envia notificações quando um novo comentário é adicionado a um ticket
    """
    if created:  # Apenas para novos comentários
        try:
            # Agenda o envio da notificação para após o commit da transação
            transaction.on_commit(lambda: enviar_notificacao_comentario(instance))
        except Exception as e:
            logger.error(f"Erro ao agendar notificação de novo comentário: {str(e)}")

def enviar_notificacao_comentario(comentario):
    """
    Função auxiliar para enviar notificação de novo comentário
    """
    try:
        EmailNotificationService.notificar_novo_comentario(comentario)
        logger.info(f"Notificação de novo comentário enviada para o ticket #{comentario.ticket.id}")
    except Exception as e:
        logger.error(f"Erro ao enviar notificação de novo comentário no ticket #{comentario.ticket.id}: {str(e)}") 