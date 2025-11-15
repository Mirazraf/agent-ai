# ============================================
# COLAB CELL: Optimize Model Performance
# Run this AFTER downloading your model
# ============================================

# Step 1: Create optimized Modelfile
modelfile_content = """
FROM qwen2.5-coder:14b

# Performance optimizations
PARAMETER num_ctx 8192
PARAMETER num_gpu 99
PARAMETER temperature 0.2
PARAMETER num_predict 2048
PARAMETER top_k 40
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.15

# Stronger system prompt
SYSTEM You are a precise coding assistant that writes complete, working code.

RULES:
1. Never use placeholders like "# Your code here" or "# TODO"
2. Always implement full functionality
3. Write production-ready code
4. Include proper error handling
5. Use clear variable names
6. Add brief comments only where necessary

When asked to add to a file, use append_file tool, not write_file.
When creating new files, use write_file tool.
"""

print("Creating optimized Modelfile...")
with open('/content/Modelfile-qwen-optimized', 'w') as f:
    f.write(modelfile_content)

# Step 2: Create the optimized model
print("\nCreating optimized model (this may take a minute)...")
!ollama create qwen-optimized -f /content/Modelfile-qwen-optimized

# Step 3: Verify it was created
print("\n✓ Optimized model created!")
print("\nAvailable models:")
!ollama list

# Step 4: Test the optimized model
print("\n" + "="*60)
print("Testing optimized model...")
print("="*60)

import ollama

test_response = ollama.generate(
    model='qwen-optimized',
    prompt='Write a complete Python function to calculate factorial. Include full implementation with error handling.',
    stream=False
)

print("\nTest Response:")
print(test_response['response'])

# Step 5: Check VRAM usage
print("\n" + "="*60)
print("GPU Memory Usage:")
print("="*60)
!nvidia-smi --query-gpu=memory.used,memory.total --format=csv

print("\n" + "="*60)
print("✓ Optimization complete!")
print("\nNext steps:")
print("1. Update MODEL_NAME in your server to 'qwen-optimized'")
print("2. Restart the server cell")
print("3. Test with your local agent")
print("="*60)
