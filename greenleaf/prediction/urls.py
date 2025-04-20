# prediction/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PlantDiseaseViewSet, PredictionViewSet, MakePredictionView, ModelInfoView,ExportModelView

router = DefaultRouter()
router.register(r'diseases', PlantDiseaseViewSet)
router.register(r'predictions', PredictionViewSet, basename='prediction')

urlpatterns = [
    path('', include(router.urls)),
    path('predict/', MakePredictionView.as_view(), name='predict'),
    path('model-info/', ModelInfoView.as_view(), name='model_info'),
    path('export-model/', ExportModelView.as_view(), name='export_model'),
]