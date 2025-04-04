from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('ticket/<int:ticket_id>/', views.detalhe_ticket, name='detalhe_ticket'),
    path('ticket/<int:ticket_id>/editar/', views.editar_ticket, name='editar_ticket'),
    path('ticket/<int:ticket_id>/atribuir/', views.atribuir_ticket, name='atribuir_ticket'),
    path('ticket/<int:ticket_id>/historico/', views.historico_ticket, name='historico_ticket'),
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
] 