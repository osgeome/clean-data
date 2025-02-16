"""
Settings manager module for the Clean Data QGIS plugin.
Handles all settings and configuration.
"""

from qgis.core import QgsSettings

class SettingsManager:
    """Manages plugin settings and configuration"""
    
    SETTINGS_PREFIX = "CleanData/"
    
    @classmethod
    def get_setting(cls, key, default=None):
        """Get a setting value"""
        settings = QgsSettings()
        full_key = cls.SETTINGS_PREFIX + key
        return settings.value(full_key, default)
    
    @classmethod
    def set_setting(cls, key, value):
        """Set a setting value"""
        settings = QgsSettings()
        full_key = cls.SETTINGS_PREFIX + key
        settings.setValue(full_key, value)
    
    # API Keys
    @classmethod
    def get_google_api_key(cls):
        """Get Google Translate API key"""
        return cls.get_setting("google_api_key")
    
    @classmethod
    def set_google_api_key(cls, key):
        """Set Google Translate API key"""
        cls.set_setting("google_api_key", key)
    
    @classmethod
    def get_ollama_url(cls):
        """Get Ollama API URL"""
        return cls.get_setting("ollama_url", "http://localhost:11434")
    
    @classmethod
    def set_ollama_url(cls, url):
        """Set Ollama API URL"""
        cls.set_setting("ollama_url", url)
    
    @classmethod
    def get_openai_api_key(cls):
        """Get OpenAI API key"""
        return cls.get_setting("openai_api_key")
    
    @classmethod
    def set_openai_api_key(cls, key):
        """Set OpenAI API key"""
        cls.set_setting("openai_api_key", key)
    
    @classmethod
    def get_deepseek_api_key(cls):
        """Get DeepSeek API key"""
        return cls.get_setting("deepseek_api_key")
    
    @classmethod
    def set_deepseek_api_key(cls, key):
        """Set DeepSeek API key"""
        cls.set_setting("deepseek_api_key", key)
    
    # Model Settings
    @classmethod
    def get_ollama_model(cls):
        """Get Ollama model name"""
        return cls.get_setting("ollama_model", "aya")
    
    @classmethod
    def set_ollama_model(cls, model):
        """Set Ollama model name"""
        cls.set_setting("ollama_model", model)
    
    @classmethod
    def get_openai_model(cls):
        """Get OpenAI model name"""
        return cls.get_setting("openai_model", "gpt-3.5-turbo")
    
    @classmethod
    def set_openai_model(cls, model):
        """Set OpenAI model name"""
        cls.set_setting("openai_model", model)
    
    @classmethod
    def get_deepseek_model(cls):
        """Get DeepSeek model name"""
        return cls.get_setting("deepseek_model", "deepseek-chat")
    
    @classmethod
    def set_deepseek_model(cls, model):
        """Set DeepSeek model name"""
        cls.set_setting("deepseek_model", model)
    
    # Batch Settings
    @classmethod
    def get_batch_size(cls):
        """Get translation batch size"""
        return int(cls.get_setting("batch_size", 10))
    
    @classmethod
    def set_batch_size(cls, size):
        """Set translation batch size"""
        cls.set_setting("batch_size", int(size))
    
    @classmethod
    def get_all_settings(cls):
        """Get all plugin settings"""
        settings = QgsSettings()
        all_settings = {}
        settings.beginGroup(cls.SETTINGS_PREFIX)
        for key in settings.childKeys():
            all_settings[key] = settings.value(key)
        settings.endGroup()
        return all_settings
    
    @classmethod
    def clear_all_settings(cls):
        """Clear all plugin settings"""
        settings = QgsSettings()
        settings.beginGroup(cls.SETTINGS_PREFIX)
        settings.remove("")
        settings.endGroup()
