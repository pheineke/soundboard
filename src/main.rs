use actix_files::Files;
use actix_multipart::Multipart;
use actix_web::{web, App, Error, HttpRequest, HttpResponse, HttpServer, Responder};
use actix_web_actors::ws;
use actix::{Actor, ActorContext, StreamHandler};
use futures::{StreamExt, TryStreamExt};
use log::{error, info};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs::{self, File};
use std::io::Write;
use std::path::Path;
use std::sync::{Arc, Mutex};
use std::thread;
use std::sync::mpsc;
use std::time::Duration;

// --- Config ---
const UPLOAD_FOLDER: &str = "uploads";
const ALLOWED_EXTENSIONS: [&str; 3] = ["wav", "ogg", "mp3"];

// --- Types ---
#[derive(Debug, Clone, Serialize, Deserialize)]
struct SoundMessage {
    action: String,
    filename: String,
}

// Audio command enum for the audio player thread
enum AudioCommand {
    Play(String),
    Stop(String),
    Quit,
}

// Audio player state handling
struct AudioState {
    command_sender: mpsc::Sender<AudioCommand>,
    playing_files: HashMap<String, bool>,
}

impl AudioState {
    fn new() -> Self {
        // Create a channel for sending commands to the audio thread
        let (tx, rx) = mpsc::channel::<AudioCommand>();
        
        // Spawn an audio player thread that handles playback
        thread::spawn(move || {
            let mut active_sounds: HashMap<String, Option<rodio::Sink>> = HashMap::new();
            
            loop {
                // Check for new commands
                match rx.recv() {
                    Ok(AudioCommand::Play(filepath)) => {
                        info!("Audio thread: Playing {}", filepath);
                        
                        // If sound is already playing, stop it first
                        if let Some(Some(sink)) = active_sounds.get(&filepath) {
                            sink.stop();
                            active_sounds.remove(&filepath);
                        }
                        
                        // Setup audio playback
                        match play_sound_file(&filepath) {
                            Ok(sink) => {
                                active_sounds.insert(filepath, Some(sink));
                            },
                            Err(e) => {
                                error!("Failed to play sound: {}", e);
                                active_sounds.insert(filepath, None); // Mark as not playing
                            }
                        }
                    },
                    Ok(AudioCommand::Stop(filepath)) => {
                        info!("Audio thread: Stopping {}", filepath);
                        if let Some(Some(sink)) = active_sounds.get(&filepath) {
                            sink.stop();
                        }
                        active_sounds.remove(&filepath);
                    },
                    Ok(AudioCommand::Quit) => {
                        info!("Audio thread: Shutting down");
                        // Stop all playing sounds
                        for (_, sink_opt) in active_sounds.iter() {
                            if let Some(sink) = sink_opt {
                                sink.stop();
                            }
                        }
                        break;
                    },
                    Err(e) => {
                        error!("Audio thread: Channel error: {}", e);
                        break;
                    }
                }
                
                // Short sleep to prevent busy-waiting
                thread::sleep(Duration::from_millis(10));
            }
        });
        
        Self {
            command_sender: tx,
            playing_files: HashMap::new(),
        }
    }

    fn toggle_sound(&mut self, filename: &str) -> bool {
        let filepath = Path::new(UPLOAD_FOLDER).join(filename);
        let filepath_str = filepath.to_string_lossy().to_string();
        
        // Check if the sound is currently playing
        let is_playing = self.playing_files.get(&filepath_str).copied().unwrap_or(false);
        
        if is_playing {
            // Stop the sound
            if let Err(e) = self.command_sender.send(AudioCommand::Stop(filepath_str.clone())) {
                error!("Failed to send stop command: {}", e);
            }
            self.playing_files.insert(filepath_str, false);
            false // Sound was stopped
        } else {
            // Start playing the sound
            if let Err(e) = self.command_sender.send(AudioCommand::Play(filepath_str.clone())) {
                error!("Failed to send play command: {}", e);
            }
            self.playing_files.insert(filepath_str, true);
            true // Sound was started
        }
    }
}

impl Drop for AudioState {
    fn drop(&mut self) {
        // Send quit command when AudioState is dropped
        let _ = self.command_sender.send(AudioCommand::Quit);
    }
}

struct WsSession {
    audio_state: Arc<Mutex<AudioState>>,
}

impl Actor for WsSession {
    type Context = ws::WebsocketContext<Self>;
}

