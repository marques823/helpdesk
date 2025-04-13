from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Empresa(models.Model):
    nome = models.CharField(max_length=200)
    cnpj = models.CharField(max_length=14, unique=True)
    telefone = models.CharField(max_length=20)
    email = models.EmailField()
    endereco = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'

class EmpresaConfig(models.Model):
    """
    Configurações específicas para cada empresa, incluindo limites e permissões administrativas.
    """
    empresa = models.OneToOneField(Empresa, on_delete=models.CASCADE, related_name='config')
    limite_usuarios = models.IntegerField(default=5, help_text="Número máximo de usuários que a empresa pode criar")
    pode_criar_categorias = models.BooleanField(default=True, help_text="Se a empresa pode criar categorias de chamados")
    pode_criar_campos_personalizados = models.BooleanField(default=True, help_text="Se a empresa pode criar campos personalizados")
    pode_acessar_relatorios = models.BooleanField(default=True, help_text="Se a empresa pode acessar relatórios")
    token_api = models.CharField(max_length=64, blank=True, null=True, help_text="Token para acesso à API")
    ativo = models.BooleanField(default=True, help_text="Se as funcionalidades administrativas da empresa estão ativas")
    criado_em = models.DateTimeField(default=timezone.now)
    atualizado_em = models.DateTimeField(default=timezone.now)
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.criado_em = timezone.now()
        self.atualizado_em = timezone.now()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Configurações de {self.empresa.nome}"
    
    def usuarios_criados(self):
        """Retorna o número de usuários criados pela empresa"""
        from tickets.models import Funcionario
        return Funcionario.objects.filter(empresas=self.empresa).count()
    
    def pode_criar_mais_usuarios(self):
        """Verifica se a empresa pode criar mais usuários"""
        return self.usuarios_criados() < self.limite_usuarios
    
    class Meta:
        verbose_name = 'Configuração de Empresa'
        verbose_name_plural = 'Configurações de Empresas'

class CategoriaChamado(models.Model):
    """
    Modelo para categorias de chamados, permitindo agrupar tickets por tipo de problema.
    """
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='categorias')
    cor = models.CharField(max_length=20, default='primary', help_text='Nome da cor Bootstrap (primary, success, danger, etc)')
    icone = models.CharField(max_length=50, default='fa-ticket-alt', help_text='Nome do ícone FontAwesome')
    ordem = models.IntegerField(default=0)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(default=timezone.now)
    atualizado_em = models.DateTimeField(default=timezone.now)
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.criado_em = timezone.now()
        self.atualizado_em = timezone.now()
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.nome} - {self.empresa.nome}"
        
    class Meta:
        verbose_name = 'Categoria de Chamado'
        verbose_name_plural = 'Categorias de Chamados'
        unique_together = ['nome', 'empresa']
        ordering = ['ordem', 'nome']

class CategoriaPermissao(models.Model):
    """
    Modelo para atribuir permissões de acesso a categorias específicas para funcionários individuais.
    """
    funcionario = models.ForeignKey('Funcionario', on_delete=models.CASCADE, related_name='categorias_permitidas')
    categoria = models.ForeignKey(CategoriaChamado, on_delete=models.CASCADE, related_name='permissoes')
    criado_em = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.funcionario.usuario.username} - {self.categoria.nome}"
    
    class Meta:
        verbose_name = 'Permissão de Categoria'
        verbose_name_plural = 'Permissões de Categorias'
        unique_together = ['funcionario', 'categoria']

