# prediction/management/commands/convert_to_tflite.py
import os
import tensorflow as tf
import json
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Convert a saved TensorFlow model to TFLite format for mobile use'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model_path',
            type=str,
            default=None,
            help='Path to saved model directory (default: MODEL_DIR/saved_model)'
        )
        parser.add_argument(
            '--output_path',
            type=str,
            default=None,
            help='Path to save TFLite model (default: MODEL_DIR/plant_disease_model.tflite)'
        )
        parser.add_argument(
            '--quantize',
            action='store_true',
            help='Apply quantization to reduce model size'
        )
        parser.add_argument(
            '--optimize',
            action='store_true',
            help='Apply optimizations'
        )

    def handle(self, *args, **options):
        # Set paths
        model_dir = settings.MODEL_DIR
        saved_model_dir = options['model_path'] or os.path.join(model_dir, 'saved_model')
        tflite_model_path = options['output_path'] or os.path.join(model_dir, 'plant_disease_model.tflite')
        
        # Check if saved model exists
        if not os.path.exists(saved_model_dir):
            self.stdout.write(self.style.ERROR(f'Saved model not found at {saved_model_dir}'))
            return
        
        self.stdout.write(self.style.SUCCESS('Converting model to TFLite...'))
        
        try:
            # Create TFLite converter
            converter = tf.lite.TFLiteConverter.from_saved_model(saved_model_dir)
            
            # Apply optimizations if requested
            if options['optimize']:
                self.stdout.write(self.style.SUCCESS('Applying optimizations...'))
                converter.optimizations = [tf.lite.Optimize.DEFAULT]
            
            # Apply quantization if requested
            if options['quantize']:
                self.stdout.write(self.style.SUCCESS('Applying quantization...'))
                converter.target_spec.supported_types = [tf.float16]
            
            # Convert model
            tflite_model = converter.convert()
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(tflite_model_path), exist_ok=True)
            
            # Save model
            with open(tflite_model_path, 'wb') as f:
                f.write(tflite_model)
            
            # Get model size
            model_size = os.path.getsize(tflite_model_path) / (1024 * 1024)
            
            self.stdout.write(self.style.SUCCESS(
                f'Model successfully converted and saved to {tflite_model_path}'
            ))
            self.stdout.write(self.style.SUCCESS(f'Model size: {model_size:.2f} MB'))
            
            # Create model info file
            model_info = {
                'model_path': tflite_model_path,
                'size_mb': round(model_size, 2),
                'optimized': options['optimize'],
                'quantized': options['quantize'],
                'conversion_date': str(tf.timestamp())
            }
            
            info_path = os.path.join(os.path.dirname(tflite_model_path), 'tflite_model_info.json')
            with open(info_path, 'w') as f:
                json.dump(model_info, f, indent=2)
                
            self.stdout.write(self.style.SUCCESS(f'Model info saved to {info_path}'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error converting model: {e}'))