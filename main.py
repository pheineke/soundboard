# app.py
from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
import os
import pygame
from werkzeug.utils import secure_filename
import threading
import logging
import time
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app and SocketIO
app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'soundboard_secret'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB max upload
socketio = SocketIO(app, cors_allowed_origins="*")

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize pygame mixer for audio playback
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
pygame.init()

# Set mixer parameters
pygame.mixer.set_num_channels(32)  # Allow up to 32 sounds to play simultaneously

# Dictionary to keep track of loaded sounds
sound_cache = {}
sound_cache_lock = threading.Lock()

# Route for serving the main application
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

# Route to get list of available sounds
@app.route('/api/sounds', methods=['GET'])
def get_sounds():
    try:
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        sounds = []
        for file in files:
            if file.lower().endswith('.mp3'):
                name = file.rsplit('.', 1)[0]
                # Remove timestamp prefix if it exists
                if '-' in name and name.split('-')[0].isdigit():
                    name = '-'.join(name.split('-')[1:])
                sounds.append({
                    'id': file,
                    'name': name,
                    'path': f'/uploads/{file}'
                })
        return jsonify(sounds)
    except Exception as e:
        logger.error(f"Error getting sounds: {e}")
        return jsonify({"error": str(e)}), 500

# Route for handling file uploads
@app.route('/api/upload', methods=['POST'])
def upload_sound():
    if 'sound' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['sound']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and file.filename.lower().endswith('.mp3'):
        try:
            filename = f"{int(time.time())}-{secure_filename(file.filename)}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            sound_info = {
                'id': filename,
                'name': os.path.splitext(os.path.basename(file.filename))[0],
                'path': f'/uploads/{filename}'
            }
            
            # Notify all clients about the new sound
            socketio.emit('new-sound', sound_info)
            
            return jsonify(sound_info), 200
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "Only MP3 files are allowed"}), 400

# Route for serving uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def load_sound(file_path):
    """Load a sound file and return a pygame Sound object."""
    with sound_cache_lock:
        if file_path in sound_cache:
            return sound_cache[file_path]
        
        try:
            # Load the sound
            sound = pygame.mixer.Sound(file_path)
            # Store in cache
            sound_cache[file_path] = sound
            return sound
        except Exception as e:
            logger.error(f"Error loading sound {file_path}: {e}")
            return None

# SocketIO event for playing a sound
@socketio.on('play-sound')
def handle_play_sound(sound_path):
    # Extract the filename from the path
    filename = os.path.basename(sound_path.replace('/uploads/', ''))
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    logger.info(f"Playing sound: {filepath}")
    
    if os.path.exists(filepath):
        # Load the sound (from cache if available)
        sound = load_sound(filepath)
        
        if sound:
            try:
                # Play the sound on an available channel
                channel = sound.play()
                # Notify all clients that sound is being played
                emit('sound-played', sound_path, broadcast=True)
            except Exception as e:
                logger.error(f"Error playing sound: {e}")
                emit('error', {'message': f'Error playing sound: {str(e)}'})
        else:
            emit('error', {'message': 'Failed to load sound'})
    else:
        logger.error(f"Sound file not found: {filepath}")
        emit('error', {'message': 'Sound file not found'})

