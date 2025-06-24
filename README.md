# 🎵 Soundboard Application

A modern, web-based soundboard application built with Go that provides a sleek interface for playing audio files with real-time controls and customization options.

## 🚀 Features

- **🎧 Audio Playback** - Support for MP3, WAV, and OGG formats
- **🌐 Web Interface** - Modern, responsive design with dark theme
- **⚡ Real-time Updates** - WebSocket communication for instant synchronization
- **📁 File Upload** - Easy audio file management through web interface
- **✏️ Edit Mode** - Drag & drop button arrangement with color customization
- **💾 Persistent Layout** - Remembers your button configuration between sessions
- **🔄 Multi-device Support** - Access from multiple browsers/devices simultaneously

## 📦 Quick Start

### For End Users

1. **Download** the latest release
2. **Extract** the files to a folder
3. **Double-click** `start_soundboard.bat`
4. **Browser opens** automatically at `http://localhost:5000`
5. **Start using** your soundboard!

### Requirements

- **Windows** (primary support)
- **Modern web browser** (Chrome, Firefox, Edge)
- **Audio output device**

## 📁 Project Structure

```
soundboard/
├── soundboard.exe          # Main Go executable
├── start_soundboard.bat    # Easy launcher script
├── build.bat              # Build script for developers
├── main.go                # Go source code
├── go.mod                 # Go module dependencies
├── templates/             # Web interface templates
├── static/               # CSS, JavaScript, and assets
├── uploads/              # Audio files storage
└── pythonversion/        # Legacy Python implementation
```

## 🎮 Usage

### Playing Sounds

- **Click** any button to play/stop audio
- **Green buttons** indicate currently playing sounds
- Only **one sound** plays at a time

### Managing Audio Files

- **Upload**: Use the web interface upload button
- **Manual**: Copy files to the `uploads/` folder and refresh

### Customization

- **Edit Mode**: Rearrange buttons and change colors
- **Layout**: Your arrangement is automatically saved
- **Organization**: Color-code buttons by category

## 🌐 Network Access

Share your soundboard across devices:

1. **Find your IP**: Run `ipconfig` in command prompt
2. **Share URL**: `http://YOUR-IP:5000`
3. **Connect**: Other devices can access via browser

Perfect for:

- **Streaming** (OBS, XSplit)
- **Discord/Voice Chat** (with virtual audio cables)
- **Presentations**
- **Gaming sessions**

## 🛠️ Development

### Building from Source

```bash
# Clone the repository
git clone <repository-url>
cd soundboard

# Install Go dependencies
go mod tidy

# Build executable
go build -ldflags="-s -w" -o soundboard.exe main.go

# Or use the build script
./build.bat
```

### Technology Stack

- **Backend**: Go with Gin web framework
- **WebSockets**: Gorilla WebSocket for real-time communication
- **Audio**: Oto audio library with Beep for MP3 decoding
- **Frontend**: Vanilla JavaScript with Tailwind CSS
- **Storage**: Local file system

### Dependencies

```go
- github.com/gin-gonic/gin v1.9.1
- github.com/gorilla/websocket v1.5.1
- github.com/hajimehoshi/oto v1.0.1
- github.com/faiface/beep (audio processing)
```

## 📋 Documentation

- **[User Guide](README_USER.md)** - Complete usage instructions
- **[Developer Guide](README_GO.md)** - Technical implementation details

## 🔧 Troubleshooting

### Common Issues

- **Port 5000 in use**: Change port in `main.go` or stop conflicting service
- **No audio**: Check system volume and audio device settings
- **Firewall**: Allow `soundboard.exe` through Windows Firewall for network access

### Support

For technical issues or questions, please refer to the troubleshooting section in the [User Guide](README_USER.md).

## 📜 License

This soundboard application is proprietary software. All rights reserved.

**Distribution Rights**: Only the original author has the right to distribute this software.  
**Usage**: Personal use only. No redistribution, modification, or commercial use without explicit permission.

For licensing inquiries, please contact the author.

## ⚠️ Security Notice

This application provides **no built-in security measures**. When exposing to networks:

- Consider firewall protection
- Use VPN for remote access
- Implement authentication if needed
- **Use at your own risk**

## 🏆 Why This Soundboard?

### Advantages over alternatives:

✅ **Single Executable** - No complex installations or dependencies  
✅ **Cross-platform Web Interface** - Works on any device with a browser  
✅ **Real-time Synchronization** - Multiple users see instant updates  
✅ **Lightweight** - Uses minimal system resources (~10-20MB RAM)  
✅ **Fast Startup** - Ready in under 3 seconds  
✅ **Intuitive Design** - Easy to use for non-technical users

---

**Built with ❤️ using Go | © 2025 | Version 1.0**
