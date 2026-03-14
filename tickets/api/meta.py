from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..models import Empresa, CategoriaChamado, Funcionario

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_companies(request):
    """
    Retorna a lista de empresas que o usuário tem acesso.
    """
    try:
        # Se for superusuário, retorna todas
        if request.user.is_superuser:
            empresas = Empresa.objects.all()
        else:
            # Caso contrário, retorna apenas as empresas associadas ao perfil de funcionário
            funcionario = Funcionario.objects.filter(usuario=request.user).first()
            if not funcionario:
                return Response([], status=200)
            empresas = funcionario.empresas.all()
        
        data = [{'id': e.id, 'nome': e.nome} for e in empresas]
        return Response(data)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_categories(request):
    """
    Retorna a lista de categorias para uma determinada empresa.
    Query params: empresa_id
    """
    try:
        empresa_id = request.GET.get('empresa_id')
        if not empresa_id:
            return Response({"error": "empresa_id é obrigatório"}, status=400)
            
        # Verifica acesso à empresa
        if not request.user.is_superuser:
            funcionario = Funcionario.objects.filter(usuario=request.user).first()
            if not funcionario or not funcionario.empresas.filter(id=empresa_id).exists():
                return Response({"error": "Sem permissão para esta empresa"}, status=403)
        
        categorias = CategoriaChamado.objects.filter(empresa_id=empresa_id, ativo=True)
        data = [
            {
                'id': c.id, 
                'nome': c.nome, 
                'cor': c.cor, 
                'icone': c.icone
            } for c in categorias
        ]
        return Response(data)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_employees(request):
    """
    Retorna a lista de funcionários de uma empresa (para atribuição).
    Query params: empresa_id
    """
    try:
        empresa_id = request.GET.get('empresa_id')
        if not empresa_id:
            return Response({"error": "empresa_id é obrigatório"}, status=400)
            
        # Verifica acesso à empresa
        if not request.user.is_superuser:
            funcionario_req = Funcionario.objects.filter(usuario=request.user).first()
            if not funcionario_req or not funcionario_req.empresas.filter(id=empresa_id).exists():
                return Response({"error": "Sem permissão para esta empresa"}, status=403)
        
        # Retorna funcionários que pertencem a essa empresa
        funcionarios = Funcionario.objects.filter(empresas__id=empresa_id).select_related('usuario')
        data = [
            {
                'id': f.id, 
                'username': f.usuario.username,
                'nome_completo': f.usuario.get_full_name(),
                'tipo': f.tipo
            } for f in funcionarios
        ]
        return Response(data)
    except Exception as e:
        return Response({"error": str(e)}, status=500)
