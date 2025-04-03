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
        
        # Cliente só pode ver seus próprios tickets
        if self.is_cliente():
            return ticket.criado_por == self.usuario or ticket.atribuido_a == self
        
        return False
    
    def pode_criar_ticket(self, empresa):
        # Verifica se o funcionário tem acesso à empresa
        if not self.tem_acesso_empresa(empresa):
            return False
        
        # Admin e suporte podem criar tickets para empresas que têm acesso
        return self.is_admin() or self.is_suporte()
    
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
    TIPO_ALTERACAO_CHOICES = [
        ('criacao', 'Criação'),
        ('edicao', 'Edição'),
        ('atribuicao', 'Atribuição'),
        ('status', 'Alteração de Status'),
        ('prioridade', 'Alteração de Prioridade'),
        ('comentario', 'Comentário'),
    ]
    
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='historico')
    tipo_alteracao = models.CharField(max_length=20, choices=TIPO_ALTERACAO_CHOICES)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    descricao = models.TextField()
    dados_anteriores = models.JSONField(null=True, blank=True)
    dados_novos = models.JSONField(null=True, blank=True)
    data_alteracao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-data_alteracao']
        verbose_name = 'Histórico de Ticket'
        verbose_name_plural = 'Históricos de Tickets'
    
    def __str__(self):
        return f"Histórico #{self.id} - {self.get_tipo_alteracao_display()} - Ticket #{self.ticket.id}"
