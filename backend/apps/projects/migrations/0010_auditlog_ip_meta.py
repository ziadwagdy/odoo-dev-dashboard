from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0009_configchangerequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='auditlog',
            name='ip',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.AddField(
            model_name='auditlog',
            name='meta',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
