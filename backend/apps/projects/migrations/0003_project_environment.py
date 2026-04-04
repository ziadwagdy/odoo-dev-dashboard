from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0002_add_backup_schedule_audit_log'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectEnvironment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('project', models.CharField(max_length=100, unique=True)),
                ('production_branch', models.CharField(blank=True, default='', max_length=200)),
                ('staging_branch', models.CharField(blank=True, default='', max_length=200)),
                ('dev_branch', models.CharField(blank=True, default='', max_length=200)),
            ],
            options={
                'ordering': ['project'],
            },
        ),
    ]
