from app import create_app

app = create_app()

if __name__ == '__main__':
    # Start the Flask development web server on port 5000
    app.run(debug=True, port=5000)
