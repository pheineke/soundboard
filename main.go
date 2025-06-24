package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"html/template"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"github.com/hajimehoshi/oto"
	// Use the beep library for audio processing
	"github.com/faiface/beep"
	"github.com/faiface/beep/mp3"
	//"github.com/faiface/beep/wav" // CORRECT: Import the WAV encoder
	"encoding/binary"
)

const (
	UPLOAD_FOLDER    = "uploads"
	STATIC_FOLDER    = "static"
	TEMPLATES_FOLDER = "templates"
	TARGET_SAMPLE_RATE = 44100
	TARGET_CHANNELS    = 2
	TARGET_BIT_DEPTH   = 2 // 16 bits = 2 bytes
)

var (
	ALLOWED_EXTENSIONS = map[string]bool{
		".mp3": true,
	}
)

type SoundManager struct {
	soundCache      map[string]*SoundData
	soundCacheLock  sync.RWMutex
	playingChannels map[string]*PlayingSound
	otoContext      *oto.Context
}

type SoundData struct {
	data []byte
}

type PlayingSound struct {
	player  *oto.Player
	playing bool
	mutex   sync.Mutex
}

type SocketMessage struct {
	Type     string `json:"type"`
	Filename string `json:"filename,omitempty"`
	Message  string `json:"message,omitempty"`
}

var (
	upgrader = websocket.Upgrader{
		CheckOrigin: func(r *http.Request) bool { return true },
	}
	soundManager *SoundManager
	clients      = make(map[*websocket.Conn]bool)
	clientsMutex sync.Mutex
)

func init() {
	os.MkdirAll(UPLOAD_FOLDER, 0755)
	os.MkdirAll(STATIC_FOLDER, 0755)
	os.MkdirAll(TEMPLATES_FOLDER, 0755)

	ctx, err := oto.NewContext(TARGET_SAMPLE_RATE, TARGET_CHANNELS, TARGET_BIT_DEPTH, 8192)
	if err != nil {
		log.Panicf("Failed to initialize audio context: %v", err)
	}

	soundManager = &SoundManager{
		soundCache:      make(map[string]*SoundData),
		playingChannels: make(map[string]*PlayingSound),
		otoContext:      ctx,
	}
}

func allowedFile(filename string) bool {
	ext := strings.ToLower(filepath.Ext(filename))
	return ALLOWED_EXTENSIONS[ext]
}

// loadSound (Final Correct Version)
func (sm *SoundManager) loadSound(filepath string) (*SoundData, error) {
	sm.soundCacheLock.Lock()
	defer sm.soundCacheLock.Unlock()

	if sound, exists := sm.soundCache[filepath]; exists {
		return sound, nil
	}

	file, err := os.Open(filepath)
	if err != nil {
		return nil, fmt.Errorf("failed to open file: %w", err)
	}

	streamer, format, err := mp3.Decode(file)
	if err != nil {
		return nil, fmt.Errorf("failed to decode mp3: %w", err)
	}
	defer streamer.Close()

	log.Printf("Loaded MP3: %s (Source format: %d Hz, %d channels)", filepath, format.SampleRate, format.NumChannels)
	
	// Resample the audio to our target format.
	resampledStreamer := beep.Resample(4, format.SampleRate, beep.SampleRate(TARGET_SAMPLE_RATE), streamer)

	// Create a buffer to write our raw PCM data into.
	var pcmData bytes.Buffer

	// This is the buffer that beep will stream audio samples into.
	// It's a slice of stereo samples.
	sampleBuffer := make([][2]float64, 512) 

	// Loop until the streamer is drained.
	for {
		// Stream fills the buffer and returns the number of samples read.
		numSamples, ok := resampledStreamer.Stream(sampleBuffer)
		if !ok {
			// The stream is over.
			break
		}

		// Iterate over the read samples and write them to our byte buffer.
		for i := 0; i < numSamples; i++ {
			sample := sampleBuffer[i]
			
			// Convert float64 sample (-1.0 to 1.0) to 16-bit signed integer.
			left := int16(sample[0] * 32767)
			right := int16(sample[1] * 32767)

			// Write the 16-bit samples as little-endian bytes.
			// This is the standard format for PCM audio data.
			binary.Write(&pcmData, binary.LittleEndian, left)
			binary.Write(&pcmData, binary.LittleEndian, right)
		}
	}

	log.Printf("Caching sound. Final format: %d Hz, %d channels, %d bytes", TARGET_SAMPLE_RATE, TARGET_CHANNELS, pcmData.Len())

	sound := &SoundData{
		data: pcmData.Bytes(),
	}

	sm.soundCache[filepath] = sound
	return sound, nil
}

