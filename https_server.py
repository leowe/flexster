#!/usr/bin/env python3
"""
Simple HTTPS server for Spotify Web Playback SDK
Generates a self-signed certificate automatically.
"""

import http.server
import ssl
import os
import subprocess

# Check if certificate exists, if not create it
if not os.path.exists("cert.pem") or not os.path.exists("key.pem"):
    print("Generating self-signed certificate...")
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:4096",
            "-keyout",
            "key.pem",
            "-out",
            "cert.pem",
            "-days",
            "365",
            "-nodes",
            "-subj",
            "/CN=127.0.0.1",
        ],
        check=True,
    )
    print("Certificate generated!")

print("=" * 60)
print("🎵 Flexster HTTPS Server Starting...")
print("=" * 60)
print("\n⚠️  IMPORTANT: Update your Spotify App settings:")
print("   1. Go to: https://developer.spotify.com/dashboard")
print("   2. Select your app: 'Flexster'")
print("   3. Click 'Settings' → 'Edit Settings'")
print("   4. Set Redirect URI to: https://127.0.0.1:8000/")
print("   5. Click 'Save'")
print("\n📍 Server running at: https://127.0.0.1:8000")
print("✅ Open: https://127.0.0.1:8000/index.html")
print("\n⚠️  Your browser will warn about the self-signed certificate.")
print("   Click 'Advanced' → 'Proceed to 127.0.0.1 (unsafe)' to continue.")
print("=" * 60)
print()

server_address = ("127.0.0.1", 8000)
httpd = http.server.HTTPServer(server_address, http.server.SimpleHTTPRequestHandler)

# Use modern SSL context instead of deprecated wrap_socket
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")
httpd.socket = ssl_context.wrap_socket(httpd.socket, server_side=True)

httpd.serve_forever()
