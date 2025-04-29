from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
import os
import re

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

def add_is_active_to_user_model(filename):
    """Add is_active column to User model in the given file"""
    if not os.path.exists(filename):
        print(f"File {filename} does not exist.")
        return False
        
    with open(filename, 'r') as file:
        content = file.read()
    
    # Find the User model definition
    user_model_pattern = r'class User\(db\.Model\):.*?def __repr__\(self\):'
    user_model_match = re.search(user_model_pattern, content, re.DOTALL)
    
    if not user_model_match:
        print(f"Could not find User model in {filename}")
        return False
    
    user_model = user_model_match.group(0)
    
    # Check if is_active already exists
    if 'is_active = db.Column' in user_model:
        print(f"is_active column already exists in {filename}")
        return True
    
    # Add is_active column before __repr__
    modified_user_model = user_model.replace(
        'def __repr__(self):',
        'is_active = db.Column(db.Boolean, default=True)\n    \n    def __repr__(self):'
    )
    
    # Replace the old model with the new one
    modified_content = content.replace(user_model, modified_user_model)
    
    with open(filename, 'w') as file:
        file.write(modified_content)
    
    print(f"Added is_active column to User model in {filename}")
    return True

def update_bulk_user_action(filename):
    """Update bulk_user_action function to use is_active instead of role"""
    if not os.path.exists(filename):
        print(f"File {filename} does not exist.")
        return False
        
    with open(filename, 'r') as file:
        content = file.read()
    
    # Find the bulk_user_action function
    bulk_action_pattern = r'@app\.route\(\'/bulk_user_action\'.*?return redirect\(url_for\(\'user_management\'\)\)'
    bulk_action_match = re.search(bulk_action_pattern, content, re.DOTALL)
    
    if not bulk_action_match:
        print(f"Could not find bulk_user_action function in {filename}")
        return False
    
    bulk_action = bulk_action_match.group(0)
    
    # Replace the activate logic
    modified_bulk_action = bulk_action.replace(
        "if user and not user.role:\n                user.role = 'User'",
        "if user:\n                user.is_active = True"
    )
    
    # Replace the deactivate logic
    modified_bulk_action = modified_bulk_action.replace(
        "if user and user.role:\n                user.role = None",
        "if user:\n                user.is_active = False"
    )
    
    # Update the status check in export action if it exists
    if "user.role else 'Inactive'" in modified_bulk_action:
        modified_bulk_action = modified_bulk_action.replace(
            "'Active' if user.role else 'Inactive'",
            "'Active' if user.is_active else 'Inactive'"
        )
    
    # Replace the old function with the new one
    modified_content = content.replace(bulk_action, modified_bulk_action)
    
    with open(filename, 'w') as file:
        file.write(modified_content)
    
    print(f"Updated bulk_user_action function in {filename}")
    return True

if __name__ == "__main__":
    backup_files = ['app_fixed.py', 'app_fixed_bak.py']
    
    for file in backup_files:
        print(f"\nProcessing {file}...")
        if add_is_active_to_user_model(file):
            update_bulk_user_action(file)
        print(f"Completed processing {file}")
    
    print("\nAll updates completed!") 