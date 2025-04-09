use actix_files::Files;
use actix_multipart::Multipart;
use actix_web::{web, App, Error, HttpRequest, HttpResponse, HttpServer, Responder};
use actix_web_actors::ws;
use futures::{StreamExt, TryStreamExt};
use log::{error, info};
use rodio::{Decoder, OutputStream, OutputStreamHandle, Sink, Source};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs::{self, File};
use std::io::BufReader;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use actix::{Actor, StreamHandler};

// --- Config ---
const UPLOAD_FOLDER: &str = "uploads";
const ALLOWED_EXTENSIONS: [&str; 3] = ["wav", "ogg", "mp3"];

// --- Types ---
#[derive(Debug, Clone, Serialize, Deserialize)]
struct SoundMessage {
    action: String,
    filename: String,
}

struct AppState {
    sound_manager: Arc<Mutex<SoundManager>>,
}

struct SoundManager {
    _stream: OutputStream,
    stream_handle: OutputStreamHandle,
    playing_sinks: HashMap<String, Sink>,
}

struct WsSession {
    sound_manager: Arc<Mutex<SoundManager>>,
}

impl SoundManager {
    fn new() -> Self {
        let (stream, stream_handle) = OutputStream::try_default().expect("Failed to get audio output device");
        Self {
            _stream: stream,
            stream_handle,
            playing_sinks: HashMap::new(),
        }
    }

    fn toggle_sound(&mut self, filename: &str) -> Result<bool, String> {
        let filepath = Path::new(UPLOAD_FOLDER).join(filename);
        let filepath_str = filepath.to_string_lossy().to_string();
        
        // Check if sound is already playing
        if let Some(sink) = self.playing_sinks.get(&filepath_str) {
            sink.stop();
            self.playing_sinks.remove(&filepath_str);
            info!("Stopped sound: {}", filepath_str);
            return Ok(false); // Sound was stopped
        }
        
        // Play the sound
        match File::open(&filepath) {
            Ok(file) => {
                let reader = BufReader::new(file);
                match Decoder::new(reader) {
                    Ok(source) => {
                        let sink = Sink::try_new(&self.stream_handle).map_err(|e| format!("Failed to create audio sink: {}", e))?;
                        sink.set_volume(0.25); // Set volume to 25%
                        sink.append(source);
                        self.playing_sinks.insert(filepath_str.clone(), sink);
                        info!("Started playing: {}", filepath_str);
                        Ok(true) // Sound was started
                    },
                    Err(e) => Err(format!("Failed to decode audio: {}", e)),
                }
            },
            Err(e) => Err(format!("Failed to open file: {}", e)),
        }
    }
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
                            let mut sound_manager = self.sound_manager.lock().unwrap();
                            match sound_manager.toggle_sound(&filename) {
                                Ok(started) => {
                                    let response = if started {
                                        SoundMessage { action: "sound-played".to_string(), filename: filename.clone() }
                                    } else {
                                        SoundMessage { action: "sound-stopped".to_string(), filename: filename.clone() }
                                    };
                                    let response_json = serde_json::to_string(&response).unwrap();
                                    ctx.text(response_json);
                                },
                                Err(e) => {
                                    error!("Error toggling sound: {}", e);
                                    ctx.text(format!("{{\"action\": \"error\", \"message\": \"{}\"}}", e));
                                }
                            }
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

// --- Audio Normalization ---
fn normalize_audio_file(filepath: &Path) -> Result<(), String> {
    // NOTE: Audio normalization would typically be implemented using a proper audio processing library
    // For simplicity, we're just logging that normalization would happen here
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
        let mut file = match fs::File::create(&filepath) {
            Ok(file) => file,
            Err(e) => {
                error!("Failed to create file: {}", e);
                return Ok(HttpResponse::InternalServerError().body("Failed to create file"));
            }
        };
        
        // Write file
        while let Some(chunk) = field.next().await {
            let data = match chunk {
                Ok(data) => data,
                Err(e) => {
                    error!("Error while uploading file: {}", e);
                    return Ok(HttpResponse::InternalServerError().body("Failed to upload file"));
                }
            };
            if let Err(e) = web::block(move || std::io::copy(&mut data.as_ref(), &mut file)).await {
                error!("Failed to write file: {}", e);
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
    let sound_manager = data.sound_manager.clone();
    ws::start(
        WsSession { sound_manager },
        &req,
        stream
    )
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init_from_env(env_logger::Env::default().default_filter_or("info"));
    
    // Make sure upload directory exists
    fs::create_dir_all(UPLOAD_FOLDER)?;
    
    // Initialize sound manager
    let sound_manager = Arc::new(Mutex::new(SoundManager::new()));
    let app_state = web::Data::new(AppState {
        sound_manager: sound_manager.clone(),
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