# Register a new user
curl --location 'http://127.0.0.1:8000/api/auth/register/' \
--header 'Content-Type: application/json' \
--data-raw '{"username":"testuser","password":"password123","email":"test@example.com"}'

# Login
curl --location 'http://127.0.0.1:8000/api/auth/login/' \
--header 'Content-Type: application/json' \
--data '{"username":"testuser","password":"password123"}'

# me 
curl --location 'http://127.0.0.1:8000/api/auth/me/' \
--header 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzQ1MTU3MzI2LCJpYXQiOjE3NDUwNzA5MjYsImp0aSI6IjM0MjczOGVjZTEyNzRiYjBhYWE0NjYyOGRiMmM1OTM3IiwidXNlcl9pZCI6Mn0.yGR3itmrbwKozyH81EHW89V_J6FlAdGX8jvaI5v9Cy0'

# refresh
curl --location 'http://127.0.0.1:8000/api/auth/refresh/' \
--header 'Content-Type: application/json' \
--data '{
    "refresh":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc0NTY3NTcyNiwiaWF0IjoxNzQ1MDcwOTI2LCJqdGkiOiIxMmVjNmY1ZmNiOGE0ZjgxOTY0MWQ1YzY1MTc2NzJjMSIsInVzZXJfaWQiOjJ9.qcGfemWtbd70ox1FnOUXmajVW58KlDbsVQLpD8DSoys"
}'

python manage.py train_model   --train_dir="data/plant_disease_dataset/New Plant Diseases Dataset/train_small"   --val_dir="data/plant_disease_dataset/New Plant Diseases Dataset/valid_small" --image_size 96 --batch_size 8 --epochs 3
