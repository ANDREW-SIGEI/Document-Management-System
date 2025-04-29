import re
import os

def update_dashboard_function(filename):
    """Update the dashboard function to show active and inactive user counts"""
    if not os.path.exists(filename):
        print(f"File {filename} not found.")
        return False
    
    try:
        with open(filename, 'r') as file:
            content = file.read()
        
        # Find the dashboard function
        dashboard_pattern = r'@app\.route\(\'/dashboard\'[\s\S]*?return render_template\(\'dashboard\.html\',[^)]*\)'
        dashboard_match = re.search(dashboard_pattern, content)
        
        if not dashboard_match:
            print(f"Dashboard function not found in {filename}.")
            return False
        
        dashboard_function = dashboard_match.group(0)
        
        # Check if we're already using is_active for user counts
        if 'is_active' in dashboard_function:
            print(f"Dashboard function already uses is_active in {filename}.")
            return True
        
        # Find the user count code and update it
        user_count_pattern = r'user_count = User\.query\.count\(\)'
        active_users_code = """user_count = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    inactive_users = User.query.filter_by(is_active=False).count()"""
        
        if user_count_pattern in dashboard_function:
            updated_dashboard = dashboard_function.replace(
                user_count_pattern, 
                active_users_code
            )
            
            # Also update the render_template call to include the new variables
            render_pattern = r'return render_template\(\'dashboard\.html\',[^)]*\)'
            render_match = re.search(render_pattern, updated_dashboard)
            
            if render_match:
                render_call = render_match.group(0)
                if 'user_count=user_count' in render_call:
                    updated_render = render_call.replace(
                        'user_count=user_count',
                        'user_count=user_count, active_users=active_users, inactive_users=inactive_users'
                    )
                else:
                    # If user_count isn't in the template variables, add all three
                    updated_render = render_call.replace(
                        'return render_template(\'dashboard.html\'',
                        'return render_template(\'dashboard.html\', user_count=user_count, active_users=active_users, inactive_users=inactive_users'
                    )
                
                updated_dashboard = updated_dashboard.replace(render_call, updated_render)
            
            updated_content = content.replace(dashboard_function, updated_dashboard)
            
            with open(filename, 'w') as file:
                file.write(updated_content)
            
            print(f"Dashboard function updated in {filename}.")
            return True
        else:
            print(f"User count code not found in dashboard function in {filename}.")
            return False
    
    except Exception as e:
        print(f"Error updating dashboard function in {filename}: {str(e)}")
        return False

def update_dashboard_template(filename='templates/dashboard.html'):
    """Update the dashboard template to display active and inactive user counts"""
    if not os.path.exists(filename):
        print(f"File {filename} not found.")
        return False
    
    try:
        with open(filename, 'r') as file:
            content = file.read()
        
        # Look for the users card/widget in the dashboard
        users_card_pattern = r'<div[^>]*class="[^"]*card[^"]*"[^>]*>[\s\S]*?users[\s\S]*?</div>\s*</div>\s*</div>'
        users_card_match = re.search(users_card_pattern, content, re.IGNORECASE)
        
        if not users_card_match:
            print(f"Users card not found in {filename}.")
            return False
        
        users_card = users_card_match.group(0)
        
        # Check if we already have active/inactive user display
        if 'active_users' in users_card:
            print(f"Dashboard template already shows active/inactive users in {filename}.")
            return True
        
        # Create an updated version of the users card with active/inactive counts
        updated_card = users_card
        
        # Find the place where the user count is displayed
        count_pattern = r'<h2[^>]*>\s*{{ user_count }}\s*</h2>'
        count_match = re.search(count_pattern, updated_card)
        
        if count_match:
            count_block = count_match.group(0)
            updated_block = f"""<h2 class="card-title">{{ user_count }}</h2>
                <p class="text-success mb-0">Active: {{ active_users }}</p>
                <p class="text-danger mb-0">Inactive: {{ inactive_users }}</p>"""
            
            updated_card = updated_card.replace(count_block, updated_block)
            updated_content = content.replace(users_card, updated_card)
            
            with open(filename, 'w') as file:
                file.write(updated_content)
            
            print(f"Dashboard template updated in {filename}.")
            return True
        else:
            print(f"User count display not found in users card in {filename}.")
            return False
    
    except Exception as e:
        print(f"Error updating dashboard template in {filename}: {str(e)}")
        return False

