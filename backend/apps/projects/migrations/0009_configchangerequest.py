from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0008_user_project_assignment'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConfigChangeRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('project', models.CharField(max_length=100)),
                ('requested_by', models.CharField(max_length=150)),
                ('requested_at', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(choices=[('pending', 'pending'), ('applied', 'applied'), ('rejected', 'rejected'), ('failed', 'failed'), ('cancelled', 'cancelled')], default='pending', max_length=20)),
                ('changes', models.JSONField(default=dict)),
                ('previous', models.JSONField(default=dict)),
                ('warnings', models.JSONField(default=list)),
                ('reason', models.TextField(blank=True, default='')),
                ('restart_required', models.BooleanField(default=True)),
                ('decided_by', models.CharField(blank=True, default='', max_length=150)),
                ('decided_at', models.DateTimeField(blank=True, null=True)),
                ('decision_note', models.TextField(blank=True, default='')),
                ('applied_at', models.DateTimeField(blank=True, null=True)),
                ('result', models.TextField(blank=True, default='')),
            ],
            options={'ordering': ['-requested_at']},
        ),
    ]
