# Model imports for your app
from .models import FruitClassification, MLWeights, UploadedImage, ModelWeights, CustomUser,UserImage, ImageData
from django.shortcuts import render, HttpResponse, redirect
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView
from .forms import ImageForm, RegistrationForm, ImageForm
from django.conf import settings
# Image processing
from PIL import Image
import numpy as np
# Standard library imports
import os
import zipfile
# TensorFlow and Keras for model architecture and processing
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout

# Other necessary imports
from FruitScan.settings import BASE_DIR
from .model_training import train_model
from keras.models import load_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.views.decorators.http import require_POST
import base64
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile

deployed_model_version = '1'
width = 256
height = 256
channels = 3
num_classes = 4

# Create model architecture
model = Sequential([
    Conv2D(32, (3, 3), activation='relu', input_shape=(width, height, channels)),
    MaxPooling2D(2, 2),
    Conv2D(64, (3, 3), activation='relu'),
    MaxPooling2D(2, 2),
    Flatten(),
    Dense(128, activation='relu'),
    #Dropout(0.5),
    Dense(num_classes, activation='softmax')
])

# Load the Keras model
deployed_weights_path = f"media/ModelWeights/fruitscan_model_weights_v{deployed_model_version}.h5"
weights_path = os.path.join(BASE_DIR, deployed_weights_path)
model.load_weights(weights_path)

# Classification table for the model output
class_labels = ['Kiwi', 'Banana', 'Mango', 'Tomato']

# Nutritional data dictionary
nutritional_info = {
    'Kiwi': {'Calories': '61', 'Protein': '1.1g', 'Carbohydrates': '14.7g', 'Dietary Fiber': '3g', 'Sugar': '9g', 'Fat': '0.5g', 'Vitamin C': '92.7mg', 'Potassium': '312g'},
    'Banana': {'Calories': '89', 'Protein': '1.1g', 'Carbohydrates': '22.8g', 'Dietary Fiber': '2.6g', 'Sugar': '12.2g', 'Fat': '0.3g', 'Vitamin C': '8.7mg', 'Potassium': '358g'},
    'Mango': {'Calories': '60', 'Protein': '0.8g', 'Carbohydrates': '15g', 'Dietary Fiber': '1.6g', 'Sugar': '14g', 'Fat': '0.4g', 'Vitamin C': '36.4mg', 'Potassium': '168g'},
    'Tomato': {'Calories': '18', 'Protein': '0.9g', 'Carbohydrates': '3.9g', 'Dietary Fiber': '1.2g', 'Sugar': '2.6g', 'Fat': '0.2g', 'Vitamin C': '13mg', 'Potassium': '237g'}
}

def resize_image(uploaded_file, size):
    image = Image.open(uploaded_file)
    image.thumbnail(size)
    buffered = BytesIO()
    image.save(buffered, format="JPEG")  # You can change the format as needed
    resized_image = InMemoryUploadedFile(buffered, None, uploaded_file.name, 'image/jpeg', buffered.tell(), None)
    return resized_image

# Home view. First page where we upload picture, login user and admin
#@login_required(login_url='/login/')
def home(request):
    # Pass a variable to the template based on user authentication
    is_user_logged_in = request.user.is_authenticated
    if request.method == 'POST':
        form = ImageForm(request.POST, request.FILES)
 
        if form.is_valid():
            uploaded_file = request.FILES['image']
            # Send image to classification and process
            result, nutritional_info = classify_image(uploaded_file)
            # Convert the uploaded image to Base64 for displaying
            base64_image = image_to_base64(Image.open(uploaded_file))

            if is_user_logged_in:
                # Resize the uploaded image
                resized_image = resize_image(uploaded_file, (100, 100))

                # Optionally, you can also save the UserImage instance
                user_image = UserImage(user=request.user, image=resized_image, pred=result)
                user_image.save()

            # Send the result to the display data page
            return render(request, 'prediction.html', {'result': result, 'nutritional_info': nutritional_info, 'base64_image': base64_image, 'is_user_logged_in': is_user_logged_in})
    else:
        form = ImageForm()
    return render(request, 'home.html', {'form': form, 'is_user_logged_in': is_user_logged_in})   

def adminPanel(request):
    weights = ModelWeights.objects.all()
    model_version = deployed_model_version
    fruitscanapp_imagedata_count = ImageData.objects.count()
    print(deployed_model_version)
    return render(request, 'admin_view.html', {'weights': weights, 
                                               'model_version': model_version,
                                               'fruitscanapp_imagedata_count': fruitscanapp_imagedata_count})

class CustomAdminLoginView(LoginView):
    def get_success_url(self, request):
        return redirect('admin_view')

