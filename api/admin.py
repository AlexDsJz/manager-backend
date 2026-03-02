from django.contrib import admin
from api.models.events.event import Event
from api.models.events.reservation import Reservation
from api.models.sat.import_batch import SATImportBatch
from api.models.sat.canceled_taxpayer import CanceledTaxpayer


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('event_code', 'name', 'date', 'total_capacity', 'available_spots', 'ticket_price')
    list_filter = ('date',)
    search_fields = ('event_code', 'name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('id', 'event', 'buyer_email', 'ticket_count', 'created_at')
    list_filter = ('event',)
    search_fields = ('buyer_email', 'event__event_code')
    readonly_fields = ('created_at',)


@admin.register(SATImportBatch)
class SATImportBatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'started_at', 'finished_at', 'records_imported', 'execution_seconds')
    list_filter = ('status',)
    readonly_fields = ('started_at', 'finished_at', 'records_imported', 'execution_seconds', 'error_message')


@admin.register(CanceledTaxpayer)
class CanceledTaxpayerAdmin(admin.ModelAdmin):
    list_display = ('rfc', 'name', 'person_type', 'state', 'batch')
    list_filter = ('person_type', 'state')
    search_fields = ('rfc', 'name')
    raw_id_fields = ('batch',)
