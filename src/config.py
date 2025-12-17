import os
from dotenv import load_dotenv

load_dotenv()

# Load system prompt once on startup
def load_system_prompt():
    prompt_path = os.path.join(os.path.dirname(__file__), 'prompt.md')
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "You are a task parsing assistant. Extract task information and return JSON."

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///tasks.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Keep ANTHROPIC_API_KEY for backward compatibility
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    # New generic AI configuration
    AI_API_KEY = os.getenv('AI_API_KEY')
    AI_API_BASE_URL = os.getenv('AI_API_BASE_URL', 'https://api.openai.com/v1/')
    AI_MODEL = os.getenv('AI_MODEL', 'gpt-3.5-turbo')
    APP_PASSWORD = os.getenv('APP_PASSWORD', 'admin')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    SYSTEM_PROMPT = load_system_prompt()
