from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    # Static data to show on the dashboard
    users = [
        {'id': 1, 'username': 'user1', 'email': 'user1@example.com'},
        {'id': 2, 'username': 'user2', 'email': 'user2@example.com'},
        {'id': 3, 'username': 'user3', 'email': 'user3@example.com'}
    ]
    return render_template('dashboard.html', users=users)

if __name__ == '__main__':
    app.run(debug=True, port=5001) 