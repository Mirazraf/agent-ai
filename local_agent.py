"""
Local AI Coder Agent - Runs on your PC, connects to Colab LLM
"""

import requests
import json
import os
import sys
import subprocess
import glob
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class ToolType(Enum):
    """Available tool types for the agent"""
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    APPEND_FILE = "append_file"
    LIST_DIR = "list_directory"
    EXECUTE_BASH = "execute_bash"
    SEARCH_CODE = "search_code"


@dataclass
class Message:
    """Represents a chat message"""
    role: str
    content: str


class ColabLLMClient:
    """Client to communicate with LLM running in Colab"""
    
    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip('/')
        self._check_connection()
    
    def _check_connection(self):
        """Check if server is reachable"""
        try:
            response = requests.get(
                f"{self.server_url}/health", 
                timeout=5,
                headers={"ngrok-skip-browser-warning": "true"}  # Skip ngrok browser warning
            )
            if response.status_code == 200:
                print(f"✓ Connected to LLM server: {response.json()}")
            else:
                print(f"⚠ Server responded with status {response.status_code}")
                print("  (This might be okay, trying to continue...)")
        except Exception as e:
            print(f"✗ Failed to connect to server: {e}")
            print("Make sure the Colab server is running and ngrok URL is correct")
            sys.exit(1)
    
    def generate(self, prompt: str, stream: bool = True, max_retries: int = 2):
        """Generate response from LLM"""
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.server_url}/generate",
                    json={"prompt": prompt, "stream": stream},
                    stream=stream,
                    timeout=120,
                    headers={"ngrok-skip-browser-warning": "true"}  # Skip ngrok warning page
                )
                
                if response.status_code != 200:
                    if attempt < max_retries - 1:
                        print(f"\n[Retry {attempt + 1}/{max_retries}...]", end="", flush=True)
                        continue
                    else:
                        yield f"Error: Server returned status {response.status_code}"
                        return
                
                if stream:
                    has_content = False
                    for line in response.iter_lines():
                        if line:
                            data = json.loads(line)
                            chunk = data.get('response', '')
                            if chunk:
                                has_content = True
                            yield chunk
                    
                    # If no content received, retry
                    if not has_content and attempt < max_retries - 1:
                        print(f"\n[Empty response, retrying {attempt + 1}/{max_retries}...]", end="", flush=True)
                        continue
                else:
                    result = response.json().get('response', '')
                    if not result and attempt < max_retries - 1:
                        continue
                    return result
                
                # If we got here, we succeeded
                break
            
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"\n[Error, retrying {attempt + 1}/{max_retries}...]", end="", flush=True)
                    continue
                else:
                    yield f"Error communicating with LLM: {e}"


class LocalFileSystem:
    """Handles file system operations on local PC"""
    
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = os.path.abspath(workspace_root)
        os.makedirs(workspace_root, exist_ok=True)
        print(f"Workspace: {self.workspace_root}")
    
    def read_file(self, path: str) -> str:
        """Read file content"""
        full_path = os.path.join(self.workspace_root, path)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return f"File: {path}\n{content}"
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    def write_file(self, path: str, content: str) -> str:
        """Write content to file (overwrites existing content)"""
        full_path = os.path.join(self.workspace_root, path)
        try:
            # Handle escape sequences - convert \n to actual newlines, \t to tabs, etc.
            # This handles cases where LLM returns escaped strings
            try:
                # Try to decode escape sequences
                content = content.encode().decode('unicode_escape')
            except:
                # If that fails, just use the content as-is
                pass
            
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"✓ Successfully wrote to {path} (file overwritten)"
        except Exception as e:
            return f"Error writing file: {str(e)}"
    
    def append_file(self, path: str, content: str) -> str:
        """Append content to existing file"""
        full_path = os.path.join(self.workspace_root, path)
        try:
            # Handle escape sequences
            try:
                content = content.encode().decode('unicode_escape')
            except:
                pass
            
            # Check if file exists
            if not os.path.exists(full_path):
                return f"Error: File {path} does not exist. Use write_file to create it first."
            
            with open(full_path, 'a', encoding='utf-8') as f:
                f.write(content)
            return f"✓ Successfully appended to {path}"
        except Exception as e:
            return f"Error appending to file: {str(e)}"
    
    def list_directory(self, path: str = ".") -> str:
        """List directory contents"""
        full_path = os.path.join(self.workspace_root, path)
        try:
            items = os.listdir(full_path)
            result = [f"Directory: {path}\n"]
            for item in sorted(items):
                item_path = os.path.join(full_path, item)
                if os.path.isdir(item_path):
                    result.append(f"  📁 {item}/")
                else:
                    size = os.path.getsize(item_path)
                    result.append(f"  📄 {item} ({size} bytes)")
            return "\n".join(result) if len(result) > 1 else "Empty directory"
        except Exception as e:
            return f"Error listing directory: {str(e)}"
    
    def search_code(self, pattern: str, file_pattern: str = "*.py") -> str:
        """Search for pattern in code files"""
        results = []
        search_path = os.path.join(self.workspace_root, "**", file_pattern)
        for filepath in glob.glob(search_path, recursive=True):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        if pattern in line:
                            rel_path = os.path.relpath(filepath, self.workspace_root)
                            results.append(f"{rel_path}:{line_num}: {line.strip()}")
            except:
                continue
        return "\n".join(results) if results else "No matches found"


