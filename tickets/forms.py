from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Empresa, Funcionario, Ticket, Comentario, CampoPersonalizado, NotaTecnica, AtribuicaoTicket, PerfilCompartilhamento, CampoPerfilCompartilhamento, CategoriaChamado, PreferenciasNotificacao
from django.db.models import Q

class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ['nome', 'cnpj', 'telefone', 'email', 'endereco']
        widgets = {
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00.000.000/0000-00'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Guardar os valores originais para validação
        if self.instance and self.instance.pk:
            self._original_nome = self.instance.nome
            self._original_cnpj = self.instance.cnpj
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Verificar se estamos editando uma empresa existente
        if hasattr(self, '_original_nome') and hasattr(self, '_original_cnpj'):
            # Garantir que o nome e CNPJ não foram alterados
            if cleaned_data.get('nome') != self._original_nome:
                cleaned_data['nome'] = self._original_nome
            
            if cleaned_data.get('cnpj') != self._original_cnpj:
                cleaned_data['cnpj'] = self._original_cnpj
        
        return cleaned_data

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
        self.criacao_usuario = kwargs.pop('criacao_usuario', False)  # Flag para indicar se é um formulário de criação de usuário
        super().__init__(*args, **kwargs)
        
        # Se estiver criando um usuário novo, não precisamos do campo usuario
        if self.criacao_usuario:
            self.fields.pop('usuario', None)
        else:
            # Filtra o campo de usuários para mostrar apenas usuários sem vínculo com funcionários
            # Exclui os usuários que já estão associados a um funcionário
            funcionarios_existentes = Funcionario.objects.all().values_list('usuario', flat=True)
            if self.instance and self.instance.pk and self.instance.usuario:
                # Quando estiver editando, incluir o usuário atual na lista
                self.fields['usuario'].queryset = User.objects.filter(
                    Q(id=self.instance.usuario.id) | 
                    ~Q(id__in=funcionarios_existentes)
                )
            else:
                self.fields['usuario'].queryset = User.objects.exclude(id__in=funcionarios_existentes)
        
        # Se o usuário não for superusuário, filtra as empresas disponíveis
        if self.user and not self.user.is_superuser:
            funcionario = Funcionario.objects.filter(usuario=self.user).first()
            if funcionario:
                # Filtra apenas as empresas do funcionário
                self.fields['empresas'].queryset = funcionario.empresas.all()
                
                # Se o usuário for apenas admin de empresa, desabilita a edição do campo
                if funcionario.is_admin() and not funcionario.is_suporte():
                    # Se houver apenas uma empresa, pré-seleciona ela
                    if funcionario.empresas.count() == 1:
                        self.initial['empresas'] = [funcionario.empresas.first().id]
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
        fields = ['empresa', 'categoria', 'titulo', 'descricao', 'status', 'prioridade', 'atribuido_a']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 4}),
            'empresa': forms.Select(attrs={'class': 'form-control', 'id': 'id_empresa'}),
            'categoria': forms.Select(attrs={'class': 'form-control', 'id': 'id_categoria'}),
            'atribuido_a': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Define a ordem dos campos
        self.fields_order = ['empresa', 'categoria', 'titulo', 'descricao', 'status', 'prioridade', 'atribuido_a']
        
        # Reorganiza os campos na ordem desejada
        original_fields = self.fields
        self.fields = {k: original_fields[k] for k in self.fields_order if k in original_fields}
        
        # Se o usuário não for admin, filtra as empresas e funcionários
        if self.user and not self.user.is_superuser:
            funcionario = Funcionario.objects.filter(usuario=self.user).first()
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
        
        # Inicialmente, não mostra categorias até que uma empresa seja selecionada
        empresa_id = self.initial.get('empresa') or self.data.get('empresa')
        if empresa_id:
            # Se uma empresa for selecionada, mostra apenas categorias daquela empresa
            self.fields['categoria'].queryset = CategoriaChamado.objects.filter(
                empresa_id=empresa_id,
                ativo=True
            ).order_by('ordem', 'nome')
        else:
            # Se nenhuma empresa for selecionada, não mostra categorias
            self.fields['categoria'].queryset = CategoriaChamado.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        empresa = cleaned_data.get('empresa')
        atribuido_a = cleaned_data.get('atribuido_a')
        
        # Verifica se o usuário tem acesso à empresa selecionada
        if self.user and not self.user.is_superuser:
            funcionario = Funcionario.objects.filter(usuario=self.user).first()
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
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar funcionários baseado no ticket e nas permissões do usuário
        if self.instance and self.instance.pk:
            empresa = self.instance.empresa
            
            if self.user and not self.user.is_superuser:
                # Para usuários não-admin, mostrar apenas funcionários das empresas a que têm acesso
                funcionario = Funcionario.objects.filter(usuario=self.user).first()
                if funcionario:
                    self.fields['atribuido_a'].queryset = Funcionario.objects.filter(
                        empresas=empresa,
                        tipo__in=['admin', 'suporte'],
                        empresas__in=funcionario.empresas.all()
                    ).distinct()
                else:
                    self.fields['atribuido_a'].queryset = Funcionario.objects.none()
            else:
                # Para admin, mostrar todos os funcionários da empresa do ticket
                self.fields['atribuido_a'].queryset = Funcionario.objects.filter(
                    empresas=empresa,
                    tipo__in=['admin', 'suporte']
                ).distinct()
        else:
            self.fields['atribuido_a'].queryset = Funcionario.objects.none()

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
        self.user = kwargs.pop('user', None) 
        super().__init__(*args, **kwargs)
        
        # Filtrar funcionários por empresa e permissões do usuário
        if self.empresa:
            if self.user and not self.user.is_superuser:
                # Para usuários não-admin, mostrar apenas funcionários das empresas a que têm acesso
                funcionario = Funcionario.objects.filter(usuario=self.user).first()
                if funcionario:
                    funcionarios = Funcionario.objects.filter(
                        empresas=self.empresa,
                        tipo__in=['admin', 'suporte'],
                        empresas__in=funcionario.empresas.all()
                    ).distinct()
                else:
                    funcionarios = Funcionario.objects.none()
            else:
                # Para admin, mostrar todos os funcionários da empresa
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
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'equipamento': forms.TextInput(attrs={'class': 'form-control'}),
            'solucao_aplicada': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'pendencias': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
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

