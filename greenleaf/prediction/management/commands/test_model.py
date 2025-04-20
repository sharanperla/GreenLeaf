# prediction/management/commands/test_model.py
import os
import argparse
from django.core.management.base import BaseCommand
from django.conf import settings
from prediction.ml_utils import plant_disease_model

class Command(BaseCommand):
    help = 'Test the plant disease detection model with a sample image'

    def add_arguments(self, parser):
        parser.add_argument(
            'image_path',
            type=str,
            help='Path to the test image'
        )
        parser.add_argument(
            '--top_k',
            type=int,
            default=3,
            help='Number of top predictions to show'
        )

    def handle(self, *args, **options):
        image_path = options['image_path']
        top_k = options['top_k']
        
        if not os.path.exists(image_path):
            self.stdout.write(self.style.ERROR(f'Image not found at {image_path}'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Testing model with image: {image_path}'))
        
        # Get top predictions
        predictions = plant_disease_model.get_top_predictions(image_path, top_k=top_k)
        
        # Print results
        self.stdout.write(self.style.SUCCESS('Predictions:'))
        for i, (disease_name, confidence) in enumerate(predictions):
            self.stdout.write(f"{i+1}. {disease_name}: {confidence*100:.2f}%")
        
        # If no predictions were made
        if not predictions:
            self.stdout.write(self.style.ERROR('No predictions were made. Check if the model is loaded correctly.'))