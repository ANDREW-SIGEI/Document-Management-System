import os
import unittest
import tempfile
import io
from flask import Flask

# Import from parent directory
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from debug_app import app, allowed_file, handle_file_upload, get_human_readable_size

class FileUploadTestCase(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test uploads
        self.temp_dir = tempfile.mkdtemp()
        app.config['TESTING'] = True
        app.config['UPLOAD_FOLDER'] = self.temp_dir
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        
    def tearDown(self):
        # Remove the temporary directory and its contents
        for filename in os.listdir(self.temp_dir):
            os.unlink(os.path.join(self.temp_dir, filename))
        os.rmdir(self.temp_dir)
        self.app_context.pop()
    
    def test_allowed_file(self):
        """Test the allowed_file function"""
        # Test allowed extensions
        self.assertTrue(allowed_file('test.pdf'))
        self.assertTrue(allowed_file('test.doc'))
        self.assertTrue(allowed_file('test.docx'))
        self.assertTrue(allowed_file('test.jpg'))
        self.assertTrue(allowed_file('test.png'))
        
        # Test disallowed extensions
        self.assertFalse(allowed_file('test.exe'))
        self.assertFalse(allowed_file('test.js'))
        self.assertFalse(allowed_file('test.php'))
        
        # Test edge cases
        self.assertFalse(allowed_file('test'))  # No extension
        self.assertFalse(allowed_file(''))  # Empty string
    
    def test_get_human_readable_size(self):
        """Test the get_human_readable_size function"""
        self.assertEqual(get_human_readable_size(500), '500 B')
        self.assertEqual(get_human_readable_size(1024), '1.0 KB')
        self.assertEqual(get_human_readable_size(1024 * 1024), '1.0 MB')
        self.assertEqual(get_human_readable_size(1024 * 1024 * 1024), '1.0 GB')
    
    def test_handle_file_upload(self):
        """Test the handle_file_upload function"""
        # Create a test file using Flask's test client
        data = b'Test file content'
        filename = 'test.pdf'
        
        # Create a file-like object correctly representing a Flask uploaded file
        class MockUploadedFile:
            def __init__(self, stream, filename, content_type):
                self.stream = stream
                self.filename = filename
                self.content_type = content_type
                
            def save(self, dst):
                with open(dst, 'wb') as f:
                    f.write(self.stream.read())
                self.stream.seek(0)  # Reset stream position for future reading
        
        # Create test file with proper save method
        test_file = MockUploadedFile(io.BytesIO(data), filename, 'application/pdf')
        
        # Test file upload
        file_info = handle_file_upload(test_file, 'TEST-123')
        
        # Assertions
        self.assertIsNotNone(file_info)
        self.assertEqual(file_info['original_filename'], 'test.pdf')
        self.assertTrue(file_info['saved_filename'].startswith('TEST-123_'))
        self.assertTrue(file_info['saved_filename'].endswith('_test.pdf'))
        self.assertEqual(file_info['file_size'], len(data))
        self.assertEqual(file_info['file_type'], 'pdf')
        
        # Verify file was saved
        self.assertTrue(os.path.exists(file_info['file_path']))
        with open(file_info['file_path'], 'rb') as f:
            content = f.read()
            self.assertEqual(content, data)
    
    def test_upload_route(self):
        """Test the compose route with file upload"""
        # Login first (assuming debug_login route exists for testing)
        response = self.app.get('/debug_login')
        self.assertEqual(response.status_code, 302)  # Should redirect to dashboard
        
        # Create a test file
        test_data = b'Test file content'
        
        # Make a POST request to the compose route with a file
        response = self.app.post(
            '/compose',
            data={
                'doc_type': 'Incoming',
                'title': 'Test Document',
                'sender': 'Test Sender',
                'recipient': 'Test Recipient',
                'details': 'Test details',
                'required_action': 'Review',
                'priority': 'Normal',
                'document_file': (io.BytesIO(test_data), 'test.pdf')
            },
            content_type='multipart/form-data',
            follow_redirects=True
        )
        
        # Check that the response is a redirect or success
        self.assertIn(response.status_code, [200, 302])
        
        # When redirect is followed, we should see a flash message
        # At a minimum, we shouldn't get any error responses
        self.assertNotIn(response.status_code, [404, 500])

if __name__ == '__main__':
    # Create the tests directory if it doesn't exist
    if not os.path.exists('tests'):
        os.makedirs('tests')
    
    unittest.main() 