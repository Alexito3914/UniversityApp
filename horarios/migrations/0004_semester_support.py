from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('horarios', '0003_professor_display_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='schedule',
            name='semester',
            field=models.CharField(
                choices=[('S1', '1º cuatrimestre'), ('S2', '2º cuatrimestre')],
                default='S1',
                max_length=2,
            ),
        ),
        migrations.AddField(
            model_name='subjectoffering',
            name='semester',
            field=models.CharField(
                choices=[('S1', '1º cuatrimestre'), ('S2', '2º cuatrimestre')],
                default='S1',
                max_length=2,
            ),
        ),
        migrations.AddField(
            model_name='subjectoffering',
            name='weekly_sessions',
            field=models.PositiveSmallIntegerField(default=2),
        ),
        migrations.AlterUniqueTogether(
            name='subjectoffering',
            unique_together={('subject', 'course', 'group_name', 'semester')},
        ),
    ]
