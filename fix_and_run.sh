#!/bin/bash

# Kill any existing Flask processes
echo "Stopping any running Flask servers..."
pkill -f "python app.py" || true
fuser -k 5000/tcp || true
fuser -k 5001/tcp || true

# Reset the database
echo "Resetting the database..."
python reset_db.py

# Run the app on port 5001
echo "Starting the app on port 5001..."
python run_app.py

# If the app doesn't start, provide instructions
echo "If the app doesn't start, try the following commands manually:"
echo "1. pkill -f 'python app.py'"
echo "2. fuser -k 5001/tcp"
echo "3. python reset_db.py"
echo "4. python run_app.py"
echo "The app should be accessible at: http://127.0.0.1:5001" 