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


class BackupSchedule(models.Model):
    project    = models.CharField(max_length=100)
    dbname     = models.CharField(max_length=100)
    schedule   = models.CharField(max_length=50, default='0 2 * * *')
    enabled    = models.BooleanField(default=False)
    retention  = models.IntegerField(default=7)
    last_run   = models.DateTimeField(null=True, blank=True)
    last_result = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        unique_together = ('project', 'dbname')
        ordering = ['project', 'dbname']


class AuditLog(models.Model):
    project      = models.CharField(max_length=100)
    action       = models.CharField(max_length=50)
    detail       = models.TextField(blank=True)
    outcome      = models.CharField(max_length=20, default='success')
    user         = models.CharField(max_length=150, blank=True, default='')
    triggered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-triggered_at']


class UserProjectAssignment(models.Model):
    user         = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='project_assignments',
    )
    project_name = models.CharField(max_length=100)

    class Meta:
        unique_together = ('user', 'project_name')
        ordering = ['user__username', 'project_name']


class ConfigChangeRequest(models.Model):
    """A requested change to a project's runtime settings. Nothing is written to
    odoo.conf until an admin has reviewed the validated diff and approved it."""
    STATUS = [('pending', 'pending'), ('applied', 'applied'), ('rejected', 'rejected'),
              ('failed', 'failed'), ('cancelled', 'cancelled')]

    project          = models.CharField(max_length=100)
    requested_by     = models.CharField(max_length=150)
    requested_at     = models.DateTimeField(auto_now_add=True)
    status           = models.CharField(max_length=20, choices=STATUS, default='pending')
    changes          = models.JSONField(default=dict)    # {key: new value (UI units)}
    previous         = models.JSONField(default=dict)    # {key: value at request time}
    warnings         = models.JSONField(default=list)
    reason           = models.TextField(blank=True, default='')
    restart_required = models.BooleanField(default=True)
    decided_by       = models.CharField(max_length=150, blank=True, default='')
    decided_at       = models.DateTimeField(null=True, blank=True)
    decision_note    = models.TextField(blank=True, default='')
    applied_at       = models.DateTimeField(null=True, blank=True)
    result           = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-requested_at']
