from django.urls import path
from . import views, admin_views
from tickets import views as tickets_views

app_name = 'tickets'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('ticket/<int:ticket_id>/', views.detalhe_ticket, name='detalhe_ticket'),
    path('ticket/<int:ticket_id>/editar/', views.editar_ticket, name='editar_ticket'),
    path('ticket/<int:ticket_id>/excluir/', views.excluir_ticket, name='excluir_ticket'),
    path('ticket/<int:ticket_id>/atribuir/', views.atribuir_ticket, name='atribuir_ticket'),
    path('ticket/<int:ticket_id>/multi-atribuir/', views.multi_atribuir_ticket, name='multi_atribuir_ticket'),
    path('ticket/<int:ticket_id>/historico/', views.historico_ticket, name='historico_ticket'),
    path('ticket/<int:ticket_id>/notas/', views.listar_notas_tecnicas, name='listar_notas_tecnicas'),
    path('ticket/<int:ticket_id>/notas/adicionar/', views.adicionar_nota_tecnica, name='adicionar_nota_tecnica'),
    path('nota/<int:nota_id>/editar/', views.editar_nota_tecnica, name='editar_nota_tecnica'),
    path('nota/<int:nota_id>/excluir/', views.excluir_nota_tecnica, name='excluir_nota_tecnica'),
    path('novo/', views.criar_ticket, name='criar_ticket'),
    path('empresas/', views.lista_empresas, name='lista_empresas'),
    path('empresas/nova/', views.criar_empresa, name='criar_empresa'),
    path('empresas/<int:pk>/editar/', views.editar_empresa, name='editar_empresa'),
    path('funcionarios/', views.lista_funcionarios, name='lista_funcionarios'),
    path('funcionarios/novo/', views.criar_funcionario, name='criar_funcionario'),
    path('funcionarios/<int:pk>/editar/', views.editar_funcionario, name='editar_funcionario'),
    path('empresas/<int:empresa_id>/campos/', views.gerenciar_campos_personalizados, name='gerenciar_campos_personalizados'),
    path('campos/<int:campo_id>/editar/', views.editar_campo_personalizado, name='editar_campo_personalizado'),
    path('campos/<int:campo_id>/excluir/', views.excluir_campo_personalizado, name='excluir_campo_personalizado'),
    
    path('admin/backups/', admin_views.backup_manager, name='admin_backup_manager'),
    path('admin/backups/download/<int:backup_id>/', admin_views.download_backup, name='admin_backup_download'),
    
    # URLs para relatórios
    path('relatorios/', views.relatorios_menu, name='relatorios_menu'),
    path('relatorios/tickets/', views.relatorio_tickets, name='relatorio_tickets'),
    path('relatorios/empresas/', views.relatorio_empresas, name='relatorio_empresas'),
    path('relatorios/tecnicos/', views.relatorio_tecnicos, name='relatorio_tecnicos'),
    path('relatorios/export/<str:tipo>/', views.exportar_relatorio, name='exportar_relatorio'),
    
    # URLs para perfis de compartilhamento
    path('perfis-compartilhamento/', views.perfis_compartilhamento_list, name='perfis_compartilhamento_list'),
    path('perfil-compartilhamento/novo/', views.perfil_compartilhamento_novo, name='perfil_compartilhamento_novo'),
    path('perfil-compartilhamento/<int:pk>/editar/', views.perfil_compartilhamento_editar, name='perfil_compartilhamento_editar'),
    path('perfil-compartilhamento/<int:pk>/excluir/', views.perfil_compartilhamento_excluir, name='perfil_compartilhamento_excluir'),
    
    # URLs para campos de perfis de compartilhamento
    path('perfil-compartilhamento/<int:perfil_id>/campos/', views.campos_perfil_compartilhamento_list, name='campos_perfil_compartilhamento_list'),
    path('perfil-compartilhamento/<int:perfil_id>/campo/novo/', views.campo_perfil_compartilhamento_novo, name='campo_perfil_compartilhamento_novo'),
    path('campo-perfil-compartilhamento/<int:pk>/editar/', views.campo_perfil_compartilhamento_editar, name='campo_perfil_compartilhamento_editar'),
    path('campo-perfil-compartilhamento/<int:pk>/excluir/', views.campo_perfil_compartilhamento_excluir, name='campo_perfil_compartilhamento_excluir'),
    
    # URL para compartilhar ticket em PDF
    path('ticket/<int:ticket_id>/compartilhar-pdf/', views.compartilhar_ticket_pdf, name='compartilhar_ticket_pdf'),
    
    # URL para obter campos personalizados via AJAX
    path('get-campos-personalizados/', views.get_campos_personalizados, name='get_campos_personalizados'),
    
    # URL para obter categorias por empresa via AJAX
    path('get-categorias-por-empresa/', views.get_categorias_por_empresa, name='get_categorias_por_empresa'),
    
    # Adicione esta URL junto com as outras API URLs
    path('get-estatisticas-categorias/', views.get_estatisticas_categorias, name='get_estatisticas_categorias'),
    
    # Rotas para o painel administrativo de empresas
    path('empresa-admin/', views.empresa_admin_dashboard, name='empresa_admin_dashboard'),
    path('empresa-admin/usuarios/', views.empresa_admin_usuarios, name='empresa_admin_usuarios'),
    path('empresa-admin/usuarios/novo/', views.empresa_admin_criar_usuario, name='empresa_admin_criar_usuario'),
    path('empresa-admin/usuarios/<int:funcionario_id>/editar/', views.empresa_admin_editar_usuario, name='empresa_admin_editar_usuario'),
    path('empresa-admin/config/', views.empresa_admin_config, name='empresa_admin_config'),
    
    # Rotas para gerenciamento de categorias no painel administrativo
    path('empresa-admin/categorias/', views.empresa_admin_categorias, name='empresa_admin_categorias'),
    path('empresa-admin/categorias/nova/', views.empresa_admin_criar_categoria, name='empresa_admin_criar_categoria'),
    path('empresa-admin/categorias/<int:categoria_id>/editar/', views.empresa_admin_editar_categoria, name='empresa_admin_editar_categoria'),
    path('empresa-admin/categorias/<int:categoria_id>/excluir/', views.empresa_admin_excluir_categoria, name='empresa_admin_excluir_categoria'),
    
    # Rotas para gerenciamento de permissões de categoria por usuário
    path('permissoes-categoria/', views.gerenciar_permissoes_categoria, name='gerenciar_permissoes_categoria'),
    path('permissoes-categoria/usuario/<int:funcionario_id>/', views.editar_permissoes_usuario, name='editar_permissoes_usuario'),
    
    # Gerenciamento de preferências de notificação
    path('notificacoes/', views.gerenciar_notificacoes, name='gerenciar_notificacoes'),
    
    # URLs de verificação de email
    path('solicitar-verificacao/', views.solicitar_verificacao_email, name='solicitar_verificacao_email'),
    path('solicitacao-enviada/<int:solicitacao_id>/', views.solicitacao_enviada, name='solicitacao_enviada'),
    path('admin/verificacoes-email/', views.gerenciar_verificacoes_email, name='gerenciar_verificacoes_email'),
    path('admin/verificacoes-email/<int:solicitacao_id>/', views.detalhe_solicitacao_verificacao, name='detalhe_solicitacao_verificacao'),
    path('admin/verificacoes-email/<int:solicitacao_id>/marcar-verificado/', views.marcar_verificado, name='marcar_verificado'),
    path('admin/verificacoes-email/<int:solicitacao_id>/enviar-notificacao/', views.enviar_notificacao, name='enviar_notificacao'),
    path('admin/verificacoes-email/<int:solicitacao_id>/excluir/', views.excluir_solicitacao, name='excluir_solicitacao'),
    path('cadastro/<str:token>/', views.completar_cadastro, name='completar_cadastro'),

    # URLs para gerenciamento de emails verificados
    path('admin/emails-verificados/', views.gerenciar_emails_verificados, name='gerenciar_emails_verificados'),
    path('admin/emails-verificados/adicionar/', views.adicionar_email_verificado, name='adicionar_email_verificado'),
    path('admin/emails-verificados/<int:email_id>/verificar/', views.marcar_email_verificado, name='marcar_email_verificado'),
    path('admin/emails-verificados/<int:email_id>/excluir/', views.excluir_email_verificado, name='excluir_email_verificado'),
    path('admin/emails-verificados/testar-envio/', views.testar_envio_email, name='testar_envio_email'),
] 