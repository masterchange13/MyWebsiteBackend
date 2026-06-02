# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('document', '0005_document_is_public'),
    ]

    operations = [
        migrations.CreateModel(
            name='Comment',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('author', models.CharField(max_length=100)),
                ('content', models.TextField()),
                ('created_time', models.DateTimeField(auto_now_add=True)),
                (
                    'document',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='comments',
                        to='document.document',
                    ),
                ),
            ],
            options={
                'ordering': ['created_time'],
            },
        ),
    ]