func (sm *SoundManager) toggleSound(filepath string) error {
	sm.soundCacheLock.Lock()
	if playingSound, exists := sm.playingChannels[filepath]; exists {
		playingSound.mutex.Lock()
		if playingSound.playing {
			playingSound.player.Close()
		}
		playingSound.mutex.Unlock()
		sm.soundCacheLock.Unlock()
		return nil
	}
	sm.soundCacheLock.Unlock()

	sound, err := sm.loadSound(filepath)
	if err != nil {
		return err
	}

	player := sm.otoContext.NewPlayer()
	playingSound := &PlayingSound{
		player:  player,
		playing: true,
	}

	sm.soundCacheLock.Lock()
	sm.playingChannels[filepath] = playingSound
	sm.soundCacheLock.Unlock()

	go func() {
		defer func() {
			player.Close()
			log.Printf("Playback finished for %s", filepath)
			
			sm.soundCacheLock.Lock()
			delete(sm.playingChannels, filepath)
			sm.soundCacheLock.Unlock()

			broadcastToClients(SocketMessage{
				Type:     "sound-stopped",
				Filename: strings.TrimPrefix(filepath, UPLOAD_FOLDER+string(os.PathSeparator)),
			})
		}()

		log.Printf("Starting playback for %s", filepath)
		if _, err := io.Copy(player, bytes.NewReader(sound.data)); err != nil {
			log.Printf("Playback error for %s: %v", filepath, err)
		}
	}()

	log.Printf("Started playing: %s", filepath)
	return nil
}


func broadcastToClients(message SocketMessage) {
	clientsMutex.Lock()
	defer clientsMutex.Unlock()

	messageBytes, _ := json.Marshal(message)
	
	for client := range clients {
		err := client.WriteMessage(websocket.TextMessage, messageBytes)
		if err != nil {
			log.Printf("Error writing to client: %v", err)
			client.Close()
			delete(clients, client)
		}
	}
}

func handleWebSocket(c *gin.Context) {
	conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		log.Printf("WebSocket upgrade failed: %v", err)
		return
	}
	defer conn.Close()

	clientsMutex.Lock()
	clients[conn] = true
	clientsMutex.Unlock()
	defer func() {
		clientsMutex.Lock()
		delete(clients, conn)
		clientsMutex.Unlock()
	}()

	for {
		_, message, err := conn.ReadMessage()
		if err != nil {
			if !websocket.IsCloseError(err, websocket.CloseGoingAway, websocket.CloseNormalClosure) {
				log.Printf("WebSocket read error: %v", err)
			}
			break
		}

		var msg map[string]interface{}
		if err := json.Unmarshal(message, &msg); err != nil {
			log.Printf("Error unmarshaling message: %v", err)
			continue
		}

		if msgType, ok := msg["type"].(string); ok && msgType == "play-sound" {
			if filename, ok := msg["filename"].(string); ok {
				filepath := filepath.Join(UPLOAD_FOLDER, filename)
				
				if _, err := os.Stat(filepath); os.IsNotExist(err) {
					conn.WriteJSON(SocketMessage{
						Type:    "error",
						Message: "Sound file not found",
					})
					continue
				}

				err := soundManager.toggleSound(filepath)
				if err != nil {
					conn.WriteJSON(SocketMessage{
						Type:    "error",
						Message: fmt.Sprintf("Failed to play sound: %v", err),
					})
					continue
				}

				broadcastToClients(SocketMessage{
					Type:     "sound-played",
					Filename: filename,
				})
			}
		}
	}
}

func indexHandler(c *gin.Context) {
	files, err := os.ReadDir(UPLOAD_FOLDER)
	if err != nil {
		log.Printf("Error reading upload folder: %v", err)
		c.HTML(http.StatusInternalServerError, "index_go.html", gin.H{
			"sound_files": []string{},
		})
		return
	}

	var soundFiles []string
	for _, file := range files {
		if !file.IsDir() && allowedFile(file.Name()) {
			soundFiles = append(soundFiles, file.Name())
		}
	}

	c.HTML(http.StatusOK, "index_go.html", gin.H{
		"sound_files": soundFiles,
	})
}

func uploadHandler(c *gin.Context) {
	file, err := c.FormFile("file")
	if err != nil {
		log.Printf("No file uploaded: %v", err)
		c.Redirect(http.StatusSeeOther, "/")
		return
	}

	if file.Filename == "" || !allowedFile(file.Filename) {
		log.Printf("Invalid file: %s", file.Filename)
		c.Redirect(http.StatusSeeOther, "/")
		return
	}

	filepath := filepath.Join(UPLOAD_FOLDER, file.Filename)
	err = c.SaveUploadedFile(file, filepath)
	if err != nil {
		log.Printf("Failed to save file: %v", err)
		c.Redirect(http.StatusSeeOther, "/")
		return
	}
	
	log.Printf("Uploaded file: %s", filepath)
	c.Redirect(http.StatusSeeOther, "/")
}

func main() {
	gin.SetMode(gin.ReleaseMode)
	r := gin.Default()

	r.SetFuncMap(template.FuncMap{
		"removeExt": func(filename string) string {
			return strings.TrimSuffix(filename, filepath.Ext(filename))
		},
	})
	r.LoadHTMLFiles(filepath.Join(TEMPLATES_FOLDER, "index_go.html"))

	r.Static("/static", STATIC_FOLDER)
	r.Static("/uploads", UPLOAD_FOLDER)

	r.GET("/", indexHandler)
	r.POST("/upload", uploadHandler)
	r.GET("/ws", handleWebSocket)

	log.Println("Server running at http://0.0.0.0:5000")
	if err := r.Run(":5000"); err != nil {
		log.Fatalf("Failed to run server: %v", err)
	}
}