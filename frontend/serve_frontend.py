from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
import os

PORT = 5500

os.chdir(os.path.dirname(os.path.abspath(__file__)))

Handler = SimpleHTTPRequestHandler

with TCPServer(("", PORT), Handler) as httpd:
    print(f"Serving frontend at http://0.0.0.0:{PORT}")
    httpd.serve_forever()