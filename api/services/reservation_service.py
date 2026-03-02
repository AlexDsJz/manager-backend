from django.db import transaction
from django.db.models import F
from rest_framework import serializers
from api.models.events.event import Event
from api.models.events.reservation import Reservation


@transaction.atomic
def create_reservation(validated_data: dict) -> Reservation:
    event: Event = validated_data['event']
    count: int = validated_data['ticket_count']

    event_lock = Event.objects.select_for_update().get(pk=event.pk)

    if event_lock.available_spots < count:
        raise serializers.ValidationError({
            'ticket_count': (
                f"Only {event_lock.available_spots} spot(s) left. "
                "Another user just reserved some tickets."
            )
        })

    Event.objects.filter(pk=event.pk).update(
        available_spots=F('available_spots') - count
    )

    return Reservation.objects.create(**validated_data)