class LocalBashExecutor:
    """Handles bash command execution on local PC"""
    
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
    
    def execute(self, command: str) -> str:
        """Execute bash command"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            output = result.stdout + result.stderr
            return output if output else "✓ Command executed successfully"
        except subprocess.TimeoutExpired:
            return "Error: Command timed out (30s limit)"
        except Exception as e:
            return f"Error executing command: {str(e)}"


class LocalAICoderAgent:
    """AI Coder Agent running locally, using remote LLM"""
    
    def __init__(self, server_url: str, workspace_root: str = "."):
        self.llm_client = ColabLLMClient(server_url)
        self.filesystem = LocalFileSystem(workspace_root)
        self.bash_executor = LocalBashExecutor(workspace_root)
        self.conversation_history: List[Message] = []
        self.file_memory = {}  # Track known files
        self.tool_call_count = 0  # ADD THIS LINE
        self.max_tool_calls = 5   # ADD THIS LINE - Maximum 5 tools per user request
        
        self.system_prompt = """You are an AI coding assistant with file system access.

CRITICAL FILE OPERATION RULES:
1. ALWAYS read_file FIRST before modifying any file
2. Use write_file ONLY for NEW files or when user says "create" or "overwrite"
3. Use append_file to ADD code to EXISTING files
4. When user says "add", "update", "fix", or "modify" → read file first, then append
5. When creating NEW files, write COMPLETE, WORKING code - not just comments or skeletons

WORKFLOW FOR CREATING NEW FILES:
User: "Create a tic-tac-toe game"
→ {"tool": "write_file", "parameters": {"path": "tictactoe.py", "content": "FULL WORKING CODE HERE WITH ALL LOGIC"}}

WORKFLOW FOR MODIFYING EXISTING FILES:
User: "Add a function to app.py"
→ Step 1: {"tool": "read_file", "parameters": {"path": "app.py"}}
→ Wait for result, then Step 2: {"tool": "append_file", "parameters": {"path": "app.py", "content": "\\ndef new_function():\\n    return 42\\n"}}

WHEN TO STOP USING TOOLS:
- After creating/modifying a file successfully, STOP and explain to the user what you did
- Do NOT keep reading the same file over and over
- Do NOT use tools if the user just wants information or explanation

Available tools (use ONE at a time):
- read_file: {"tool": "read_file", "parameters": {"path": "file.py"}}
- write_file: {"tool": "write_file", "parameters": {"path": "file.py", "content": "COMPLETE_WORKING_CODE\\n"}} - For NEW files
- append_file: {"tool": "append_file", "parameters": {"path": "file.py", "content": "more_code\\n"}} - For EXISTING files
- list_directory: {"tool": "list_directory", "parameters": {"path": "."}}
- execute_bash: {"tool": "execute_bash", "parameters": {"command": "python file.py"}}
- search_code: {"tool": "search_code", "parameters": {"pattern": "def", "file_pattern": "*.py"}}

