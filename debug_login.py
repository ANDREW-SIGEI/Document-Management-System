from app_fixed import db, User, app

with app.app_context():
    # Check if the admin user exists
    admin = User.query.filter_by(username='admin').first()
    
    if admin:
        print(f"Admin user found:")
        print(f"  Username: {admin.username}")
        print(f"  Email: {admin.email}")
        print(f"  Password: {admin.password}")
        print(f"  Role: {admin.role}")
    else:
        print("Admin user not found!")
        
        # Create a new admin user
        print("Creating a new admin user...")
        admin = User(
            username='admin',
            email='admin@example.com',
            phone='+1234567890',
            department='IT Department',
            password='password',
            role='Administrator'
        )
        db.session.add(admin)
        db.session.commit()
        print("New admin user created successfully.") 