from app import app

if __name__ == '__main__':
    # Run the app on port 5001 instead of the default 5000
    app.run(debug=True, port=5001) 