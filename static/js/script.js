// Basic JavaScript functionality for the Discord clone

document.addEventListener('DOMContentLoaded', function() {
    // Toggle mobile menu
    const mobileMenuButton = document.querySelector('.navbar-toggler');
    const navbarCollapse = document.querySelector('.navbar-collapse');
    
    if (mobileMenuButton) {
        mobileMenuButton.addEventListener('click', function() {
            navbarCollapse.classList.toggle('show');
        });
    }
    
    // Handle form validation
    const registerForm = document.querySelector('form');
    if (registerForm) {
        registerForm.addEventListener('submit', function(e) {
            const password = document.getElementById('password');
            const confirmPassword = document.getElementById('confirm_password');
            
            if (password && confirmPassword && password.value !== confirmPassword.value) {
                e.preventDefault();
                alert('Passwords do not match!');
                return false;
            }
        });
    }
    
    // Set user status
    const statusButtons = document.querySelectorAll('.status-btn');
    statusButtons.forEach(button => {
        button.addEventListener('click', function() {
            const status = this.getAttribute('data-status');
            // In a real app, this would send a request to update the user's status
            console.log('Setting status to:', status);
            
            // Update UI to reflect status change
            document.querySelectorAll('.status-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            this.classList.add('active');
        });
    });
    
    // Channel switching
    const channelItems = document.querySelectorAll('.channel-item');
    channelItems.forEach(item => {
        item.addEventListener('click', function() {
            // Remove active class from all channels
            channelItems.forEach(ch => ch.classList.remove('active'));
            // Add active class to clicked channel
            this.classList.add('active');
            
            // In a real app, this would load the channel's messages
            console.log('Switching to channel:', this.textContent.trim());
        });
    });
    
    // Server switching
    const serverItems = document.querySelectorAll('.server-item');
    serverItems.forEach(item => {
        item.addEventListener('click', function() {
            // Remove active class from all servers
            serverItems.forEach(s => s.classList.remove('active'));
            // Add active class to clicked server
            this.classList.add('active');
            
            // In a real app, this would load the server's channels
            console.log('Switching to server:', this.textContent.trim());
        });
    });
});

// Function to format timestamps
function formatTimestamp(dateString) {
    const date = new Date(dateString);
    return date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
}

// Function to scroll to bottom of message list
function scrollToBottom(element) {
    if (element) {
        element.scrollTop = element.scrollHeight;
    }
}

// Function to toggle channel list
function toggleChannels(serverId) {
    const channelList = document.getElementById(`channels-${serverId}`);
    channelList.style.display = channelList.style.display === 'none' ? 'block' : 'none';
}

// Update user status via AJAX
function updateStatus(status) {
    fetch('/status/update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status: status })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update status indicator in UI
            const statusElements = document.querySelectorAll('.status-indicator');
            statusElements.forEach(element => {
                element.className = 'status-indicator ' + getStatusClass(data.status);
            });
            
            // Close modal if open
            const modal = bootstrap.Modal.getInstance(document.getElementById('statusModal'));
            if (modal) {
                modal.hide();
            }
        }
    })
    .catch(error => {
        console.error('Error updating status:', error);
    });
}

// Helper function to get status class
function getStatusClass(status) {
    const statusClasses = {
        'online': 'status-online',
        'idle': 'status-idle',
        'dnd': 'status-dnd',
        'offline': 'status-offline'
    };
    return statusClasses[status] || 'status-offline';
}

// Simulate real-time updates (in a real app, this would use WebSockets)
function simulateRealTimeUpdates() {
    console.log('Simulating real-time updates...');
    // This would be replaced with actual WebSocket logic
}

// Placeholder for real-time updates
setInterval(() => {
    // This would be replaced with WebSocket logic in a real app
    console.log('Checking for new messages...');
}, 5000);   // This would be replaced with actual WebSocket logic

// Initialize when page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', simulateRealTimeUpdates);
} else {
    simulateRealTimeUpdates();
}

// ====================
// VOICE CHAT FUNCTIONALITY
// ====================

// Voice chat elements
const voiceChatContainer = document.getElementById('voice-chat-container');
const incomingCallContainer = document.getElementById('incoming-call');
const callStatus = document.getElementById('call-status');
const participantsList = document.getElementById('participants-list');
const callerName = document.getElementById('caller-name');

