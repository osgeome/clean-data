from qgis.core import QgsSettings
from typing import Optional

class SettingsManager:
    """Manages plugin settings using QgsSettings"""
    
    # Settings keys with proper prefix
    GOOGLE_API_KEY = 'clean_data/google_api_key'
    OPENAI_API_KEY = 'clean_data/openai_api_key'
    OPENAI_MODEL = 'clean_data/openai_model'
    DEEPSEEK_API_KEY = 'clean_data/deepseek_api_key'
    DEEPSEEK_MODEL = 'clean_data/deepseek_model'
    OLLAMA_URL = 'clean_data/ollama_url'
    OLLAMA_MODEL = 'clean_data/ollama_model'
    OLLAMA_BATCH_SIZE = 'clean_data/ollama_batch_size'
    
    # Default values
    DEFAULT_OLLAMA_MODEL = 'aya'
    DEFAULT_OLLAMA_BATCH_SIZE = 10
    DEFAULT_OPENAI_MODEL = 'gpt-3.5-turbo'
    DEFAULT_DEEPSEEK_MODEL = 'deepseek-chat'
    
    @classmethod
    def get_setting(cls, key, default=None):
        settings = QgsSettings()
        return settings.value(key, default)

    @classmethod
    def set_setting(cls, key, value):
        settings = QgsSettings()
        settings.setValue(key, value)

    @classmethod
    def get_google_api_key(cls) -> Optional[str]:
        return cls.get_setting(cls.GOOGLE_API_KEY)

    @classmethod
    def get_openai_api_key(cls) -> Optional[str]:
        return cls.get_setting(cls.OPENAI_API_KEY)
        
    @classmethod
    def get_openai_model(cls) -> str:
        return cls.get_setting(cls.OPENAI_MODEL, cls.DEFAULT_OPENAI_MODEL)

    @classmethod
    def get_deepseek_api_key(cls) -> Optional[str]:
        return cls.get_setting(cls.DEEPSEEK_API_KEY)
        
    @classmethod
    def get_deepseek_model(cls) -> str:
        return cls.get_setting(cls.DEEPSEEK_MODEL, cls.DEFAULT_DEEPSEEK_MODEL)

    @classmethod
    def get_ollama_url(cls) -> str:
        return cls.get_setting(cls.OLLAMA_URL, "http://localhost:11434")
        
    @classmethod
    def get_ollama_model(cls) -> str:
        return cls.get_setting(cls.OLLAMA_MODEL, cls.DEFAULT_OLLAMA_MODEL)
        
    @classmethod
    def get_ollama_batch_size(cls) -> int:
        value = cls.get_setting(cls.OLLAMA_BATCH_SIZE, cls.DEFAULT_OLLAMA_BATCH_SIZE)
        try:
            return int(value)
        except (TypeError, ValueError):
            return cls.DEFAULT_OLLAMA_BATCH_SIZE
