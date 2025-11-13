#!/usr/bin/env python3
"""
Simple HTTP server for serving the track map viewer locally.
Run this script and navigate to http://localhost:8000 to view the demo.
"""

import http.server
import socketserver
import os
import sys
from pathlib import Path

def main():
    # Change to the directory containing this script
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)

    PORT = 8000

    # Create a custom handler to serve files with proper MIME types
    class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
        def end_headers(self):
            # Add CORS headers to allow local file access
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            super().end_headers()

        def guess_type(self, path):
            # Ensure proper MIME types for our files
            result = super().guess_type(path)
            if isinstance(result, tuple):
                mimetype, encoding = result
            else:
                mimetype, encoding = result, None

            if path.endswith('.js'):
                return 'application/javascript', encoding
            elif path.endswith('.png'):
                return 'image/png', encoding
            return mimetype, encoding

    try:
        with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
            print(f"Track Map Viewer Demo Server")
            print(f"Serving at http://localhost:{PORT}")
            print(f"Directory: {script_dir}")
            print(f"Open http://localhost:{PORT} in your browser to view the demo")
            print("Press Ctrl+C to stop the server")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"Port {PORT} is already in use. Try a different port or stop the existing server.")
        else:
            print(f"Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()