use actix_files::NamedFile;
use actix_web::{web, guard, App, HttpServer, HttpResponse, Result, Error};
use actix_web::middleware::Logger;
use actix_web::web::Json;
use actix_web::web::Bytes;
use actix_rt::System;
use rodio::{Decoder, OutputStream, source::Source};
use std::fs::{File, create_dir_all};
use std::sync::{Arc, Mutex};
use std::path::Path;
use std::io::Cursor;
use std::io::Write;
use std::collections::HashMap;
use futures_util::StreamExt;
use tokio::sync::broadcast;
use std::io::{Seek, Read};
use rodio::Sink;

// --- Config ---
const UPLOAD_FOLDER: &str = "uploads";
const ALLOWED_EXTENSIONS: [&str; 3] = ["wav", "ogg", "mp3"];

// --- Global Variables ---
lazy_static::lazy_static! {
    static ref SOUND_CACHE: Arc<Mutex<HashMap<String, rodio::Decoder<Cursor<Vec<u8>>>>>> = Arc::new(Mutex::new(HashMap::new()));
    static ref PLAYING_CHANNELS: Arc<Mutex<HashMap<String, rodio::Sink>>> = Arc::new(Mutex::new(HashMap::new()));
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Ensure uploads folder exists
    create_dir_all(UPLOAD_FOLDER).unwrap();

    // Setup the server
    HttpServer::new(|| {
        App::new()
            .wrap(Logger::default())
            .route("/", web::get().to(index))
            .route("/upload", web::post().to(upload_file))
            .route("/uploads/{filename}", web::get().to(uploaded_file))
            .route("/play_sound", web::post().to(play_sound))
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}

async fn index() -> Result<HttpResponse> {
    let sound_files: Vec<String> = std::fs::read_dir(UPLOAD_FOLDER)?
        .filter_map(|entry| {
            if let Ok(entry) = entry {
                if let Some(extension) = entry.path().extension() {
                    if ALLOWED_EXTENSIONS.contains(&extension.to_str().unwrap()) {
                        return Some(entry.file_name().to_str().unwrap().to_string());
                    }
                }
            }
            None
        })
        .collect();

    Ok(HttpResponse::Ok().json(sound_files))
}

async fn upload_file(mut payload: web::Payload) -> Result<HttpResponse, Error> {
    let mut body = web::BytesMut::new();
    while let Some(Ok(chunk)) = payload.next().await {
        body.extend_from_slice(&chunk);
    }

    let file_name = "uploaded_file"; // Get from the file metadata
    let file_path = format!("{}/{}", UPLOAD_FOLDER, file_name);

    let mut file = File::create(file_path.clone()).unwrap();
    file.write_all(&body)?;

    // Normalization can be done here (you can implement a Rust version of the normalizer)

    Ok(HttpResponse::Found()
        .header("LOCATION", "/")
        .finish())
}

async fn uploaded_file(path: web::Path<String>) -> Result<NamedFile> {
    let filename = path.into_inner();
    let path = format!("{}/{}", UPLOAD_FOLDER, filename);
    Ok(NamedFile::open(path)?)
}

#[derive(serde::Deserialize)]
struct PlaySoundData {
    filename: String,
}

async fn play_sound(info: web::Json<PlaySoundData>) -> Result<HttpResponse> {
    let filename = &info.filename;
    let file_path = format!("{}/{}", UPLOAD_FOLDER, filename);

    if !Path::new(&file_path).exists() {
        return Ok(HttpResponse::BadRequest().body("Sound file not found"));
    }

    // Load sound
    let sound = load_sound(file_path.clone()).await;
    if sound.is_none() {
        return Ok(HttpResponse::InternalServerError().body("Failed to load sound"));
    }

    let sound = sound.unwrap();
    let (_stream, stream_handle) = OutputStream::try_default().unwrap();
    let sink = Sink::try_new(&stream_handle).unwrap();

    sink.append(sound);
    sink.play();

    // Optionally, manage the playing channels (stop the previous sound if playing)
    let mut channels = PLAYING_CHANNELS.lock().unwrap();
    if let Some(existing_channel) = channels.remove(filename) {
        existing_channel.stop();
    }
    channels.insert(filename.clone(), sink);

    Ok(HttpResponse::Ok().body("Playing sound"))
}

async fn load_sound(file_path: String) -> Option<rodio::Decoder<Cursor<Vec<u8>>>> {
    let mut file = File::open(&file_path).ok()?;
    file.seek(std::io::SeekFrom::Start(0)).ok()?;

    let mut buffer = Vec::new();
    file.read_to_end(&mut buffer).ok()?;

    let cursor = Cursor::new(buffer);
    Decoder::new(cursor).ok()
}
