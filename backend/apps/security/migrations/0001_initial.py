import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name='SecurityAlert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rule', models.CharField(max_length=60)),
                ('severity', models.CharField(choices=[('info', 'info'), ('warning', 'warning'), ('high', 'high'), ('critical', 'critical')], max_length=10)),
                ('source', models.CharField(max_length=100)),
                ('key', models.CharField(db_index=True, max_length=300)),
                ('summary', models.CharField(max_length=300)),
                ('sample', models.CharField(blank=True, default='', max_length=300)),
                ('count', models.PositiveIntegerField(default=1)),
                ('first_seen', models.DateTimeField(auto_now_add=True)),
                ('last_seen', models.DateTimeField(default=django.utils.timezone.now)),
                ('status', models.CharField(choices=[('open', 'open'), ('acknowledged', 'acknowledged')], default='open', max_length=15)),
                ('acknowledged_by', models.CharField(blank=True, default='', max_length=150)),
                ('acknowledged_at', models.DateTimeField(blank=True, null=True)),
                ('note', models.TextField(blank=True, default='')),
            ],
            options={'ordering': ['-last_seen']},
        ),
    ]
