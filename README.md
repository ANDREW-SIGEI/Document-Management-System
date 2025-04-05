# KEMRI101 Document Management System

A comprehensive document management system for tracking, processing, and managing documents within an organization. Built with Flask and modern web technologies.

## Features

- **Document Tracking**: Unique tracking codes and QR codes for each document
- **User Management**: Add, edit, and manage user accounts with different roles
- **Workflow Management**: Configure document workflows with approval steps
- **Reports and Analytics**: Generate reports on document processing times and statuses
- **Mobile-Friendly Interface**: Responsive design for all screen sizes
- **QR Code Generation**: Generate and scan QR codes for quick document tracking
- **Advanced Search**: Search documents by various criteria

## Document Lifecycle Management

The system supports the complete lifecycle of documents:

1. **Upload**: Documents can be uploaded with detailed metadata
2. **Tracking**: Each document gets a unique tracking code
3. **Processing**: Documents can be assigned, commented on, and have status changes
4. **Actions**: Various actions can be performed on documents including:
   - Priority changes
   - Reassigning to different departments/users
   - Linking related documents
   - Adding comments and notes
   - Exporting document history
5. **Archiving**: Documents can be marked as completed or archived

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Flask
- SQLAlchemy
- Other dependencies listed in requirements.txt

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/ANDREW-SIGEI/KEMRI101.git
   cd KEMRI101
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the application:
   ```
   flask --app app_fixed run
   ```

5. Access the application in your browser at:
   ```
   http://127.0.0.1:5000/
   ```

## Usage

### Document Upload

1. Navigate to the "Compose" page
2. Fill in document details
3. Upload the document file
4. Optionally preview the tracking code
5. Submit the form

### Document Tracking

1. Go to the "Track Document" page
2. Enter the tracking code or scan a QR code
3. View document status, history, and details
4. Add actions or comments if authorized

### User Management

1. Access the "User Management" page (admin only)
2. Add, edit, or delete users
3. Assign roles and permissions

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

* KEMRI for project requirements and feedback
* All contributors to the project 