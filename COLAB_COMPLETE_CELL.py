# ============================================
# COMPLETE COLAB CELL - Copy and paste this entire cell
# Run this AFTER your Cell 1 & 2 (Ollama setup + model download)
# ============================================

# 1. Install Flask and ngrok
print("Installing Flask and ngrok...")
!pip install -q flask flask-cors pyngrok
print("✓ Packages installed")

# 2. Start Ollama server
print("\nStarting Ollama server...")
!nohup ollama serve > /dev/null 2>&1 &
import time
time.sleep(5)
print("✓ Ollama server started")

# 3. Verify model exists
MODEL_NAME = "deepseek"  # ← CHANGE THIS to your model name
print(f"\nChecking if model '{MODEL_NAME}' exists...")
!ollama list

# 4. Create the server code
server_code = '''
from flask import Flask, request, jsonify, Response
import ollama
import json

MODEL_NAME = "deepseek"  # ← CHANGE THIS to match above

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "model": MODEL_NAME})

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    prompt = data.get('prompt', '')
    stream = data.get('stream', False)
    
    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400
    
    try:
        if stream:
            def generate_stream():
                response_stream = ollama.generate(
                    model=MODEL_NAME,
                    prompt=prompt,
                    stream=True
                )
                for chunk in response_stream:
                    yield json.dumps({"response": chunk['response']}) + "\\n"
            
            return Response(generate_stream(), mimetype='application/x-ndjson')
        else:
            response = ollama.generate(
                model=MODEL_NAME,
                prompt=prompt,
                stream=False
            )
            return jsonify({"response": response['response']})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
'''

with open('/content/colab_server.py', 'w') as f:
    f.write(server_code)
print("✓ Server code created")

# 5. Start Flask server in background
import sys
sys.path.append('/content')
from colab_server import app
import threading

def run_flask():
    app.run(host='0.0.0.0', port=5000, use_reloader=False)

flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()
time.sleep(3)
print("✓ Flask server started")

# 6. Create ngrok tunnel
from pyngrok import ngrok
public_url = ngrok.connect(5000)

# 7. Display connection info
print("\n" + "="*60)
print("🚀 LLM Server is running!")
print(f"📡 Model: {MODEL_NAME}")
print(f"🌐 Public URL: {public_url}")
print("="*60)
print("\n⚠️ COPY THIS URL!")
print("\nOn your local PC, run:")
print(f"  python local_agent.py {public_url}")
print("\nOr just: python local_agent.py")
print("and paste the URL when prompted.")
print("\n💡 Keep this cell running!")
print("="*60)

# 8. Keep running
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nServer stopped.")
