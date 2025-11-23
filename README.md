++ README.md

# Flexster — QR to Music Player

This is a web application that scans QR codes (camera or image upload), extracts Apple Music or Spotify URLs, and plays them inline using either platform's player.

## Features

- **QR Code Scanner**: Scan QR codes from camera or uploaded images
- **Multi-Platform Support**: Works with both Apple Music and Spotify
- **Spotify Web Playback SDK**: Full playback control with Spotify Premium
- **Apple Music Embed**: Play Apple Music previews (30s) or full embed player
- **Privacy Mode**: Developer mode to hide/show scanned URLs

## Files

- `index.html` — the web UI: camera scanner, file upload, manual URL input, and music players
- `qr_generator.py` — Python script to create QR code PNG files
- `main.py` — CLI tool to generate music flashcards with QR codes
- `music_fetcher.py` — Fetches metadata from iTunes and MusicBrainz APIs
- `pdf_generator.py` — Generates printable PDF flashcards
- `spotify_config.json` — Spotify API credentials (you need to configure this)

## How it works

- The page uses `jsQR` (from CDN) to decode QR codes from the camera stream or uploaded images
- **Apple Music**: Converts URLs to embed format or uses 30s preview API
- **Spotify**: Uses Web Playback SDK for full playback control (requires Premium + login)

## Deployment

To use the camera scanner on a mobile device, the page must be served over **HTTPS**.

### GitHub Pages (Recommended)

1.  Push this repository to GitHub.
2.  Go to **Settings** > **Pages**.
3.  Select the `main` branch as the source.
4.  Your site will be live at `https://<username>.github.io/<repo-name>/client.html`.

### Netlify / Vercel

1.  Drag and drop the project folder onto Netlify Drop.
2.  Or connect your GitHub repository to Vercel/Netlify for automatic deployments.

## Python Tools

The project includes a set of Python tools to fetch music metadata and generate printable flashcards.

### Setup

```bash
# Install dependencies
python3 -m pip install requests reportlab qrcode pillow
```

### Usage

Run the main script to fetch metadata and generate a PDF:

```bash
# Default usage (uses built-in example list)
python3 main.py

# Use a custom list of songs
python3 main.py --input songs.txt

# Customize grid size (e.g., 2x2)
python3 main.py --rows 2 --cols 2

# Disable metadata mirroring (for single-sided printing)
python3 main.py --no-mirror
```

This will generate `music_cards.pdf` in the current directory.

### Files

- `main.py`: Entry point for the CLI tool.
- `music_fetcher.py`: Handles fetching metadata from iTunes and MusicBrainz.
- `pdf_generator.py`: Generates the PDF flashcards.
- `client.html`: The web player interface.

## Setup for Spotify Web Playback

To use Spotify's full playback features:

### 1. Configure Spotify App

1. Go to <https://developer.spotify.com/dashboard>
2. Log in with your Spotify account
3. Click "Create app"
4. Fill in:
   - **App name**: Flexster
   - **App description**: Music flashcards player
   - **Redirect URI**: `https://127.0.0.1:8000/`
5. Accept terms and click "Create"
6. Copy your **Client ID** to `spotify_config.json`
7. **Add your user**: Click "Settings" → scroll to "User Management" → "Add new user" → enter your Spotify email
8. **Important**: In the app settings, make sure the Redirect URI is exactly: `https://127.0.0.1:8000/`
9. Click "Save"

### 2. Run HTTPS Server

Spotify Web Playback SDK requires HTTPS. Use the included HTTPS server:

```bash
cd /path/to/flexster
python3 https_server.py
```

This will automatically generate a self-signed certificate and start the server at `https://127.0.0.1:8000`

### 3. Login to Spotify

1. Click "Login with Spotify"
2. Authorize the app
3. You'll be redirected back with full playback controls

**Note**: Spotify Web Playback SDK requires a **Spotify Premium** account.

### Browser Notes

- Use a Chromium-based browser or recent Safari for camera access
- You will be prompted to allow camera access
- If camera permission is blocked, use the "Upload QR image" control or paste the music URL

## Generate a QR for testing

The repository contains `qr_generator.py` which uses the `qrcode` Python package to generate PNG files. Example URL (already used in the generator):

```
https://music.apple.com/de/album/rolling-in-the-deep/403037872?i=403037877
```

To create a test QR file (requires `qrcode` package):

```bash
python3 -m pip install qrcode[pil]
python3 qr_generator.py
# this will create rolling-in-the-deep-qr.png in the project folder
```

Then either upload the PNG in `client.html` or open it on another device and scan via the page's camera.

## Troubleshooting

- If the camera doesn't start, check browser permissions and try a different browser.
- QR decoding works best when the QR image fills most of the camera frame and is well lit.

If you want, I can:

- Add a small Node/Flask dev server to serve the page and static assets.
- Add a demo QR image into the repository.

## Configuration Options

### Developer Mode

- The page includes a **Developer mode** checkbox
- For privacy, QR links detected from the camera or uploaded images are only revealed when Developer mode is enabled
- This prevents the page from automatically showing scanned links unless you opt in

### Player Options

- **Use Embed Player**: Switch between custom player (30s preview) and full embed player
- **Spotify Authentication**: Login required for full Spotify playback with Web Playback SDK
- **Apple Music**: Works without authentication (30s previews or embed player)

## Platform Comparison

| Feature          | Apple Music     | Spotify               |
| ---------------- | --------------- | --------------------- |
| Preview Playback | ✅ 30s previews | ❌ Requires login     |
| Full Playback    | ✅ Embed player | ✅ Web Playback SDK   |
| Authentication   | ❌ Not required | ✅ Required (Premium) |
| Offline          | ❌              | ❌                    |
| Custom Controls  | ✅ Play/Stop    | ✅ Play/Pause/Stop    |