# Function to process the uploaded image and resize to fit the model
def preprocess_image(uploaded_image):
    with Image.open(uploaded_image) as img:
        img_data = img.resize((width, height))
        # Normalize data
        img_array = np.array(img_data) / 255.0
    return img_array

# Convert uploaded image to Base64 format and send it to the front-end
# The image stays in the memory of the client's browser, not on the server 
def image_to_base64(img):
    # Convert the image to a Base64 string for display on the front-end
    buffered = BytesIO()
    img.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode()

# Function that runs the prediction
def classify_image(uploaded_image):
    processed_image = preprocess_image(uploaded_image)
    
    # Reshape processed image
    image = np.expand_dims(processed_image, axis=0)
    
    # Make prediction
    prediction = model.predict(image)

    # Debug to see the output for prediction
    print("Prediction:", prediction)
    predicted_class_index = np.argmax(prediction, axis=1)
    
    # Convert this index to a label 
    predicted_class_label = class_labels[predicted_class_index[0]]
    fruit_nutritional_info = nutritional_info[predicted_class_label]
    
    return predicted_class_label, fruit_nutritional_info

# This function can be used to display the history of the images uploaded by the user. But it should to be modified.
def display_all_uploaded_image(request):
    if request.method == 'GET':
        #getting all the objects of the image
        images = UploadedImage.objects.all()
        return render(request, 'uploaded_image.html', {'uploaded_image': images})

def train_model_view(request):
    # Call your model training function here
    train_model()
    #return redirect('home') #Redirect to page instead of popup

    return HttpResponse("""
        <script>
            alert('New model trained successfully!');
            window.location.href='/admin_view'; // Redirect to home after showing the alert
        </script>
    """)

# For user registration
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')  # Redirect to login page after successful registration
    else:
        form = RegistrationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def profile(request):
    user_images = UserImage.objects.filter(user=request.user)
    context = {
        'user': request.user,
        'user_images': user_images,
    }
    return render(request, 'profile.html', context)

def user_logout(request):
    logout(request)
    return redirect('home')  # Replace 'home' with the name or URL of your home page

class CustomLoginView(LoginView):
    def form_valid(self, form):
        response = super().form_valid(form)
        # Redirect to the homepage after successful login
        return redirect('home')

def upload_zip(request):
    if request.method == 'POST' and request.FILES['zip_file']:
        uploaded_file = request.FILES['zip_file']
        
        if uploaded_file.name.endswith('.zip'):
            destination_path = os.path.join(BASE_DIR, 'Dataset/')
            
            if not os.path.exists(destination_path):
                os.makedirs(destination_path)
            
            with open(os.path.join(destination_path, uploaded_file.name), 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            with zipfile.ZipFile(os.path.join(destination_path, uploaded_file.name), 'r') as zip_ref:
                for file in zip_ref.namelist():
                    # Filter out __MACOSX entries
                    if '__MACOSX' not in file:
                        zip_ref.extract(file, destination_path)
            
            os.remove(os.path.join(destination_path, uploaded_file.name))
            
            extracted_folders = [f for f in os.listdir(destination_path) if os.path.isdir(os.path.join(destination_path, f))]
            
            for folder in extracted_folders:
                folder_path = os.path.join(destination_path, folder)
                label = folder
                
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        
                        if file.endswith(('.jpg', '.jpeg', '.png')):
                            with open(file_path, 'rb') as img_file:
                                image_data = img_file.read()
                                
                                image_instance = ImageData(label=label, image_data=image_data)
                                image_instance.save()

                            os.remove(file_path)
            
            return HttpResponse("""
                <script>
                    alert('Files uploaded successfully!!');
                    window.location.href='/admin_view';
                </script>
            """)

def delete_all_images(request):
    # Delete all entries in the ImageData table
    ImageData.objects.all().delete()
    return HttpResponse("""
        <script>
            alert('All image data in the database has been deleted.');
            window.location.href='/admin_view';
        </script>
    """)


def deploy_selected(request):
    global deployed_model_version

    if request.method == 'POST':
        if 'deploy_selected' in request.POST:
            deployed_version = request.POST.get('selected_version')

            # Update model version and reload model weights
            deployed_model_version = deployed_version
            update_model(deployed_model_version)

            return HttpResponse("""
                <script>
                    alert('Selected model has been deployed.');
                    window.location.href='/admin_view';
                </script>
            """)

    return HttpResponse("""
        <script>
            alert('Something went wrong');
            window.location.href='/admin_view';
        </script>
    """)

def update_model(version):
    global model
    deployed_weights_path = f"media/ModelWeights/fruitscan_model_weights_v{version}.h5"
    weights_path = os.path.join(BASE_DIR, deployed_weights_path)
    model.load_weights(weights_path)
