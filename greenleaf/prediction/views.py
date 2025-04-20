# prediction/views.py
from rest_framework import status, viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.db.models import Count
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import uuid
import json
import datetime
from django.conf import settings


from .models import PlantDisease, Prediction
from .serializers import PlantDiseaseSerializer, PredictionSerializer
from .ml_utils import plant_disease_model

class PlantDiseaseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A viewset for viewing plant diseases
    """
    queryset = PlantDisease.objects.all()
    serializer_class = PlantDiseaseSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def common(self, request):
        """Return most common plant diseases based on predictions"""
        common_diseases = PlantDisease.objects.annotate(
            prediction_count=Count('predictions')
        ).order_by('-prediction_count')[:10]
        
        serializer = self.get_serializer(common_diseases, many=True)
        return Response(serializer.data)

class PredictionViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and creating predictions
    """
    serializer_class = PredictionSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        return Prediction.objects.filter(user=self.request.user).order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Return recent predictions for the current user"""
        recent_predictions = self.get_queryset()[:5]
        serializer = self.get_serializer(recent_predictions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def sync_offline(self, request):
        """
        Sync offline predictions with the server
        Expects a JSON array of offline predictions
        """
        if not request.data:
            return Response({'error': 'No data provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Process batch of offline predictions
        offline_predictions = request.data
        synced_predictions = []
        errors = []
        
        for idx, pred_data in enumerate(offline_predictions):
            try:
                # Extract prediction details
                image_data = pred_data.get('image_data')  # Base64 encoded image
                disease_name = pred_data.get('disease_name')
                confidence = pred_data.get('confidence', 0)
                timestamp = pred_data.get('timestamp')
                
                if not image_data or not disease_name:
                    errors.append({'index': idx, 'error': 'Missing image data or disease name'})
                    continue
                
                # Find or create disease
                try:
                    plant_disease = PlantDisease.objects.get(name=disease_name)
                except PlantDisease.DoesNotExist:
                    plant_disease = PlantDisease.objects.create(
                        name=disease_name,
                        description="Information not available yet",
                        symptoms="Information not available yet",
                        treatment="Information not available yet",
                        prevention="Information not available yet"
                    )
                
                # Save image from base64
                image_name = f"offline_{uuid.uuid4()}.jpg"
                image_path = default_storage.save(
                    os.path.join('prediction_images', image_name),
                    ContentFile(image_data)
                )
                
                # Create prediction record
                prediction = Prediction.objects.create(
                    user=request.user,
                    plant_disease=plant_disease,
                    image=image_path,
                    confidence_score=confidence,
                    is_offline=True,
                    created_at=datetime.datetime.fromisoformat(timestamp) if timestamp else datetime.datetime.now()
                )
                
                synced_predictions.append(PredictionSerializer(prediction).data)
                
            except Exception as e:
                errors.append({'index': idx, 'error': str(e)})
        
        return Response({
            'synced': len(synced_predictions),
            'failed': len(errors),
            'predictions': synced_predictions,
            'errors': errors
        })

class MakePredictionView(APIView):
    """
    API view for making a prediction from an image
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        if 'image' not in request.FILES:
            return Response({'error': 'No image provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        image = request.FILES['image']
        is_offline = request.data.get('is_offline', 'false').lower() == 'true'
        
        # Generate a unique filename
        ext = os.path.splitext(image.name)[1]
        unique_filename = f"{uuid.uuid4()}{ext}"
        
        # Save the image temporarily
        temp_path = os.path.join('/tmp', unique_filename)
        with open(temp_path, 'wb+') as temp_file:
            for chunk in image.chunks():
                temp_file.write(chunk)
        
        # Make prediction
        try:
            # Get top 3 predictions
            predictions = plant_disease_model.get_top_predictions(temp_path, top_k=3)
            
            if not predictions:
                return Response({'error': 'No predictions returned from model'}, 
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Get top prediction
            disease_name, confidence = predictions[0]
            
            # Find the disease in the database
            try:
                plant_disease = PlantDisease.objects.get(name=disease_name)
            except PlantDisease.DoesNotExist:
                # If the disease doesn't exist in the database, create a placeholder
                plant_disease = PlantDisease.objects.create(
                    name=disease_name,
                    description="Information not available yet.",
                    symptoms="Information not available yet.",
                    treatment="Information not available yet.",
                    prevention="Information not available yet."
                )
            
            # Create prediction record
            prediction = Prediction.objects.create(
                user=request.user,
                plant_disease=plant_disease,
                image=image,
                confidence_score=confidence,
                is_offline=is_offline
            )
            
            # Prepare response data
            response_data = {
                'prediction': PredictionSerializer(prediction).data,
                'all_predictions': [
                    {
                        'disease_name': pred[0],
                        'confidence': pred[1]
                    } for pred in predictions
                ]
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)

class ModelInfoView(APIView):
    """
    View to get information about the current ML model
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        model_dir = settings.MODEL_DIR
        metadata_path = os.path.join(model_dir, 'model_metadata.json')
        
        model_info = {
            'status': 'loaded' if plant_disease_model.interpreter else 'not_loaded',
            'classes': len(plant_disease_model.classes),
            'image_size': plant_disease_model.image_size,
        }
        
        # Add metadata if available
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                model_info['metadata'] = metadata
            except Exception as e:
                model_info['metadata_error'] = str(e)
        
        # Add model file info
        tflite_path = os.path.join(model_dir, 'plant_disease_model.tflite')
        if os.path.exists(tflite_path):
            model_info['model_size_mb'] = os.path.getsize(tflite_path) / (1024 * 1024)
            model_info['model_last_modified'] = datetime.datetime.fromtimestamp(
                os.path.getmtime(tflite_path)
            ).isoformat()
        
        return Response(model_info)

# prediction/views.py (add this function to the existing file)

class ExportModelView(APIView):
    """
    View to export the TFLite model for mobile use
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        model_dir = settings.MODEL_DIR
        tflite_path = os.path.join(model_dir, 'plant_disease_model.tflite')
        
        if not os.path.exists(tflite_path):
            return Response(
                {'error': 'Model not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get model metadata
        metadata_path = os.path.join(model_dir, 'model_metadata.json')
        metadata = {}
        
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            except Exception as e:
                metadata = {'error': str(e)}
        
        # Check if the request includes 'download' parameter
        if request.query_params.get('download', '').lower() == 'true':
            from django.http import FileResponse
            return FileResponse(
                open(tflite_path, 'rb'),
                as_attachment=True,
                filename='plant_disease_model.tflite'
            )
        
        # Otherwise return model info
        model_size = os.path.getsize(tflite_path) / (1024 * 1024)
        last_modified = datetime.datetime.fromtimestamp(
            os.path.getmtime(tflite_path)
        ).isoformat()
        
        return Response({
            'model_size_mb': round(model_size, 2),
            'last_modified': last_modified,
            'metadata': metadata,
            'download_url': request.build_absolute_uri() + '?download=true'
        })