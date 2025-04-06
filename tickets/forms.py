from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Empresa, Funcionario, Ticket, Comentario, CampoPersonalizado, NotaTecnica, AtribuicaoTicket

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

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Se o usuário não for superusuário, filtra as empresas disponíveis
        if self.user and not self.user.is_superuser:
            funcionario = self.user.funcionarios.first()
            if funcionario:
                # Filtra apenas as empresas do funcionário
                self.fields['empresas'].queryset = funcionario.empresas.all()
            else:
                # Se não for funcionário, remove o campo de empresas
                self.fields.pop('empresas', None)

class UserForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['empresa', 'titulo', 'descricao', 'status', 'prioridade', 'atribuido_a']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 4}),
            'empresa': forms.Select(attrs={'class': 'form-control', 'id': 'id_empresa'}),
            'atribuido_a': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Define a ordem dos campos
        self.fields_order = ['empresa', 'titulo', 'descricao', 'status', 'prioridade', 'atribuido_a']
        
        # Reorganiza os campos na ordem desejada
        original_fields = self.fields
        self.fields = {k: original_fields[k] for k in self.fields_order if k in original_fields}
        
        # Se o usuário não for admin, filtra as empresas e funcionários
        if self.user and not self.user.is_superuser:
            funcionario = self.user.funcionarios.first()
            if funcionario:
                # Filtra apenas as empresas do funcionário
                self.fields['empresa'].queryset = funcionario.empresas.all()
                
                # Se tiver apenas uma empresa, seleciona automaticamente
                if funcionario.empresas.count() == 1:
                    self.initial['empresa'] = funcionario.empresas.first()
                
                # Filtra os funcionários que podem ser atribuídos
                self.fields['atribuido_a'].queryset = Funcionario.objects.filter(
                    empresas__in=funcionario.empresas.all(),
                    tipo__in=['admin', 'suporte']
                ).distinct()
            else:
                # Se não for funcionário, remove os campos de empresa e atribuição
                self.fields.pop('empresa', None)
                self.fields.pop('atribuido_a', None)
        else:
            # Para admin, mostra todas as empresas
            self.fields['empresa'].queryset = Empresa.objects.all()
            
            # Inicialmente, não mostra funcionários até que uma empresa seja selecionada
            empresa_id = self.initial.get('empresa') or self.data.get('empresa')
            if empresa_id:
                # Se uma empresa for selecionada, mostra apenas funcionários daquela empresa
                self.fields['atribuido_a'].queryset = Funcionario.objects.filter(
                    empresas__id=empresa_id,
                    tipo__in=['admin', 'suporte']
                ).distinct()
            else:
                # Se nenhuma empresa for selecionada, não mostra funcionários
                self.fields['atribuido_a'].queryset = Funcionario.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        empresa = cleaned_data.get('empresa')
        atribuido_a = cleaned_data.get('atribuido_a')
        
        # Verifica se o usuário tem acesso à empresa selecionada
        if self.user and not self.user.is_superuser:
            funcionario = self.user.funcionarios.first()
            if funcionario and empresa:
                if not funcionario.tem_acesso_empresa(empresa):
                    raise forms.ValidationError("Você não tem acesso a esta empresa.")
                
                if not funcionario.pode_criar_ticket(empresa):
                    raise forms.ValidationError("Você não tem permissão para criar tickets para esta empresa.")
        
        # Verifica se o funcionário atribuído pertence à empresa selecionada
        if empresa and atribuido_a:
            if not atribuido_a.empresas.filter(id=empresa.id).exists():
                raise forms.ValidationError("O funcionário atribuído não pertence à empresa selecionada.")
        
        return cleaned_data

class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ['texto']
        widgets = {
            'texto': forms.Textarea(attrs={'rows': 3}),
        }

class AtribuirTicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['atribuido_a']
        widgets = {
            'atribuido_a': forms.Select(attrs={'class': 'form-control'}),
        }

