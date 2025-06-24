# 🎵 Soundboard - Go Version

## 🚀 Quick Start

**For End Users (No Programming Required):**

1. **Double-click** `start_soundboard.bat`
2. **Wait** for the server to start (about 2-3 seconds)
3. **Your browser** will automatically open to `http://localhost:5000`
4. **Start playing sounds!** 🎉

## 📁 What You Get

Your `soundboard.exe` is a **single, self-contained executable** that includes:

- ✅ **Web Server** - No additional software needed
- ✅ **Audio Engine** - Plays MP3, WAV, OGG files
- ✅ **Modern Web UI** - Responsive design with dark theme
- ✅ **Real-time Updates** - WebSocket communication
- ✅ **File Upload** - Add new sounds through the web interface

## 🎮 How to Use

### Playing Sounds

- **Click any button** to play a sound
- **Click again** to stop the sound
- **Green buttons** show currently playing sounds
- Only **one sound plays at a time**

### Adding New Sounds

1. **Click the upload button** (📁) in the top-right
2. **Select an audio file** (MP3, WAV, or OGG)
3. **Click "Upload"**
4. **New button appears** automatically

### Edit Mode

1. **Click the edit button** (✏️) in the top-right
2. **Drag & drop** buttons to rearrange them
3. **Click buttons** to cycle through different colors
4. **Click save button** (💾) to exit edit mode
5. **Layout is remembered** between sessions

## 📂 File Structure

```
soundboard/
├── soundboard.exe          # ← Main executable (double-click to run)
├── start_soundboard.bat    # ← Easy launcher with browser auto-open
├── templates/
│   └── index_go.html       # Web interface template
├── static/
│   └── icons/              # UI icons
└── uploads/                # Your sound files go here
    ├── sound1.mp3
    ├── sound2.wav
    └── ...
```

## 🎵 Adding Your Own Sounds

### Method 1: Web Upload (Recommended)

- Use the upload button in the web interface

### Method 2: Manual Copy

1. **Copy audio files** to the `uploads/` folder
2. **Refresh the browser** to see new buttons

### Supported Formats

- **MP3** - Full support with metadata
- **WAV** - Full support
- **OGG** - Full support

## 🌐 Multi-User Setup

The soundboard works great for:

- **Streaming** - Use with OBS, XSplit, etc.
- **Discord/TeamSpeak** - Route audio through virtual cables
- **Local Network** - Access from multiple devices
- **Presentations** - Professional sound effects

### Network Access

1. **Start the soundboard** normally
2. **Find your IP address**: `ipconfig` in command prompt
3. **Share the URL**: `http://YOUR-IP:5000`
4. **Others can connect** from their browsers

## 🔧 Troubleshooting

### Server Won't Start

- **Check port 5000** isn't used by another application
- **Run as Administrator** if you get permission errors
- **Check Windows Firewall** settings

### No Sound Playing

- **Check system volume** and audio settings
- **Try different audio files** to isolate the issue
- **Restart the soundboard** if audio gets stuck

### Browser Issues

- **Refresh the page** if buttons don't respond
- **Clear browser cache** if experiencing issues
- **Try different browser** (Chrome, Firefox, Edge)

### Network Access Issues

- **Check Windows Firewall** allows the application
- **Verify IP address** is correct
- **Ensure devices are on same network**

## 🎯 Advanced Features

### Virtual Audio Cables

For streaming/Discord use:

1. **Install VB-Audio Cable** or similar
2. **Set system default** to virtual cable
3. **Soundboard audio** routes through the cable
4. **Streaming software** captures the audio

### Custom Layouts

- **Edit Mode** lets you organize buttons by categories
- **Color coding** helps identify different sound types
- **Arrangement persists** between sessions

### Batch Operations

- **Copy multiple files** to uploads/ folder at once
- **Use consistent naming** for better organization
- **File extensions** are automatically hidden in buttons

## 🚀 Performance

- **Fast startup** - Launches in under 3 seconds
- **Low memory** - Uses ~10-20MB RAM
- **Instant response** - WebSocket communication
- **Efficient caching** - Sounds load once, play many times

## 🆚 Comparison with Python Version

### Advantages ✅

- **No Dependencies** - Single .exe file, no Python/pip needed
- **Faster Startup** - Instant launch vs. Python initialization
- **Lower Resource Usage** - More efficient memory and CPU
- **Easy Distribution** - Just copy the .exe file
- **Cross-Platform** - Can build for Windows/Mac/Linux

### Limitations ⚠️

- **No Audio Normalization** - Files play at original volume
- **Basic Format Support** - No advanced audio processing
- **Single Audio Device** - Uses system default audio

## 📜 License

This soundboard application is proprietary software. All rights reserved.

- **Distribution Rights** - Only the original author has the right to distribute this software
- **Personal Use Only** - This software is provided for personal use only
- **No Redistribution** - Users may not redistribute, share, or distribute copies of this software
- **No Modification Rights** - Users may not modify, reverse engineer, or create derivative works
- **No Commercial Use** - This software may not be used for commercial purposes without explicit permission

For licensing inquiries or permissions, please contact the author.

## ⚠️ Security Notice

**Important**: This application provides **no security measures** against potential attacks or vulnerabilities. By using this software, you acknowledge that:

- **No security protection** - The web server runs without authentication or security hardening
- **Network exposure** - When accessible over a network, it may be vulnerable to attacks
- **Personal responsibility** - Any problems, security issues, or damages arising from the use of this application are solely the user's personal matter
- **Use at your own risk** - The developers assume no liability for any issues that may occur

For production environments or network-accessible deployments, consider implementing additional security measures such as firewalls, authentication, or VPN access.

---

**Enjoy your new Go-powered soundboard! 🎵✨**
