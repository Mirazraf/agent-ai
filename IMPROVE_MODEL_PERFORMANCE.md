# How to Improve Model Performance

## Problem: Model is Hallucinating / Performing Poorly

Even with a 14B model (Qwen), you're seeing:
- Hallucinations (gibberish output)
- Poor code quality
- Repeated mistakes
- Only using 5GB of 14GB VRAM

## Root Cause: Ollama Default Settings

Ollama uses conservative defaults to ensure compatibility. This limits:
- Context window size
- Number of GPU layers
- Temperature settings
- Token generation limits

## Solution: Configure Ollama with Modelfile

### Step 1: Create a Modelfile in Colab

```python
# In Colab, create a custom Modelfile
modelfile_content = """
FROM qwen2.5-coder:14b

# Increase context window (default is 2048)
PARAMETER num_ctx 8192

# Use more GPU layers (default is 33, max depends on model)
PARAMETER num_gpu 99

# Lower temperature for more focused responses (default 0.8)
PARAMETER temperature 0.3

# Increase token limit
PARAMETER num_predict 2048

# Better sampling
PARAMETER top_k 40
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1

# System message
SYSTEM You are a precise coding assistant. Generate complete, working code. Never use placeholders or comments like "# Your code here". Always implement full functionality.
"""

with open('/content/Modelfile-qwen-optimized', 'w') as f:
    f.write(modelfile_content)

# Create optimized model
!ollama create qwen-optimized -f /content/Modelfile-qwen-optimized

print("✓ Optimized model created: qwen-optimized")
```

### Step 2: Update Server to Use Optimized Model

In `colab_server.py` or `config.py`:
```python
MODEL_NAME = "qwen-optimized"  # Use the optimized version
```

### Step 3: Restart Colab Server

Run your server cell again with the new model name.

## Parameter Explanations

| Parameter | Default | Recommended | Effect |
|-----------|---------|-------------|--------|
| `num_ctx` | 2048 | 8192-16384 | Larger context = better memory |
| `num_gpu` | 33 | 99 | More GPU layers = faster |
| `temperature` | 0.8 | 0.1-0.3 | Lower = more focused |
| `num_predict` | -1 | 2048-4096 | Max tokens to generate |
| `top_p` | 0.9 | 0.9 | Nucleus sampling |
| `repeat_penalty` | 1.1 | 1.1-1.2 | Prevent repetition |

## Quick Test

After creating the optimized model:

```python
# Test in Colab
import ollama

response = ollama.generate(
    model='qwen-optimized',
    prompt='Write a complete Python function to check if a number is prime. Include full implementation, no placeholders.'
)

print(response['response'])
```

You should see complete, working code without placeholders.

## Alternative: Use API Parameters

If you don't want to create a Modelfile, modify the server to pass parameters:

```python
# In colab_server.py, update the generate function:
response_stream = ollama.generate(
    model=MODEL_NAME,
    prompt=prompt,
    stream=True,
    options={
        'num_ctx': 8192,
        'temperature': 0.3,
        'num_predict': 2048,
        'top_p': 0.9,
        'repeat_penalty': 1.1
    }
)
```

## Expected Improvements

After optimization:
- ✅ VRAM usage: 5GB → 10-12GB (using more GPU)
- ✅ Context: 2K → 8K tokens (better memory)
- ✅ Quality: Fewer hallucinations
- ✅ Completeness: Full implementations instead of placeholders
- ✅ Speed: Faster generation with more GPU layers

## Verify VRAM Usage

In Colab:
```python
!nvidia-smi
```

You should see higher GPU memory usage after optimization.

## Best Models for Coding

Ranked by quality (if you have VRAM):

1. **qwen2.5-coder:14b** - Best for coding (14GB)
2. **codellama:13b** - Good for code (13GB)
3. **deepseek-coder:6.7b** - Balanced (7GB)
4. **qwen2.5-coder:7b** - Fast, decent quality (7GB)
5. **phi3:3.8b** - Fastest, lowest quality (4GB)

## Troubleshooting

**Still hallucinating?**
- Lower temperature to 0.1
- Increase repeat_penalty to 1.3
- Add stronger system message
- Use `reset` command more frequently

**Out of memory?**
- Reduce num_ctx to 4096
- Use smaller model
- Reduce num_gpu to 50

**Slow responses?**
- Increase num_gpu to 99
- Reduce num_predict to 1024
- Use Colab Pro for better GPU
