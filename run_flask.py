import os
import sys
import traceback

try:
    from app_fixed import app
    print("Successfully imported app from app_fixed.py")
    app.run(debug=True, host='0.0.0.0')
except Exception as e:
    print(f"Error when running app: {e}")
    traceback.print_exc()
    
    print("\nTrying to debug imports...")
    try:
        import flask
        print(f"Flask version: {flask.__version__}")
    except Exception as ie:
        print(f"Error importing flask: {ie}")
        
    try:
        import sqlalchemy
        print(f"SQLAlchemy version: {sqlalchemy.__version__}")
    except Exception as ie:
        print(f"Error importing sqlalchemy: {ie}")

    sys.exit(1) 