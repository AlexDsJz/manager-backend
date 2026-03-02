import re
from django.utils import timezone
from rest_framework import serializers
from api.models.events.event import Event
from api.models.events.reservation import Reservation

EVENT_CODE_REGEX = re.compile(r'^EVT-\d{4}-[A-Z]{2}$')


class EventSerializer(serializers.ModelSerializer):
    is_sold_out = serializers.BooleanField(read_only=True)

    class Meta:
        model = Event
        fields = [
            'id', 'event_code', 'name', 'date',
            'total_capacity', 'available_spots', 'ticket_price',
            'is_sold_out', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'available_spots', 'is_sold_out', 'created_at', 'updated_at']

    def validate_event_code(self, value):
        if not EVENT_CODE_REGEX.match(value):
            raise serializers.ValidationError(
                "Format must be EVT-YYYY-XX where YYYY are digits and XX are uppercase letters. "
                "Example: EVT-2024-MX"
            )
        return value

    def validate_name(self, value):
        stripped = value.strip()
        if len(stripped) < 5:
            raise serializers.ValidationError("Name must be at least 5 characters.")
        if len(stripped) > 100:
            raise serializers.ValidationError("Name cannot exceed 100 characters.")
        return stripped

    def validate_date(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Event date must be in the future.")
        return value

    def validate_total_capacity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Total capacity must be greater than 0.")
        return value

    def validate_ticket_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Ticket price cannot be negative.")
        return value

    def validate(self, attrs):
        instance = self.instance
        if instance and 'total_capacity' in attrs:
            reserved = instance.total_capacity - instance.available_spots
            if attrs['total_capacity'] < reserved:
                raise serializers.ValidationError({
                    'total_capacity': (
                        f"Cannot reduce capacity to {attrs['total_capacity']}. "
                        f"There are already {reserved} reserved ticket(s)."
                    )
                })
        return attrs

    def create(self, validated_data):
        validated_data['available_spots'] = validated_data['total_capacity']
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'total_capacity' in validated_data:
            reserved = instance.total_capacity - instance.available_spots
            validated_data['available_spots'] = validated_data['total_capacity'] - reserved
        return super().update(instance, validated_data)


class ReservationSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source='event.name', read_only=True)
    event_code = serializers.CharField(source='event.event_code', read_only=True)

    class Meta:
        model = Reservation
        fields = ['id', 'event', 'event_name', 'event_code', 'buyer_email', 'ticket_count', 'created_at']
        read_only_fields = ['id', 'event_name', 'event_code', 'created_at']

    def validate_ticket_count(self, value):
        if value < 1:
            raise serializers.ValidationError("Must reserve at least 1 ticket.")
        if value > 5:
            raise serializers.ValidationError("Cannot reserve more than 5 tickets at once.")
        return value

    def validate(self, attrs):
        event = attrs.get('event')
        count = attrs.get('ticket_count', 0)
        if event:
            if event.available_spots <= 0:
                raise serializers.ValidationError({'event': f"Event '{event.name}' is sold out."})
            if count > event.available_spots:
                raise serializers.ValidationError({
                    'ticket_count': (
                        f"Only {event.available_spots} spot(s) available for '{event.name}'."
                    )
                })
        return attrs
