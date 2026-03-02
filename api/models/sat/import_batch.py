from django.db import models


class SATImportBatch(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        RUNNING = 'running', 'Running'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    source_url = models.URLField()
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    records_imported = models.IntegerField(default=0)
    execution_seconds = models.FloatField(null=True, blank=True)
    error_message = models.TextField(blank=True, default='')

    class Meta:
        app_label = 'api'
        db_table = 'sat_import_batches'
        ordering = ['-started_at']

    def __str__(self):
        return f"Batch #{self.pk} [{self.status}] {self.started_at:%Y-%m-%d %H:%M}"
