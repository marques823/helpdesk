from django.core.management.base import BaseCommand
from django.db import transaction
from tickets.models import Ticket, SequenciaTicketEmpresa, Empresa
from django.db.models import Max

class Command(BaseCommand):
    help = 'Inicializa o número de empresa para tickets existentes e cria sequências para cada empresa'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Inicializando números de tickets por empresa...'))
        
        # Cria sequências para todas as empresas que ainda não têm
        empresas = Empresa.objects.all()
        for empresa in empresas:
            sequencia, created = SequenciaTicketEmpresa.objects.get_or_create(empresa=empresa)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Sequência criada para empresa {empresa.nome}'))
        
        # Processa cada empresa
        with transaction.atomic():
            for empresa in empresas:
                # Obtém a sequência para esta empresa
                sequencia = SequenciaTicketEmpresa.objects.get(empresa=empresa)
                
                # Obtém todos os tickets desta empresa que ainda não têm número
                tickets = Ticket.objects.filter(
                    empresa=empresa, 
                    numero_empresa=0
                ).order_by('criado_em')
                
                if not tickets.exists():
                    self.stdout.write(f'Nenhum ticket para processar na empresa {empresa.nome}')
                    continue
                
                self.stdout.write(f'Processando {tickets.count()} tickets para empresa {empresa.nome}')
                
                # Atribui números aos tickets existentes em ordem cronológica
                contador = 1
                for ticket in tickets:
                    ticket.numero_empresa = contador
                    ticket.save(update_fields=['numero_empresa'])
                    contador += 1
                
                # Atualiza o contador na sequência
                sequencia.ultimo_numero = contador - 1
                sequencia.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Empresa {empresa.nome}: {contador-1} tickets processados, próximo número: {contador}'
                    )
                )
        
        self.stdout.write(self.style.SUCCESS('Inicialização concluída!')) 