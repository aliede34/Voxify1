from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_security import UserMixin, RoleMixin
import uuid

db = SQLAlchemy()

# Association table for User-Roles many-to-many relationship
roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('users.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)

class Role(db.Model, RoleMixin):
    __tablename__ = 'role'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))
    
    def __repr__(self):
        return f'<Role {self.name}>'


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False, default=lambda: uuid.uuid4().hex)
    avatar = db.Column(db.String(255), default='default.png')
    status = db.Column(db.String(20), default='offline')  # online, offline, idle, dnd
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    servers = db.relationship('Server', secondary='server_members', back_populates='members')
    messages = db.relationship('Message', backref='author', lazy=True)
    direct_messages_sent = db.relationship('DirectMessage', foreign_keys='DirectMessage.sender_id', backref='sender', lazy=True)
    direct_messages_received = db.relationship('DirectMessage', foreign_keys='DirectMessage.recipient_id', backref='recipient', lazy=True)
    roles = db.relationship('Role', secondary=roles_users, backref='users')
    
    def __repr__(self):
        return f'<User {self.username}>'

class Server(db.Model):
    __tablename__ = 'servers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    icon = db.Column(db.String(255), default='default.png')
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    owner = db.relationship('User', backref='owned_servers')
    members = db.relationship('User', secondary='server_members', back_populates='servers')
    channels = db.relationship('Channel', backref='server', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Server {self.name}>'

class ServerMember(db.Model):
    __tablename__ = 'server_members'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    server_id = db.Column(db.Integer, db.ForeignKey('servers.id'), nullable=False)
    role = db.Column(db.String(50), default='member')  # member, admin, owner
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure a user can only join a server once
    __table_args__ = (db.UniqueConstraint('user_id', 'server_id', name='unique_user_server'),)

class Channel(db.Model):
    __tablename__ = 'channels'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    topic = db.Column(db.String(255))
    server_id = db.Column(db.Integer, db.ForeignKey('servers.id'), nullable=False)
    type = db.Column(db.String(20), default='text')  # text, voice
    position = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Voice channel specific fields
    bitrate = db.Column(db.Integer, default=64000)  # Default 64kbps
    user_limit = db.Column(db.Integer, default=0)   # 0 = no limit
    
    # Relationships
    messages = db.relationship('Message', backref='channel', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Channel {self.name} ({self.type})>'

class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    channel_id = db.Column(db.Integer, db.ForeignKey('channels.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    edited_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Message {self.id}>'

class DirectMessage(db.Model):
    __tablename__ = 'direct_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<DirectMessage {self.id}>'

class Friend(db.Model):
    __tablename__ = 'friends'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, blocked
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure a friendship can only exist once
    __table_args__ = (db.UniqueConstraint('user_id', 'friend_id', name='unique_friendship'),)
    
    def __repr__(self):
        return f'<Friend {self.user_id} - {self.friend_id}>'


class VoiceParticipant(db.Model):
    __tablename__ = 'voice_participants'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    channel_id = db.Column(db.Integer, db.ForeignKey('channels.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='voice_participations')
    channel = db.relationship('Channel', backref='participants')
    
    # Ensure a user can only be in a voice channel once
    __table_args__ = (db.UniqueConstraint('user_id', 'channel_id', name='unique_user_channel'),)
    
    def __repr__(self):
        return f'<VoiceParticipant {self.user_id} in {self.channel_id}>'
