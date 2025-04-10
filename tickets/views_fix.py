from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import connection
import logging

from .models import Empresa, Funcionario, CategoriaPermissao, CategoriaChamado

# Configurar o logger
logger = logging.getLogger(__name__)

@login_required
def gerenciar_permissoes_categoria(request):
    """
    View para gerenciar as permissões de categorias dos funcionários.
    """
    # DEBUG
    logger.info("***** FUNÇÃO SIMPLIFICADA *****")
    
    # Verifica se o usuário é admin ou superuser, redirecionando caso não seja
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, 'Você não tem permissão para acessar esta página.')
        return redirect('tickets:dashboard')
    
    try:
        # Obtém apenas as empresas às quais o usuário tem acesso
        if request.user.is_superuser:
            # Superusuários veem todas as empresas
            empresas = Empresa.objects.all().order_by('nome')
        else:
            # Funcionários administrativos veem apenas as empresas associadas a eles
            funcionario = request.user.funcionarios.first()
            if funcionario and funcionario.is_admin():
                empresas = funcionario.empresas.all().order_by('nome')
            else:
                empresas = Empresa.objects.none()
        
        empresa_id = request.GET.get('empresa')
        empresa_selecionada = None
        funcionarios_dados = []
        
        # Se uma empresa foi selecionada
        if empresa_id:
            try:
                # Verificar se a empresa selecionada está entre as empresas permitidas
                empresa_selecionada = empresas.get(id=empresa_id)
                
                # Versão simplificada usando apenas o ORM
                funcionarios = Funcionario.objects.filter(empresas=empresa_selecionada)
                
                # Para cada funcionário, preparar os dados para exibição
                for funcionario in funcionarios:
                    # Contar categorias permitidas
                    categorias_count = CategoriaPermissao.objects.filter(
                        funcionario=funcionario,
                        categoria__empresa=empresa_selecionada
                    ).count()
                    
                    usuario = funcionario.usuario
                    
                    # Criar dados do funcionário para exibição
                    funcionario_data = {
                        'id': funcionario.id,
                        'tipo': funcionario.tipo,
                        'tipo_display': dict(Funcionario.TIPO_CHOICES).get(funcionario.tipo, funcionario.tipo),
                        'username': usuario.username,
                        'first_name': usuario.first_name or '',
                        'last_name': usuario.last_name or '',
                        'email': usuario.email or '',
                        'categorias_count': categorias_count
                    }
                    
                    funcionarios_dados.append(funcionario_data)
            
            except Empresa.DoesNotExist:
                messages.error(request, 'Empresa não encontrada ou você não tem permissão para acessá-la.')
                return redirect('tickets:gerenciar_permissoes_categoria')
        
        context = {
            'empresas': empresas,
            'empresa_selecionada': empresa_selecionada,
            'funcionarios_dados': funcionarios_dados,
        }
        
        return render(request, 'tickets/admin/permissoes_categoria.html', context)
        
    except Exception as e:
        logger.exception(f"Erro ao gerenciar permissões de categoria: {str(e)}")
        messages.error(request, f"Ocorreu um erro ao gerenciar permissões: {str(e)}")
        return redirect('tickets:gerenciar_permissoes_categoria')

@login_required
def editar_permissoes_usuario(request, funcionario_id):
    """
    View para editar as permissões de categorias de um funcionário específico.
    """
    # Verifica se o usuário é admin ou superuser
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, 'Você não tem permissão para acessar esta página.')
        return redirect('tickets:dashboard')
    
    try:
        # Obter o funcionário
        funcionario = get_object_or_404(Funcionario, id=funcionario_id)
        
        # Obter a empresa selecionada
        empresa_id = request.GET.get('empresa')
        if not empresa_id:
            messages.error(request, 'É necessário selecionar uma empresa.')
            return redirect('tickets:gerenciar_permissoes_categoria')
        
        # Obtém apenas as empresas às quais o usuário tem acesso
        if request.user.is_superuser:
            # Superusuários veem todas as empresas
            empresas = Empresa.objects.all()
            empresa_selecionada = get_object_or_404(Empresa, id=empresa_id)
        else:
            # Funcionários administrativos veem apenas as empresas associadas a eles
            funcionario_logado = request.user.funcionarios.first()
            if not funcionario_logado or not funcionario_logado.is_admin():
                messages.error(request, 'Você não tem permissão para acessar esta página.')
                return redirect('tickets:dashboard')
                
            empresas = funcionario_logado.empresas.all()
            try:
                # Verifica se a empresa selecionada está entre as empresas permitidas
                empresa_selecionada = empresas.get(id=empresa_id)
            except Empresa.DoesNotExist:
                messages.error(request, 'Você não tem permissão para gerenciar esta empresa.')
                return redirect('tickets:gerenciar_permissoes_categoria')
        
        # Verificar se o funcionário tem acesso à empresa selecionada
        if not funcionario.empresas.filter(id=empresa_selecionada.id).exists():
            messages.error(request, 'Este funcionário não pertence à empresa selecionada.')
            return redirect('tickets:gerenciar_permissoes_categoria')
        
        # Obter todas as categorias da empresa
        categorias = CategoriaChamado.objects.filter(empresa=empresa_selecionada)
        
        # Obter as categorias permitidas para o funcionário nesta empresa
        categorias_permitidas = CategoriaPermissao.objects.filter(
            funcionario=funcionario,
            categoria__empresa=empresa_selecionada
        )
        categorias_permitidas_ids = [cp.categoria.id for cp in categorias_permitidas]
        
        if request.method == 'POST':
            # Recebe os IDs das categorias enviadas no formulário
            categoria_ids = request.POST.getlist('categorias')
            
            # Remove todas as permissões existentes para esta empresa
            CategoriaPermissao.objects.filter(
                funcionario=funcionario,
                categoria__empresa=empresa_selecionada
            ).delete()
            
            # Adiciona as novas permissões selecionadas
            if categoria_ids:
                for cat_id in categoria_ids:
                    try:
                        categoria = CategoriaChamado.objects.get(id=cat_id, empresa=empresa_selecionada)
                        CategoriaPermissao.objects.create(
                            funcionario=funcionario,
                            categoria=categoria
                        )
                    except Exception as e:
                        logger.error(f"Erro ao adicionar categoria {cat_id}: {str(e)}")
            
            messages.success(request, f'Permissões de {funcionario.usuario.get_full_name() or funcionario.usuario.username} atualizadas com sucesso.')
            return redirect('tickets:gerenciar_permissoes_categoria')
        
        context = {
            'funcionario': funcionario,
            'empresas': empresas,
            'empresa_selecionada': empresa_selecionada,
            'categorias': categorias,
            'categorias_permitidas_ids': categorias_permitidas_ids,
        }
        
        return render(request, 'tickets/admin/editar_permissoes_usuario.html', context)
        
    except Exception as e:
        logger.exception(f"Erro ao editar permissões de usuário: {str(e)}")
        messages.error(request, f"Ocorreu um erro ao editar permissões: {str(e)}")
        return redirect('tickets:gerenciar_permissoes_categoria') 