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

    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    empresas = models.ManyToManyField(Empresa, related_name='funcionarios')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    telefone = models.CharField(max_length=20)
    cargo = models.CharField(max_length=100)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.usuario.get_full_name()} - {', '.join([e.nome for e in self.empresas.all()])}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Atualiza as permissões do usuário baseado no tipo
        if self.tipo == 'admin':
            self.usuario.is_staff = True
            self.usuario.is_superuser = True
            self.usuario.save()
        elif self.tipo == 'suporte':
            self.usuario.is_staff = True
            self.usuario.is_superuser = False
            self.usuario.save()
        else:  # cliente
            self.usuario.is_staff = False
            self.usuario.is_superuser = False
            self.usuario.save()

    class Meta:
        verbose_name = 'Funcionário'
        verbose_name_plural = 'Funcionários'

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
    atribuido_a = models.ForeignKey('Funcionario', on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets_atribuidos')
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
