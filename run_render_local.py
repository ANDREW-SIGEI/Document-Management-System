import os
import secrets
from debug_app import app

# Set environment variables similar to Render
os.environ['SECRET_KEY'] = secrets.token_hex(16)
os.environ['WEB_CONCURRENCY'] = '2'

if __name__ == '__main__':
    print("Starting KEMRI Laboratory System in Render configuration...")
    # This uses production settings like Render would
    app.run(host='0.0.0.0', port=5001, debug=False) 