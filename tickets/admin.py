from django.contrib import admin
from .models import Empresa, Funcionario, Ticket, Comentario, HistoricoTicket, CampoPersonalizado, ValorCampoPersonalizado, NotaTecnica
from django.utils import timezone
from django.urls import path
from . import admin_views

# Obtém uma referência para o site de administração existente
admin_site = admin.site

# Adiciona URLs personalizadas ao site de administração padrão
original_get_urls = admin_site.get_urls

def custom_get_urls():
    urls = original_get_urls()
    urls += [
        path('backups/', admin_views.backup_manager, name='backup_manager'),
        path('backups/download/<int:backup_id>/', admin_views.download_backup, name='backup_download'),
    ]
    return urls

admin_site.get_urls = custom_get_urls

# Registramos todos os nossos modelos normalmente
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
    list_display = ('nome', 'empresa', 'tipo', 'obrigatorio', 'ativo', 'editavel')
    list_filter = ('empresa', 'tipo', 'obrigatorio', 'ativo', 'editavel')
    search_fields = ('nome', 'empresa__nome')
    readonly_fields = ('criado_em', 'atualizado_em')
    fieldsets = (
        (None, {
            'fields': ('empresa', 'nome', 'tipo', 'obrigatorio')
        }),
        ('Opções avançadas', {
            'fields': ('opcoes', 'ordem', 'ativo', 'editavel')
        }),
        ('Datas', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # Se for uma nova instância
            obj.criado_em = timezone.now()
        obj.atualizado_em = timezone.now()
        super().save_model(request, obj, form, change)

@admin.register(ValorCampoPersonalizado)
class ValorCampoPersonalizadoAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'campo', 'valor')
    list_filter = ('campo__empresa', 'campo__nome')
    search_fields = ('ticket__titulo', 'campo__nome', 'valor')
    readonly_fields = ('criado_em', 'atualizado_em')
    
    def save_model(self, request, obj, form, change):
        if not change:  # Se for uma nova instância
            obj.criado_em = timezone.now()
        obj.atualizado_em = timezone.now()
        super().save_model(request, obj, form, change)

@admin.register(NotaTecnica)
class NotaTecnicaAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'tecnico', 'equipamento', 'criado_em')
    list_filter = ('tecnico', 'criado_em')
    search_fields = ('ticket__titulo', 'descricao', 'equipamento', 'solucao_aplicada')
    readonly_fields = ('criado_em', 'atualizado_em')
    
    fieldsets = (
        (None, {
            'fields': ('ticket', 'tecnico', 'descricao')
        }),
        ('Detalhes técnicos', {
            'fields': ('equipamento', 'solucao_aplicada', 'pendencias')
        }),
        ('Datas', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Se for uma nova instância
            obj.criado_em = timezone.now()
        obj.atualizado_em = timezone.now()
        super().save_model(request, obj, form, change)
