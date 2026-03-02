import re
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class Event(models.Model):
    event_code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    date = models.DateTimeField()
    total_capacity = models.PositiveIntegerField()
    available_spots = models.PositiveIntegerField()
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'api'
        db_table = 'events'
        ordering = ['date']

    def __str__(self):
        return f"{self.event_code} - {self.name}"

    @property
    def is_sold_out(self):
        return self.available_spots == 0

    def clean(self):
        if self.event_code and not re.match(r'^EVT-\d{4}-[A-Z]{2}$', self.event_code):
            raise ValidationError(
                {'event_code': "Format must be EVT-YYYY-XX (e.g. EVT-2024-MX)."}
            )
        if self.name and len(self.name.strip()) < 5:
            raise ValidationError({'name': "Name must be at least 5 characters."})
        if self.date and self.date <= timezone.now():
            raise ValidationError({'date': "Event date must be in the future."})
        if self.total_capacity is not None and self.total_capacity <= 0:
            raise ValidationError({'total_capacity': "Total capacity must be greater than 0."})
        if self.ticket_price is not None and self.ticket_price < 0:
            raise ValidationError({'ticket_price': "Ticket price cannot be negative."})

    def save(self, *args, **kwargs):
        if not self.pk:
            self.available_spots = self.total_capacity
        self.full_clean()
        super().save(*args, **kwargs)
