import requests
import json

class OllamaAPI:
    def __init__(self, host="localhost", port=11434):
        self.base_url = f"http://{host}:{port}"
        
    def generate(self, prompt, model="qwen2.5:7b", temperature=0.7):
        """Генерация текста через API"""
        url = f"{self.base_url}/api/generate"
        
        data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 2000
            }
        }
        
        try:
            response = requests.post(url, json=data, timeout=60)
            if response.status_code == 200:
                result = response.json()
                return result['response']
            else:
                return f"Ошибка API: {response.status_code}"
        except Exception as e:
            return f"Ошибка подключения: {e}"
    
    def chat(self, messages, model="qwen2.5:7b"):
        """Chat completion через API (более новый метод)"""
        url = f"{self.base_url}/api/chat"
        
        data = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.7
            }
        }
        
        try:
            response = requests.post(url, json=data, timeout=60)
            if response.status_code == 200:
                result = response.json()
                return result['message']['content']
            else:
                return f"Ошибка API: {response.status_code}"
        except Exception as e:
            return f"Ошибка подключения: {e}"