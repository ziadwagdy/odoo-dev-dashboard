from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('security', '0002_pushsubscription')]
    operations = [
        migrations.CreateModel(
            name='SeenItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scope', models.CharField(db_index=True, max_length=200)),
                ('kind', models.CharField(max_length=30)),
                ('item_id', models.CharField(max_length=100)),
                ('label', models.CharField(blank=True, default='', max_length=300)),
                ('first_seen', models.DateTimeField(auto_now_add=True)),
            ],
            options={'unique_together': {('scope', 'kind', 'item_id')}},
        ),
    ]
