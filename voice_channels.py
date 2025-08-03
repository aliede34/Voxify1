from flask import session
from flask_socketio import join_room, leave_room, emit
from models import db, VoiceParticipant

# Voice Channel Event Handlers
def register_voice_channel_events(socketio):
    @socketio.on('join_voice_channel')
    def handle_join_voice_channel(data):
        channel_id = data['channel_id']
        user_id = session.get('user_id')
        
        if not user_id:
            return
        
        # Join the SocketIO room for this channel
        join_room(f'channel_{channel_id}')
        
        # Add user to voice participants in database
        existing_participant = VoiceParticipant.query.filter_by(
            user_id=user_id, channel_id=channel_id).first()
        
        if not existing_participant:
            participant = VoiceParticipant(user_id=user_id, channel_id=channel_id)
            db.session.add(participant)
            db.session.commit()
        
        # Notify others in the channel
        emit('user_joined_voice_channel', {
            'user_id': user_id,
            'username': data.get('username', 'Unknown')
        }, room=f'channel_{channel_id}')
    
    @socketio.on('leave_voice_channel')
    def handle_leave_voice_channel(data):
        channel_id = data['channel_id']
        user_id = session.get('user_id')
        
        if not user_id:
            return
        
        # Leave the SocketIO room for this channel
        leave_room(f'channel_{channel_id}')
        
        # Remove user from voice participants in database
        participant = VoiceParticipant.query.filter_by(
            user_id=user_id, channel_id=channel_id).first()
        
        if participant:
            db.session.delete(participant)
            db.session.commit()
        
        # Notify others in the channel
        emit('user_left_voice_channel', {
            'user_id': user_id
        }, room=f'channel_{channel_id}')
    
    # We can reuse some of the existing WebRTC signaling events for voice channels
    # The main difference is that we'll use channel rooms instead of user-to-user rooms
    
    @socketio.on('channel_offer')
    def handle_channel_offer(data):
        offer = data['offer']
        channel_id = data['channel_id']
        target_user = data['target_user']
        
        emit('channel_offer', {
            'offer': offer,
            'user_id': session['user_id'],
            'channel_id': channel_id
        }, room=target_user)
    
    @socketio.on('channel_answer')
    def handle_channel_answer(data):
        answer = data['answer']
        channel_id = data['channel_id']
        target_user = data['target_user']
        
        emit('channel_answer', {
            'answer': answer,
            'user_id': session['user_id'],
            'channel_id': channel_id
        }, room=target_user)
    
    @socketio.on('channel_ice_candidate')
    def handle_channel_ice_candidate(data):
        candidate = data['candidate']
        channel_id = data['channel_id']
        target_user = data['target_user']
        
        emit('channel_ice_candidate', {
            'candidate': candidate,
            'user_id': session['user_id'],
            'channel_id': channel_id
        }, room=target_user)
