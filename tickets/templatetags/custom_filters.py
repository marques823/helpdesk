from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Filtro para acessar valores de dicionário pela chave no template
    Uso: {{ dicionario|get_item:chave }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key) 