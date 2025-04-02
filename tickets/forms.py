from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Empresa, Funcionario, Ticket, Comentario

class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ['nome', 'cnpj', 'telefone', 'email', 'endereco']
        widgets = {
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00.000.000/0000-00'}),
        }

class FuncionarioForm(forms.ModelForm):
    class Meta:
        model = Funcionario
        fields = ['usuario', 'empresas', 'tipo', 'telefone', 'cargo']
        widgets = {
            'empresas': forms.CheckboxSelectMultiple(),
            'tipo': forms.Select(choices=Funcionario.TIPO_CHOICES),
        }

class UserForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['titulo', 'descricao', 'status', 'prioridade', 'empresa', 'atribuido_para']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Se o usuário não for admin, remove os campos de empresa e atribuição
        if hasattr(self.instance, 'criado_por') and hasattr(self.instance.criado_por, 'funcionario'):
            if self.instance.criado_por.funcionario.tipo != 'admin':
                self.fields.pop('empresa', None)
                self.fields.pop('atribuido_para', None)

class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ['texto']
        widgets = {
            'texto': forms.Textarea(attrs={'rows': 3}),
        } 