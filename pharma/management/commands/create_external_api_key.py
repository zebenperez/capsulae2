from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from pharma.external_api_models import ExternalApiCredential


class Command(BaseCommand):
    help = "Crea una clave revocable para consultar pacientes desde una plataforma externa."

    def add_arguments(self, parser):
        parser.add_argument("--owner", required=True, help="ID o nombre de usuario del propietario de los pacientes")
        parser.add_argument("--name", required=True, help="Nombre identificativo de la integración")

    def handle(self, *args, **options):
        user_model = get_user_model()
        owner_value = options["owner"]
        queryset = user_model.objects
        owner = queryset.filter(pk=owner_value).first() or queryset.filter(username=owner_value).first()
        if owner is None:
            raise CommandError("No existe el usuario indicado en --owner.")

        credential, plaintext_key = ExternalApiCredential.issue(owner=owner, name=options["name"])
        self.stdout.write(self.style.SUCCESS("Credencial %s creada (id=%s)." % (credential.name, credential.pk)))
        self.stdout.write(self.style.WARNING("Guarde esta clave ahora; no volverá a mostrarse:"))
        self.stdout.write(plaintext_key)
