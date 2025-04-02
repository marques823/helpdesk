from django.contrib import admin
from .models import Empresa, Funcionario, Ticket, Comentario

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cnpj', 'telefone', 'email')
    search_fields = ('nome', 'cnpj', 'email')
    ordering = ('nome',)

@admin.register(Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'empresa', 'tipo', 'telefone', 'cargo')
    list_filter = ('tipo', 'empresa')
    search_fields = ('usuario__username', 'usuario__first_name', 'usuario__last_name', 'empresa__nome')
    ordering = ('empresa__nome', 'usuario__first_name')

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'empresa', 'criado_por', 'status', 'prioridade', 'criado_em')
    list_filter = ('status', 'prioridade', 'empresa')
    search_fields = ('titulo', 'descricao', 'empresa__nome')
    ordering = ('-criado_em',)

@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'autor', 'criado_em')
    list_filter = ('criado_em',)
    search_fields = ('texto', 'autor__username', 'ticket__titulo')
    ordering = ('-criado_em',)
