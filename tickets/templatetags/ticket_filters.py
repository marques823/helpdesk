from django import template

register = template.Library()

@register.filter
def status_color(status):
    color_map = {
        'aberto': 'danger',
        'em_andamento': 'primary',
        'pendente': 'warning',
        'resolvido': 'success',
        'fechado': 'secondary'
    }
    return color_map.get(status, 'secondary') 

@register.filter
def mul(value, arg):
    """Multiplica o valor pelo argumento"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def div(value, arg):
    """Divide o valor pelo argumento"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0 