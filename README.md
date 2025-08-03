# Voxify - Discord-like Chat Application

Voxify is a Discord-like chat application built with Python Flask that includes voice chat and voice channel functionality.

## Features

- User authentication system with registration and login
- Server management (create, join, leave servers)
- Channel system (text and voice channels)
- Real-time messaging system with message history
- Direct messaging between users
- Friend system (add, remove friends, requests, online status)
- User status and presence features (online, offline, idle, dnd)
- Role-based access control system
- Voice chat with DM calling and peer-to-peer audio
- Voice channels with multi-user voice communication

## Technologies Used

- Python Flask
- Flask-SQLAlchemy for database management
- Flask-SocketIO for real-time communication
- Flask-Security for authentication and authorization
- WebRTC for peer-to-peer audio streaming
- Tailwind CSS and Bootstrap for frontend styling

## Deployment to Render

1. Create a new Web Service on Render
2. Connect your repository
3. Set the following environment variables:
   - `SECRET_KEY` - A random secret key for Flask
   - `DATABASE_URL` - PostgreSQL database URL (Render will provide this)
4. Set the build command to: `pip install -r requirements.txt`
5. Set the start command to: `gunicorn --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 app:app`
6. Add a `render.yaml` file to your repository (see below)

## Render Configuration

Create a `render.yaml` file in your repository root:

```yaml
services:
  - type: web
    name: voxify
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 app:app
    envVars:
      - key: SECRET_KEY
        sync: false
      - key: DATABASE_URL
        fromDatabase:
          name: voxify-db
          property: connectionString

databases:
  - name: voxify-db
    databaseName: voxify
```

## Local Development

1. Install dependencies: `pip install -r requirements.txt`
2. Run the application: `python app.py`
3. Access the application at `http://localhost:5000`

Note: There may be port conflicts on Windows. If this occurs, try using a different port or a Linux/Mac environment for development.

## Environment Variables

- `SECRET_KEY` - Flask secret key (required)
- `DATABASE_URL` - Database connection string (optional, defaults to SQLite)

## Database Migrations

The application uses SQLite for local development and PostgreSQL for production. When deploying to Render, the database will be automatically provisioned.

## Troubleshooting

If you encounter issues with voice functionality, ensure that:
1. WebRTC is supported in the user's browser
2. The browser has permission to access microphone
3. The server is running with proper WebSocket support

For port conflict issues on Windows during local development:
1. Try using a different port
2. Ensure no other instances of the application are running
3. Consider using a Linux/Mac environment for development
