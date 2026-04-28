from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_all_projects(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Group = apps.get_model('auth', 'Group')
    UserProjectAssignment = apps.get_model('projects', 'UserProjectAssignment')

    try:
        from services.registry import read_registry
        projects = read_registry()
        project_names = [p['name'] for p in projects]
    except Exception:
        return

    if not project_names:
        return

    admin_user_ids = set(
        User.objects.filter(groups__in=Group.objects.filter(name='admin')).values_list('id', flat=True)
    )
    non_admin_users = User.objects.exclude(id__in=admin_user_ids)

    assignments = [
        UserProjectAssignment(user=user, project_name=name)
        for user in non_admin_users
        for name in project_names
    ]
    UserProjectAssignment.objects.bulk_create(assignments, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('projects', '0007_auditlog_user'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProjectAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('project_name', models.CharField(max_length=100)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='project_assignments',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['user__username', 'project_name'],
                'unique_together': {('user', 'project_name')},
            },
        ),
        migrations.RunPython(seed_all_projects, migrations.RunPython.noop),
    ]
