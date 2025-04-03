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