// Voice chat buttons
const closeVoiceChatBtn = document.getElementById('close-voice-chat');
const toggleMuteBtn = document.getElementById('toggle-mute');
const endCallBtn = document.getElementById('end-call');
const toggleSpeakerBtn = document.getElementById('toggle-speaker');
const acceptCallBtn = document.getElementById('accept-call');
const rejectCallBtn = document.getElementById('reject-call');

// WebRTC variables
let localStream = null;
let remoteStream = null;
let peerConnection = null;
let currentCall = null;
let isMuted = false;
let isSpeakerEnabled = true;

// SocketIO connection
const socket = io();

// Configuration for STUN servers
const configuration = {
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' }
    ]
};

// Initialize voice chat functionality
function initVoiceChat() {
    // Button event listeners
    if (closeVoiceChatBtn) {
        closeVoiceChatBtn.addEventListener('click', closeVoiceChat);
    }
    
    if (toggleMuteBtn) {
        toggleMuteBtn.addEventListener('click', toggleMute);
    }
    
    if (endCallBtn) {
        endCallBtn.addEventListener('click', endCall);
    }
    
    if (toggleSpeakerBtn) {
        toggleSpeakerBtn.addEventListener('click', toggleSpeaker);
    }
    
    if (acceptCallBtn) {
        acceptCallBtn.addEventListener('click', acceptCall);
    }
    
    if (rejectCallBtn) {
        rejectCallBtn.addEventListener('click', rejectCall);
    }
    
    // SocketIO event listeners
    socket.on('incoming_call', handleIncomingCall);
    socket.on('call_accepted', handleCallAccepted);
    socket.on('call_rejected', handleCallRejected);
    socket.on('call_ended', handleCallEnded);
    socket.on('offer', handleOffer);
    socket.on('answer', handleAnswer);
    socket.on('ice_candidate', handleIceCandidate);
    socket.on('user_joined', handleUserJoined);
    socket.on('user_left', handleUserLeft);
}

// Start a voice call with a user
function startVoiceCall(targetUserId, targetUsername) {
    currentCall = {
        targetUserId: targetUserId,
        targetUsername: targetUsername
    };
    
    updateCallStatus(`Calling ${targetUsername}...`);
    showVoiceChat();
    
    // Get user media
    navigator.mediaDevices.getUserMedia({ audio: true, video: false })
        .then(stream => {
            localStream = stream;
            setupLocalAudio();
            
            // Send call request
            socket.emit('voice_call', {
                target_user: targetUserId,
                username: getCurrentUsername()
            });
        })
        .catch(error => {
            console.error('Error accessing microphone:', error);
            updateCallStatus('Microphone access denied');
        });
}

// Handle incoming call
function handleIncomingCall(data) {
    currentCall = {
        callerId: data.user_id,
        callerUsername: data.username
    };
    
    callerName.textContent = `${data.username} is calling...`;
    incomingCallContainer.classList.remove('hidden');
}

// Accept incoming call
function acceptCall() {
    incomingCallContainer.classList.add('hidden');
    
    updateCallStatus(`Connected to ${currentCall.callerUsername}`);
    showVoiceChat();
    
    // Get user media
    navigator.mediaDevices.getUserMedia({ audio: true, video: false })
        .then(stream => {
            localStream = stream;
            setupLocalAudio();
            
            // Create peer connection
            createPeerConnection();
            
            // Send acceptance
            socket.emit('call_accepted', {
                target_user: currentCall.callerId
            });
            
            // Create offer
            peerConnection.createOffer()
                .then(offer => {
                    return peerConnection.setLocalDescription(offer);
                })
                .then(() => {
                    socket.emit('offer', {
                        offer: peerConnection.localDescription,
                        target_user: currentCall.callerId
                    });
                })
                .catch(error => {
                    console.error('Error creating offer:', error);
                });
        })
        .catch(error => {
            console.error('Error accessing microphone:', error);
            updateCallStatus('Microphone access denied');
        });
}

// Reject incoming call
function rejectCall() {
    incomingCallContainer.classList.add('hidden');
    
    if (currentCall && currentCall.callerId) {
        socket.emit('call_rejected', {
            target_user: currentCall.callerId
        });
    }
    
    currentCall = null;
}