class MultiAtribuirTicketForm(forms.Form):
    funcionarios = forms.ModelMultipleChoiceField(
        queryset=Funcionario.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False
    )
    
    funcionario_principal = forms.ModelChoiceField(
        queryset=Funcionario.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False,
        help_text="Este funcionário será o principal responsável pelo ticket"
    )
    
    def __init__(self, *args, **kwargs):
        self.ticket = kwargs.pop('ticket', None)
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar funcionários por empresa
        if self.empresa:
            funcionarios = Funcionario.objects.filter(
                empresas=self.empresa,
                tipo__in=['admin', 'suporte']
            ).distinct()
            
            self.fields['funcionarios'].queryset = funcionarios
            self.fields['funcionario_principal'].queryset = funcionarios
            
            # Preencher valores iniciais se o ticket existir
            if self.ticket:
                self.fields['funcionario_principal'].initial = self.ticket.atribuido_a
                self.fields['funcionarios'].initial = [
                    atribuicao.funcionario.id for atribuicao in self.ticket.atribuicoes.all()
                ]
    
    def save(self):
        if not self.ticket:
            return None
            
        # Obter os funcionários selecionados
        funcionarios = self.cleaned_data.get('funcionarios', [])
        funcionario_principal = self.cleaned_data.get('funcionario_principal')
        
        # Limpar atribuições existentes
        self.ticket.atribuicoes.all().delete()
        
        # Criar novas atribuições
        for funcionario in funcionarios:
            is_principal = funcionario == funcionario_principal
            AtribuicaoTicket.objects.create(
                ticket=self.ticket,
                funcionario=funcionario,
                principal=is_principal
            )
        
        # Se houver um funcionário principal mas ele não estiver na lista de funcionários
        if funcionario_principal and funcionario_principal not in funcionarios:
            AtribuicaoTicket.objects.create(
                ticket=self.ticket,
                funcionario=funcionario_principal,
                principal=True
            )
            
        # Atualizar o campo atribuido_a do ticket
        if funcionario_principal:
            self.ticket.atribuido_a = funcionario_principal
            self.ticket.save(update_fields=['atribuido_a'])
            
        return self.ticket

class CampoPersonalizadoForm(forms.ModelForm):
    class Meta:
        model = CampoPersonalizado
        fields = ['nome', 'tipo', 'obrigatorio', 'opcoes', 'ordem', 'ativo', 'editavel']
        widgets = {
            'opcoes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Digite uma opção por linha'}),
            'ordem': forms.NumberInput(attrs={'min': 0}),
        }

    def clean_opcoes(self):
        opcoes = self.cleaned_data.get('opcoes', '')
        tipo = self.cleaned_data.get('tipo')
        
        if tipo == 'selecao' and not opcoes:
            raise forms.ValidationError("Para campos do tipo 'Seleção', é necessário informar as opções.")
        
        if tipo != 'selecao' and opcoes:
            raise forms.ValidationError("Opções só podem ser definidas para campos do tipo 'Seleção'.")
        
        return opcoes

class ValorCampoPersonalizadoForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        
        if self.empresa:
            campos = CampoPersonalizado.objects.filter(empresa=self.empresa).order_by('nome')
            for campo in campos:
                field_name = f'campo_{campo.id}'
                if campo.tipo == 'texto':
                    self.fields[field_name] = forms.CharField(
                        label=campo.nome,
                        required=campo.obrigatorio,
                        widget=forms.TextInput(attrs={'class': 'form-control'})
                    )
                elif campo.tipo == 'numero':
                    self.fields[field_name] = forms.DecimalField(
                        label=campo.nome,
                        required=campo.obrigatorio,
                        widget=forms.NumberInput(attrs={'class': 'form-control'})
                    )
                elif campo.tipo == 'data':
                    self.fields[field_name] = forms.DateField(
                        label=campo.nome,
                        required=campo.obrigatorio,
                        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
                    )
                elif campo.tipo == 'selecao':
                    opcoes = [(op.strip(), op.strip()) for op in campo.opcoes.splitlines()]
                    self.fields[field_name] = forms.ChoiceField(
                        label=campo.nome,
                        required=campo.obrigatorio,
                        choices=[('', '---')] + opcoes,
                        widget=forms.Select(attrs={'class': 'form-control'})
                    )
                elif campo.tipo == 'booleano':
                    self.fields[field_name] = forms.BooleanField(
                        label=campo.nome,
                        required=campo.obrigatorio,
                        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
                    )
                
                self.fields[field_name].campo_id = campo.id

class NotaTecnicaForm(forms.ModelForm):
    class Meta:
        model = NotaTecnica
        fields = ['descricao', 'equipamento', 'solucao_aplicada', 'pendencias']
        widgets = {
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Descreva o problema técnico ou observações sobre o equipamento'}),
            'equipamento': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Servidor Dell PowerEdge R740, Impressora HP LaserJet Pro'}),
            'solucao_aplicada': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descreva a solução aplicada ou as ações executadas'}),
            'pendencias': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Liste pendências ou itens que precisam de acompanhamento'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.ticket = kwargs.pop('ticket', None)
        self.tecnico = kwargs.pop('tecnico', None)
        super().__init__(*args, **kwargs)
        
    def save(self, commit=True):
        nota = super().save(commit=False)
        if self.ticket:
            nota.ticket = self.ticket
        if self.tecnico:
            nota.tecnico = self.tecnico
        if commit:
            nota.save()
        return nota 