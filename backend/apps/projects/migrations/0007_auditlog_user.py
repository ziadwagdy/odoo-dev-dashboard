# Generated migration — add user field to AuditLog

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0006_remove_multienv_tables'),
    ]

    operations = [
        migrations.AddField(
            model_name='auditlog',
            name='user',
            field=models.CharField(blank=True, default='', max_length=150),
        ),
    ]
