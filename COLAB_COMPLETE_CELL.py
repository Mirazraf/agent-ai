#####
# Cell1
#####

print("Updating package list...")
!sudo apt-get update -y -qq
print("Package list updated.")

print("Installing aria2, curl, and other packages...")
!sudo apt-get install -y -qq aria2 curl
!pip install -q ollama
!pip install -q flask flask-cors pyngrok
print("Necessary packages installed.")

print("Installing Ollama for running model...")
!aria2c -x 8 -s 8 https://ollama.com/install.sh -o install.sh
!sh install.sh
print("Ollama installed.")

print("\nInstalled package versions:")
!aria2c --version | head -n 1
!ollama --version

print("Starting Ollama server...")
!nohup ollama serve > /dev/null 2>&1 &
import time; time.sleep(3)
print("Ollama server started and ready.")


#####
# Cell2
#####

import os

# --- Model Configuration ---
# Define all model information in a single dictionary
# This makes it easier to manage and loop through.
MODELS_INFO = {
    'phi3': {
        'display_name': 'Phi-3 mini : Microsoft/Phi-3-mini-4k-instruct-q4 (3.8B parameters)',
        'filename': 'Phi-3-mini-4k-instruct-q4.gguf',
        'url': 'https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf?download=true'
    },
    'llama3': {
        'display_name': 'Llama-3 : MaziyarPanahi/Meta-Llama-3-8B-Instruct.Q4_K_M (8B parameters)',
        'filename': 'Meta-Llama-3-8B-Instruct.Q4_K_M.gguf',
        'url': 'https://huggingface.co/MaziyarPanahi/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf?download=true'
    },
    'deepseek': {
        'display_name': 'Deepseek: TheBloke/deepseek-llm-7b-chat.Q4_K_M.gguf (8B parameters)',
        'filename': 'deepseek-llm-7b-chat.Q4_K_M.gguf',
        'url': 'https://huggingface.co/TheBloke/deepseek-llm-7B-chat-GGUF/resolve/main/deepseek-llm-7b-chat.Q4_K_M.gguf?download=true'
    },
    'qwen' : {
        'display_name': 'Qwen-3: Unsloth/Qwen3-14B-Q4_K_M.gguf (14B parameters)',
        'filename': 'Qwen3-14B-Q4_K_M.gguf',
        'url': 'https://huggingface.co/unsloth/Qwen3-14B-GGUF/resolve/main/Qwen3-14B-Q4_K_M.gguf?download=true'
    }
}

# --- User Selection (Checkboxes) ---
download_phi3 = False #@param {type:"boolean"}
download_llama3 = False #@param {type:"boolean"}
download_deepseek = False #@param {type:"boolean"}
download_qwen = True #@param {type:"boolean"}

# --- Download and Setup Logic ---

# Create a list of models to download based on the checkboxes
selected_models = []
if download_phi3:
    selected_models.append('phi3')
if download_llama3:
    selected_models.append('llama3')
if download_deepseek:
    selected_models.append('deepseek')
if download_qwen:
    selected_models.append('qwen')

save_dir = "/content/models"
os.makedirs(save_dir, exist_ok=True)
os.chdir(save_dir) # Change directory once

if not selected_models:
    print("Please select at least one model to download by checking its box.")
else:
    print(f"Starting download and setup for: {', '.join(selected_models)}")

    for nickname in selected_models:
        try:
            info = MODELS_INFO[nickname]
            model_file = info['filename']
            model_path = os.path.join(save_dir, model_file)
            display_name = info['display_name']

            print(f"\n--- Processing: {display_name} ---")

            # 1. Download the model
            if not os.path.exists(model_path):
                print(f"Downloading {model_file}...")
                # Use ! to run shell commands in Colab/Jupyter
                !aria2c -x 8 -s 8 -d {save_dir} -o {model_file} {info['url']}
                print(f'{display_name} downloaded successfully!')
            else:
                print(f'{display_name} is already downloaded.')

            # 2. Create the nickname file (Modelfile)
            nickname_file_path = os.path.join(save_dir, nickname)
            with open(nickname_file_path, 'w') as f:
                f.write(f"FROM ./{model_file}")

            print(f"Nickname file '{nickname}' created in {save_dir}")

            # 3. Create the model in ollama
            print(f"Creating ollama model for '{nickname}'...")
            # We are already in the /content/models directory
            !ollama create {nickname} -f {nickname}
            print(f"--- Successfully created '{nickname}' model. ---")

        except Exception as e:
            print(f"An error occurred while processing {nickname}: {e}")

    print("\nAll selected models have been processed.")
    print("Your models are ready. Please select a model in the next cell.")

#####
# Cell3
#####

# Create the server file
# Create the server file
server_code = '''
from flask import Flask, request, jsonify, Response
import ollama
import json

app = Flask(__name__)
MODEL_NAME = "phi3"

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
                    stream=True,
                    options={
                        'temperature': 0.1,      # Lower = less random
                        'top_p': 0.9,            # Focus on likely tokens
                        'repeat_penalty': 1.2,   # Prevent repetition
                        'num_predict': 512,      # Limit response length
                    }
                )
                for chunk in response_stream:
                    yield json.dumps({"response": chunk['response']}) + "\\n"
            
            return Response(generate_stream(), mimetype='application/x-ndjson')
        else:
            response = ollama.generate(
                model=MODEL_NAME,
                prompt=prompt,
                stream=False,
                options={
                    'temperature': 0.1,
                    'top_p': 0.9,
                    'repeat_penalty': 1.2,
                    'num_predict': 512,
                }
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

# Start Ollama server first (IMPORTANT!)
print("Starting Ollama server...")
!nohup ollama serve > /dev/null 2>&1 &
import time
time.sleep(5)  # Wait for Ollama to start
print("✓ Ollama server started")

# Verify the model exists
print(f"\nChecking if model '{MODEL_NAME}' exists...")
!ollama list | grep qwen3 || echo "⚠️ Model not found! Run Cell 2 to download it."

# Start the Flask server with ngrok
from pyngrok import ngrok
import threading
import sys
sys.path.append('/content')

from colab_server import app

# Change model name here
MODEL_NAME = "qwen3"

def run_flask():
    app.run(host='0.0.0.0', port=5000, use_reloader=False)

flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()
time.sleep(3)

public_url = ngrok.connect(5000)

print("="*60)
print(f"🚀 LLM Server is running!")
print(f"📡 Model: qwen3")
print(f"🌐 Public URL: {public_url}")
print("="*60)
print("\n⚠️ COPY THIS URL!")
print("\nOn your local PC, run:")
print(f"  python local_agent.py {public_url}")
print("\nOr just: python local_agent.py")
print("and paste the URL when prompted.")
print("\n💡 Keep this cell running!")
print("="*60)

# Keep running
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nServer stopped.")