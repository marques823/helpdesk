from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('ticket/novo/', views.criar_ticket, name='criar_ticket'),
    path('ticket/<int:ticket_id>/', views.detalhe_ticket, name='detalhe_ticket'),
    path('ticket/<int:ticket_id>/editar/', views.editar_ticket, name='editar_ticket'),
    path('ticket/<int:ticket_id>/atribuir/', views.atribuir_ticket, name='atribuir_ticket'),
    path('ticket/<int:ticket_id>/historico/', views.historico_ticket, name='historico_ticket'),
    path('empresas/', views.lista_empresas, name='lista_empresas'),
    path('funcionarios/', views.lista_funcionarios, name='lista_funcionarios'),
] 