from rest_framework import serializers
from .models import DeployHistory, CronJob, BackupSchedule, AuditLog


class DeployHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DeployHistory
        fields = '__all__'


class CronJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = CronJob
        fields = '__all__'


class BackupScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackupSchedule
        fields = '__all__'


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = '__all__'
