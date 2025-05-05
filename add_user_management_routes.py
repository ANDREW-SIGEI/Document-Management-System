import os

def main():
    """Main function"""
    print("Starting the process to add user management routes to debug_app.py...")
    
    print(f"Current directory: {os.getcwd()}")
    print(f"debug_app.py exists: {os.path.exists(DEBUG_APP_PATH)}")
    
    # Create backup first
    create_backup()
    
    # Dump current content for debugging
    try:
        with open(DEBUG_APP_PATH, 'r') as f:
            current_content = f.read()
            print(f"Length of current content: {len(current_content)} bytes")
    except Exception as e:
        print(f"Error reading debug_app.py: {str(e)}")
    
    # Check and add User class if necessary
    if not check_if_user_class_exists():
        print("User class not found in debug_app.py, adding it...")
        if not add_user_class():
            print("Failed to add User class. Aborting.")
            return
    else:
        print("User class already exists in debug_app.py")
    
    # Check and add routes if necessary
    if not check_if_routes_exist():
        print("User management routes not found in debug_app.py, adding them...")
        if not add_user_management_routes():
            print("Failed to add user management routes. Aborting.")
            return
    else:
        print("User management routes already exist in debug_app.py")
    
    print("Successfully updated debug_app.py with User class and user management routes.")
    print("Please run the application to see the changes.") 