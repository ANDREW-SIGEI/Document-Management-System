#!/usr/bin/env python3
"""
Startup script for KEMRI Lab System
This script:
1. Runs the migration to ensure database schema is correct
2. Starts the application
"""

import os
import subprocess
import sys
import time

def run_command(command, check=True):
    """Run a shell command and return its output"""
    result = subprocess.run(command, shell=True, text=True, capture_output=True, check=check)
    return result.stdout.strip() if result.returncode == 0 else None

def main():
    print("=== KEMRI Laboratory System Startup ===")
    
    # Run database migration
    print("Checking database schema...")
    migration_result = run_command("python migrate_user_schema.py", check=False)
    if migration_result is None:
        print("Warning: Migration script returned an error, but we'll continue anyway.")
    
    # Select which app to run
    print("\nSelect which app to run:")
    print("1. Production app (app.py)")
    print("2. Debug app (debug_app.py)")
    choice = input("Enter your choice (1/2) [default: 2]: ").strip() or "2"
    
    port = input("Enter port to run on [default: 5000]: ").strip() or "5000"
    
    if choice == "1":
        app_file = "app.py"
        print(f"\nStarting production app on port {port}...")
    else:
        app_file = "debug_app.py"
        print(f"\nStarting debug app on port {port}...")
    
    # Set environment variables
    os.environ["FLASK_APP"] = app_file
    os.environ["FLASK_ENV"] = "development"
    
    # Print startup message
    print("\nStarting KEMRI Lab System...")
    print(f"The application will be available at: http://127.0.0.1:{port}")
    print("Press Ctrl+C to stop the server\n")
    
    # Run the app
    os.system(f"python {app_file} --port {port}")

if __name__ == "__main__":
    main() 