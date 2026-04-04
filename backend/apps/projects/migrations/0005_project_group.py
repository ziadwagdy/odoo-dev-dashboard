from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0004_projectenvironment_add_db_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('production_instance', models.CharField(blank=True, default='', max_length=100)),
                ('staging_instance', models.CharField(blank=True, default='', max_length=100)),
                ('dev_instance', models.CharField(blank=True, default='', max_length=100)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
    ]
