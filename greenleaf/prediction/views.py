# prediction/views.py

import os
import uuid
import json
import datetime
import tempfile

from django.conf import settings
from django.db.models import Count
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from django.http import FileResponse

from rest_framework import status, viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from .models import PlantDisease, Prediction
from .serializers import PlantDiseaseSerializer, PredictionSerializer
from .ml_utils import plant_disease_model
import traceback
import logging

logger = logging.getLogger(__name__)


class PlantDiseaseViewSet(viewsets.ReadOnlyModelViewSet):
    """Viewset to list and retrieve plant diseases"""
    queryset = PlantDisease.objects.all()
    serializer_class = PlantDiseaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def common(self, request):
        """Return the most commonly predicted plant diseases"""
        common_diseases = PlantDisease.objects.annotate(
            prediction_count=Count('predictions')
        ).order_by('-prediction_count')[:10]

        serializer = self.get_serializer(common_diseases, many=True)
        return Response(serializer.data)


class PredictionViewSet(viewsets.ModelViewSet):
    """Viewset for viewing and creating predictions"""
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
        Sync offline predictions to the server.
        Expects a list of predictions with image_data (Base64), disease_name, confidence, and timestamp.
        """
        if not request.data:
            return Response({'error': 'No data provided'}, status=status.HTTP_400_BAD_REQUEST)

        offline_predictions = request.data
        synced_predictions = []
        errors = []

        for idx, pred_data in enumerate(offline_predictions):
            try:
                image_data = pred_data.get('image_data')  # This should be raw binary, not base64
                disease_name = pred_data.get('disease_name')
                confidence = pred_data.get('confidence', 0)
                timestamp = pred_data.get('timestamp')

                if not image_data or not disease_name:
                    errors.append({'index': idx, 'error': 'Missing image data or disease name'})
                    continue

                # Find or create plant disease
                plant_disease, _ = PlantDisease.objects.get_or_create(
                    name=disease_name,
                    defaults={
                        "description": "Information not available yet",
                        "symptoms": "Information not available yet",
                        "treatment": "Information not available yet",
                        "prevention": "Information not available yet"
                    }
                )

                # Save image
                image_name = f"offline_{uuid.uuid4()}.jpg"
                image_path = default_storage.save(
                    os.path.join('prediction_images', image_name),
                    ContentFile(image_data)
                )

                # Create prediction
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
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            image = request.FILES.get('image')

            if not image:
                return Response({'error': 'No image provided'}, status=status.HTTP_400_BAD_REQUEST)

            # Use a safe temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                temp_file.write(image.read())
                temp_path = temp_file.name

            # Get predictions
            predictions = plant_disease_model.get_top_predictions(temp_path, top_k=3)

            if not predictions:
                return Response({'error': 'No predictions returned from model'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            disease_name, confidence = predictions[0]
            other_predictions = predictions[1:]

            return Response({
                'disease': disease_name,
                'confidence': round(confidence * 100, 2),
                'other_predictions': [
                    {'disease': name, 'confidence': round(conf * 100, 2)}
                    for name, conf in other_predictions
                ]
            })

        except Exception as e:
            logger.error("Prediction failed: %s", traceback.format_exc())
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        finally:
            # Clean up the temporary image file
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)


class ModelInfoView(APIView):
    """View to retrieve info about the loaded ML model"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        model_dir = settings.MODEL_DIR
        metadata_path = os.path.join(model_dir, 'model_metadata.json')
        tflite_path = os.path.join(model_dir, 'plant_disease_model.tflite')

        model_info = {
            'status': 'loaded' if plant_disease_model.interpreter else 'not_loaded',
            'classes': len(plant_disease_model.classes),
            'image_size': plant_disease_model.image_size,
        }

        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r') as f:
                    model_info['metadata'] = json.load(f)
            except Exception as e:
                model_info['metadata_error'] = str(e)

        if os.path.exists(tflite_path):
            model_info['model_size_mb'] = round(os.path.getsize(tflite_path) / (1024 * 1024), 2)
            model_info['model_last_modified'] = datetime.datetime.fromtimestamp(
                os.path.getmtime(tflite_path)
            ).isoformat()

        return Response(model_info)


class ExportModelView(APIView):
    """View to download/export the TFLite model file for mobile use"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        model_dir = settings.MODEL_DIR
        tflite_path = os.path.join(model_dir, 'plant_disease_model.tflite')
        metadata_path = os.path.join(model_dir, 'model_metadata.json')

        if not os.path.exists(tflite_path):
            return Response({'error': 'Model not found'}, status=status.HTTP_404_NOT_FOUND)

        if request.query_params.get('download', '').lower() == 'true':
            return FileResponse(
                open(tflite_path, 'rb'),
                as_attachment=True,
                filename='plant_disease_model.tflite'
            )

        metadata = {}
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            except Exception as e:
                metadata = {'error': str(e)}

        model_size = round(os.path.getsize(tflite_path) / (1024 * 1024), 2)
        last_modified = datetime.datetime.fromtimestamp(
            os.path.getmtime(tflite_path)
        ).isoformat()

        return Response({
            'model_size_mb': model_size,
            'last_modified': last_modified,
            'metadata': metadata,
            'download_url': request.build_absolute_uri() + '?download=true'
        })
