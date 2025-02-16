"""
Translation module for the Clean Data QGIS plugin.
Handles all translation-related functionality.
"""

from qgis.core import QgsMessageLog, Qgis, QgsVectorLayer
import requests
from .settings_manager import SettingsManager

class TranslationService:
    """Base class for translation services"""
    def translate(self, texts, target_lang, **kwargs):
        raise NotImplementedError("Subclasses must implement translate()")

class GoogleTranslateService(TranslationService):
    """Google Translate API implementation"""
    def translate(self, texts, target_lang, **kwargs):
        api_key = SettingsManager.get_google_api_key()
        if not api_key:
            raise ValueError("Google Translate API key not configured")
        # Implement Google Translate logic here
        pass

class OllamaService(TranslationService):
    """Ollama API implementation"""
    def __init__(self):
        self.url = SettingsManager.get_ollama_url()
        if not self.url:
            raise ValueError("Ollama URL not configured")
        if not self.url.endswith('/api/generate'):
            self.url = self.url.rstrip('/') + '/api/generate'

    def translate(self, texts, target_lang, model='aya', batch_size=10, prompt_template=None, max_retries=2):
        """Translate texts using Ollama API with batch processing"""
        translations = []
        total_texts = len(texts)
        processed = 0
        
        # Process texts in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_translations = self._translate_batch(
                batch, target_lang, model, prompt_template, max_retries
            )
            translations.extend(batch_translations)
            processed += len(batch)
            QgsMessageLog.logMessage(
                f"Translated {processed}/{total_texts} features...", 
                'Clean Data', 
                Qgis.Info
            )
        
        return translations

    def _translate_batch(self, batch, target_lang, model, prompt_template, max_retries):
        """Translate a single batch of texts"""
        batch_translations = None
        retries = 0
        
        while retries <= max_retries and (batch_translations is None or len(batch_translations) != len(batch)):
            try:
                # Create indexed texts
                indexed_texts = [f"{idx+1}. {text}" for idx, text in enumerate(batch)]
                texts_str = "\n".join(indexed_texts)
                
                # Format the prompt template
                batch_prompt = prompt_template.format(
                    batch_size=len(batch),
                    target_lang=target_lang,
                    texts=texts_str
                )
                
                # Add emphasis on retries
                if retries > 0:
                    emphasis = "!" * retries
                    batch_prompt = batch_prompt.replace("Rules:", f"Rules{emphasis}:")
                    batch_prompt = batch_prompt.replace("items", f"items{emphasis}")
                    batch_prompt = f"STRICT MODE: YOU MUST RETURN EXACTLY THE RIGHT NUMBER OF TRANSLATIONS!\n{batch_prompt}"
                
                data = {
                    "model": model,
                    "prompt": batch_prompt,
                    "stream": False
                }
                
                response = requests.post(self.url, json=data)
                response.raise_for_status()
                result = response.json()
                
                # Log the raw response for debugging
                QgsMessageLog.logMessage(
                    f"Raw response for batch {batch}: {result['response']}", 
                    'Clean Data', 
                    Qgis.Info
                )
                
                # Parse and clean the response
                batch_translations = self._parse_translations_list(result['response'], len(batch))
                
                # Validate batch result length
                if len(batch_translations) != len(batch):
                    if retries < max_retries:
                        QgsMessageLog.logMessage(
                            f"Retry {retries + 1}: Got {len(batch_translations)} translations, expected {len(batch)}", 
                            'Clean Data', 
                            Qgis.Warning
                        )
                        retries += 1
                        continue
                    else:
                        raise ValueError(f"Expected {len(batch)} translations but got {len(batch_translations)}")
                
                break
                
            except Exception as e:
                if retries < max_retries:
                    QgsMessageLog.logMessage(
                        f"Retry {retries + 1}: {str(e)}", 
                        'Clean Data', 
                        Qgis.Warning
                    )
                    retries += 1
                    continue
                QgsMessageLog.logMessage(
                    f"Translation error: {str(e)}", 
                    'Clean Data', 
                    Qgis.Critical
                )
                raise
        
        return batch_translations

    def _parse_translations_list(self, response_text, expected_count):
        """Parse and clean translations list from response text"""
        import re
        
        # First try to find a proper Python list
        list_match = re.search(r'\[.*?\]', response_text, re.DOTALL)
        if list_match:
            try:
                # Try to safely evaluate the list
                list_str = list_match.group()
                translations = eval(list_str)
                if isinstance(translations, list):
                    return [t.strip() for t in translations]
            except:
                pass
        
        # If that fails, try to extract translations more aggressively
        translations = []
        
        # Remove common prefixes/suffixes that might confuse the parser
        clean_text = response_text.replace('Here are the translations:', '')
        clean_text = re.sub(r'^.*?\[', '[', clean_text, flags=re.DOTALL)
        clean_text = re.sub(r'\].*?$', ']', clean_text, flags=re.DOTALL)
        
        # Try to find all Arabic text segments
        arabic_pattern = r'[\'"]([^\'"\n]+?)[\'"]'
        matches = re.findall(arabic_pattern, clean_text)
        
        if matches:
            translations = [m.strip() for m in matches]
            
            # If we got more translations than expected, trim to expected count
            if len(translations) > expected_count:
                translations = translations[:expected_count]
                
            # If we got fewer translations, try alternative parsing
            if len(translations) < expected_count:
                # Try splitting by commas and cleaning
                parts = clean_text.split(',')
                translations = []
                for part in parts:
                    # Clean each part
                    part = part.strip(' []\'\"')
                    if part and not part.lower().startswith(('here', 'translation')):
                        translations.append(part)
        
        return translations

class TranslationManager:
    """Factory class for creating and managing translation services"""
    @staticmethod
    def get_service(service_name):
        services = {
            'Google Translate': GoogleTranslateService,
            'Ollama': OllamaService,
            # Add other services here
        }
        
        if service_name not in services:
            raise ValueError(f"Unknown translation service: {service_name}")
            
        return services[service_name]()