class Funcionario(models.Model):
    TIPO_CHOICES = [
        ('admin', 'Administrador'),
        ('suporte', 'Suporte'),
        ('cliente', 'Cliente'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='funcionarios')
    empresas = models.ManyToManyField(Empresa, related_name='funcionarios')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    telefone = models.CharField(max_length=20, blank=True)
    cargo = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return f"{self.usuario.username} - {self.get_tipo_display()}"
    
    def is_admin(self):
        return self.tipo == 'admin'
    
    def is_suporte(self):
        return self.tipo == 'suporte'
    
    def is_cliente(self):
        return self.tipo == 'cliente'
    
    def get_empresas(self):
        return self.empresas.all()
    
    def tem_acesso_empresa(self, empresa):
        return self.empresas.filter(id=empresa.id).exists()
    
    def pode_ver_ticket(self, ticket):
        # Verifica se o funcionário tem acesso à empresa do ticket
        if not self.tem_acesso_empresa(ticket.empresa):
            return False
        
        # Admin da empresa pode ver todos os tickets da empresa
        if self.is_admin():
            return True
        
        # Suporte pode ver todos os tickets da empresa
        if self.is_suporte():
            return True
        
        # Cliente só pode ver seus próprios tickets ou tickets atribuídos a ele
        if self.is_cliente():
            return ticket.criado_por == self.usuario or ticket.atribuicoes.filter(funcionario=self).exists() or ticket.atribuido_a == self
        
        return False
    
    def pode_criar_ticket(self, empresa):
        # Verifica se o funcionário tem acesso à empresa
        if not self.tem_acesso_empresa(empresa):
            return False
        
        # Todos os tipos de usuários (admin, suporte e cliente) podem criar tickets
        return True
    
    def pode_editar_ticket(self, ticket):
        # Verifica se o funcionário tem acesso à empresa do ticket
        if not self.tem_acesso_empresa(ticket.empresa):
            return False
        
        # Admin da empresa pode editar qualquer ticket da empresa
        if self.is_admin():
            return True
        
        # Suporte pode editar tickets da empresa
        if self.is_suporte():
            return True
        
        # Cliente só pode editar seus próprios tickets
        if self.is_cliente():
            return ticket.criado_por == self.usuario
        
        return False
    
    def pode_atribuir_ticket(self, ticket):
        # Verifica se o funcionário tem acesso à empresa do ticket
        if not self.tem_acesso_empresa(ticket.empresa):
            return False
        
        # Admin e suporte podem atribuir tickets
        return self.is_admin() or self.is_suporte()
    
    def pode_comentar_ticket(self):
        # Admin, suporte e cliente podem comentar em tickets que têm acesso
        return True
    
    def pode_comentar_ticket_especifico(self, ticket):
        # Verifica se o funcionário tem acesso à empresa do ticket
        if not self.tem_acesso_empresa(ticket.empresa):
            return False
        
        # Admin, suporte e cliente podem comentar em tickets que têm acesso
        return True
    
    def tem_acesso_categoria(self, categoria):
        """
        Verifica se o funcionário tem acesso à categoria especificada.
        Administradores e suporte têm acesso a todas as categorias da empresa.
        Clientes só têm acesso às categorias explicitamente permitidas.
        """
        # Primeiro, verifica se a categoria pertence a uma empresa que o funcionário tem acesso
        if not self.tem_acesso_empresa(categoria.empresa):
            return False
        
        # Administradores e suporte têm acesso a todas as categorias
        if self.is_admin() or self.is_suporte():
            return True
        
        # Clientes só têm acesso às categorias explicitamente permitidas
        if self.is_cliente():
            return self.categorias_permitidas.filter(categoria=categoria).exists()
        
        return False
    
    def get_categorias_permitidas(self, empresa=None):
        """
        Retorna as categorias que o funcionário tem acesso.
        Para admin, retorna todas as categorias da empresa.
        Para suporte e clientes, retorna apenas as categorias explicitamente permitidas.
        """
        if empresa:
            # Verifica se o funcionário tem acesso à empresa
            if not self.tem_acesso_empresa(empresa):
                return CategoriaChamado.objects.none()
                
            # Para admin, retorna todas as categorias da empresa
            if self.is_admin():
                return CategoriaChamado.objects.filter(empresa=empresa, ativo=True)
            
            # Para suporte e clientes, retorna apenas categorias permitidas
            return CategoriaChamado.objects.filter(
                permissoes__funcionario=self,
                empresa=empresa,
                ativo=True
            ).distinct()
        else:
            # Se empresa não for especificada, considerar todas as empresas que o funcionário tem acesso
            empresas = self.empresas.all()
            
            # Para admin, retorna todas as categorias das empresas
            if self.is_admin():
                return CategoriaChamado.objects.filter(empresa__in=empresas, ativo=True)
            
            # Para suporte e clientes, retorna apenas categorias permitidas
            return CategoriaChamado.objects.filter(
                permissoes__funcionario=self,
                empresa__in=empresas,
                ativo=True
            ).distinct()
        
        return CategoriaChamado.objects.none()
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Atualiza as permissões do usuário baseado no tipo
        if self.is_admin():
            self.usuario.is_staff = True
            self.usuario.is_superuser = True
            self.usuario.save()
        elif self.is_suporte():
            self.usuario.is_staff = True
            self.usuario.is_superuser = False
            self.usuario.save()
        else:  # cliente
            self.usuario.is_staff = False
            self.usuario.is_superuser = False
            self.usuario.save()

class Ticket(models.Model):
    STATUS_CHOICES = [
        ('aberto', 'Aberto'),
        ('em_andamento', 'Em Andamento'),
        ('pendente', 'Pendente'),
        ('resolvido', 'Resolvido'),
        ('fechado', 'Fechado'),
    ]
    
    PRIORIDADE_CHOICES = [
        ('baixa', 'Baixa'),
        ('media', 'Média'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ]
    
    titulo = models.CharField(max_length=200)
    descricao = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='aberto')
    prioridade = models.CharField(max_length=20, choices=PRIORIDADE_CHOICES, default='media')
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='tickets')
    categoria = models.ForeignKey(CategoriaChamado, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    criado_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets_criados')
    atribuido_a = models.ForeignKey(Funcionario, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets_atribuidos')
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Ticket'
        verbose_name_plural = 'Tickets'
    
    def __str__(self):
        return f"#{self.id} - {self.titulo}"
    
    def get_atribuicoes(self):
        """Retorna todas as atribuições deste ticket"""
        return self.atribuicoes.all()

class AtribuicaoTicket(models.Model):
    """
    Modelo para permitir a atribuição de múltiplos funcionários a um ticket.
    Isso permite que mais de um técnico seja responsável por um ticket.
    """
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='atribuicoes')
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='tickets_atribuidos_multi')
    principal = models.BooleanField(default=False, help_text="Indica se este funcionário é o principal responsável pelo ticket")
    criado_em = models.DateTimeField(default=timezone.now)
    atualizado_em = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ['ticket', 'funcionario']
        verbose_name = 'Atribuição de Ticket'
        verbose_name_plural = 'Atribuições de Tickets'
        ordering = ['-principal', '-criado_em']
    
    def __str__(self):
        return f"Ticket #{self.ticket.id} atribuído a {self.funcionario.usuario.username}"
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.criado_em = timezone.now()
        self.atualizado_em = timezone.now()
        
        # Se este funcionário for marcado como principal, atualiza também o campo atribuido_a no ticket
        if self.principal:
            self.ticket.atribuido_a = self.funcionario
            self.ticket.save(update_fields=['atribuido_a'])
            
            # Garante que nenhum outro funcionário seja principal para este ticket
            AtribuicaoTicket.objects.filter(
                ticket=self.ticket, 
                principal=True
            ).exclude(
                id=self.id if self.id else 0
            ).update(principal=False)
            
        super().save(*args, **kwargs)