IMPORTANT: 
- Use \\n for newlines, \\t for tabs
- Write COMPLETE, FUNCTIONAL code, not just comments
- After tool execution succeeds, provide a brief explanation and STOP
- Respond with ONLY valid JSON object (not array)
- Do NOT hallucinate user messages or instructions"""
        
        self.conversation_history.append(Message("system", self.system_prompt))
    
    def parse_tool_call(self, response: str) -> Optional[tuple]:
        """Extract tool call from LLM response"""
        import re
        
        # Method 1: Look for ```json blocks
        json_block_pattern = r'```json\s*(\{.*?\})\s*```'
        matches = re.findall(json_block_pattern, response, re.DOTALL)
        
        for match in matches:
            try:
                tool_data = json.loads(match)
                if "tool" in tool_data:
                    tool_type = ToolType(tool_data.get("tool"))
                    parameters = tool_data.get("parameters", {})
                    return (tool_type, parameters)
            except (json.JSONDecodeError, ValueError):
                continue
        
        # Method 2: Look for generic ``` blocks
        code_block_pattern = r'```\s*(\{.*?\})\s*```'
        matches = re.findall(code_block_pattern, response, re.DOTALL)
        
        for match in matches:
            try:
                tool_data = json.loads(match)
                if "tool" in tool_data:
                    tool_type = ToolType(tool_data.get("tool"))
                    parameters = tool_data.get("parameters", {})
                    return (tool_type, parameters)
            except (json.JSONDecodeError, ValueError):
                continue
        
        # Method 3: Find raw JSON by counting braces (handles JSON without markdown blocks)
        # Look for opening brace followed by "tool" (handles pretty-printed JSON)
        # Try multiple patterns: {"tool", { "tool", {\n  "tool", etc.
        start_idx = -1
        
        # Pattern 1: Compact JSON
        start_idx = response.find('{"tool"')
        
        # Pattern 2: JSON with space after brace
        if start_idx == -1:
            match = re.search(r'\{\s*"tool"', response)
            if match:
                start_idx = match.start()
        
        if start_idx != -1:
            brace_count = 0
            in_string = False
            escape_next = False
            
            for i in range(start_idx, len(response)):
                char = response[i]
                
                if escape_next:
                    escape_next = False
                    continue
                
                if char == '\\':
                    escape_next = True
                    continue
                
                if char == '"':
                    in_string = not in_string
                
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            # Found complete JSON
                            json_str = response[start_idx:i+1]
                            try:
                                tool_data = json.loads(json_str)
                                
                                if "tool" in tool_data:
                                    tool_value = tool_data.get("tool")
                                    
                                    # Handle case where LLM returns array of tools
                                    if isinstance(tool_value, list):
                                        if len(tool_value) > 0:
                                            # Take the first tool from the array
                                            first_tool = tool_value[0]
                                            if isinstance(first_tool, dict) and "tool" in first_tool:
                                                tool_type = ToolType(first_tool.get("tool"))
                                                parameters = first_tool.get("parameters", {})
                                                return (tool_type, parameters)
                                    else:
                                        # Normal case: single tool
                                        tool_type = ToolType(tool_value)
                                        parameters = tool_data.get("parameters", {})
                                        return (tool_type, parameters)
                            except (json.JSONDecodeError, ValueError) as e:
                                # Silently continue to next pattern
                                break
        
        return None
    
    def execute_tool(self, tool_type: ToolType, parameters: Dict) -> str:
        """Execute a tool and return the result"""
        try:
            if tool_type == ToolType.READ_FILE:
                result = self.filesystem.read_file(parameters["path"])
                # Remember this file exists
                self.file_memory[parameters["path"]] = True
                return result
            
            elif tool_type == ToolType.WRITE_FILE:
                path = parameters["path"]
                # Warn if overwriting existing file
                warning = ""
                if path in self.file_memory:
                    warning = f"⚠️  WARNING: Overwriting existing file {path}!\n"
                result = self.filesystem.write_file(path, parameters["content"])
                self.file_memory[path] = True
                return warning + result
            
            elif tool_type == ToolType.APPEND_FILE:
                path = parameters["path"]
                # Check if we know about this file
                if path not in self.file_memory:
                    # Try to read it first to verify it exists
                    try:
                        self.filesystem.read_file(path)
                        self.file_memory[path] = True
                    except:
                        return f"❌ Error: File {path} doesn't exist. Use write_file to create it first."
                
                result = self.filesystem.append_file(path, parameters["content"])
                return result
            
            elif tool_type == ToolType.LIST_DIR:
                path = parameters.get("path", ".")
                result = self.filesystem.list_directory(path)
                # Remember files we see
                for line in result.split('\n'):
                    if '📄' in line:
                        filename = line.split('📄')[1].split('(')[0].strip()
                        full_path = os.path.join(path, filename) if path != "." else filename
                        self.file_memory[full_path] = True
                return result
            
            elif tool_type == ToolType.EXECUTE_BASH:
                return self.bash_executor.execute(parameters["command"])
            
            elif tool_type == ToolType.SEARCH_CODE:
                pattern = parameters["pattern"]
                file_pattern = parameters.get("file_pattern", "*.py")
                return self.filesystem.search_code(pattern, file_pattern)
        
        except Exception as e:
            return f"Error executing tool: {str(e)}"
    
    def chat(self, user_message: str, stream: bool = True, debug: bool = False) -> str:
        """Send a message and get response"""
        # Reset counter for new user messages (not for internal "Continue..." messages)
        if not user_message.startswith("Based on the tool result"):
            self.tool_call_count = 0  # ADD THIS LINE
        self.conversation_history.append(Message("user", user_message))
        
        prompt = self._build_prompt()
        
        full_response = ""
        print("Assistant: ", end="", flush=True)
        
        for chunk in self.llm_client.generate(prompt, stream=stream):
            full_response += chunk
            if stream:
                print(chunk, end="", flush=True)
        
        if stream:
            print()
        
        # Debug: show raw response
        if debug:
            print(f"\n[DEBUG] Raw response length: {len(full_response)}")
            print(f"[DEBUG] First 200 chars: {repr(full_response[:200])}")
            
            # Show if we can find the tool marker
            if '{"tool"' in full_response:
                print("[DEBUG] Found '{{\"tool\"' in response")
                start = full_response.find('{"tool"')
                print(f"[DEBUG] JSON starts at position {start}")
        
        # Check for tool calls - strip whitespace first
        tool_call = self.parse_tool_call(full_response.strip())
        
        if tool_call:
            self.tool_call_count += 1  # ADD THIS LINE
            
            # ADD THIS CHECK:
            if self.tool_call_count > self.max_tool_calls:
                print(f"\n[WARNING: Maximum tool calls ({self.max_tool_calls}) reached. Stopping.]")
                return "I've made several tool calls but seem to be stuck. Please try rephrasing your request or reset the conversation with 'reset'."
            tool_type, parameters = tool_call
            print(f"\n[Executing: {tool_type.value}]")
            tool_result = self.execute_tool(tool_type, parameters)
            print(f"[Result: {tool_result[:150]}...]" if len(tool_result) > 150 else f"[Result: {tool_result}]")
            
            self.conversation_history.append(Message("assistant", full_response))
            self.conversation_history.append(Message("user", f"Tool result:\n{tool_result}"))

            # Add a stopping condition to prevent infinite loops
            continue_prompt = "Based on the tool result above, provide a final response to the user. If the task is complete, explain what was done. If more actions are needed, use ONE more tool."

            return self.chat(continue_prompt, stream=stream, debug=debug)
        else:
            if debug:
                print("[DEBUG] No tool call detected in response")
        
        self.conversation_history.append(Message("assistant", full_response))
        return full_response
    
    def _build_prompt(self) -> str:
        """Build prompt from conversation history (with limit to prevent overflow)"""
        MAX_MESSAGES = 12  # Keep system + last 11 messages
        
        if len(self.conversation_history) > MAX_MESSAGES:
            # Keep system prompt + recent messages
            messages = [self.conversation_history[0]]  # system prompt
            messages.append(Message("system", f"[{len(self.conversation_history) - MAX_MESSAGES} earlier messages truncated]"))
            messages.extend(self.conversation_history[-MAX_MESSAGES+2:])
        else:
            messages = self.conversation_history
        
        prompt_parts = []
        for msg in messages:
            prompt_parts.append(f"{msg.role.capitalize()}: {msg.content}\n")
        return "\n".join(prompt_parts)
    
    def reset(self):
        """Reset conversation history"""
        self.conversation_history = [Message("system", self.system_prompt)]
        self.file_memory = {}  # Also clear file memory


def main():
    """Main entry point"""
    print("=" * 60)
    print("AI Coder Agent - Local Edition")
    print("=" * 60)
    
    # Get server URL from user
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
    else:
        server_url = "https://testy-daniel-uninertly.ngrok-free.dev"
    
    workspace = input("Enter workspace directory (default: current directory): ").strip() or "."
    
    print("\nInitializing agent...")
    agent = LocalAICoderAgent(server_url=server_url, workspace_root=workspace)
    
    print("\nCommands:")
    print("  - Type your coding questions or requests")
    print("  - Type 'debug' to toggle debug mode")
    print("  - Type 'reset' to clear conversation history")
    print("  - Type 'exit' or 'quit' to stop")
    print("=" * 60)
    
    debug_mode = False
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\nGoodbye! Happy coding!")
                break
            
            if user_input.lower() == 'debug':
                debug_mode = not debug_mode
                print(f"\n[Debug mode: {'ON' if debug_mode else 'OFF'}]")
                continue
            
            if user_input.lower() == 'reset':
                agent.reset()
                print("\n[Conversation history cleared]")
                continue
            
            agent.chat(user_input, stream=True, debug=debug_mode)
            
        except KeyboardInterrupt:
            print("\n\nInterrupted. Type 'exit' to quit.")
        except Exception as e:
            print(f"\nError: {str(e)}")


if __name__ == "__main__":
    main()