// Handle call accepted
function handleCallAccepted(data) {
    updateCallStatus(`Connected to ${currentCall.targetUsername}`);
    
    // Create peer connection
    createPeerConnection();
}

// Handle call rejected
function handleCallRejected(data) {
    updateCallStatus(`${currentCall.targetUsername} rejected the call`);
    setTimeout(() => {
        closeVoiceChat();
    }, 3000);
}

// Handle call ended
function handleCallEnded(data) {
    updateCallStatus('Call ended');
    
    if (peerConnection) {
        peerConnection.close();
        peerConnection = null;
    }
    
    if (remoteStream) {
        remoteStream.getTracks().forEach(track => track.stop());
        remoteStream = null;
    }
    
    setTimeout(() => {
        closeVoiceChat();
    }, 2000);
}

// Create peer connection
function createPeerConnection() {
    peerConnection = new RTCPeerConnection(configuration);
    
    // Add local stream to peer connection
    if (localStream) {
        localStream.getTracks().forEach(track => {
            peerConnection.addTrack(track, localStream);
        });
    }
    
    // Handle incoming stream
    peerConnection.ontrack = event => {
        remoteStream = event.streams[0];
        setupRemoteAudio();
    };
    
    // Handle ICE candidates
    peerConnection.onicecandidate = event => {
        if (event.candidate) {
            socket.emit('ice_candidate', {
                candidate: event.candidate,
                target_user: currentCall.callerId || currentCall.targetUserId
            });
        }
    };
}

// Handle offer
function handleOffer(data) {
    if (!peerConnection) {
        createPeerConnection();
    }
    
    peerConnection.setRemoteDescription(new RTCSessionDescription(data.offer))
        .then(() => {
            return peerConnection.createAnswer();
        })
        .then(answer => {
            return peerConnection.setLocalDescription(answer);
        })
        .then(() => {
            socket.emit('answer', {
                answer: peerConnection.localDescription,
                target_user: data.user_id
            });
        })
        .catch(error => {
            console.error('Error handling offer:', error);
        });
}

// Handle answer
function handleAnswer(data) {
    peerConnection.setRemoteDescription(new RTCSessionDescription(data.answer))
        .catch(error => {
            console.error('Error handling answer:', error);
        });
}

// Handle ICE candidate
function handleIceCandidate(data) {
    if (peerConnection) {
        peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate))
            .catch(error => {
                console.error('Error adding ICE candidate:', error);
            });
    }
}

// Handle user joined voice room
function handleUserJoined(data) {
    // Add user to participants list
    addParticipant(data.user_id, 'Unknown User');
}

// Handle user left voice room
function handleUserLeft(data) {
    // Remove user from participants list
    removeParticipant(data.user_id);
}

// Setup local audio
function setupLocalAudio() {
    // In a real implementation, we would connect the local stream to an audio element
    // For now, we'll just log that it's working
    console.log('Local audio stream setup complete');
}

// Setup remote audio
function setupRemoteAudio() {
    // In a real implementation, we would connect the remote stream to an audio element
    // For now, we'll just log that it's working
    console.log('Remote audio stream setup complete');
}

// Toggle mute
function toggleMute() {
    if (localStream) {
        isMuted = !isMuted;
        localStream.getAudioTracks().forEach(track => {
            track.enabled = !isMuted;
        });
        
        // Update UI
        const icon = toggleMuteBtn.querySelector('i');
        if (isMuted) {
            icon.className = 'fas fa-microphone-slash';
            updateCallStatus('Microphone muted');
        } else {
            icon.className = 'fas fa-microphone';
            updateCallStatus('Microphone unmuted');
        }
    }
}

// Toggle speaker
function toggleSpeaker() {
    isSpeakerEnabled = !isSpeakerEnabled;
    
    // Update UI
    const icon = toggleSpeakerBtn.querySelector('i');
    if (isSpeakerEnabled) {
        icon.className = 'fas fa-volume-up';
        updateCallStatus('Speaker enabled');
    } else {
        icon.className = 'fas fa-volume-mute';
        updateCallStatus('Speaker disabled');
    }
}

// End call
function endCall() {
    if (currentCall) {
        socket.emit('end_call', {
            target_user: currentCall.callerId || currentCall.targetUserId
        });
    }
    
    cleanupCall();
    closeVoiceChat();
}

