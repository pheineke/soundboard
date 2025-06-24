import os
import logging
import threading
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask_socketio import SocketIO, emit
import pygame

from normalize_audio import AudioNormalizer

# --- Config ---
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'wav', 'ogg', 'mp3'}

# --- Setup ---
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
socketio = SocketIO(app, cors_allowed_origins="*")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure uploads folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Pygame Mixer ---

DEVICE_NAME = "CABLE Input (VB-Audio Virtual Cable)" 

try:
    # Initialize the mixer on the specific virtual audio device
    pygame.mixer.init(devicename=DEVICE_NAME)
    logger.info(f"Pygame mixer initialized successfully on device: {DEVICE_NAME}")
except pygame.error as e:
    logger.error(f"Could not initialize Pygame mixer on specific device '{DEVICE_NAME}': {e}")
    logger.warning("Falling back to default audio device.")
    pygame.mixer.init() # Fallback to default if the specific one fails

sound_cache = {}
sound_cache_lock = threading.Lock()
playing_channels = {}  # filepath: channel


# --- Helpers ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_sound(filepath):
    with sound_cache_lock:
        if filepath not in sound_cache:
            try:
                sound_cache[filepath] = pygame.mixer.Sound(filepath)
                logger.info(f"Loaded sound: {filepath}")
            except Exception as e:
                logger.error(f"Failed to load sound: {e}")
                return None
        return sound_cache[filepath]


# --- Routes ---
@app.route('/', methods=['GET'])
def index():
    sound_files = [
        f for f in os.listdir(UPLOAD_FOLDER)
        if allowed_file(f)
    ]
    return render_template('index.html', sound_files=sound_files)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return redirect(url_for('index'))

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    AudioNormalizer().normalize_audio_file(filepath)

    logger.info(f"Uploaded file: {filepath}")
    return redirect(url_for('index'))

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# --- Socket.IO Events ---
@socketio.on('play-sound')
def handle_play_sound(filename):
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    logger.info(f"Toggling sound: {filepath}")

    if not os.path.exists(filepath):
        logger.error(f"Sound file not found: {filepath}")
        emit('error', {'message': 'Sound file not found'})
        return

    sound = load_sound(filepath)
    if not sound:
        emit('error', {'message': 'Failed to load sound'})
        return

    with sound_cache_lock:
        current_channel = playing_channels.get(filepath)
        if current_channel and current_channel.get_busy():
            logger.info(f"Stopping sound: {filepath}")
            current_channel.stop()
            del playing_channels[filepath]
            emit('sound-stopped', filename, broadcast=True)
        else:
            try:
                # adjust volume if needed
                sound.set_volume(0.35)  # Set volume to 50%
                channel = sound.play()
                if channel:
                    playing_channels[filepath] = channel
                    logger.info(f"Started playing: {filepath}")
                    emit('sound-played', filename, broadcast=True)
                else:
                    emit('error', {'message': 'No available channel to play sound'})
            except Exception as e:
                logger.error(f"Error playing sound: {e}")
                emit('error', {'message': f'Error playing sound: {str(e)}'})


# --- Start ---
if __name__ == '__main__':
    logger.info("Server running at http://127.0.0.1:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
