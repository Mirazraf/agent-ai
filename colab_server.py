"""
LLM Server running in Colab - Exposes the model via Flask API
"""

from flask import Flask, request, jsonify, Response
import ollama
import json

# Try to import config, fallback to default
try:
    from config import MODEL_NAME, SERVER_HOST, SERVER_PORT
except ImportError:
    MODEL_NAME = "deepseek"  # Change this to your model name
    SERVER_HOST = "0.0.0.0"
    SERVER_PORT = 5000

app = Flask(__name__)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "model": MODEL_NAME})


@app.route('/generate', methods=['POST'])
def generate():
    """Generate response from the model"""
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
                    yield json.dumps({"response": chunk['response']}) + "\n"
            
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


@app.route('/chat', methods=['POST'])
def chat():
    """Chat endpoint with conversation history"""
    data = request.json
    messages = data.get('messages', [])
    stream = data.get('stream', False)
    
    if not messages:
        return jsonify({"error": "No messages provided"}), 400
    
    try:
        if stream:
            def generate_stream():
                response_stream = ollama.chat(
                    model=MODEL_NAME,
                    messages=messages,
                    stream=True
                )
                for chunk in response_stream:
                    if 'message' in chunk:
                        yield json.dumps({"content": chunk['message']['content']}) + "\n"
            
            return Response(generate_stream(), mimetype='application/x-ndjson')
        else:
            response = ollama.chat(
                model=MODEL_NAME,
                messages=messages,
                stream=False
            )
            return jsonify({"content": response['message']['content']})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print(f"Starting LLM Server with model: {MODEL_NAME}")
    print("Server will be accessible via ngrok tunnel")
    app.run(host=SERVER_HOST, port=SERVER_PORT)
