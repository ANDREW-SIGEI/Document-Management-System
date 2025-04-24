import os
import sys
import traceback
import logging

# Configure logging
logging.basicConfig(
    filename='flask_app.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

try:
    from app import app
    print("Successfully imported app from app.py")
    logging.info("Starting KEMRI Laboratory System application in production mode")
    app.run(debug=False, host='0.0.0.0', port=5001)
except Exception as e:
    error_message = f"Error when running app: {e}"
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