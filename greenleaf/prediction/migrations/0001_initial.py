# Generated by Django 5.2 on 2025-04-20 05:35

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
            name='PlantDisease',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('scientific_name', models.CharField(blank=True, max_length=255, null=True)),
                ('description', models.TextField()),
                ('symptoms', models.TextField()),
                ('treatment', models.TextField()),
                ('prevention', models.TextField()),
                ('image', models.ImageField(blank=True, null=True, upload_to='disease_images/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Prediction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='prediction_images/')),
                ('confidence_score', models.FloatField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_offline', models.BooleanField(default=False)),
                ('plant_disease', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='predictions', to='prediction.plantdisease')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='predictions', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
