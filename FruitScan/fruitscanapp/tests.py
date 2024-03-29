# Contributors: Mijin, Erik

# Import necessary packages
from django.test import TestCase
from .models import CustomUser, ImageData, TestImageData, UploadedImage, UserImage, user_directory_path
from django.urls import reverse


class ImageDataTestCase(TestCase):
    """ Test related to image data"""
    def setUp(self):
        # Example image data (bytes)
        example_image_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR...'
        
        # Create an ImageData instance
        ImageData.objects.create(label='1', image_data=example_image_data)

    def test_image_data_content(self):
        # ImageData objects have the correct label and image data.
        image_data_instance = ImageData.objects.get(label='1')
        
        # Check if the label is correct
        self.assertEqual(image_data_instance.label, '1')
        
        # Check if the image data is correct (this is a simplistic check)
        self.assertTrue(image_data_instance.image_data.startswith(b'\x89PNG'))

class UploadedImageTestCase(TestCase):
    """ Test related to uploaded image files """
    def setUp(self):
        # Create an UploadedImage instance and save it
        self.image = UploadedImage.objects.create(image="image.jpg")

    def test_uploaded_image_content(self):
        # UploadedImage objects have the correct image path.
        image = UploadedImage.objects.get(id=self.image.id)

        # Get the expected relative image path
        expected_image_path = 'image.jpg'

        # Check if the image path is correct
        self.assertEqual(image.image.name, expected_image_path)


class TestImageDataTestCase(TestCase):
    """ Test related to image data for test """
    def setUp(self):
        # Example image data (bytes)
        example_image_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR...'

        # Create a TestImageData instance
        TestImageData.objects.create(label='B', image_data=example_image_data)

    def test_test_image_data_content(self):
        # TestImageData objects have the correct label and image data.
        image_data_instance = TestImageData.objects.get(label='B')

        # Check if the label is correct
        self.assertEqual(image_data_instance.label, 'B')

        # Check if the image data is correct (this is a simplistic check)
        self.assertTrue(image_data_instance.image_data.startswith(b'\x89PNG'))

    def test_prediction_success(self):
        # TestImageData objects have the correct label and image data.
        image_data_instance = TestImageData.objects.get(label='B')

        # Upload the image and make a prediction
        response = self.client.post(reverse('home'), {'image': image_data_instance})

        # Check if the response is successful (status code 200)
        self.assertEqual(response.status_code, 200)

class CustomUserTestCase(TestCase):
    """ Test creation of custom user instance """
    def test_custom_user_str(self):
        # Check the string representation of a CustomUser object
        user = CustomUser.objects.create(username='testuser')
        self.assertEqual(str(user), 'testuser')

class UserImageTestCase(TestCase):
    """ Test images uploaded by user together with its prediction result """
    def setUp(self):
        # Create a CustomUser instance
        self.user = CustomUser.objects.create(username='testuser')

        # Create a UserImage instance related to the user
        self.image_instance = UserImage.objects.create(
            user=self.user,
            image="media/images/user_1/image.jpg",
            pred="prediction"
        )

    def test_user_image_content(self):
        image_instance = UserImage.objects.get(id=self.image_instance.id)
        expected_image_path = f'media/images/user_{image_instance.user.id}/image.jpg'

        # Check if the image path is correct
        self.assertEqual(image_instance.image.name, expected_image_path)

        # Check if the user is correct
        self.assertEqual(image_instance.user.username, 'testuser')

        # Check if the prediction is correct
        self.assertEqual(image_instance.pred, "prediction")

class AuthenticationTests(TestCase):
    """ Test user authentication; i.e. login, logout and conditional display of restricted view """
    def test_user_login(self):
        # Log in the user
        response = self.client.post(reverse('login'), {'username': 'testuser', 'password': 'testpassword'})

        # Check if the login was successful
        self.assertEqual(response.status_code, 200)

    def test_user_logout(self):
        # Log in a test user
        self.client.login(username='testuser', password='testpassword')

        # Log out the user
        response = self.client.get(reverse('user_logout'))

        # Check if the logout was successful with a redirect (status code 302)
        self.assertEqual(response.status_code, 302)
       
    def test_non_logged_in_user_access_restricted_view(self):
        # Access a view that requires authentication
        response = self.client.get(reverse('profile'))

        # Check if the user is redirected to the login page
        login_url = reverse('login')
        self.assertRedirects(response, f"/accounts{login_url}?next={reverse('profile')}")