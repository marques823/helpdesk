from django.urls import path
from tickets.api import n8n, auth, dashboard

# Padrões de URL para a API
urlpatterns = [
    # Autenticação
    path('auth/login/', auth.api_login, name='api_login'),
    path('auth/logout/', auth.api_logout, name='api_logout'),
    path('auth/user/', auth.api_user, name='api_user'),
    
    # Dashboard
    path('dashboard/stats/', dashboard.get_dashboard_stats, name='api_dashboard_stats'),
    
    # n8n API Endpoints
    path('n8n/tickets/', n8n.get_tickets, name='api_n8n_tickets'),
    path('n8n/tickets/<int:ticket_id>/', n8n.get_ticket_detail, name='api_n8n_ticket_detail'),
    path('n8n/tickets/<int:ticket_id>/update/', n8n.update_ticket, name='api_n8n_update_ticket'),
    path('n8n/tickets/<int:ticket_id>/comment/', n8n.add_comment, name='api_n8n_add_comment'),
    path('n8n/tickets/create/', n8n.create_ticket, name='api_n8n_create_ticket'),
] 