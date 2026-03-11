from rest_framework import serializers
from .models import DeployHistory, CronJob


class DeployHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DeployHistory
        fields = '__all__'


class CronJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = CronJob
        fields = '__all__'
