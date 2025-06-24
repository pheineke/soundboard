# Soundboard - Go Version

A web-based soundboard application written in Go that allows you to upload, organize, and play audio files through a modern web interface.

## Features

- 🎵 **Audio Playback**: Play/stop audio files with a single click
- 📁 **File Upload**: Upload MP3, WAV, and OGG files
- 🎨 **Modern UI**: Clean, responsive design with dark theme
- ✏️ **Edit Mode**: Rearrange buttons and change their colors
- 🔄 **Real-time Updates**: WebSocket-based communication for instant updates
- 💾 **Persistent Layout**: Remembers your button arrangement

## Quick Start

### Method 1: Run the Executable (Easiest)

1. **Build the application**:

   ```bash
   # Double-click build.bat or run in terminal:
   build.bat
   ```

2. **Run the soundboard**:

   ```bash
   # Double-click run.bat or run in terminal:
   run.bat
   ```

3. **Open in browser**:
   - Navigate to `http://localhost:5000`

### Method 2: Manual Build

1. **Install Go** (if not installed):

   - Download from [golang.org](https://golang.org/downloads/)

2. **Install dependencies**:

   ```bash
   go mod tidy
   ```

3. **Build and run**:
   ```bash
   go build -o soundboard.exe main.go
   ./soundboard.exe
   ```

## Usage

### Uploading Sounds

1. Click the upload button (📁) in the top-right corner
2. Select an audio file (MP3, WAV, or OGG)
3. Click "Upload"

### Playing Sounds

- Click any sound button to play/stop the audio
- Only one sound can play at a time
- Green buttons indicate currently playing sounds

### Edit Mode

1. Click the edit button (✏️) in the top-right corner
2. **Rearrange**: Drag and drop buttons to reorder them
3. **Change Colors**: Click buttons to cycle through different colors
4. Click the save button (💾) to exit edit mode

## File Structure

```
soundboard/
├── main.go              # Main Go application
├── go.mod              # Go module file
├── templates/
│   └── index_go.html   # HTML template for Go version
├── static/
│   └── icons/          # UI icons
├── uploads/            # Uploaded audio files
├── build.bat           # Windows build script
└── run.bat             # Windows run script
```

## Technical Details

### Dependencies

- **Gin**: Web framework for Go
- **Gorilla WebSocket**: WebSocket implementation
- **Oto**: Audio playback library
- **go-mp3**: MP3 decoding

### Audio Support

- **MP3**: Full support with go-mp3 decoder
- **WAV/OGG**: Basic support (raw audio data)

### Browser Compatibility

- Chrome/Edge: Full support
- Firefox: Full support
- Safari: WebSocket and audio support

## Differences from Python Version

### Advantages ✅

- **Single Executable**: No Python/pip dependencies required
- **Faster Startup**: Compiled binary starts immediately
- **Lower Memory**: More efficient memory usage
- **Cross-platform**: Easy to build for different operating systems

### Limitations ⚠️

- **Audio Normalization**: Not implemented (Python version uses pydub)
- **Device Selection**: Uses default audio device only
- **Codec Support**: Limited compared to pygame/pydub

## Building for Different Platforms

```bash
# Windows
GOOS=windows GOARCH=amd64 go build -o soundboard.exe main.go

# macOS
GOOS=darwin GOARCH=amd64 go build -o soundboard main.go

# Linux
GOOS=linux GOARCH=amd64 go build -o soundboard main.go
```

## Troubleshooting

### Audio Not Playing

- Check if audio files are in supported formats (MP3, WAV, OGG)
- Ensure system audio is not muted
- Try different audio files

### WebSocket Connection Issues

- Check firewall settings
- Ensure port 5000 is available
- Try refreshing the browser

### Build Errors

- Ensure Go 1.21+ is installed
- Run `go mod tidy` to update dependencies
- Check internet connection for dependency downloads

## License

This project is open source and available under the MIT License.
