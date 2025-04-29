import re
import os

def update_user_model(filename):
    """Update the User model in the given file to include the is_active column"""
    if not os.path.exists(filename):
        print(f"File {filename} not found.")
        return False
    
    try:
        with open(filename, 'r') as file:
            content = file.read()
        
        # Check if is_active already exists in User model
        user_model_pattern = r'class User\(db\.Model\):[\s\S]*?__repr__'
        user_model_match = re.search(user_model_pattern, content)
        
        if not user_model_match:
            print(f"User model not found in {filename}.")
            return False
        
        user_model = user_model_match.group(0)
        
        # Check if is_active already exists
        if 'is_active' in user_model:
            print(f"is_active column already exists in User model in {filename}.")
            return True
        
        # Add is_active column before __repr__
        updated_user_model = user_model.replace('    def __repr__', '    is_active = db.Column(db.Boolean, default=True)\n\n    def __repr__')
        updated_content = content.replace(user_model, updated_user_model)
        
        with open(filename, 'w') as file:
            file.write(updated_content)
        
        print(f"User model updated in {filename}.")
        return True
    
    except Exception as e:
        print(f"Error updating User model in {filename}: {str(e)}")
        return False

def update_login_function(filename):
    """Update the login function to consider is_active status"""
    if not os.path.exists(filename):
        print(f"File {filename} not found.")
        return False
    
    try:
        with open(filename, 'r') as file:
            content = file.read()
        
        # Find the login function
        login_function_pattern = r'@app\.route\(\'/login\',[\s\S]*?return redirect\(url_for\(\'home\'\)\)'
        login_function_match = re.search(login_function_pattern, content)
        
        if not login_function_match:
            print(f"Login function not found in {filename}.")
            return False
        
        login_function = login_function_match.group(0)
        
        # Check if we're already checking is_active
        if 'is_active' in login_function:
            print(f"Login function already checks is_active in {filename}.")
            return True
        
        # Update the user authentication to check is_active
        updated_login_function = login_function.replace(
            'if user and check_password_hash(user.password, password):',
            'if user and check_password_hash(user.password, password) and user.is_active:'
        )
        
        # Add flash message for inactive accounts
        updated_login_function = updated_login_function.replace(
            'flash(\'Invalid username or password\')',
            'if user and check_password_hash(user.password, password) and not user.is_active:\n            flash(\'Your account is inactive. Please contact an administrator.\')\n        else:\n            flash(\'Invalid username or password\')'
        )
        
        updated_content = content.replace(login_function, updated_login_function)
        
        with open(filename, 'w') as file:
            file.write(updated_content)
        
        print(f"Login function updated in {filename}.")
        return True
    
    except Exception as e:
        print(f"Error updating login function in {filename}: {str(e)}")
        return False

def update_bulk_user_action(filename):
    """Update the bulk_user_action function to use is_active column"""
    if not os.path.exists(filename):
        print(f"File {filename} not found.")
        return False
    
    try:
        with open(filename, 'r') as file:
            content = file.read()
        
        # Find the bulk_user_action function
        bulk_function_pattern = r'@app\.route\(\'/bulk_user_action\'[\s\S]*?return redirect\(url_for\(\'user_management\'\)\)'
        bulk_function_match = re.search(bulk_function_pattern, content)
        
        if not bulk_function_match:
            print(f"bulk_user_action function not found in {filename}.")
            return False
        
        bulk_function = bulk_function_match.group(0)
        
        # Update activate action
        updated_function = bulk_function
        if 'action == \'activate\'' in bulk_function:
            updated_function = re.sub(
                r'(if action == \'activate\':[\s\S]*?)user\.role = \'user\'([\s\S]*?)db\.session\.commit\(\)',
                r'\1user.is_active = True\2db.session.commit()',
                updated_function
            )
        
        # Update deactivate action
        if 'action == \'deactivate\'' in updated_function:
            updated_function = re.sub(
                r'(if action == \'deactivate\':[\s\S]*?)user\.role = None([\s\S]*?)db\.session\.commit\(\)',
                r'\1user.is_active = False\2db.session.commit()',
                updated_function
            )
        
        # Update the export users function to check is_active instead of roles
        if 'action == \'export\'' in updated_function:
            updated_function = re.sub(
                r'(csv_header = \[[\s\S]*?\][\s\S]*?)writer\.writerow\(\[[\s\S]*?, \'Status\': \'Active\' if user\.role else \'Inactive\'',
                r'\1writer.writerow([user.username, user.name, user.email, user.department, user.role or \'\', \'Active\' if user.is_active else \'Inactive\'',
                updated_function
            )
        
        updated_content = content.replace(bulk_function, updated_function)
        
        with open(filename, 'w') as file:
            file.write(updated_content)
        
        print(f"bulk_user_action function updated in {filename}.")
        return True
    
    except Exception as e:
        print(f"Error updating bulk_user_action function in {filename}: {str(e)}")
        return False

if __name__ == "__main__":
    files_to_update = ['app.py', 'app_fixed.py', 'app_fixed_bak.py']
    print("Starting update of User model and related functions...")
    
    for file in files_to_update:
        if os.path.exists(file):
            print(f"\nProcessing {file}...")
            update_user_model(file)
            update_login_function(file)
            update_bulk_user_action(file)
        else:
            print(f"File {file} not found, skipping.")
    
    print("\nUpdate process completed.") 