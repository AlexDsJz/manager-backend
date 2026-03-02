from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Reservation(models.Model):
    event = models.ForeignKey(
        'api.Event',
        on_delete=models.CASCADE,
        related_name='reservations',
    )
    buyer_email = models.EmailField(max_length=254)
    ticket_count = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'api'
        db_table = 'reservations'
        ordering = ['-created_at']

    def __str__(self):
        return f"Reservation #{self.pk} - {self.buyer_email} → {self.event.event_code}"
