from django import template

register = template.Library()

@register.filter
def pode_editar(funcionario, ticket):
    try:
        if funcionario:
            return funcionario.pode_editar_ticket(ticket)
        return False
    except:
        return False

@register.filter
def pode_atribuir(funcionario, ticket):
    try:
        if funcionario:
            return funcionario.pode_atribuir_ticket(ticket)
        return False
    except:
        return False

@register.filter
def pode_ver(funcionario, ticket):
    try:
        if funcionario:
            return funcionario.pode_ver_ticket(ticket)
        return False
    except:
        return False

@register.filter
def status_color(status):
    color_map = {
        'aberto': 'primary',
        'em_andamento': 'warning',
        'pendente': 'info',
        'resolvido': 'success',
        'fechado': 'secondary',
    }
    return color_map.get(status, 'secondary')

@register.filter
def prioridade_color(prioridade):
    color_map = {
        'baixa': 'success',
        'media': 'info',
        'alta': 'warning',
        'urgente': 'danger',
    }
    return color_map.get(prioridade, 'secondary')

@register.filter
def get_status_label(status_value):
    from tickets.models import Ticket
    for status_choice in Ticket.STATUS_CHOICES:
        if status_choice[0] == status_value:
            return status_choice[1]
    return status_value

@register.filter
def get_prioridade_label(prioridade_value):
    from tickets.models import Ticket
    for prioridade_choice in Ticket.PRIORIDADE_CHOICES:
        if prioridade_choice[0] == prioridade_value:
            return prioridade_choice[1]
    return prioridade_value

@register.filter
def get_empresa_nome(empresa_id):
    from tickets.models import Empresa
    try:
        return Empresa.objects.get(id=empresa_id).nome
    except (Empresa.DoesNotExist, ValueError):
        return empresa_id 