class Comentario(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comentarios')
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    texto = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Comentário de {self.autor.username} em {self.ticket.titulo}"

    class Meta:
        ordering = ['-criado_em']

class HistoricoTicket(models.Model):
    TIPO_ALTERACAO_CHOICES = (
        ('status', 'Alteração de Status'),
        ('prioridade', 'Alteração de Prioridade'),
        ('atribuicao', 'Alteração de Atribuição'),
        ('atribuicao_multipla', 'Atribuição Múltipla'),
        ('edicao', 'Edição de Informações'),
        ('comentario', 'Comentário'),
        ('campo_personalizado', 'Campo Personalizado'),
    )
    
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='historico')
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    tipo_alteracao = models.CharField(max_length=20, choices=TIPO_ALTERACAO_CHOICES)
    valor_anterior = models.TextField(blank=True, null=True)
    valor_novo = models.TextField(blank=True, null=True)
    data_alteracao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-data_alteracao']
        
    def __str__(self):
        return f"Alteração em {self.ticket.titulo} por {self.usuario.username} em {self.data_alteracao}"

class CampoPersonalizado(models.Model):
    TIPO_CHOICES = [
        ('texto', 'Texto'),
        ('numero', 'Número'),
        ('data', 'Data'),
        ('booleano', 'Sim/Não'),
        ('selecao', 'Seleção'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='campos_personalizados')
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    obrigatorio = models.BooleanField(default=False)
    opcoes = models.TextField(blank=True, null=True, help_text='Opções para campo do tipo seleção (uma por linha)')
    ordem = models.IntegerField(default=0)
    ativo = models.BooleanField(default=True)
    editavel = models.BooleanField(default=True, help_text='Se marcado, este campo poderá ser editado após a criação do ticket')
    criado_em = models.DateTimeField(default=timezone.now)
    atualizado_em = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        # Se for um novo objeto (não tem ID), defina criado_em
        if not self.id:
            self.criado_em = timezone.now()
        # Sempre atualize atualizado_em ao salvar
        self.atualizado_em = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()}) - {self.empresa.nome}"

    class Meta:
        verbose_name = 'Campo Personalizado'
        verbose_name_plural = 'Campos Personalizados'
        unique_together = ['empresa', 'nome']
        ordering = ['ordem', 'nome']

class ValorCampoPersonalizado(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='valores_campos_personalizados')
    campo = models.ForeignKey(CampoPersonalizado, on_delete=models.CASCADE)
    valor = models.TextField()
    criado_em = models.DateTimeField(default=timezone.now)
    atualizado_em = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        # Se for um novo objeto (não tem ID), defina criado_em
        if not self.id:
            self.criado_em = timezone.now()
        # Sempre atualize atualizado_em ao salvar
        self.atualizado_em = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.campo.nome}: {self.valor} ({self.ticket.titulo})"

    class Meta:
        verbose_name = 'Valor de Campo Personalizado'
        verbose_name_plural = 'Valores de Campos Personalizados'
        unique_together = ['ticket', 'campo']

