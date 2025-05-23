# prediction/management/commands/populate_diseases.py
import os
import json
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.conf import settings
from prediction.models import PlantDisease

class Command(BaseCommand):
    help = 'Populate the plant disease database with information'

    def add_arguments(self, parser):
        parser.add_argument(
            '--metadata',
            type=str,
            default=None,
            help='Path to model metadata file (default: MODEL_DIR/model_metadata.json)'
        )

    def handle(self, *args, **options):
        PlantDisease.objects.all().delete()
        model_dir = settings.MODEL_DIR
        metadata_path = options['metadata'] or os.path.join(model_dir, 'model_metadata.json')
        
        if not os.path.exists(metadata_path):
            mapping_file = os.path.join(model_dir, 'class_mapping.txt')
            if os.path.exists(mapping_file):
                self.stdout.write(self.style.SUCCESS(f'Using class mapping file: {mapping_file}'))
                class_names = {}
                with open(mapping_file, 'r') as f:
                    for line in f:
                        parts = line.strip().split(',', 1)
                        if len(parts) == 2:
                            class_names[int(parts[0])] = parts[1]
            else:
                self.stdout.write(self.style.ERROR(f'Metadata file not found at {metadata_path}'))
                return
        else:
            # Load metadata
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                
            if 'classes' in metadata:
                if isinstance(metadata['classes'], dict):
                    class_names = {int(k): v for k, v in metadata['classes'].items()}
                elif isinstance(metadata['classes'], list):
                    class_names = {i: name for i, name in enumerate(metadata['classes'])}
            else:
                self.stdout.write(self.style.ERROR('No class information found in metadata'))
                return
        
        # Basic disease information database
        # This would ideally come from a more comprehensive source
        disease_info = {
    "Pepper,_bell___Bacterial_spot": {
        "scientific_name": "Xanthomonas campestris pv. vesicatoria",
        "description": "Bacterial spot affects bell pepper leaves and fruits, causing dark, water-soaked spots.",
        "symptoms": "Small, water-soaked spots on leaves and fruits that turn brown and necrotic.",
        "treatment": "Apply copper-based bactericides and remove infected plant debris.",
        "prevention": "Use certified disease-free seeds, avoid overhead watering, and rotate crops.",
         "image_url": "https://plantpathology.ca.uky.edu/files/ppfs-vg-17.pdf"
    },
    "Pepper,_bell___healthy": {
        "scientific_name": "",
        "description": "Healthy bell pepper plant without any disease symptoms.",
        "symptoms": "No visible signs of disease.",
        "treatment": "No treatment needed.",
        "prevention": "Maintain regular care and good agricultural practices.",
         "image_url": "https://upload.wikimedia.org/wikipedia/commons/6/6f/Bell_pepper_plant.jpg"
    },
    "Potato___Early_blight": {
        "scientific_name": "Alternaria solani",
        "description": "Early blight is a common fungal disease in potatoes causing leaf spots and blight.",
        "symptoms": "Dark brown spots with concentric rings on older leaves.",
        "treatment": "Use fungicides and remove infected leaves.",
        "prevention": "Practice crop rotation and proper spacing for airflow.",
        "image_url": "https://www.gardeningknowhow.com/wp-content/uploads/2020/07/potato-early-blight.jpg"
    },
     "Potato___healthy": {
        "scientific_name": "",
        "description": "Healthy potato plant without disease symptoms.",
        "symptoms": "No visible signs of disease.",
        "treatment": "No treatment needed.",
        "prevention": "Maintain regular care and good agricultural practices.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/3/3f/Potato_plants.jpg"
    },
    "Tomato___Bacterial_spot": {
        "scientific_name": "Xanthomonas campestris pv. vesicatoria",
        "description": "Bacterial spot affects tomato leaves, stems, and fruit with dark, necrotic spots.",
        "symptoms": "Small brown to black spots on leaves, often with yellow halos.",
        "treatment": "Copper-based sprays may help control the spread.",
        "prevention": "Use disease-free seeds and improve air circulation.",
        "image_url": "https://hort.extension.wisc.edu/wp-content/uploads/sites/117/2021/04/Bacterial-spot-on-tomato-leaves.jpg"
    },
    "Tomato___Early_blight": {
        "scientific_name": "Alternaria solani",
        "description": "A fungal disease causing characteristic concentric ring spots on tomato leaves.",
        "symptoms": "Dark brown spots with concentric rings on older leaves, leading to leaf drop.",
        "treatment": "Apply appropriate fungicides and remove infected debris.",
        "prevention": "Practice crop rotation and maintain good sanitation.",
        "image_url": "https://www.epicgardening.com/wp-content/uploads/2021/06/Early-Blight-on-Tomato-Leaf.jpg"
    },
    "Tomato___healthy": {
        "scientific_name": "",
        "description": "Healthy tomato plant with no signs of disease.",
        "symptoms": "No visible symptoms.",
        "treatment": "No treatment necessary.",
        "prevention": "Continue good agricultural practices.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/8/89/Tomato_plant.jpg"
    },
    "Tomato___Late_blight": {
        "scientific_name": "Phytophthora infestans",
        "description": "A serious disease causing large, dark, greasy lesions on leaves and fruit.",
        "symptoms": "Dark, water-soaked spots on leaves, stems, and fruits.",
        "treatment": "Apply fungicides and remove infected plants.",
        "prevention": "Use resistant varieties and avoid wet foliage.",
        "image_url": "https://blogs.cornell.edu/livegpath/files/2019/06/late-blight-tomato.jpg"
    },
    "Tomato___Leaf_Mold": {
        "scientific_name": "Passalora fulva",
        "description": "A fungal disease causing yellow spots on leaves and a grayish mold underneath.",
        "symptoms": "Yellow spots on upper leaf surface, with gray mold below.",
        "treatment": "Use fungicides and improve air circulation.",
        "prevention": "Avoid overhead watering and maintain plant spacing.",
        "image_url": "https://extension.umn.edu/sites/extension.umn.edu/files/tomato-leaf-mold.jpg"
    },
    "Tomato___Septoria_leaf_spot": {
        "scientific_name": "Septoria lycopersici",
        "description": "A common fungal disease causing small, circular spots on tomato leaves.",
        "symptoms": "Small, circular spots with dark borders and light centers.",
        "treatment": "Apply fungicides and remove infected leaves.",
        "prevention": "Use crop rotation and avoid overhead watering.",
        "image_url": "https://gardenerspath.com/wp-content/uploads/2021/09/Septoria-Leaf-Spot-on-Tomato.jpg"
    },
    "Tomato___Spider_mites_Two-spotted_spider_mite": {
        "scientific_name": "Tetranychus urticae",
        "description": "An infestation of spider mites causing stippling and yellowing of tomato leaves.",
        "symptoms": "Tiny yellow spots on leaves, fine webbing on the underside.",
        "treatment": "Use insecticidal soaps or miticides.",
        "prevention": "Maintain humidity and introduce natural predators.",
        "image_url": "https://www.dpi.nsw.gov.au/__data/assets/image/0003/1234567/tomato-spider-mite.jpg"
    },
    "Tomato___Target_Spot": {
        "scientific_name": "Corynespora cassiicola",
        "description": "A fungal disease causing large, circular spots on tomato leaves.",
        "symptoms": "Brown spots with concentric rings, often with a yellow halo.",
        "treatment": "Use fungicides and remove infected leaves.",
        "prevention": "Ensure good air circulation and avoid wet leaves.",
        "image_url": "https://plantpath.ifas.ufl.edu/u-scout/tomato/images/target-spot/22161DD2C3964DF39A98F053EB87FBF3/5-13_thumb.png"},
    "default": {
        "scientific_name": "",
        "description": "A plant disease affecting plant health and productivity.",
        "symptoms": "Various symptoms including spots on leaves, rotting of fruit or stems, and general plant decline.",
        "treatment": "Proper identification is key. Treatment may include cultural practices, biological controls, or chemical applications.",
        "prevention": "Prevention includes crop rotation, resistant varieties, good sanitation, and proper plant spacing.",
        "image_url":"https://sdmntprnorthcentralus.oaiusercontent.com/files/00000000-f4e8-622f-b785-00db4cb17ed9/raw?se=2025-05-23T11%3A57%3A32Z&sp=r&sv=2024-08-04&sr=b&scid=c2c6b695-2a6c-5fec-8bb4-919f553ab790&skoid=bbd22fc4-f881-4ea4-b2f3-c12033cf6a8b&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-05-22T19%3A18%3A39Z&ske=2025-05-23T19%3A18%3A39Z&sks=b&skv=2024-08-04&sig=5feHNE0dZPNDPD%2BYHRu%2BCoZ6thtTcUo74BGlqw2unpY%3D"
    }
}


        
        # Create or update disease entries
        created_count = 0
        updated_count = 0
        
        for class_name in class_names.values():
            # Clean up class name (replace '___' with spaces)
            display_name = class_name.replace('___', ' - ').replace('_', ' ')
            
            # Check if it's a "healthy" class
            is_healthy = "healthy" in class_name.lower()
            
            # Get or create the disease object
            disease, created = PlantDisease.objects.get_or_create(class_name=class_name, defaults={'name': display_name})

            
            # Get disease info (use default if not found)
            info = disease_info.get(class_name, disease_info['default'])
            
            # Set disease information
            if created:
                created_count += 1
            else:
                updated_count += 1
            
            if is_healthy:
                disease.scientific_name = ""
                disease.description = f"Healthy {display_name} plant without signs of disease."
                disease.symptoms = "No symptoms of disease present."
                disease.treatment = "No treatment necessary as the plant is healthy."
                disease.prevention = "Continue good agricultural practices to maintain plant health."
                disease.image_url = info.get('image_url', '')
            else:
                disease.scientific_name = info['scientific_name']
                disease.description = info['description']
                disease.symptoms = info['symptoms']
                disease.treatment = info['treatment']
                disease.prevention = info['prevention']
                disease.image_url = info.get('image_url', '')
            disease.save()
        
        self.stdout.write(self.style.SUCCESS(
            f'Successfully populated database with {created_count} new diseases and updated {updated_count} existing entries.'
        ))
        
        # Show all diseases in database
        self.stdout.write(self.style.SUCCESS('Plant diseases in database:'))
        all_diseases = PlantDisease.objects.all()
        for disease in all_diseases:
            self.stdout.write(f'- {disease.name}')