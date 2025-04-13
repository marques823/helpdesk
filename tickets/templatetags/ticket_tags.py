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
        'pending': 'warning',
        'open': 'primary',
        'in_progress': 'info',
        'resolved': 'success',
        'closed': 'secondary',
        'reopened': 'danger',
        
        # Nomes antigos/alternativos para compatibilidade
        'aberto': 'primary',
        'em_andamento': 'warning',
        'pendente': 'info',
        'resolvido': 'success',
        'fechado': 'secondary',
    }
    return color_map.get(status, 'secondary')

@register.filter
def status_text_color(status):
    """Retorna a cor do texto para o status específico"""
    return f"text-{status_color(status)}"

@register.filter
def prioridade_color(prioridade):
    color_map = {
        'low': 'success',
        'medium': 'warning',
        'high': 'danger',
        'critical': 'danger',
        
        # Nomes antigos/alternativos para compatibilidade
        'baixa': 'success',
        'media': 'info',
        'alta': 'warning',
        'urgente': 'danger',
    }
    return color_map.get(prioridade, 'secondary')

@register.filter
def prioridade_text_color(prioridade):
    """Retorna a cor do texto para a prioridade específica"""
    return f"text-{prioridade_color(prioridade)}"

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
    """Obter o nome da empresa pelo ID"""
    try:
        from tickets.models import Empresa
        empresa = Empresa.objects.get(id=empresa_id)
        return empresa.nome
    except (Empresa.DoesNotExist, ValueError):
        return "Desconhecida"

@register.filter
def get_categoria_nome(categoria_id):
    """Obter o nome da categoria pelo ID"""
    try:
        from tickets.models import CategoriaChamado
        categoria = CategoriaChamado.objects.get(id=categoria_id)
        return categoria.nome
    except (CategoriaChamado.DoesNotExist, ValueError):
        return "Desconhecida"

@register.filter
def get_item(dictionary, key):
    """Retorna o valor de um dicionário a partir de uma chave"""
    if not dictionary:
        return None
    return dictionary.get(str(key))

@register.filter
def truncate_text(text, length=100):
    """Truncar texto para o comprimento especificado, adicionando '...' se necessário"""
    if not text:
        return ""
    
    if len(text) <= length:
        return text
    
    return text[:length] + "..."

@register.filter
def values_differ(value1, value2):
    """Verifica se dois valores são diferentes, considerando tipos e representações em string"""
    # Converter para string para comparação uniforme
    str_value1 = str(value1).strip() if value1 is not None else ""
    str_value2 = str(value2).strip() if value2 is not None else ""
    
    # Verifica se as strings são diferentes
    return str_value1 != str_value2

@register.filter
def split(value, delimiter):
    """Divide uma string usando o delimitador e retorna a lista resultante"""
    if not value:
        return []
    return value.split(delimiter)

@register.filter
def get_domain(email):
    """Extrai e retorna o domínio de um endereço de email"""
    if not email or '@' not in email:
        return ""
    return email.split('@')[-1] 