class NotaTecnica(models.Model):
    """
    Modelo para armazenar anotações técnicas sobre o serviço executado ou sobre o equipamento.
    Essas notas são feitas por técnicos e podem ser usadas para documentação e relatórios técnicos.
    """
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='notas_tecnicas')
    tecnico = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='notas_tecnicas')
    descricao = models.TextField(verbose_name="Descrição da nota técnica")
    equipamento = models.CharField(max_length=255, blank=True, null=True, verbose_name="Equipamento relacionado")
    solucao_aplicada = models.TextField(blank=True, null=True, verbose_name="Solução aplicada")
    pendencias = models.TextField(blank=True, null=True, verbose_name="Pendências", help_text="Itens pendentes ou que precisam de acompanhamento")
    criado_em = models.DateTimeField(default=timezone.now)
    atualizado_em = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        if not self.id:
            self.criado_em = timezone.now()
        self.atualizado_em = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Nota técnica #{self.id} - Ticket #{self.ticket.id}"

    class Meta:
        verbose_name = 'Nota Técnica'
        verbose_name_plural = 'Notas Técnicas'
        ordering = ['-criado_em']

class PerfilCompartilhamento(models.Model):
    """
    Modelo para armazenar perfis de compartilhamento de tickets em PDF.
    Cada perfil define quais campos do ticket serão incluídos no PDF gerado.
    """
    nome = models.CharField(max_length=100, verbose_name="Nome do perfil")
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição do perfil")
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='perfis_compartilhamento')
    is_padrao = models.BooleanField(default=False, verbose_name="Perfil padrão", help_text="Se marcado, este perfil será o padrão para a empresa")
    incluir_notas_tecnicas = models.BooleanField(default=False, verbose_name="Incluir notas técnicas")
    incluir_historico = models.BooleanField(default=False, verbose_name="Incluir histórico")
    incluir_comentarios = models.BooleanField(default=True, verbose_name="Incluir comentários")
    incluir_campos_personalizados = models.BooleanField(default=True, verbose_name="Incluir campos personalizados")
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='perfis_compartilhamento_criados')
    criado_em = models.DateTimeField(default=timezone.now)
    atualizado_em = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        # Se este perfil for definido como padrão, desative o padrão anterior
        if self.is_padrao:
            PerfilCompartilhamento.objects.filter(
                empresa=self.empresa, 
                is_padrao=True
            ).exclude(pk=self.pk).update(is_padrao=False)
            
        if not self.id:
            self.criado_em = timezone.now()
        self.atualizado_em = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} ({self.empresa.nome})"

    class Meta:
        verbose_name = 'Perfil de Compartilhamento'
        verbose_name_plural = 'Perfis de Compartilhamento'
        ordering = ['-is_padrao', 'nome']
        unique_together = ['nome', 'empresa']

class CampoPerfilCompartilhamento(models.Model):
    """
    Modelo para definir quais campos específicos serão incluídos em um perfil de compartilhamento.
    """
    TIPO_CAMPO_CHOICES = [
        ('basico', 'Campo Básico'),
        ('personalizado', 'Campo Personalizado')
    ]
    
    perfil = models.ForeignKey(PerfilCompartilhamento, on_delete=models.CASCADE, related_name='campos')
    tipo_campo = models.CharField(max_length=20, choices=TIPO_CAMPO_CHOICES, default='basico')
    nome_campo = models.CharField(max_length=100, verbose_name="Nome do campo")
    # Se for um campo personalizado, referência para o modelo CampoPersonalizado
    campo_personalizado = models.ForeignKey(
        CampoPersonalizado, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='perfis_compartilhamento'
    )
    ordem = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.nome_campo} - {self.perfil.nome}"
    
    class Meta:
        verbose_name = 'Campo de Perfil de Compartilhamento'
        verbose_name_plural = 'Campos de Perfil de Compartilhamento'
        ordering = ['ordem', 'nome_campo']
        unique_together = ['perfil', 'nome_campo']

class PreferenciasNotificacao(models.Model):
    """
    Preferências de notificação por e-mail para cada usuário
    """
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferencias_notificacao')
    notificar_todas = models.BooleanField(default=True, help_text="Receber todas as notificações")
    notificar_atribuicao = models.BooleanField(default=True, help_text="Receber notificações quando um ticket for atribuído")
    notificar_alteracao_status = models.BooleanField(default=True, help_text="Receber notificações quando o status de um ticket for alterado")
    notificar_novo_comentario = models.BooleanField(default=True, help_text="Receber notificações quando um novo comentário for adicionado")
    notificar_prioridade_alterada = models.BooleanField(default=True, help_text="Receber notificações quando a prioridade for alterada")
    atualizado_em = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Preferências de notificação de {self.usuario.username}"
        
    class Meta:
        verbose_name = 'Preferência de Notificação'
        verbose_name_plural = 'Preferências de Notificação'
