from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from tickets.api import n8n, auth, dashboard, meta, mobile

# Padrões de URL para a API
urlpatterns = [
    # Autenticação
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/login/', auth.api_login, name='api_login'), # Mantendo compatibilidade temporária
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

    # Meta Endpoints
    path('meta/companies/', meta.get_companies, name='api_meta_companies'),
    path('meta/categories/', meta.get_categories, name='api_meta_categories'),
    path('meta/employees/', meta.get_employees, name='api_meta_employees'),

    # Mobile/Session Endpoints
    path('mobile/tickets/', mobile.list_tickets, name='api_mobile_tickets'),
    path('mobile/tickets/<int:ticket_id>/', mobile.ticket_detail, name='api_mobile_ticket_detail'),
    path('mobile/tickets/create/', mobile.create_ticket, name='api_mobile_create_ticket'),
    path('mobile/tickets/<int:ticket_id>/comment/', mobile.add_comment, name='api_mobile_add_comment'),
    path('mobile/tickets/<int:ticket_id>/status/', mobile.update_ticket_status, name='api_mobile_update_ticket_status'),
]