impl StreamHandler<Result<ws::Message, ws::ProtocolError>> for WsSession {
    fn handle(&mut self, msg: Result<ws::Message, ws::ProtocolError>, ctx: &mut Self::Context) {
        match msg {
            Ok(ws::Message::Text(text)) => {
                match serde_json::from_str::<SoundMessage>(&text) {
                    Ok(sound_msg) => {
                        if sound_msg.action == "play-sound" {
                            let filename = sound_msg.filename;
                            let mut audio_state = self.audio_state.lock().unwrap();
                            let started = audio_state.toggle_sound(&filename);
                            
                            let response = if started {
                                SoundMessage { action: "sound-played".to_string(), filename: filename.clone() }
                            } else {
                                SoundMessage { action: "sound-stopped".to_string(), filename: filename.clone() }
                            };
                            let response_json = serde_json::to_string(&response).unwrap();
                            ctx.text(response_json);
                        }
                    },
                    Err(e) => {
                        error!("Failed to parse WebSocket message: {}", e);
                        ctx.text("{\"action\": \"error\", \"message\": \"Invalid message format\"}");
                    }
                }
            },
            Ok(ws::Message::Ping(msg)) => ctx.pong(&msg),
            Ok(ws::Message::Pong(_)) => (),
            Ok(ws::Message::Binary(_)) => ctx.text("{\"action\": \"error\", \"message\": \"Binary messages not supported\"}"),
            Ok(ws::Message::Close(reason)) => {
                ctx.close(reason);
                ctx.stop();
            },
            Ok(ws::Message::Continuation(_)) => ctx.text("{\"action\": \"error\", \"message\": \"Continuation messages not supported\"}"),
            Ok(ws::Message::Nop) => (),
            Err(e) => {
                error!("WebSocket protocol error: {}", e);
                ctx.stop();
            }
        }
    }
}

// --- Helpers ---
fn is_allowed_file(filename: &str) -> bool {
    if let Some(ext) = Path::new(filename).extension() {
        if let Some(ext_str) = ext.to_str() {
            return ALLOWED_EXTENSIONS.contains(&ext_str.to_lowercase().as_str());
        }
    }
    false
}

// Function to play a sound file and return the sink for controlling playback
fn play_sound_file(filepath: &str) -> Result<rodio::Sink, String> {
    // Get a output stream handle to the default physical sound device
    let (_stream, stream_handle) = rodio::OutputStream::try_default()
        .map_err(|e| format!("Failed to get audio output device: {}", e))?;
    
    // Load the sound file
    let file = File::open(filepath)
        .map_err(|e| format!("Failed to open sound file: {}", e))?;
    
    let source = rodio::Decoder::new(std::io::BufReader::new(file))
        .map_err(|e| format!("Failed to decode audio file: {}", e))?;
    
    // Create a sink to play the sound
    let sink = rodio::Sink::try_new(&stream_handle)
        .map_err(|e| format!("Failed to create audio sink: {}", e))?;
    
    // Set volume (0.0 to 1.0)
    sink.set_volume(0.5);
    
    // Add the source to the sink
    sink.append(source);
    
    Ok(sink)
}

// --- Audio Normalization ---
fn normalize_audio_file(filepath: &Path) -> Result<(), String> {
    // NOTE: Audio normalization would typically be implemented using a proper audio processing library
    info!("Audio normalization would be applied to: {}", filepath.display());
    Ok(())
}

// --- Routes ---
async fn index() -> impl Responder {
    let files = match fs::read_dir(UPLOAD_FOLDER) {
        Ok(entries) => {
            let mut sound_files = Vec::new();
            for entry in entries {
                if let Ok(entry) = entry {
                    if let Some(filename) = entry.file_name().to_str() {
                        if is_allowed_file(filename) {
                            sound_files.push(filename.to_string());
                        }
                    }
                }
            }
            sound_files
        },
        Err(e) => {
            error!("Failed to read upload directory: {}", e);
            Vec::new()
        }
    };

    let files_json = serde_json::to_string(&files).unwrap_or_else(|_| "[]".to_string());
    let html = format!(
        r#"<!DOCTYPE html>
<html>
<head>
    <title>Sound Board</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .sound-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 10px;
            margin-top: 20px;
        }}
        .sound-button {{
            padding: 15px;
            background-color: #4CAF50;
            color: white;
            text-align: center;
            cursor: pointer;
            border: none;
            border-radius: 5px;
        }}
        .sound-button.playing {{
            background-color: #f44336;
        }}
        .upload-form {{
            margin: 20px 0;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }}
    </style>
