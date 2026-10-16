from django.db import models
from django.utils import timezone


class SecurityAlert(models.Model):
    """A de-duplicated detection (see services/detection.py and services/alerting.py)."""
    SEVERITIES = [('info', 'info'), ('warning', 'warning'), ('high', 'high'), ('critical', 'critical')]
    STATUSES = [('open', 'open'), ('acknowledged', 'acknowledged')]

    rule            = models.CharField(max_length=60)
    severity        = models.CharField(max_length=10, choices=SEVERITIES)
    source          = models.CharField(max_length=100)               # e.g. the database container
    key             = models.CharField(max_length=300, db_index=True)  # what counts as "the same thing"
    summary         = models.CharField(max_length=300)
    sample          = models.CharField(max_length=300, blank=True, default='')   # scrubbed evidence line
    count           = models.PositiveIntegerField(default=1)
    first_seen      = models.DateTimeField(auto_now_add=True)
    last_seen       = models.DateTimeField(default=timezone.now)
    status          = models.CharField(max_length=15, choices=STATUSES, default='open')
    acknowledged_by = models.CharField(max_length=150, blank=True, default='')
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    note            = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-last_seen']


class PushSubscription(models.Model):
    """A browser/phone registered for Web Push by an admin."""
    user       = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='push_subscriptions')
    endpoint   = models.TextField(unique=True)
    p256dh     = models.CharField(max_length=200)
    auth       = models.CharField(max_length=100)
    user_agent = models.CharField(max_length=300, blank=True, default='')
    created    = models.DateTimeField(auto_now_add=True)
    last_ok    = models.DateTimeField(null=True, blank=True)
