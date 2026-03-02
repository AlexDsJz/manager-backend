from rest_framework import viewsets, mixins, filters, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from api.models.events.event import Event
from api.models.events.reservation import Reservation
from api.serializers.event_serializers import EventSerializer, ReservationSerializer
from api.services.event_service import can_delete_event
from api.services.reservation_service import create_reservation


class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all().order_by('date')
    serializer_class = EventSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'event_code']
    ordering_fields = ['date', 'ticket_price', 'available_spots']

    def get_permissions(self):
        # Any authenticated user can list/retrieve events
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        # Only admins can create, update or delete
        return [IsAdminUser()]

    def destroy(self, request, *args, **kwargs):
        event = self.get_object()
        error = can_delete_event(event)
        if error:
            return Response({'error': error}, status=status.HTTP_409_CONFLICT)
        self.perform_destroy(event)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReservationViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ReservationSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['buyer_email', 'event__name', 'event__event_code']
    ordering_fields = ['created_at']

    def get_permissions(self):
        # Any authenticated user can create a reservation
        if self.action == 'create':
            return [IsAuthenticated()]
        # Only admins can list or retrieve reservations
        return [IsAdminUser()]

    def get_queryset(self):
        qs = Reservation.objects.select_related('event').order_by('-created_at')
        event_id = self.request.query_params.get('event')
        if event_id:
            qs = qs.filter(event_id=event_id)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reservation = create_reservation(serializer.validated_data)
        return Response(self.get_serializer(reservation).data, status=status.HTTP_201_CREATED)


router = DefaultRouter()
router.register(r'events', EventViewSet, basename='event')
router.register(r'reservations', ReservationViewSet, basename='reservation')

urlpatterns = router.urls
