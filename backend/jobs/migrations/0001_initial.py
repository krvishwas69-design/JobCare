import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Candidate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('role', models.CharField(blank=True, max_length=200)),
                ('city', models.CharField(blank=True, max_length=100)),
                ('area', models.CharField(blank=True, max_length=100)),
                ('experience', models.CharField(blank=True, max_length=50)),
                ('expected_salary', models.CharField(blank=True, max_length=50)),
                ('skills', models.JSONField(blank=True, default=list)),
                ('phone', models.CharField(max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Job',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=300)),
                ('category', models.CharField(default='General', max_length=50)),
                ('job_type', models.CharField(default='Full Time', max_length=20)),
                ('location', models.CharField(max_length=200)),
                ('min_salary', models.PositiveIntegerField(default=0)),
                ('max_salary', models.PositiveIntegerField(default=0)),
                ('openings', models.PositiveIntegerField(default=1)),
                ('description', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('active', 'Active'), ('closed', 'Closed')], default='draft', max_length=10)),
                ('plan', models.CharField(blank=True, max_length=20)),
                ('activated_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('posted_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='jobs', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at', '-id']},
        ),
        migrations.CreateModel(
            name='Application',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('applied', 'Applied'), ('shortlisted', 'Shortlisted'), ('interviewed', 'Interviewed'), ('hired', 'Hired'), ('rejected', 'Rejected')], default='applied', max_length=20)),
                ('applied_at', models.DateTimeField(auto_now_add=True)),
                ('candidate', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='applications', to='jobs.candidate')),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='applications', to='jobs.job')),
            ],
            options={'ordering': ['-applied_at', '-id']},
        ),
        migrations.CreateModel(
            name='CandidateUnlock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('candidate', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='unlocks', to='jobs.candidate')),
                ('employer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='unlocks', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name='application',
            constraint=models.UniqueConstraint(fields=('job', 'candidate'), name='unique_application_per_job'),
        ),
        migrations.AddConstraint(
            model_name='candidateunlock',
            constraint=models.UniqueConstraint(fields=('employer', 'candidate'), name='unique_unlock_per_employer'),
        ),
    ]
