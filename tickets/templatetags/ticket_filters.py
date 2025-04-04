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