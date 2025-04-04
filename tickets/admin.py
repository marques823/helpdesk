from django.contrib import admin
from .models import Empresa, Funcionario, Ticket, Comentario, HistoricoTicket, CampoPersonalizado, ValorCampoPersonalizado

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cnpj', 'telefone', 'email')
    search_fields = ('nome', 'cnpj', 'email')
    ordering = ('nome',)

@admin.register(Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'get_empresas', 'tipo', 'telefone', 'cargo')
    list_filter = ('tipo', 'empresas')
    search_fields = ('usuario__username', 'usuario__first_name', 'usuario__last_name', 'telefone')
    filter_horizontal = ('empresas',)
    
    def get_empresas(self, obj):
        return ", ".join([empresa.nome for empresa in obj.empresas.all()])
    get_empresas.short_description = 'Empresas'

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'empresa', 'status', 'prioridade', 'criado_por', 'atribuido_a', 'criado_em')
    list_filter = ('status', 'prioridade', 'empresa', 'criado_em')
    search_fields = ('titulo', 'descricao', 'criado_por__username', 'atribuido_a__usuario__username')
    date_hierarchy = 'criado_em'

@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'autor', 'criado_em')
    search_fields = ('ticket__titulo', 'autor__username', 'texto')
    date_hierarchy = 'criado_em'

@admin.register(HistoricoTicket)
class HistoricoTicketAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'tipo_alteracao', 'usuario', 'data_alteracao')
    list_filter = ('tipo_alteracao', 'data_alteracao')
    search_fields = ('ticket__titulo', 'usuario__username', 'descricao')
    date_hierarchy = 'data_alteracao'

@admin.register(CampoPersonalizado)
class CampoPersonalizadoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'empresa', 'tipo', 'obrigatorio', 'ordem', 'ativo')
    list_filter = ('empresa', 'tipo', 'obrigatorio', 'ativo')
    search_fields = ('nome', 'empresa__nome')
    list_editable = ('ordem', 'ativo')

@admin.register(ValorCampoPersonalizado)
class ValorCampoPersonalizadoAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'campo', 'valor')
    list_filter = ('campo__empresa', 'campo__nome')
    search_fields = ('ticket__titulo', 'campo__nome', 'valor')
