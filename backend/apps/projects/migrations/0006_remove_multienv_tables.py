from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0005_project_group'),
    ]

    operations = [
        migrations.DeleteModel(name='ProjectEnvironment'),
        migrations.DeleteModel(name='ProjectGroup'),
    ]
