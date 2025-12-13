"""
AI Model Fallback System - Uses Gemini API with local Ollama as backup
"""
import os
import json
import requests
from typing import Optional, Dict, Any
import google.generativeai as genai

class AIModelManager:
    """Manages AI model requests with automatic fallback to local model"""
    
    def __init__(self):
        self.gemini_api_key = os.environ.get('GEMINI_API_KEY')
        self.ollama_base_url = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.ollama_model = os.environ.get('OLLAMA_MODEL', 'llama3.2')
        self.use_gemini = True
        
        if self.gemini_api_key:
            try:
                genai.configure(api_key=self.gemini_api_key)
                self.gemini_model = genai.GenerativeModel('gemini-2.5-flash')
            except Exception as e:
                print(f"Failed to configure Gemini: {e}")
                self.use_gemini = False
    
    def _check_ollama_available(self) -> bool:
        """Check if Ollama is running and accessible"""
        try:
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def _generate_with_gemini(self, prompt: str, **kwargs) -> Optional[str]:
        """Generate response using Gemini API"""
        try:
            response = self.gemini_model.generate_content(
                prompt,
                generation_config=kwargs.get('generation_config'),
                safety_settings=kwargs.get('safety_settings')
            )
            return response.text
        except Exception as e:
            print(f"Gemini API failed: {e}")
            return None
    
    def _generate_with_ollama(self, prompt: str, **kwargs) -> Optional[str]:
        """Generate response using local Ollama model"""
        try:
            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": kwargs.get('temperature', 0.7),
                    "top_p": kwargs.get('top_p', 0.9),
                }
            }
            
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json().get('response', '')
            return None
        except Exception as e:
            print(f"Ollama generation failed: {e}")
            return None
    
    def generate_content(self, prompt: str, **kwargs) -> str:
        """
        Generate content with automatic fallback
        Returns response text or error message
        """
        # Try Gemini first
        if self.use_gemini and self.gemini_api_key:
            result = self._generate_with_gemini(prompt, **kwargs)
            if result:
                return result
            print("⚠️ Gemini failed, switching to local model...")
        
        # Fallback to Ollama
        if self._check_ollama_available():
            result = self._generate_with_ollama(prompt, **kwargs)
            if result:
                print("✓ Using local Ollama model")
                return result
            print("❌ Local model also failed")
        else:
            print("❌ Ollama is not running. Install: https://ollama.com")
        
        return "Error: AI service temporarily unavailable. Please try again later."
    
    def generate_chat_response(self, messages: list, **kwargs) -> str:
        """Generate chat response with context"""
        # Convert messages to prompt
        prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        return self.generate_content(prompt, **kwargs)
    
    def extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from model response"""
        try:
            # Try direct parse
            return json.loads(text)
        except:
            # Try to find JSON in markdown code blocks
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except:
                    pass
            
            # Try to find raw JSON
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except:
                    pass
        return None

# Global instance
ai_manager = AIModelManager()

def generate_content(prompt: str, **kwargs) -> str:
    """Convenience function for generating content"""
    return ai_manager.generate_content(prompt, **kwargs)

def generate_chat_response(messages: list, **kwargs) -> str:
    """Convenience function for chat responses"""
    return ai_manager.generate_chat_response(messages, **kwargs)
