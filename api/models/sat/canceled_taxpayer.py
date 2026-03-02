from django.db import models


class CanceledTaxpayer(models.Model):
    batch = models.ForeignKey(
        'api.SATImportBatch',
        on_delete=models.CASCADE,
        related_name='canceled_taxpayers',
    )
    rfc = models.CharField(max_length=20, db_index=True)
    name = models.CharField(max_length=500)
    person_type = models.CharField(max_length=200, blank=True, default='')
    assumption = models.CharField(max_length=300, blank=True, default='')
    credit_number = models.CharField(max_length=100, blank=True, default='')
    amount = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    state = models.CharField(max_length=100, blank=True, default='')
    extra_data = models.JSONField(default=dict, blank=True)

    class Meta:
        app_label = 'api'
        db_table = 'sat_canceled_taxpayers'
        indexes = [
            models.Index(fields=['rfc'], name='idx_canceled_rfc'),
            models.Index(fields=['batch'], name='idx_canceled_batch'),
        ]

    def __str__(self):
        return f"{self.rfc} - {self.name[:50]}"
