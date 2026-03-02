from rest_framework import viewsets, mixins, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from api.models.sat.import_batch import SATImportBatch
from api.models.sat.canceled_taxpayer import CanceledTaxpayer
from api.serializers.sat_serializers import SATImportBatchSerializer, CanceledTaxpayerSerializer
from api.services.sat_scraper import SAT_PAGE_URL, run_import


class SATImportBatchViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = SATImportBatch.objects.all().order_by('-started_at')
    serializer_class = SATImportBatchSerializer

    @action(detail=False, methods=['post'], url_path='trigger')
    def trigger(self, request):
        if SATImportBatch.objects.filter(status=SATImportBatch.Status.RUNNING).exists():
            return Response(
                {'error': 'An import is already running. Wait for it to finish.'},
                status=status.HTTP_409_CONFLICT,
            )

        batch = SATImportBatch.objects.create(
            status=SATImportBatch.Status.PENDING,
            source_url=SAT_PAGE_URL,
        )

        try:
            run_import(batch)
            batch.refresh_from_db()
            return Response(SATImportBatchSerializer(batch).data, status=status.HTTP_200_OK)
        except Exception as exc:
            batch.refresh_from_db()
            return Response(
                {'error': str(exc), 'batch': SATImportBatchSerializer(batch).data},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class CanceledTaxpayerViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = CanceledTaxpayerSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['rfc', 'name', 'state']
    ordering_fields = ['rfc', 'name']

    def get_queryset(self):
        qs = CanceledTaxpayer.objects.select_related('batch').order_by('rfc')
        batch_id = self.request.query_params.get('batch')
        if batch_id:
            qs = qs.filter(batch_id=batch_id)
        return qs


router = DefaultRouter()
router.register(r'sat/batches', SATImportBatchViewSet, basename='sat-batch')
router.register(r'sat/canceled', CanceledTaxpayerViewSet, basename='sat-canceled')

urlpatterns = router.urls
