from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_security import Security, SQLAlchemyUserDatastore, UserMixin, RoleMixin, login_required, roles_required
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import os

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
    
    # Database configuration for Render deployment
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Render provides a DATABASE_URL with 'postgres://' scheme, but SQLAlchemy needs 'postgresql://'
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///voxify.db'
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    # Import db from models and initialize with app
    from models import db
    db.init_app(app)
    
    bcrypt = Bcrypt(app)
    
    # Import models after db initialization to avoid circular imports
    from models import User, Server, Channel, Message, DirectMessage, Friend, ServerMember, Role, VoiceParticipant
    
    # Import voice channel functionality
    from voice_channels import register_voice_channel_events
    
    # Setup Flask-Security
    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    security = Security(app, user_datastore)
    
    # Create tables and default roles
    with app.app_context():
        # Handle database migrations for existing databases
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        
        # Check if users table exists
        if 'users' in inspector.get_table_names():
            # Check if fs_uniquifier column exists
            columns = [column['name'] for column in inspector.get_columns('users')]
            if 'fs_uniquifier' not in columns:
                # For SQLite, we need to recreate the table with the new column
                # since it doesn't support adding UNIQUE columns to existing tables
                import uuid
                from sqlalchemy import text
                
                try:
                    # Check if we're using SQLite
                    if 'sqlite' in str(db.engine.url).lower():
                        # For SQLite, recreate the table with the new column
                        print("Performing SQLite migration for fs_uniquifier column...")
                        
                        # Import User model
                        from models import User
                        
                        # Get all existing users
                        existing_users = User.query.all()
                        
                        # Create a backup of existing data
                        user_data = []
                        for user in existing_users:
                            user_data.append({
                                'id': user.id,
                                'username': user.username,
                                'email': user.email,
                                'password': user.password,
                                'avatar': user.avatar,
                                'status': user.status,
                                'last_seen': user.last_seen,
                                'created_at': user.created_at
                            })
                        
                        # Drop the old table
                        db.session.execute(text('DROP TABLE users'))
                        db.session.commit()
                        
                        # Create the new table with the correct schema
                        db.create_all()
                        
                        # Repopulate with existing data plus fs_uniquifier
                        for data in user_data:
                            user = User(
                                id=data['id'],
                                username=data['username'],
                                email=data['email'],
                                password=data['password'],
                                avatar=data['avatar'],
                                status=data['status'],
                                last_seen=data['last_seen'],
                                created_at=data['created_at'],
                                fs_uniquifier=uuid.uuid4().hex
                            )
                            db.session.add(user)
                        
                        db.session.commit()
                        print("SQLite migration completed successfully.")
                    else:
                        # For other databases, try the standard ALTER TABLE approach
                        db.session.execute(text('ALTER TABLE users ADD COLUMN fs_uniquifier VARCHAR(255) UNIQUE'))
                        db.session.commit()
                        
                        # Import User model after adding column
                        from models import User
                        
                        # Populate existing users with unique identifiers
                        users = User.query.all()
                        for user in users:
                            if not user.fs_uniquifier:
                                user.fs_uniquifier = uuid.uuid4().hex
                        
                        db.session.commit()
                except Exception as e:
                    # Handle case where column already exists or other issues
                    db.session.rollback()
                    print(f"Migration warning: {e}")
        
        db.create_all()
        
        # Import models after db initialization to avoid circular imports
        from models import User, Server, Channel, Message, DirectMessage, Friend, ServerMember, Role, VoiceParticipant
        
        # Create default roles if they don't exist
        if not user_datastore.find_role('admin'):
            user_datastore.create_role(name='admin', description='Administrator')
        if not user_datastore.find_role('moderator'):
            user_datastore.create_role(name='moderator', description='Moderator')
        if not user_datastore.find_role('user'):
            user_datastore.create_role(name='user', description='Regular User')
        db.session.commit()
    
    # Routes will be added here
    
    @app.route('/')
    def index():
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        return render_template('index.html')
    
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            
            # Check if user already exists
            existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
            if existing_user:
                flash('Username or email already exists', 'error')
                return redirect(url_for('register'))
            
            # Create new user
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            user = User(username=username, email=email, password=hashed_password)
            db.session.add(user)
            db.session.commit()
            
            # Assign default user role
            user_datastore.add_role_to_user(user, 'user')
            db.session.commit()
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        
        return render_template('register.html')
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']
            
            user = User.query.filter_by(email=email).first()
            
            if user and bcrypt.check_password_hash(user.password, password):
                session['user_id'] = user.id
                user.last_seen = datetime.utcnow()
                db.session.commit()
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid email or password', 'error')
        
        return render_template('login.html')
    
    @app.route('/logout')
    def logout():
        session.pop('user_id', None)
        return redirect(url_for('index'))
    
    @app.route('/dashboard')
    def dashboard():
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        user = User.query.get(session['user_id'])
        if not user:
            # User not found in database, clear session and redirect to login
            session.pop('user_id', None)
            flash('User not found. Please log in again.', 'error')
            return redirect(url_for('login'))
        
        servers = Server.query.join(ServerMember).filter(ServerMember.user_id == user.id).all()
        friends = Friend.query.filter(
            ((Friend.user_id == user.id) | (Friend.friend_id == user.id)) & 
            (Friend.status == 'accepted')
        ).all()
        
        return render_template('dashboard.html', user=user, servers=servers, friends=friends)
    
    # Server routes
    @app.route('/server/create', methods=['GET', 'POST'])
    def create_server():
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        if request.method == 'POST':
            name = request.form['name']
            
            if not name:
                flash('Server name is required', 'error')
                return redirect(url_for('create_server'))
            
            # Create new server
            server = Server(name=name, owner_id=session['user_id'])
            db.session.add(server)
            db.session.commit()
            
            # Add owner as server member
            member = ServerMember(user_id=session['user_id'], server_id=server.id, role='owner')
            db.session.add(member)
            db.session.commit()
            
            flash(f'Server "{name}" created successfully!', 'success')
            return redirect(url_for('server', server_id=server.id))
        
        return render_template('create_server.html')
    
    @app.route('/server/<int:server_id>')
    def server(server_id):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        # Check if user is a member of the server
        member = ServerMember.query.filter_by(user_id=session['user_id'], server_id=server_id).first()
        if not member:
            flash('You are not a member of this server', 'error')
            return redirect(url_for('dashboard'))
        
        server = Server.query.get_or_404(server_id)
        channels = Channel.query.filter_by(server_id=server_id).order_by(Channel.position).all()
        
        return render_template('server.html', server=server, channels=channels)
    
    @app.route('/server/<int:server_id>/join')
    def join_server(server_id):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        # Check if user is already a member
        existing_member = ServerMember.query.filter_by(user_id=session['user_id'], server_id=server_id).first()
        if existing_member:
            flash('You are already a member of this server', 'info')
            return redirect(url_for('server', server_id=server_id))
        
        # Add user as member
        member = ServerMember(user_id=session['user_id'], server_id=server_id, role='member')
        db.session.add(member)
        db.session.commit()
        
        server = Server.query.get_or_404(server_id)
        flash(f'You have joined "{server.name}"', 'success')
        return redirect(url_for('server', server_id=server_id))
    
    # Channel routes
    @app.route('/channel/<int:channel_id>')
    def channel(channel_id):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        channel = Channel.query.get_or_404(channel_id)
        server = channel.server
        
        # Check if user is a member of the server
        member = ServerMember.query.filter_by(user_id=session['user_id'], server_id=server.id).first()
        if not member:
            flash('You are not a member of this server', 'error')
            return redirect(url_for('dashboard'))
        
        messages = Message.query.filter_by(channel_id=channel_id).order_by(Message.created_at).all()
        
        return render_template('channel.html', channel=channel, server=server, messages=messages)
    
    @app.route('/channel/create/<int:server_id>', methods=['POST'])
    def create_channel(server_id):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        # Check if user is a member of the server
        member = ServerMember.query.filter_by(user_id=session['user_id'], server_id=server_id).first()
        if not member:
            flash('You are not a member of this server', 'error')
            return redirect(url_for('dashboard'))
        
        # Check if user has permission to create channels (owner or admin)
        if member.role not in ['owner', 'admin']:
            flash('You do not have permission to create channels', 'error')
            return redirect(url_for('server', server_id=server_id))
        
        name = request.form['name']
        channel_type = request.form.get('type', 'text')
        
        if not name:
            flash('Channel name is required', 'error')
            return redirect(url_for('server', server_id=server_id))
        
        # Create new channel
        channel = Channel(name=name, server_id=server_id, type=channel_type)
        db.session.add(channel)
        db.session.commit()
        
        flash(f'Channel "#{name}" created successfully!', 'success')
        return redirect(url_for('server', server_id=server_id))
    
    # Messaging routes
    @app.route('/message/send/<int:channel_id>', methods=['POST'])
    def send_message(channel_id):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        content = request.form['content']
        if not content.strip():
            flash('Message cannot be empty', 'error')
            return redirect(url_for('channel', channel_id=channel_id))
        
        # Check if channel exists
        channel = Channel.query.get_or_404(channel_id)
        
        # Check if user is a member of the server
        member = ServerMember.query.filter_by(user_id=session['user_id'], server_id=channel.server_id).first()
        if not member:
            flash('You are not a member of this server', 'error')
            return redirect(url_for('dashboard'))
        
        # Create new message
        message = Message(content=content.strip(), author_id=session['user_id'], channel_id=channel_id)
        db.session.add(message)
        db.session.commit()
        
        return redirect(url_for('channel', channel_id=channel_id))
    
    # Direct messaging routes
    @app.route('/dm/<int:user_id>')
    def direct_message(user_id):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        # Check if user exists
        recipient = User.query.get_or_404(user_id)
        
        # Get messages between current user and recipient
        messages = DirectMessage.query.filter(
            ((DirectMessage.sender_id == session['user_id']) & (DirectMessage.recipient_id == user_id)) |
            ((DirectMessage.sender_id == user_id) & (DirectMessage.recipient_id == session['user_id']))
        ).order_by(DirectMessage.created_at).all()
        
        # Mark messages as read
        DirectMessage.query.filter(
            (DirectMessage.sender_id == user_id) & 
            (DirectMessage.recipient_id == session['user_id']) & 
            (DirectMessage.is_read == False)
        ).update({DirectMessage.is_read: True})
        db.session.commit()
        
        return render_template('direct_message.html', recipient=recipient, messages=messages)
    
    @app.route('/dm/send/<int:user_id>', methods=['POST'])
    def send_direct_message(user_id):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        content = request.form['content']
        if not content.strip():
            flash('Message cannot be empty', 'error')
            return redirect(url_for('direct_message', user_id=user_id))
        
        # Check if recipient exists
        recipient = User.query.get_or_404(user_id)
        
        # Create new direct message
        message = DirectMessage(content=content.strip(), sender_id=session['user_id'], recipient_id=user_id)
        db.session.add(message)
        db.session.commit()
        
        return redirect(url_for('direct_message', user_id=user_id))
    
    # Friend routes
    @app.route('/friends')
    def friends():
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        # Get accepted friends
        friends = User.query.join(Friend, User.id == Friend.friend_id).filter(
            (Friend.user_id == session['user_id']) & (Friend.status == 'accepted')
        ).union(
            User.query.join(Friend, User.id == Friend.user_id).filter(
                (Friend.friend_id == session['user_id']) & (Friend.status == 'accepted')
            )
        ).all()
        
        # Get pending friend requests
        pending_requests = User.query.join(Friend, User.id == Friend.user_id).filter(
            (Friend.friend_id == session['user_id']) & (Friend.status == 'pending')
        ).all()
        
        return render_template('friends.html', friends=friends, pending_requests=pending_requests)
    
    @app.route('/friends/add', methods=['POST'])
    def add_friend_by_username():
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        username = request.form.get('friend_username')
        if not username:
            flash('Username is required', 'error')
            return redirect(url_for('friends'))
        
        # Find user by username
        user = User.query.filter_by(username=username).first()
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('friends'))
        
        # Prevent users from adding themselves
        if user.id == session['user_id']:
            flash('You cannot add yourself as a friend', 'error')
            return redirect(url_for('friends'))
        
        # Check if already friends or request pending
        existing_friendship = Friend.query.filter(
            ((Friend.user_id == session['user_id']) & (Friend.friend_id == user.id)) |
            ((Friend.user_id == user.id) & (Friend.friend_id == session['user_id']))
        ).first()
        
        if existing_friendship:
            if existing_friendship.status == 'accepted':
                flash('You are already friends with this user', 'info')
            elif existing_friendship.status == 'pending' and existing_friendship.user_id == session['user_id']:
                flash('Friend request already sent', 'info')
            elif existing_friendship.status == 'pending' and existing_friendship.friend_id == session['user_id']:
                # Accept the friend request
                existing_friendship.status = 'accepted'
                db.session.commit()
                flash('Friend request accepted!', 'success')
            return redirect(url_for('friends'))
        
        # Create new friend request
        friend_request = Friend(user_id=session['user_id'], friend_id=user.id, status='pending')
        db.session.add(friend_request)
        db.session.commit()
        
        flash('Friend request sent!', 'success')
        return redirect(url_for('friends'))
    
    @app.route('/friends/add/<int:user_id>')
    def add_friend(user_id):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        # Check if user exists
        user = User.query.get_or_404(user_id)
        
        # Check if already friends or request pending
        existing_friendship = Friend.query.filter(
            ((Friend.user_id == session['user_id']) & (Friend.friend_id == user_id)) |
            ((Friend.user_id == user_id) & (Friend.friend_id == session['user_id']))
        ).first()
        
        if existing_friendship:
            if existing_friendship.status == 'accepted':
                flash('You are already friends with this user', 'info')
            elif existing_friendship.status == 'pending' and existing_friendship.user_id == session['user_id']:
                flash('Friend request already sent', 'info')
            elif existing_friendship.status == 'pending' and existing_friendship.friend_id == session['user_id']:
                # Accept the friend request
                existing_friendship.status = 'accepted'
                db.session.commit()
                flash('Friend request accepted!', 'success')
            return redirect(url_for('friends'))
        
        # Create new friend request
        friend_request = Friend(user_id=session['user_id'], friend_id=user_id, status='pending')
        db.session.add(friend_request)
        db.session.commit()
        
        flash('Friend request sent!', 'success')
        return redirect(url_for('friends'))
    
    @app.route('/friends/remove/<int:user_id>')
    def remove_friend(user_id):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        # Find friendship
        friendship = Friend.query.filter(
            ((Friend.user_id == session['user_id']) & (Friend.friend_id == user_id)) |
            ((Friend.user_id == user_id) & (Friend.friend_id == session['user_id']))
        ).first()
        
        if friendship:
            db.session.delete(friendship)
            db.session.commit()
            flash('Friend removed successfully', 'success')
        else:
            flash('You are not friends with this user', 'error')
        
        return redirect(url_for('friends'))
    
    # User status routes
    @app.route('/status/update', methods=['POST'])
    def update_status():
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        user = User.query.get(session['user_id'])
        if not user:
            # User not found in database, clear session and redirect to login
            session.pop('user_id', None)
            flash('User not found. Please log in again.', 'error')
            return redirect(url_for('login'))
        
        status = request.form['status']
        valid_statuses = ['online', 'idle', 'dnd', 'offline']
        
        if status in valid_statuses:
            user.status = status
            user.last_seen = datetime.utcnow()
            db.session.commit()
            
            # Return JSON response for AJAX requests
            if request.headers.get('Content-Type') == 'application/json':
                return jsonify({'success': True, 'status': status})
        
        # Redirect back for regular form submissions
        return redirect(request.referrer or url_for('dashboard'))
    
    # WebRTC Signaling Event Handlers
    @socketio.on('join_voice_room')
    def handle_join_voice_room(data):
        room = data['room']
        user_id = data['user_id']
        join_room(room)
        emit('user_joined', {'user_id': user_id}, room=room)
    
    @socketio.on('leave_voice_room')
    def handle_leave_voice_room(data):
        room = data['room']
        user_id = data['user_id']
        leave_room(room)
        emit('user_left', {'user_id': user_id}, room=room)
    
    @socketio.on('offer')
    def handle_offer(data):
        offer = data['offer']
        target_user = data['target_user']
        emit('offer', {'offer': offer, 'user_id': session['user_id']}, room=target_user)
    
    @socketio.on('answer')
    def handle_answer(data):
        answer = data['answer']
        target_user = data['target_user']
        emit('answer', {'answer': answer, 'user_id': session['user_id']}, room=target_user)
    
    @socketio.on('ice_candidate')
    def handle_ice_candidate(data):
        candidate = data['candidate']
        target_user = data['target_user']
        emit('ice_candidate', {'candidate': candidate, 'user_id': session['user_id']}, room=target_user)
    
    @socketio.on('voice_call')
    def handle_voice_call(data):
        target_user = data['target_user']
        emit('incoming_call', {'user_id': session['user_id'], 'username': data['username']}, room=target_user)
    
    @socketio.on('call_accepted')
    def handle_call_accepted(data):
        target_user = data['target_user']
        emit('call_accepted', {'user_id': session['user_id']}, room=target_user)
    
    @socketio.on('call_rejected')
    def handle_call_rejected(data):
        target_user = data['target_user']
        emit('call_rejected', {'user_id': session['user_id']}, room=target_user)
    
    @socketio.on('end_call')
    def handle_end_call(data):
        target_user = data['target_user']
        emit('call_ended', {'user_id': session['user_id']}, room=target_user)
    
    # Register voice channel events
    register_voice_channel_events(socketio)
    
    return app, socketio

# Create application instance for gunicorn
app, socketio = create_app()

if __name__ == '__main__':
    # Get port from environment variable (for Render deployment) or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    print(f"Starting server on http://0.0.0.0:{port}...")
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
