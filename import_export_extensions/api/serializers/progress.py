from rest_framework import serializers


class ProgressInfoSerializer(serializers.Serializer):
    """Serializer to show progress info, like how much is done."""

    current = serializers.IntegerField()
    total = serializers.IntegerField()


class ProgressSerializer(serializers.Serializer):
    """Serializer to show progress of job."""

    info = ProgressInfoSerializer()
