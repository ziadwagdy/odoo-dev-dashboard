from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0003_project_environment'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectenvironment',
            name='production_db',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='projectenvironment',
            name='staging_db',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='projectenvironment',
            name='dev_db',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
    ]
