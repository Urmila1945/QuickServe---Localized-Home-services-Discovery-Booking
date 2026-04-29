import http.server
import socketserver
import os

PORT = 3001
HOST = "127.0.0.1"
DIRECTORY = "public"

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        super().end_headers()

os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("="*60)
print("  🚀 QuickServe Frontend Server")
print("="*60)
print(f"✅ Server running at http://{HOST}:{PORT}")
print()
print("📱 Access Points:")
print(f"   • Main App:     http://{HOST}:{PORT}/index-standalone.html")
print(f"   • Landing Page: http://{HOST}:{PORT}/landing.html")
print()
print("⚠️  Make sure Backend API is running on port 8000")
print("   Backend: http://127.0.0.1:8000")
print()
print("Press Ctrl+C to stop the server")
print("="*60)
print()

with socketserver.TCPServer((HOST, PORT), MyHTTPRequestHandler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n" + "="*60)
        print("❌ Server stopped")
        print("="*60)
