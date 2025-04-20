# prediction/ml_utils.py
import os
import numpy as np
from PIL import Image
import tensorflow as tf
import json
from django.conf import settings

# Path to the saved model
MODEL_PATH = os.path.join(settings.MODEL_DIR, 'plant_disease_model.tflite')
METADATA_PATH = os.path.join(settings.MODEL_DIR, 'model_metadata.json')

class PlantDiseaseModel:
    def __init__(self):
        self.interpreter = None
        self.input_details = None
        self.output_details = None
        self.classes = {}
        self.image_size = 224  # Default size
        self.load_model()
        self.load_metadata()
    
    def load_metadata(self):
        """Load model metadata from JSON file"""
        try:
            if os.path.exists(METADATA_PATH):
                with open(METADATA_PATH, 'r') as f:
                    metadata = json.load(f)
                    
                    # Update class mapping
                    if 'classes' in metadata:
                        # Classes might be stored as {index: class_name} dictionary
                        if isinstance(metadata['classes'], dict):
                            self.classes = {int(k): v for k, v in metadata['classes'].items()}
                        # Or as a list of class names
                        elif isinstance(metadata['classes'], list):
                            self.classes = {i: name for i, name in enumerate(metadata['classes'])}
                    
                    # Update image size
                    if 'image_size' in metadata:
                        self.image_size = metadata['image_size']
                    
                    print(f"Loaded metadata: {len(self.classes)} classes, image size: {self.image_size}")
            else:
                print(f"Metadata file not found at {METADATA_PATH}")
                # Fall back to default class mapping from class_mapping.txt if it exists
                mapping_file = os.path.join(settings.MODEL_DIR, 'class_mapping.txt')
                if os.path.exists(mapping_file):
                    with open(mapping_file, 'r') as f:
                        for line in f:
                            parts = line.strip().split(',', 1)
                            if len(parts) == 2:
                                self.classes[int(parts[0])] = parts[1]
                    print(f"Loaded {len(self.classes)} classes from class_mapping.txt")
        except Exception as e:
            print(f"Error loading metadata: {e}")
    
    def load_model(self):
        """Load the TFLite model"""
        try:
            if os.path.exists(MODEL_PATH):
                self.interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
                self.interpreter.allocate_tensors()
                self.input_details = self.interpreter.get_input_details()
                self.output_details = self.interpreter.get_output_details()
                print(f"Model loaded successfully from {MODEL_PATH}")
            else:
                print(f"Model file not found at {MODEL_PATH}")
                self.interpreter = None
        except Exception as e:
            print(f"Error loading model: {e}")
            self.interpreter = None
    
    def preprocess_image(self, image_path):
        """Preprocess the image to fit model input"""
        try:
            img = Image.open(image_path)
            
            # Convert to RGB if needed (e.g., if PNG with transparency)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize to the expected input size
            img = img.resize((self.image_size, self.image_size))
            
            # Convert to numpy array and normalize
            img_array = np.array(img, dtype=np.float32)
            
            # Check if we need to normalize to [0,1] or [-1,1] 
            # (for MobileNetV2 we use [0,1])
            img_array = img_array / 255.0
            
            # Add batch dimension
            img_array = np.expand_dims(img_array, axis=0)
            
            return img_array
        except Exception as e:
            print(f"Error preprocessing image: {e}")
            return None
    
    def predict(self, image_path):
        """Make a prediction on the given image"""
        if not self.interpreter:
            return "Model not loaded", 0
        
        try:
            # Preprocess image
            input_data = self.preprocess_image(image_path)
            if input_data is None:
                return "Error preprocessing image", 0
            
            # Set input tensor
            self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
            
            # Run inference
            self.interpreter.invoke()
            
            # Get output tensor
            output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
            
            # Get predicted class and confidence
            pred_class = np.argmax(output_data[0])
            confidence = float(output_data[0][pred_class])
            
            # Map class index to disease name
            disease_name = self.classes.get(pred_class, f"Unknown_Class_{pred_class}")
            
            return disease_name, confidence
        except Exception as e:
            print(f"Prediction error: {e}")
            return "Error during prediction", 0

    def get_top_predictions(self, image_path, top_k=3):
        """Get top-k predictions for the image"""
        if not self.interpreter:
            return [("Model not loaded", 0)]
        
        try:
            # Preprocess image
            input_data = self.preprocess_image(image_path)
            if input_data is None:
                return [("Error preprocessing image", 0)]
            
            # Set input tensor
            self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
            
            # Run inference
            self.interpreter.invoke()
            
            # Get output tensor
            output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
            
            # Get top k predictions
            indices = np.argsort(output_data[0])[-top_k:][::-1]
            results = []
            
            for idx in indices:
                confidence = float(output_data[0][idx])
                disease_name = self.classes.get(idx, f"Unknown_Class_{idx}")
                results.append((disease_name, confidence))
            
            return results
        except Exception as e:
            print(f"Prediction error: {e}")
            return [("Error during prediction", 0)]

# Initialize the model (singleton)
plant_disease_model = PlantDiseaseModel()