class PerfilCompartilhamentoForm(forms.ModelForm):
    class Meta:
        model = PerfilCompartilhamento
        fields = ['nome', 'descricao', 'empresa', 'is_padrao', 'incluir_notas_tecnicas', 'incluir_historico', 'incluir_comentarios', 'incluir_campos_personalizados']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'empresa': forms.Select(attrs={'class': 'form-control'}),
            'is_padrao': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'incluir_notas_tecnicas': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'incluir_historico': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'incluir_comentarios': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'incluir_campos_personalizados': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar empresas com base nas permissões do usuário
        if self.user and not self.user.is_superuser:
            # Para usuários que não são superusuários, mostrar apenas empresas às quais eles têm acesso
            funcionario = Funcionario.objects.filter(usuario=self.user).first()
            if funcionario:
                self.fields['empresa'].queryset = funcionario.empresas.all().distinct()
        
        # Se estiver editando um perfil existente, não permitir alterar a empresa
        if self.instance.pk:
            self.fields['empresa'].disabled = True

class CampoPerfilCompartilhamentoForm(forms.ModelForm):
    class Meta:
        model = CampoPerfilCompartilhamento
        fields = ['perfil', 'tipo_campo', 'nome_campo', 'campo_personalizado', 'ordem']
        widgets = {
            'perfil': forms.Select(attrs={'class': 'form-control'}),
            'tipo_campo': forms.Select(attrs={'class': 'form-control', 'id': 'id_tipo_campo'}),
            'nome_campo': forms.TextInput(attrs={'class': 'form-control'}),
            'campo_personalizado': forms.Select(attrs={'class': 'form-control', 'id': 'id_campo_personalizado'}),
            'ordem': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar perfis com base nas permissões do usuário
        if self.user and not self.user.is_superuser:
            # Para usuários que não são superusuários, mostrar apenas perfis de empresas às quais eles têm acesso
            funcionario = Funcionario.objects.filter(usuario=self.user).first()
            if funcionario:
                empresas = funcionario.empresas.all()
                self.fields['perfil'].queryset = PerfilCompartilhamento.objects.filter(empresa__in=empresas)
        
        # Inicialmente, filtrar campos personalizados com base no perfil selecionado (se houver)
        if self.instance.pk and self.instance.perfil:
            self.fields['campo_personalizado'].queryset = CampoPersonalizado.objects.filter(empresa=self.instance.perfil.empresa)
        else:
            self.fields['campo_personalizado'].queryset = CampoPersonalizado.objects.none()

class CategoriaChamadoForm(forms.ModelForm):
    """Formulário para criar e editar categorias de chamados"""
    class Meta:
        model = CategoriaChamado
        fields = ['nome', 'descricao', 'cor', 'icone', 'ordem', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'cor': forms.Select(attrs={'class': 'form-control', 'id': 'id_cor'}),
            'icone': forms.Select(attrs={'class': 'form-control', 'id': 'id_icone'}),
            'ordem': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Opções para cores bootstrap
        COR_CHOICES = [
            ('primary', 'Azul (Primary)'),
            ('secondary', 'Cinza (Secondary)'),
            ('success', 'Verde (Success)'),
            ('danger', 'Vermelho (Danger)'),
            ('warning', 'Amarelo (Warning)'),
            ('info', 'Azul claro (Info)'),
            ('light', 'Claro (Light)'),
            ('dark', 'Escuro (Dark)'),
        ]
        
        self.fields['cor'] = forms.ChoiceField(
            choices=COR_CHOICES,
            widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_cor'}),
            initial=self.instance.cor if self.instance and self.instance.pk else 'primary'
        )
        
        # Lista de ícones FontAwesome comuns
        ICONE_CHOICES = [
            ('fa-ticket-alt', 'Ticket (Padrão)'),
            ('fa-desktop', 'Computador'),
            ('fa-laptop', 'Laptop'),
            ('fa-wifi', 'Wi-Fi'),
            ('fa-server', 'Servidor'),
            ('fa-print', 'Impressora'),
            ('fa-keyboard', 'Teclado'),
            ('fa-mouse', 'Mouse'),
            ('fa-network-wired', 'Rede'),
            ('fa-database', 'Banco de Dados'),
            ('fa-envelope', 'E-mail'),
            ('fa-users', 'Usuários'),
            ('fa-user-shield', 'Segurança'),
            ('fa-lock', 'Cadeado'),
            ('fa-shield-alt', 'Escudo'),
            ('fa-bug', 'Bug'),
            ('fa-exclamation-triangle', 'Alerta'),
            ('fa-question-circle', 'Dúvida'),
            ('fa-info-circle', 'Informação'),
            ('fa-phone', 'Telefone'),
            ('fa-mobile-alt', 'Celular'),
            ('fa-file', 'Arquivo'),
            ('fa-window-restore', 'Janela'),
            ('fa-cog', 'Engrenagem'),
            ('fa-tools', 'Ferramentas'),
            ('fa-wrench', 'Chave de Fenda'),
            ('fa-chart-bar', 'Gráfico'),
            ('fa-clipboard-list', 'Lista'),
            ('fa-box', 'Caixa'),
            ('fa-folder', 'Pasta'),
            ('fa-bullhorn', 'Comunicado'),
            ('fa-comment', 'Comentário'),
            ('fa-headset', 'Headset'),
            ('fa-camera', 'Câmera'),
            ('fa-video', 'Vídeo'),
            ('fa-credit-card', 'Cartão'),
            ('fa-dollar-sign', 'Financeiro'),
            ('fa-calendar', 'Calendário'),
            ('fa-clock', 'Relógio'),
            ('fa-bookmark', 'Favorito'),
        ]
        
        # Configurar campo de ícone como select
        self.fields['icone'] = forms.ChoiceField(
            choices=ICONE_CHOICES,
            widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_icone'}),
            help_text='Selecione um ícone para representar visualmente a categoria'
        )
        
        # Se for edição, ajustar o ícone para exibir corretamente
        if self.instance and self.instance.pk and self.instance.icone:
            # Verificar se o ícone atual está na lista; se não, adicioná-lo
            icone_atual = self.instance.icone
            if not icone_atual.startswith('fa-'):
                icone_atual = f"fa-{icone_atual}"
                
            # Verificar se o valor existe nas opções
            if not any(icone_atual == choice[0] for choice in ICONE_CHOICES):
                # Adicionar o valor atual às opções
                custom_choice = [(icone_atual, f"Personalizado: {icone_atual}")]
                self.fields['icone'].choices = custom_choice + ICONE_CHOICES
                
            self.initial['icone'] = icone_atual

class CompartilharTicketForm(forms.Form):
    perfil = forms.ModelChoiceField(
        queryset=PerfilCompartilhamento.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True,
        empty_label="Selecione um perfil de compartilhamento"
    )
    
    def __init__(self, *args, **kwargs):
        self.ticket = kwargs.pop('ticket', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar perfis com base na empresa do ticket e nas permissões do usuário
        if self.ticket:
            if self.user and self.user.is_superuser:
                # Superusuários podem ver todos os perfis da empresa do ticket
                self.fields['perfil'].queryset = PerfilCompartilhamento.objects.filter(empresa=self.ticket.empresa)
            else:
                # Outros usuários só podem ver perfis se tiverem acesso à empresa do ticket
                funcionario = Funcionario.objects.filter(usuario=self.user).first()
                if funcionario and funcionario.empresas.filter(id=self.ticket.empresa.id).exists():
                    self.fields['perfil'].queryset = PerfilCompartilhamento.objects.filter(empresa=self.ticket.empresa)
            
            # Definir perfil padrão, se existir
            perfil_padrao = PerfilCompartilhamento.objects.filter(empresa=self.ticket.empresa, is_padrao=True).first()
            if perfil_padrao:
                self.fields['perfil'].initial = perfil_padrao 

class PreferenciasNotificacaoForm(forms.ModelForm):
    class Meta:
        model = PreferenciasNotificacao
        fields = [
            'notificar_todas',
            'notificar_atribuicao',
            'notificar_alteracao_status',
            'notificar_novo_comentario',
            'notificar_prioridade_alterada'
        ]
        widgets = {
            'notificar_todas': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notificar_atribuicao': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notificar_alteracao_status': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notificar_novo_comentario': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notificar_prioridade_alterada': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        } 