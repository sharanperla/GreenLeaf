# prediction/serializers.py
from rest_framework import serializers
from .models import PlantDisease, Prediction

class PlantDiseaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlantDisease
        fields = '__all__'

class PredictionSerializer(serializers.ModelSerializer):
    plant_disease = PlantDiseaseSerializer(read_only=True)
    plant_disease_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = Prediction
        fields = ('id', 'user', 'plant_disease', 'plant_disease_id', 'image', 
                  'confidence_score', 'created_at', 'is_offline')
        read_only_fields = ('user', 'confidence_score')