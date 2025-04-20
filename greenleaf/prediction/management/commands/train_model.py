# prediction/management/commands/train_model.py
import os, json, tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Train plant disease model using local dataset'

    def add_arguments(self, parser):
        parser.add_argument('--train_dir', type=str, required=True)
        parser.add_argument('--val_dir', type=str, required=True)
        parser.add_argument('--epochs', type=int, default=20)
        parser.add_argument('--batch_size', type=int, default=32)
        parser.add_argument('--image_size', type=int, default=224)

    def handle(self, *args, **options):
        train_dir, val_dir = options['train_dir'], options['val_dir']
        epochs, batch_size, image_size = options['epochs'], options['batch_size'], options['image_size']
        model_dir = settings.MODEL_DIR
        os.makedirs(model_dir, exist_ok=True)

        class_names = sorted(os.listdir(train_dir))
        class_mapping = {i: name for i, name in enumerate(class_names)}
        with open(os.path.join(model_dir, 'class_mapping.txt'), 'w') as f:
            f.writelines(f"{i},{name}\n" for i, name in class_mapping.items())

        datagen_args = dict(rescale=1./255, rotation_range=20, width_shift_range=0.2, height_shift_range=0.2, horizontal_flip=True, fill_mode='nearest')
        train_gen = ImageDataGenerator(**datagen_args).flow_from_directory(train_dir, target_size=(image_size, image_size), batch_size=batch_size, class_mode='categorical')
        val_gen = ImageDataGenerator(rescale=1./255).flow_from_directory(val_dir, target_size=(image_size, image_size), batch_size=batch_size, class_mode='categorical')

        base_model = MobileNetV2(weights='imagenet', include_top=False, input_shape=(image_size, image_size, 3))
        base_model.trainable = False
        x = GlobalAveragePooling2D()(base_model.output)
        x = Dense(512, activation='relu')(x)
        x = Dropout(0.3)(x)
        out = Dense(len(class_names), activation='softmax')(x)
        model = Model(inputs=base_model.input, outputs=out)
        model.compile(optimizer=Adam(0.001), loss='categorical_crossentropy', metrics=['accuracy'])

        callbacks = [
            ModelCheckpoint(os.path.join(model_dir, 'best_model.h5'), monitor='val_accuracy', save_best_only=True, verbose=1),
            EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True, verbose=1)
        ]

        model.fit(train_gen, validation_data=val_gen, epochs=epochs,steps_per_epoch=500,  # only run 500 batches per epoch
  validation_steps=100, callbacks=callbacks)

        saved_model_dir = os.path.join(model_dir, 'saved_model')
        model.export(saved_model_dir)

        converter = tf.lite.TFLiteConverter.from_saved_model(saved_model_dir)
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        tflite_model = converter.convert()
        with open(os.path.join(model_dir, 'plant_disease_model.tflite'), 'wb') as f:
            f.write(tflite_model)

        metadata = {
            'model_version': '1.0.0',
            'image_size': image_size,
            'class_count': len(class_names),
            'classes': class_mapping
        }
        with open(os.path.join(model_dir, 'model_metadata.json'), 'w') as f:
            json.dump(metadata, f, indent=2)

        self.stdout.write(self.style.SUCCESS('✅ Model trained, converted to TFLite, and saved successfully!'))
