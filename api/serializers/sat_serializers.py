from rest_framework import serializers
from api.models.sat.import_batch import SATImportBatch
from api.models.sat.canceled_taxpayer import CanceledTaxpayer


class SATImportBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = SATImportBatch
        fields = [
            'id', 'status', 'source_url', 'started_at', 'finished_at',
            'records_imported', 'execution_seconds', 'error_message',
        ]
        read_only_fields = fields


class CanceledTaxpayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = CanceledTaxpayer
        fields = [
            'id', 'batch', 'rfc', 'name', 'person_type',
            'assumption', 'credit_number', 'amount', 'state', 'extra_data',
        ]
