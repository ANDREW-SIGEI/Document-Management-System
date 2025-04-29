import os
import sys
import traceback
import logging

# Configure logging
logging.basicConfig(
    filename='debug_app.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

try:
    # Import the app explicitly from debug_app.py
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from debug_app import app
    print("Successfully imported app from debug_app.py")
    logging.info("Starting KEMRI Laboratory System in debug mode on port 8080")
    app.run(debug=True, host='0.0.0.0', port=8080)
except Exception as e:
    error_message = f"Error when running debug app: {e}"
    print(error_message)
    logging.error(error_message)
    traceback.print_exc()
    
    print("\nTrying to debug imports...")
    try:
        import flask
        print(f"Flask version: {flask.__version__}")
        logging.info(f"Flask version: {flask.__version__}")
    except Exception as ie:
        print(f"Error importing flask: {ie}")
        logging.error(f"Error importing flask: {ie}")
        
    try:
        import sqlalchemy
        print(f"SQLAlchemy version: {sqlalchemy.__version__}")
        logging.info(f"SQLAlchemy version: {sqlalchemy.__version__}")
    except Exception as ie:
        print(f"Error importing sqlalchemy: {ie}")
        logging.error(f"Error importing sqlalchemy: {ie}")

    sys.exit(1) 