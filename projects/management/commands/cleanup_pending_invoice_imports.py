import os
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from projects.models import PendingInvoiceImport, PendingInvoiceImportStatus


def failed_import_retention():
    configured = getattr(settings, "INVOICE_IMPORT_FAILED_RETENTION_HOURS", None) or os.getenv(
        "INVOICE_IMPORT_FAILED_RETENTION_HOURS", "24"
    )
    try:
        return timedelta(hours=max(1, int(configured)))
    except (TypeError, ValueError):
        return timedelta(hours=24)


class Command(BaseCommand):
    help = "Elimina importaciones temporales de facturas caducadas o fallidas antiguas."

    def handle(self, *args, **options):
        now = timezone.now()
        failed_before = now - failed_import_retention()
        queryset = PendingInvoiceImport.objects.filter(
            Q(
                status__in=[PendingInvoiceImportStatus.PROCESSING, PendingInvoiceImportStatus.PENDING_REVIEW],
                expires_at__lte=now,
            )
            | Q(status=PendingInvoiceImportStatus.FAILED, created_at__lte=failed_before)
            | Q(status=PendingInvoiceImportStatus.EXPIRED)
        )
        deleted = 0
        for pending_import in queryset.iterator():
            if pending_import.temporary_document:
                pending_import.temporary_document.delete(save=False)
            pending_import.delete()
            deleted += 1
        self.stdout.write(self.style.SUCCESS("Importaciones temporales eliminadas: {}".format(deleted)))
