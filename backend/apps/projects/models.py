from django.db import models


class DeployHistory(models.Model):
    project          = models.CharField(max_length=100)
    triggered_at     = models.DateTimeField(auto_now_add=True)
    trigger_type     = models.CharField(max_length=20, default='manual')
    prev_commit      = models.CharField(max_length=40, null=True, blank=True)
    new_commit       = models.CharField(max_length=40, null=True, blank=True)
    outcome          = models.CharField(max_length=20)
    duration_seconds = models.FloatField(null=True, blank=True)
    log_snippet      = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-triggered_at']


class CronJob(models.Model):
    project     = models.CharField(max_length=100, unique=True)
    schedule    = models.CharField(max_length=50, default='*/2 * * * *')
    enabled     = models.BooleanField(default=True)
    last_run    = models.DateTimeField(null=True, blank=True)
    last_result = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        ordering = ['project']
