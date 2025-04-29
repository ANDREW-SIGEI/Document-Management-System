import requests

# Start a session to maintain cookies
session = requests.Session()

# Base URL
base_url = 'http://localhost:5000'

# Get the login page to get any CSRF token if needed
login_response = session.get(f'{base_url}/login')
print(f"Fetched login page: {login_response.status_code}")

# Login credentials
login_data = {
    'username': 'admin',
    'password': 'admin123'
}

# Submit login
post_response = session.post(f'{base_url}/login', data=login_data)
print(f"Login attempt: {post_response.status_code}")
print(f"Redirected to: {post_response.url}")

# Try to access my_account
account_response = session.get(f'{base_url}/my_account')
print(f"My Account page: {account_response.status_code}")
print(f"URL: {account_response.url}")

# Print cookies
print("\nSession cookies:")
for cookie in session.cookies:
    print(f"{cookie.name}: {cookie.value}") 