@socketio.on('connect')
def handle_connect():
    logger.info(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")

if __name__ == '__main__':
    logger.info("Starting soundboard server...")
    
    # Create static folder if it doesn't exist
    os.makedirs('static', exist_ok=True)
    
    # Create default index.html if it doesn't exist
    index_path = os.path.join('static', 'index.html')
    if not os.path.exists(index_path):
        with open(index_path, 'w') as f:
            f.write('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Python Soundboard</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        
        h1 {
            text-align: center;
            color: #333;
        }
        
        .upload-section {
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        .upload-form {
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }
        
        .upload-form input[type="file"] {
            flex: 1;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        
        .upload-form button {
            padding: 8px 16px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        
        .upload-form button:hover {
            background-color: #45a049;
        }
        
        .sounds-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
        }
        
        .sound-button {
            background-color: #3498db;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 20px 10px;
            font-size: 16px;
            cursor: pointer;
            text-align: center;
            transition: all 0.3s;
            height: 80px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            word-break: break-word;
            position: relative;
        }
        
        .sound-button:hover {
            background-color: #2980b9;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
        
        .sound-button.playing {
            background-color: #e74c3c;
            transform: scale(0.98);
        }
        
        .status-message {
            text-align: center;
            margin: 20px 0;
            color: #555;
            font-style: italic;
        }
        
        .loading-indicator {
            display: none;
            text-align: center;
            margin: 10px 0;
        }
        
        .spinner {
            border: 4px solid rgba(0, 0, 0, 0.1);
            width: 36px;
            height: 36px;
            border-radius: 50%;
            border-left-color: #09f;
            margin: 0 auto;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        @media (max-width: 600px) {
            .upload-form {
                flex-direction: column;
            }
            
            .sounds-grid {
                grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            }
        }
    </style>
</head>
<body>
    <h1>Python Soundboard</h1>
    
    <div class="upload-section">
        <h2>Add New Sound</h2>
        <form id="upload-form" class="upload-form">
            <input type="file" id="sound-file" accept="audio/mpeg" required>
            <button type="submit">Upload Sound</button>
        </form>
        <div class="loading-indicator" id="loading-indicator">
            <div class="spinner"></div>
            <p>Uploading sound...</p>
        </div>
    </div>
    
    <div id="sounds-container" class="sounds-grid"></div>
    
    <p class="status-message" id="status-message">No sounds yet. Upload an MP3 to get started!</p>
    
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script>
        // Connect to the server
        const socket = io();
        
        // DOM elements
        const uploadForm = document.getElementById('upload-form');
        const soundsContainer = document.getElementById('sounds-container');
        const statusMessage = document.getElementById('status-message');
        const loadingIndicator = document.getElementById('loading-indicator');
        
        // Load existing sounds when the page loads
        window.addEventListener('DOMContentLoaded', loadSounds);
        
        // Handle form submission
        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const fileInput = document.getElementById('sound-file');
            const file = fileInput.files[0];
            
            if (!file) {
                alert('Please select a sound file');
                return;
            }
            
            // Show loading indicator
            loadingIndicator.style.display = 'block';
            
            // Create form data for upload
            const formData = new FormData();
            formData.append('sound', file);
            
            try {
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || 'Upload failed');
                }
                
                // Reset form
                fileInput.value = '';
            } catch (error) {
                alert('Error uploading sound: ' + error.message);
            } finally {
                // Hide loading indicator
                loadingIndicator.style.display = 'none';
            }
        });
        
        // Load existing sounds from the server
        async function loadSounds() {
            try {
                const response = await fetch('/api/sounds');
                const sounds = await response.json();
                
                if (sounds.length === 0) {
                    statusMessage.textContent = 'No sounds yet. Upload an MP3 to get started!';
                    statusMessage.style.display = 'block';
                } else {
                    statusMessage.style.display = 'none';
                    renderSounds(sounds);
                }
            } catch (error) {
                console.error('Error loading sounds:', error);
                statusMessage.textContent = 'Failed to load sounds. Please refresh the page.';
            }
        }
        
        // Render sound buttons
        function renderSounds(sounds) {
            sounds.forEach(sound => addSoundButton(sound));
        }
        
        // Add a new sound button to the grid
        function addSoundButton(sound) {
            // Check if button already exists
            if (document.getElementById(`sound-${sound.id}`)) {
                return;
            }
            
            const button = document.createElement('button');
            button.id = `sound-${sound.id}`;
            button.className = 'sound-button';
            button.textContent = sound.name;
            button.dataset.path = sound.path;
            
            button.addEventListener('click', function() {
                socket.emit('play-sound', sound.path);
                
                // Add visual feedback
                button.classList.add('playing');
                setTimeout(() => {
                    button.classList.remove('playing');
                }, 500);
            });
            
            soundsContainer.appendChild(button);
            statusMessage.style.display = 'none';
        }
        
        // Socket events
        socket.on('new-sound', (sound) => {
            addSoundButton(sound);
        });
        
        socket.on('sound-played', (soundPath) => {
            // Find the button for this sound
            const buttons = document.querySelectorAll('.sound-button');
            
            buttons.forEach(button => {
                if (button.dataset.path === soundPath) {
                    // Add playing class for visual feedback
                    button.classList.add('playing');
                    
                    // Remove the class after animation completes
                    setTimeout(() => {
                        button.classList.remove('playing');
                    }, 500);
                }
            });
        });
        
        socket.on('error', (data) => {
            console.error('Error:', data.message);
            alert('Error: ' + data.message);
        });
    </script>
</body>
</html>
            ''')
    
    # Start the server
    host = "0.0.0.0"  # Listen on all interfaces
    port = 3000
    logger.info(f"Soundboard server running at http://localhost:{port}")
    logger.info(f"Access on other devices using your computer's IP address")
    socketio.run(app, host=host, port=port, debug=True, allow_unsafe_werkzeug=True)