// Cleanup call resources
function cleanupCall() {
    if (peerConnection) {
        peerConnection.close();
        peerConnection = null;
    }
    
    if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
        localStream = null;
    }
    
    if (remoteStream) {
        remoteStream.getTracks().forEach(track => track.stop());
        remoteStream = null;
    }
    
    currentCall = null;
}

// Close voice chat UI
function closeVoiceChat() {
    voiceChatContainer.classList.add('hidden');
    updateCallStatus('Ready to connect');
    
    // Reset UI elements
    const muteIcon = toggleMuteBtn.querySelector('i');
    muteIcon.className = 'fas fa-microphone';
    
    const speakerIcon = toggleSpeakerBtn.querySelector('i');
    speakerIcon.className = 'fas fa-volume-up';
    
    isMuted = false;
    isSpeakerEnabled = true;
}

// Show voice chat UI
function showVoiceChat() {
    voiceChatContainer.classList.remove('hidden');
}

// Update call status
function updateCallStatus(message) {
    if (callStatus) {
        callStatus.innerHTML = `<p>${message}</p>`;
    }
}

// Add participant to list
function addParticipant(userId, username) {
    const participantElement = document.createElement('div');
    participantElement.id = `participant-${userId}`;
    participantElement.className = 'flex items-center space-x-2 p-2 rounded bg-dark';
    participantElement.innerHTML = `
        <i class="fas fa-circle text-online text-xs"></i>
        <span class="text-light">${username}</span>
    `;
    participantsList.appendChild(participantElement);
}

// Remove participant from list
function removeParticipant(userId) {
    const participantElement = document.getElementById(`participant-${userId}`);
    if (participantElement) {
        participantElement.remove();
    }
}

// Get current username (placeholder)
function getCurrentUsername() {
    // In a real implementation, this would get the current user's username
    return 'CurrentUser';
}

// Initialize voice chat when DOM is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initVoiceChat);
} else {
    initVoiceChat();
    
    // Initialize voice channel functionality
    initVoiceChannels();
}

// Initialize voice channel functionality
function initVoiceChannels() {
    // Add event listeners to voice channel buttons
    const voiceChannelButtons = document.querySelectorAll('.voice-channel-btn');
    
    voiceChannelButtons.forEach(button => {
        button.addEventListener('click', function() {
            const channelId = this.getAttribute('data-channel-id');
            const action = this.getAttribute('data-action');
            
            if (action === 'join') {
                joinVoiceChannel(channelId);
            }
        });
    });
}

// Join a voice channel
function joinVoiceChannel(channelId) {
    // Update UI to show user is in voice channel
    updateVoiceChannelButton(channelId, 'leave');
    
    // Join the SocketIO room for this channel
    socket.emit('join_voice_channel', {
        channel_id: channelId,
        username: getCurrentUsername()
    });
    
    // Show voice chat interface
    showVoiceChat();
    updateCallStatus(`Joined voice channel`);
}

// Leave a voice channel
function leaveVoiceChannel(channelId) {
    // Update UI to show user is not in voice channel
    updateVoiceChannelButton(channelId, 'join');
    
    // Leave the SocketIO room for this channel
    socket.emit('leave_voice_channel', {
        channel_id: channelId
    });
    
    // Hide voice chat interface
    closeVoiceChat();
}

// Update voice channel button UI
function updateVoiceChannelButton(channelId, action) {
    const button = document.querySelector(`.voice-channel-btn[data-channel-id="${channelId}"]`);
    
    if (button) {
        if (action === 'leave') {
            button.setAttribute('data-action', 'leave');
            button.innerHTML = '<i class="fas fa-phone-slash"></i>';
        } else {
            button.setAttribute('data-action', 'join');
            button.innerHTML = '<i class="fas fa-phone"></i>';
        }
    }
}

// Handle user joined voice channel
socket.on('user_joined_voice_channel', function(data) {
    addParticipant(data.user_id, data.username);
});

// Handle user left voice channel
socket.on('user_left_voice_channel', function(data) {
    removeParticipant(data.user_id);
});

// Handle channel offer
socket.on('channel_offer', function(data) {
    handleOffer(data);
});

// Handle channel answer
socket.on('channel_answer', function(data) {
    handleAnswer(data);
});

// Handle channel ICE candidate
socket.on('channel_ice_candidate', function(data) {
    handleIceCandidate(data);
});
