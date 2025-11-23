++ README.md

# Flexster — QR to Apple Music Player

This is a small static web page that scans QR codes (camera or image upload), extracts Apple Music URLs, and plays them inline using Apple's embed player so you don't have to leave the page.

## Files

- `client.html` — the web UI: camera scanner, file upload, manual URL input, and an embed player.
- `qr_generator.py` — (provided) a small Python script to create QR code PNG files.

## How it works

- The page uses `jsQR` (from CDN) to decode QR codes from the camera stream or uploaded images.
- If a scanned URL is from `music.apple.com`, the page converts it to the Apple embed host `embed.music.apple.com` and inserts an `<iframe>` player.

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

## Run locally

Open a terminal in the project folder and start a static HTTP server. On macOS, `python3`'s simple server works and `localhost` is treated as a secure context so camera access works.

```bash
cd /path/to/flexster
python3 -m http.server 8000
# then open http://localhost:8000/client.html in your browser
```

Notes:

- Use a Chromium-based browser or recent Safari. You will be prompted to allow camera access.
- If camera permission is blocked, use the "Upload QR image" control or paste the Apple Music URL.

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

Developer mode and metadata hiding

- The page includes a **Developer mode** checkbox. For privacy, QR links detected from the camera or uploaded images are only revealed when Developer mode is enabled. This prevents the page from automatically showing scanned links unless you opt in.
- By default the Apple Music embed is cropped to hide the cover image, artist, and other metadata; click **Show Full Embed** to reveal the full player including artwork.
