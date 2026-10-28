from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from pharma.external_api_models import ExternalApiCredential
from account.models import Company


class Command(BaseCommand):
    help = "Crea una clave revocable y limitada para una plataforma externa."

    def add_arguments(self, parser):
        parser.add_argument("--owner", required=True, help="ID o nombre de usuario del propietario de los pacientes")
        parser.add_argument("--name", required=True, help="Nombre identificativo de la integración")
        parser.add_argument(
            "--purpose",
            choices=(ExternalApiCredential.PURPOSE_PATIENT_LOOKUP, ExternalApiCredential.PURPOSE_STORE_CATALOG),
            default=ExternalApiCredential.PURPOSE_PATIENT_LOOKUP,
        )
        parser.add_argument("--company", help="ID o código de la empresa, obligatorio para purpose=store_catalog")

    def handle(self, *args, **options):
        user_model = get_user_model()
        owner_value = options["owner"]
        queryset = user_model.objects
        owner = queryset.filter(pk=owner_value).first() or queryset.filter(username=owner_value).first()
        if owner is None:
            raise CommandError("No existe el usuario indicado en --owner.")

        company = None
        if options["purpose"] == ExternalApiCredential.PURPOSE_STORE_CATALOG:
            company_value = options["company"]
            if not company_value:
                raise CommandError("--company es obligatorio para una clave de catálogo.")
            company = Company.objects.filter(pk=company_value).first() or Company.objects.filter(code__iexact=company_value).first()
            if company is None:
                raise CommandError("No existe la empresa indicada.")

        credential, plaintext_key = ExternalApiCredential.issue(
            owner=owner,
            name=options["name"],
            purpose=options["purpose"],
            catalog_company=company,
        )
        self.stdout.write(self.style.SUCCESS("Credencial %s creada (id=%s)." % (credential.name, credential.pk)))
        self.stdout.write(self.style.WARNING("Guarde esta clave ahora; no volverá a mostrarse:"))
        self.stdout.write(plaintext_key)
