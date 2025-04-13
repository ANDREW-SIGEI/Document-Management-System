# KEMRI Laboratory System Deployment Guide

## Pre-Deployment Checklist

1. ✅ Debug mode disabled
2. ✅ Secure secret key implemented 
3. ✅ Database initialization safe (no data loss)
4. ✅ Application runs without errors

## Deployment Instructions

### Option 1: Using the run_flask.py script

1. Copy the application files to your production server
2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set environment variables (recommended for security):
   ```
   export SECRET_KEY=your_secure_secret_key
   ```
4. Run the application with:
   ```
   python run_flask.py
   ```

### Option 2: Using Gunicorn (Recommended for Production)

1. Install Gunicorn:
   ```
   pip install gunicorn
   ```
2. Run the application with:
   ```
   gunicorn -w 4 -b 0.0.0.0:5000 debug_app:app
   ```
3. For running as a service, create a systemd service file:
   ```
   [Unit]
   Description=KEMRI Laboratory System
   After=network.target

   [Service]
   User=your_username
   WorkingDirectory=/path/to/KEMRI101
   Environment="SECRET_KEY=your_secure_secret_key"
   ExecStart=/path/to/python/bin/gunicorn -w 4 -b 0.0.0.0:5000 debug_app:app
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

## Post-Deployment Tasks

1. Set up a reverse proxy (Nginx or Apache) to handle HTTPS
2. Configure regular database backups
3. Set up monitoring for the application
4. Configure log rotation for the application logs

## Default Login Credentials

For the demo version:
- Username: admin
- Password: admin

**IMPORTANT:** Change the default credentials after deployment!

## Troubleshooting

- If the application fails to start, check the `flask_app.log` file for errors
- If database errors occur, ensure the database file is writable by the application user
- For issues with user management, verify that the `users.json` file exists and is writable

## Security Notes

1. The application currently stores passwords in plaintext for the debug version
2. In a production environment, consider implementing:
   - HTTPS for all connections
   - Rate limiting for login attempts
   - IP-based access restrictions for admin functions
   - Regular security audits

## Contact

For support or questions, contact the KEMRI Laboratory System team. 