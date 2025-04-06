from django.urls import path
from . import views, admin_views

app_name = 'tickets'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('ticket/<int:ticket_id>/', views.detalhe_ticket, name='detalhe_ticket'),
    path('ticket/<int:ticket_id>/editar/', views.editar_ticket, name='editar_ticket'),
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
] 