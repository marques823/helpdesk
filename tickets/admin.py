from django.contrib import admin
from .models import (
    Empresa, Funcionario, Ticket, Comentario, HistoricoTicket,
    CategoriaChamado, CampoPersonalizado, ValorCampoPersonalizado,
    EmpresaConfig, AtribuicaoTicket, PerfilCompartilhamento, 
    CampoPerfilCompartilhamento, NotaTecnica, PreferenciasNotificacao
)
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

@admin.register(EmpresaConfig)
class EmpresaConfigAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'limite_usuarios', 'usuarios_criados', 'ativo')
    list_filter = ('ativo', 'pode_criar_categorias', 'pode_criar_campos_personalizados', 'pode_acessar_relatorios')
    search_fields = ('empresa__nome', 'empresa__cnpj')
    readonly_fields = ('criado_em', 'atualizado_em', 'usuarios_criados')
    
    fieldsets = (
        (None, {
            'fields': ('empresa', 'ativo')
        }),
        ('Limites e Permissões', {
            'fields': ('limite_usuarios', 'usuarios_criados', 'pode_criar_categorias', 'pode_criar_campos_personalizados', 'pode_acessar_relatorios')
        }),
        ('API', {
            'fields': ('token_api',),
            'classes': ('collapse',)
        }),
        ('Informações do Sistema', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )
    
    def usuarios_criados(self, obj):
        """Retorna o número de usuários criados pela empresa"""
        count = obj.usuarios_criados()
        limit = obj.limite_usuarios
        return f"{count} de {limit} ({(count / limit * 100):.0f}%)"
    usuarios_criados.short_description = "Usuários Criados"
    
    def save_model(self, request, obj, form, change):
        if not change:  # Se for uma nova instância
            obj.criado_em = timezone.now()
        obj.atualizado_em = timezone.now()
        super().save_model(request, obj, form, change)

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
    list_display = ('id', 'titulo', 'empresa', 'categoria', 'status', 'prioridade', 'criado_por', 'atribuido_a', 'criado_em')
    list_filter = ('status', 'prioridade', 'empresa', 'categoria', 'criado_em')
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

@admin.register(AtribuicaoTicket)
class AtribuicaoTicketAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'funcionario', 'principal', 'criado_em')
    list_filter = ('principal', 'criado_em')
    search_fields = ('ticket__titulo', 'funcionario__usuario__username')
    readonly_fields = ('criado_em', 'atualizado_em')

    def save_model(self, request, obj, form, change):
        if not change:  # Se for uma nova instância
            obj.criado_em = timezone.now()
        obj.atualizado_em = timezone.now()
        super().save_model(request, obj, form, change)

@admin.register(PerfilCompartilhamento)
class PerfilCompartilhamentoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'empresa', 'is_padrao', 'incluir_notas_tecnicas', 'incluir_historico', 'incluir_comentarios', 'criado_por')
    list_filter = ('empresa', 'is_padrao', 'incluir_notas_tecnicas', 'incluir_historico', 'incluir_comentarios')
    search_fields = ('nome', 'descricao', 'empresa__nome')
    readonly_fields = ('criado_em', 'atualizado_em')
    
    fieldsets = (
        (None, {
            'fields': ('nome', 'descricao', 'empresa', 'is_padrao')
        }),
        ('Opções de Conteúdo', {
            'fields': ('incluir_notas_tecnicas', 'incluir_historico', 'incluir_comentarios', 'incluir_campos_personalizados')
        }),
        ('Informações do Sistema', {
            'fields': ('criado_por', 'criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Se for uma nova instância
            obj.criado_por = request.user
            obj.criado_em = timezone.now()
        obj.atualizado_em = timezone.now()
        super().save_model(request, obj, form, change)

@admin.register(CampoPerfilCompartilhamento)
class CampoPerfilCompartilhamentoAdmin(admin.ModelAdmin):
    list_display = ('nome_campo', 'perfil', 'tipo_campo', 'ordem')
    list_filter = ('perfil__empresa', 'perfil', 'tipo_campo')
    search_fields = ('nome_campo', 'perfil__nome')
    raw_id_fields = ('perfil', 'campo_personalizado')
    
    fieldsets = (
        (None, {
            'fields': ('perfil', 'tipo_campo', 'nome_campo', 'ordem')
        }),
        ('Campo Personalizado', {
            'fields': ('campo_personalizado',),
            'classes': ('collapse',),
            'description': 'Apenas para campos do tipo "Campo Personalizado"'
        }),
    )

@admin.register(CategoriaChamado)
class CategoriaChamadoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'empresa', 'cor', 'ordem', 'ativo')
    list_filter = ('empresa', 'ativo')
    search_fields = ('nome', 'descricao')
    ordering = ('empresa', 'ordem', 'nome')
    readonly_fields = ('criado_em', 'atualizado_em')
    fieldsets = (
        (None, {
            'fields': ('nome', 'descricao', 'empresa', 'cor', 'icone', 'ordem', 'ativo')
        }),
        ('Informações de Sistema', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )

@admin.register(PreferenciasNotificacao)
class PreferenciasNotificacaoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'notificar_todas', 'notificar_atribuicao', 'notificar_alteracao_status', 'atualizado_em')
    list_filter = ('notificar_todas', 'notificar_atribuicao', 'notificar_alteracao_status')
    search_fields = ('usuario__username', 'usuario__email')
    raw_id_fields = ('usuario',)
