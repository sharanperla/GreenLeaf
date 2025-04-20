# prediction/models.py
from django.db import models
from django.contrib.auth.models import User

class PlantDisease(models.Model):
    name = models.CharField(max_length=255)
    scientific_name = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField()
    symptoms = models.TextField()
    treatment = models.TextField()
    prevention = models.TextField()
    image = models.ImageField(upload_to='disease_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Prediction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='predictions')
    plant_disease = models.ForeignKey(PlantDisease, on_delete=models.CASCADE, related_name='predictions')
    image = models.ImageField(upload_to='prediction_images/')
    confidence_score = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_offline = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.username} - {self.plant_disease.name} - {self.created_at}"