def update_user_management_template(filename='templates/user_management.html'):
    """Update the user management template to display active status"""
    if not os.path.exists(filename):
        print(f"File {filename} not found.")
        return False
    
    try:
        with open(filename, 'r') as file:
            content = file.read()
        
        # Look for the user table in the template
        table_pattern = r'<table[^>]*id="userTable"[^>]*>[\s\S]*?</table>'
        table_match = re.search(table_pattern, content)
        
        if not table_match:
            print(f"User table not found in {filename}.")
            return False
        
        user_table = table_match.group(0)
        
        # Check if we already show is_active status
        if 'is_active' in user_table or 'user.is_active' in user_table:
            print(f"User management template already shows active status in {filename}.")
            return True
        
        # Look for the table headers
        header_pattern = r'<thead>\s*<tr>[\s\S]*?</tr>\s*</thead>'
        header_match = re.search(header_pattern, user_table)
        
        if not header_match:
            print(f"Table headers not found in user table in {filename}.")
            return False
        
        header_row = header_match.group(0)
        
        # Check if we need to update the status header or add a new one
        if '<th>Status</th>' in header_row:
            # Header already exists, we'll just update the display logic
            pass
        else:
            # Add a status column header
            updated_header = header_row.replace('</tr>', '<th>Status</th></tr>')
            user_table = user_table.replace(header_row, updated_header)
        
        # Now update the table body to use is_active
        body_pattern = r'<tbody>[\s\S]*?</tbody>'
        body_match = re.search(body_pattern, user_table)
        
        if not body_match:
            print(f"Table body not found in user table in {filename}.")
            return False
        
        table_body = body_match.group(0)
        
        # Find the row template for users
        row_pattern = r'{% for user in users %}[\s\S]*?{% endfor %}'
        row_match = re.search(row_pattern, table_body)
        
        if not row_match:
            print(f"User row template not found in table body in {filename}.")
            return False
        
        row_template = row_match.group(0)
        
        # Check if there's a status column already
        status_pattern = r'<td>.*?Active.*?Inactive.*?</td>'
        status_match = re.search(status_pattern, row_template)
        
        updated_row_template = row_template
        
        if status_match:
            # Update existing status column
            status_cell = status_match.group(0)
            updated_status = '<td><span class="badge {% if user.is_active %}bg-success{% else %}bg-danger{% endif %}">{% if user.is_active %}Active{% else %}Inactive{% endif %}</span></td>'
            updated_row_template = updated_row_template.replace(status_cell, updated_status)
        else:
            # Add new status column before the last column (actions)
            updated_row_template = updated_row_template.replace('</tr>', '<td><span class="badge {% if user.is_active %}bg-success{% else %}bg-danger{% endif %}">{% if user.is_active %}Active{% else %}Inactive{% endif %}</span></td></tr>')
        
        updated_table_body = table_body.replace(row_template, updated_row_template)
        updated_user_table = user_table.replace(table_body, updated_table_body)
        updated_content = content.replace(user_table, updated_user_table)
        
        with open(filename, 'w') as file:
            file.write(updated_content)
        
        print(f"User management template updated in {filename}.")
        return True
    
    except Exception as e:
        print(f"Error updating user management template in {filename}: {str(e)}")
        return False

if __name__ == "__main__":
    print("Starting update of dashboard and user management to show active/inactive users...")
    
    app_files = ['app.py', 'app_fixed.py', 'app_fixed_bak.py']
    for file in app_files:
        if os.path.exists(file):
            print(f"\nUpdating dashboard function in {file}...")
            update_dashboard_function(file)
        else:
            print(f"File {file} not found, skipping.")
    
    print("\nUpdating dashboard template...")
    update_dashboard_template()
    
    print("\nUpdating user management template...")
    update_user_management_template()
    
    print("\nUpdate process completed.") 