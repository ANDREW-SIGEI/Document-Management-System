# KEMRI Laboratory System - Production Deployment Guide

This guide outlines the steps to deploy the KEMRI Laboratory System in a production environment.

## System Requirements

- Linux server (Ubuntu 20.04 LTS or newer recommended)
- Python 3.8 or higher
- Nginx or Apache web server
- SSL/TLS certificate
- SQLite (current) or PostgreSQL (recommended for scaling)

## Pre-Deployment Preparation

1. **Create a dedicated user account**:
   ```bash
   sudo adduser kemri
   sudo usermod -aG sudo kemri
   ```

2. **Clone the repository**:
   ```bash
   sudo -u kemri git clone https://github.com/ANDREW-SIGEI/KEMRI101.git /home/kemri/KEMRI101
   cd /home/kemri/KEMRI101
   ```

3. **Set up Python virtual environment**:
   ```bash
   sudo -u kemri python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install gunicorn  # For production server
   ```

4. **Configure environment variables**:
   Create a `.env` file with secure settings:
   ```bash
   cat > .env << EOL
   SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(16))')
   DATABASE_URI=sqlite:///app.db
   FLASK_ENV=production
   EOL
   ```

## Database Setup

1. **Initialize the database**:
   ```bash
   source venv/bin/activate
   python add_is_active_column.py
   ```

2. **Create initial admin user**:
   ```bash
   python init_db.py
   ```

## Web Server Configuration

### Option 1: Gunicorn with Nginx (Recommended)

1. **Create a systemd service file**:
   ```bash
   sudo nano /etc/systemd/system/kemri.service
   ```

   Add the following content:
   ```
   [Unit]
   Description=KEMRI Laboratory System
   After=network.target

   [Service]
   User=kemri
   WorkingDirectory=/home/kemri/KEMRI101
   Environment="PATH=/home/kemri/KEMRI101/venv/bin"
   EnvironmentFile=/home/kemri/KEMRI101/.env
   ExecStart=/home/kemri/KEMRI101/venv/bin/gunicorn --workers 4 --bind 0.0.0.0:8000 debug_app:app
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

2. **Configure Nginx as a reverse proxy**:
   ```bash
   sudo nano /etc/nginx/sites-available/kemri
   ```

   Add the following configuration:
   ```
   server {
       listen 80;
       server_name your_domain.com;
       
       location / {
           return 301 https://$host$request_uri;
       }
   }

   server {
       listen 443 ssl;
       server_name your_domain.com;
       
       ssl_certificate /etc/letsencrypt/live/your_domain.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/your_domain.com/privkey.pem;
       
       ssl_protocols TLSv1.2 TLSv1.3;
       ssl_prefer_server_ciphers on;
       ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
       
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
       
       location /static {
           alias /home/kemri/KEMRI101/static;
           expires 30d;
       }
   }
   ```

3. **Enable the site and restart Nginx**:
   ```bash
   sudo ln -s /etc/nginx/sites-available/kemri /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

4. **Start the application service**:
   ```bash
   sudo systemctl enable kemri
   sudo systemctl start kemri
   ```

### Option 2: Run with systemd directly

1. **Create a systemd service file that runs the application directly**:
   ```bash
   sudo nano /etc/systemd/system/kemri-direct.service
   ```

   Add the following content:
   ```
   [Unit]
   Description=KEMRI Laboratory System
   After=network.target

   [Service]
   User=kemri
   WorkingDirectory=/home/kemri/KEMRI101
   Environment="PATH=/home/kemri/KEMRI101/venv/bin"
   EnvironmentFile=/home/kemri/KEMRI101/.env
   ExecStart=/home/kemri/KEMRI101/venv/bin/python run_flask.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

2. **Enable and start the service**:
   ```bash
   sudo systemctl enable kemri-direct
   sudo systemctl start kemri-direct
   ```

## SSL Certificate Setup

1. **Install Certbot for Let's Encrypt**:
   ```bash
   sudo apt update
   sudo apt install certbot python3-certbot-nginx
   ```

2. **Obtain and install SSL certificate**:
   ```bash
   sudo certbot --nginx -d your_domain.com
   ```

## Backup Strategy

1. **Set up automatic database backups**:
   Create a backup script:
   ```bash
   cat > /home/kemri/backup.sh << EOL
   #!/bin/bash
   TIMESTAMP=\$(date +"%Y%m%d_%H%M%S")
   BACKUP_DIR="/home/kemri/backups"
   mkdir -p \$BACKUP_DIR
   cp /home/kemri/KEMRI101/app.db "\$BACKUP_DIR/app_\$TIMESTAMP.db"
   find \$BACKUP_DIR -type f -name "app_*.db" -mtime +30 -delete
   EOL
   
   chmod +x /home/kemri/backup.sh
   ```

2. **Schedule regular backups with cron**:
   ```bash
   (crontab -l 2>/dev/null; echo "0 2 * * * /home/kemri/backup.sh") | crontab -
   ```

## Monitoring and Logging

1. **Configure log rotation**:
   ```bash
   sudo nano /etc/logrotate.d/kemri
   ```

   Add the following:
   ```
   /home/kemri/KEMRI101/*.log {
       daily
       missingok
       rotate 14
       compress
       delaycompress
       notifempty
       create 0640 kemri kemri
   }
   ```

2. **Set up basic monitoring with systemd**:
   ```bash
   sudo systemctl status kemri
   journalctl -u kemri -f
   ```

## Security Hardening

1. **Set up a firewall**:
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw allow 22/tcp
   sudo ufw enable
   ```

2. **Secure shared file permissions**:
   ```bash
   sudo chown -R kemri:kemri /home/kemri/KEMRI101
   sudo find /home/kemri/KEMRI101 -type d -exec chmod 750 {} \;
   sudo find /home/kemri/KEMRI101 -type f -exec chmod 640 {} \;
   sudo chmod 660 /home/kemri/KEMRI101/app.db
   sudo chmod 770 /home/kemri/KEMRI101/uploads
   ```

## Troubleshooting

If you encounter issues during deployment:

1. **Check application logs**:
   ```bash
   sudo journalctl -u kemri -n 100
   cat /home/kemri/KEMRI101/flask_app.log
   ```

2. **Verify database permission issues**:
   ```bash
   sudo -u kemri ls -la /home/kemri/KEMRI101/app.db
   ```

3. **Test the application directly**:
   ```bash
   cd /home/kemri/KEMRI101
   source venv/bin/activate
   python run_debug.py
   ```

## Post-Deployment Verification

1. **Verify the application is running**:
   ```bash
   curl -I https://your_domain.com
   ```

2. **Test login functionality**:
   Access the site in a browser and attempt to log in with the admin credentials.

3. **Check server performance**:
   ```bash
   top
   htop  # If installed
   ```

## Maintenance

1. **Update the application**:
   ```bash
   cd /home/kemri/KEMRI101
   sudo -u kemri git pull
   source venv/bin/activate
   pip install -r requirements.txt
   sudo systemctl restart kemri
   ```

2. **Database maintenance**:
   ```bash
   source venv/bin/activate
   python maintenance.py
   ```

For additional support, contact the KEMRI Laboratory System development team. 