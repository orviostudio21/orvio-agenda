import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from workspace.domain import seed_data, REGISTRY

class Command(BaseCommand):
    help = 'Cria dados fictícios para um usuário existente e vazio.'
    def add_arguments(self, parser):
        parser.add_argument('--username', required=True)
    def handle(self, *args, **options):
        try:
            user = get_user_model().objects.get(username=options['username'])
        except get_user_model().DoesNotExist:
            raise CommandError('Usuário não existe. Crie uma conta primeiro.')
        if any(c['model'].objects.filter(owner=user).exists() for c in REGISTRY.values()):
            raise CommandError('O espaço já contém registros. Nenhum dado foi alterado.')
        from django.db import transaction
        with transaction.atomic():
            seed_data(user)
        self.stdout.write(self.style.SUCCESS('Dados fictícios criados.'))
