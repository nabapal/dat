from app import app, db

if __name__ == '__main__':
    import sys
    port = 5004
    host = '0.0.0.0'
    if '--port=' in ' '.join(sys.argv):
        for arg in sys.argv:
            if arg.startswith('--port='):
                port = int(arg.split('=')[1])
    # Print DB file in use for debugging
    with app.app_context():
        print('DB file in use:', db.engine.url)
    app.run(debug=True, port=port, host=host)