</head>
<body>
    <h1>Sound Board</h1>
    
    <div class="upload-form">
        <h2>Upload New Sound</h2>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".wav,.mp3,.ogg">
            <button type="submit">Upload</button>
        </form>
    </div>
    
    <h2>Available Sounds</h2>
    <div class="sound-grid" id="soundGrid"></div>
    
    <script>
        const soundFiles = {files_json};
        const ws = new WebSocket(`${{window.location.protocol === 'https:' ? 'wss' : 'ws'}}://${{window.location.host}}/ws`);
        
        ws.onopen = () => console.log('WebSocket connected');
        ws.onclose = () => console.log('WebSocket disconnected');
        ws.onerror = (error) => console.error('WebSocket error:', error);
        
        ws.onmessage = (event) => {{
            const data = JSON.parse(event.data);
            console.log('WebSocket message:', data);
            
            if (data.action === 'sound-played') {{
                const button = document.querySelector(`[data-filename="${{data.filename}}"]`);
                if (button) button.classList.add('playing');
            }} else if (data.action === 'sound-stopped') {{
                const button = document.querySelector(`[data-filename="${{data.filename}}"]`);
                if (button) button.classList.remove('playing');
            }} else if (data.action === 'error') {{
                alert(`Error: ${{data.message}}`);
            }}
        }};
        
        function toggleSound(filename) {{
            ws.send(JSON.stringify({{
                action: 'play-sound',
                filename: filename
            }}));
        }}
        
        function populateSoundGrid() {{
            const grid = document.getElementById('soundGrid');
            grid.innerHTML = '';
            
            soundFiles.forEach(filename => {{
                const button = document.createElement('button');
                button.className = 'sound-button';
                button.textContent = filename;
                button.setAttribute('data-filename', filename);
                button.onclick = () => toggleSound(filename);
                grid.appendChild(button);
            }});
        }}
        
        window.onload = populateSoundGrid;
    </script>
</body>
</html>"#
    );
    
    HttpResponse::Ok().content_type("text/html").body(html)
}

async fn upload_file(mut payload: Multipart) -> Result<HttpResponse, Error> {
    // Make sure upload directory exists
    if let Err(e) = fs::create_dir_all(UPLOAD_FOLDER) {
        error!("Failed to create upload directory: {}", e);
        return Ok(HttpResponse::InternalServerError().body("Failed to create upload directory"));
    }
    
    while let Ok(Some(mut field)) = payload.try_next().await {
        let content_disposition = field.content_disposition();
        let filename = match content_disposition.get_filename() {
            Some(name) => name.to_string(),
            None => continue,
        };
        
        if !is_allowed_file(&filename) {
            continue;
        }
        
        let filepath = Path::new(UPLOAD_FOLDER).join(&filename);
        let filepath_str = filepath.to_string_lossy().to_string();
        info!("Saving file to: {}", filepath_str);
        
        // Create file
        let mut file = match File::create(&filepath) {
            Ok(file) => file,
            Err(e) => {
                error!("Failed to create file: {}", e);
                return Ok(HttpResponse::InternalServerError().body("Failed to create file"));
            }
        };
        
        // Write file - fixed to handle the moved value issue
        while let Some(chunk) = field.next().await {
            let data = match chunk {
                Ok(data) => data,
                Err(e) => {
                    error!("Error while uploading file: {}", e);
                    return Ok(HttpResponse::InternalServerError().body("Failed to upload file"));
                }
            };
            
            // Write chunk directly to file instead of using web::block and move
            if let Err(e) = file.write_all(&data) {
                error!("Failed to write file chunk: {}", e);
                return Ok(HttpResponse::InternalServerError().body("Failed to write file"));
            }
        }
        
        // Normalize audio file
        if let Err(e) = normalize_audio_file(&filepath) {
            error!("Failed to normalize audio: {}", e);
        }
    }
    
    Ok(HttpResponse::Found().append_header(("location", "/")).finish())
}

async fn websocket(req: HttpRequest, stream: web::Payload, data: web::Data<AppState>) -> Result<HttpResponse, Error> {
    let audio_state = data.audio_state.clone();
    ws::start(
        WsSession { audio_state },
        &req,
        stream
    )
}

// App state with thread-safe audio state
struct AppState {
    audio_state: Arc<Mutex<AudioState>>,
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init_from_env(env_logger::Env::default().default_filter_or("info"));
    
    // Make sure upload directory exists
    fs::create_dir_all(UPLOAD_FOLDER)?;
    
    // Initialize audio state
    let audio_state = Arc::new(Mutex::new(AudioState::new()));
    let app_state = web::Data::new(AppState {
        audio_state: audio_state.clone(),
    });
    
    info!("Server running at http://127.0.0.1:5000");
    
    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .service(web::resource("/").to(index))
            .service(web::resource("/upload").route(web::post().to(upload_file)))
            .service(Files::new("/uploads", UPLOAD_FOLDER))
            .service(web::resource("/ws").route(web::get().to(websocket)))
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}