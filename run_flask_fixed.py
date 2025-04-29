import os
import sys

print("Attempting to import app from app_fixed.py")
try:
    from app_fixed import app
    print("Successfully imported app from app_fixed.py")
except ImportError as e:
    print(f"Error importing app: {e}")
    sys.exit(1)

if __name__ == '__main__':
    # Run the app on a different port to avoid conflicts
    app.run(host='0.0.0.0', port=5003, debug=False) 