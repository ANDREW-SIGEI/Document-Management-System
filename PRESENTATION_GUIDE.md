# KEMRI Laboratory System - Presentation Guide

## Setup Instructions

1. **Start the server:**
   ```
   ./start_server.sh
   ```
   This script will:
   - Check for and fix any database schema issues
   - Start the server on port 8080
   - Open the application in your browser

2. **Open the application manually if needed:**
   ```
   http://127.0.0.1:8080
   ```

## Demo Walkthrough

### 1. Login
- Username: `admin`
- Password: `admin`

### 2. Document Management
- **Dashboard** - Show document statistics and overview
- **Compose** - Create a new document/form
- **Track Document** - Demonstrate how to track a document by code
- **Incoming/Outgoing** - Show document lists and filtering

### 3. Workflow Management  
- **Registry Approval** - Show approval process
- **Registry Workflow** - Demonstrate workflow steps

### 4. User Management
- **User Management** - Show adding/editing users with different roles
- **File Manager** - Demonstrate file upload and organization

### 5. System Administration
- **Database Management** - Show backup/restore options
- **Maintenance** - Demonstrate system maintenance features

## Key Features to Highlight

1. **Document Tracking** - Each document gets a unique tracking code and QR code
2. **Workflow Management** - Multi-step approval processes
3. **User Roles** - Different access levels and permissions
4. **Mobile-Friendly** - Responsive design works on all devices
5. **Search Capabilities** - Advanced filtering and searching

## Future Improvements

1. **Security Enhancements**
   - Password hashing implementation
   - HTTPS support
   - Two-factor authentication

2. **Performance Optimization**
   - Database indexing
   - Caching for frequently accessed data

3. **Additional Features**
   - Email notifications
   - Document expiration management
   - Integration with other systems

## Troubleshooting

If you encounter any issues during the presentation:

1. **Database Issues:**
   ```
   python add_is_active_column.py
   ```

2. **Server Won't Start:**
   ```
   pkill -f "python run_*"
   ./start_server.sh
   ```

3. **UI Issues:**
   Try a hard refresh (Ctrl+F5) 