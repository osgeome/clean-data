"""
Translation module for the Clean Data QGIS plugin.
Handles all translation-related functionality.
"""

from qgis.core import (QgsTask, QgsApplication, QgsMessageLog, Qgis, 
                      QgsVectorLayer, QgsField, QgsFeature, QgsFeatureRequest)
from PyQt5.QtCore import QVariant
import requests
from .settings_manager import SettingsManager

class TranslationService:
    """Base class for translation services"""
    def translate(self, texts, target_lang, **kwargs):
        raise NotImplementedError("Subclasses must implement translate()")

class GoogleTranslateService(TranslationService):
    """Google Cloud Translation API implementation"""
    
    def __init__(self):
        # Get API key from settings
        api_key = SettingsManager.get_google_api_key()
        if not api_key:
            raise ValueError("Google Cloud API key not configured")
            
        self.api_key = api_key
        self.base_url = "https://translation.googleapis.com/language/translate/v2"
        self._verify_api_key()
        
    def _verify_api_key(self):
        """Verify the API key works"""
        try:
            # Try a simple translation to verify the key
            test_data = {
                'q': 'test',
                'target': 'ar',
                'key': self.api_key
            }
            
            response = requests.post(self.base_url, json=test_data, timeout=5)
            response.raise_for_status()
            
            result = response.json()
            if 'error' in result:
                raise ValueError(f"API key verification failed: {result['error']['message']}")
                
            QgsMessageLog.logMessage(
                "Google Translate API key verified successfully",
                'Clean Data',
                Qgis.Info
            )
            
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Failed to verify Google Translate API key: {str(e)}")
            
    def translate(self, texts, target_lang, batch_mode=True, batch_size=128, 
                 source_lang='auto', **kwargs):
        """Translate texts using Google Cloud Translation API"""
        if not texts:
            return []
            
        # Use a reasonable batch size
        batch_size = min(batch_size, 128)  # Google's limit is 128
        
        if not batch_mode or len(texts) == 1:
            return [self._translate_single(text, target_lang, source_lang)
                   for text in texts]
        
        # Process in batches
        translations = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_translations = self._translate_batch(batch, target_lang, source_lang)
            translations.extend(batch_translations)
            
        return translations
        
    def _translate_single(self, text, target_lang, source_lang='auto'):
        """Translate a single text"""
        if not text:
            return ""
            
        try:
            data = {
                'q': text,
                'target': target_lang,
                'key': self.api_key
            }
            
            if source_lang != 'auto':
                data['source'] = source_lang
                
            response = requests.post(self.base_url, json=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if 'error' in result:
                raise ValueError(f"Translation error: {result['error']['message']}")
                
            translations = result.get('data', {}).get('translations', [])
            if not translations:
                raise ValueError("No translation received")
                
            return translations[0]['translatedText']
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Translation failed: {str(e)}",
                'Clean Data',
                Qgis.Critical
            )
            return ""
            
    def _translate_batch(self, batch, target_lang, source_lang='auto'):
        """Translate a batch of texts"""
        if not batch:
            return []
            
        try:
            data = {
                'q': batch,
                'target': target_lang,
                'key': self.api_key
            }
            
            if source_lang != 'auto':
                data['source'] = source_lang
                
            response = requests.post(self.base_url, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if 'error' in result:
                raise ValueError(f"Translation error: {result['error']['message']}")
                
            translations = result.get('data', {}).get('translations', [])
            if not translations:
                raise ValueError("No translations received")
                
            if len(translations) != len(batch):
                raise ValueError(f"Got {len(translations)} translations, expected {len(batch)}")
                
            return [t['translatedText'] for t in translations]
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Batch translation failed: {str(e)}",
                'Clean Data',
                Qgis.Critical
            )
            # Return empty strings for failed batch
            return [""] * len(batch)

class OllamaService(TranslationService):
    """Ollama API implementation"""
    def __init__(self):
        base_url = SettingsManager.get_ollama_url()
        if not base_url:
            raise ValueError("Ollama URL not configured")
        self.url = base_url.rstrip('/') + '/api/generate'
        self._verify_connection()
        
    def _verify_connection(self):
        """Verify Ollama server connectivity"""
        try:
            # Check basic server connectivity
            base_url = self.url.replace('/api/generate', '')
            response = requests.get(base_url, timeout=5)
            if response.status_code != 200:
                raise ValueError(f"Ollama server returned status {response.status_code}")
                
            # Check model availability
            models_url = base_url + '/api/tags'
            models_response = requests.get(models_url, timeout=5)
            if models_response.status_code != 200:
                raise ValueError("Failed to get available models")
                
            models = models_response.json().get('models', [])
            if not models:
                raise ValueError("No models available on Ollama server")
                
            QgsMessageLog.logMessage(
                f"Connected to Ollama server. Available models: {', '.join(m['name'] for m in models)}",
                'Clean Data',
                Qgis.Info
            )
            
        except requests.exceptions.ConnectionError:
            raise ValueError(f"Cannot connect to Ollama server at {self.url}. Is the server running?")
        except requests.exceptions.Timeout:
            raise ValueError("Connection to Ollama server timed out")
        except Exception as e:
            raise ValueError(f"Failed to verify Ollama server: {str(e)}")

    def translate(self, texts, target_lang, model='aya', batch_mode=True, batch_size=5, 
                 prompt_template=None, max_retries=2, **kwargs):
        """Translate texts using Ollama API"""
        if not texts:
            return []
            
        # Get default prompt templates if none provided
        if not prompt_template:
            if batch_mode and len(texts) > 1:
                prompt_template = SettingsManager.DEFAULT_BATCH_TRANSLATION_PROMPT
            else:
                prompt_template = SettingsManager.DEFAULT_SINGLE_TRANSLATION_PROMPT
        
        # Use smaller batch size for safety
        batch_size = min(batch_size, 5)
        
        if not batch_mode:
            return [self._translate_single(text, target_lang, model, prompt_template, max_retries)
                   for text in texts]
        
        # Process in batches
        translations = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_translations = self._translate_batch(
                batch, target_lang, model, prompt_template, max_retries
            )
            if batch_translations:
                translations.extend(batch_translations)
            else:
                # If batch fails, try one by one
                QgsMessageLog.logMessage(
                    "Batch translation failed, falling back to single mode",
                    'Clean Data',
                    Qgis.Warning
                )
                for text in batch:
                    trans = self._translate_single(
                        text, target_lang, model, prompt_template, max_retries
                    )
                    translations.append(trans if trans else "")
                    
        return translations

    def _translate_single(self, text, target_lang, model, prompt_template, max_retries):
        """Translate a single text"""
        if not text:
            return ""
            
        for attempt in range(max_retries + 1):
            try:
                prompt = prompt_template.format(
                    target_lang=target_lang,
                    text=text
                )
                
                data = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                }
                
                response = requests.post(self.url, json=data, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                if not result or 'response' not in result:
                    raise ValueError("Invalid response format")
                    
                translation = result['response'].strip()
                if not translation:
                    raise ValueError("Empty translation received")
                    
                return translation
                
            except Exception as e:
                if attempt < max_retries:
                    QgsMessageLog.logMessage(
                        f"Retry {attempt + 1}/{max_retries}: {str(e)}",
                        'Clean Data',
                        Qgis.Warning
                    )
                    continue
                QgsMessageLog.logMessage(
                    f"Translation failed: {str(e)}",
                    'Clean Data',
                    Qgis.Critical
                )
                return ""

    def _translate_batch(self, batch, target_lang, model, prompt_template, max_retries):
        """Translate a batch of texts"""
        if not batch:
            return []
            
        for attempt in range(max_retries + 1):
            try:
                # Create indexed texts
                texts_str = "\n".join(f"{i+1}. {text}" for i, text in enumerate(batch))
                
                # Format prompt
                prompt = prompt_template.format(
                    batch_size=len(batch),
                    target_lang=target_lang,
                    texts=texts_str
                )
                
                data = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                }
                
                response = requests.post(self.url, json=data, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                if not result or 'response' not in result:
                    raise ValueError("Invalid response format")
                    
                # Parse translations
                translations = []
                response_text = result['response'].strip()
                lines = [line.strip() for line in response_text.split('\n') if line.strip()]
                
                for line in lines:
                    # Remove numbering and other markers
                    cleaned = line.lstrip('0123456789.)-][ *•-').strip()
                    if cleaned:
                        translations.append(cleaned)
                
                # Validate translation count
                if len(translations) != len(batch):
                    raise ValueError(f"Got {len(translations)} translations, expected {len(batch)}")
                    
                return translations
                
            except Exception as e:
                if attempt < max_retries:
                    QgsMessageLog.logMessage(
                        f"Retry {attempt + 1}/{max_retries}: {str(e)}",
                        'Clean Data',
                        Qgis.Warning
                    )
                    continue
                QgsMessageLog.logMessage(
                    f"Batch translation failed: {str(e)}",
                    'Clean Data',
                    Qgis.Critical
                )
                return None

class TranslationTask(QgsTask):
    """Task for handling translations in background"""
    
    def __init__(self, description, layer, source_field, target_field, service, 
                 target_lang='ar', model=None, batch_mode=True, batch_size=10,
                 prompt_template=None, source_lang='auto', instructions='', 
                 callback=None):
        super().__init__(description, QgsTask.CanCancel)
        
        # Store parameters
        self.layer = layer
        self.source_field = source_field
        self.target_field = target_field
        self.service = service
        self.target_lang = target_lang
        self.model = model
        self.batch_mode = batch_mode
        self.batch_size = min(batch_size, 5)  # Limit batch size for safety
        self.prompt_template = prompt_template
        self.source_lang = source_lang
        self.instructions = instructions
        self.callback = callback
        
        # Initialize state
        self.features_to_translate = []
        self.total_features = 0
        self.translated_count = 0
        self.exception = None
        self.failed_features = []
        
    def run(self):
        """Run the translation task"""
        try:
            # First, get all features and store them in memory
            all_features = []
            feature_map = {}
            
            # Get source field index first
            source_idx = self.layer.fields().indexOf(self.source_field)
            if source_idx < 0:
                raise ValueError(f"Source field '{self.source_field}' not found in layer")
            
            # Create target field if it doesn't exist
            target_idx = self.layer.fields().indexOf(self.target_field)
            if target_idx < 0:
                self.layer.startEditing()
                self.layer.addAttribute(QgsField(self.target_field, QVariant.String))
                if not self.layer.commitChanges():
                    raise Exception("Failed to add target field to layer")
                target_idx = self.layer.fields().indexOf(self.target_field)
            
            # Store initial feature count for verification
            initial_count = self.layer.featureCount()
            QgsMessageLog.logMessage(
                f"Initial feature count: {initial_count}",
                'Clean Data',
                Qgis.Info
            )
            
            # Safely get all features first
            request = QgsFeatureRequest()
            request.setFlags(QgsFeatureRequest.NoGeometry)  # We don't need geometry
            request.setSubsetOfAttributes([source_idx])  # Only get the source field
            
            for feature in self.layer.getFeatures(request):
                fid = feature.id()
                text = feature[source_idx]
                
                # Skip empty or whitespace-only texts
                if not text or not str(text).strip():
                    continue
                    
                # Store feature data
                feature_data = {
                    'id': fid,
                    'text': str(text).strip(),
                    'translated': False
                }
                
                all_features.append(feature_data)
                feature_map[fid] = feature_data
            
            self.total_features = len(feature_map)
            if self.total_features == 0:
                QgsMessageLog.logMessage(
                    "No features to translate",
                    'Clean Data',
                    Qgis.Warning
                )
                return True
            
            QgsMessageLog.logMessage(
                f"Found {self.total_features} features with non-empty values to translate",
                'Clean Data',
                Qgis.Info
            )
            
            # Process in smaller chunks with minimal batch size
            chunk_size = 25  # Process 25 features at a time
            batch_size = min(2, self.batch_size)  # Start with small batches
            
            # Start editing once for all changes
            if not self.layer.startEditing():
                raise Exception("Failed to start editing layer")
            
            try:
                # Process features in chunks
                feature_ids = list(feature_map.keys())
                for chunk_start in range(0, len(feature_ids), chunk_size):
                    if self.isCanceled():
                        self.layer.rollBack()
                        return False
                    
                    chunk_end = min(chunk_start + chunk_size, len(feature_ids))
                    chunk_ids = feature_ids[chunk_start:chunk_end]
                    
                    # Process in small batches
                    for i in range(0, len(chunk_ids), batch_size):
                        if self.isCanceled():
                            self.layer.rollBack()
                            return False
                        
                        batch_ids = chunk_ids[i:i + batch_size]
                        batch_texts = [feature_map[fid]['text'] for fid in batch_ids]
                        
                        try:
                            # Translate batch
                            translations = self.service.translate(
                                texts=batch_texts,
                                target_lang=self.target_lang,
                                model=self.model,
                                batch_mode=self.batch_mode,
                                batch_size=len(batch_texts),
                                prompt_template=self.prompt_template,
                                source_lang=self.source_lang,
                                instructions=self.instructions
                            )
                            
                            # Update features
                            for fid, translation in zip(batch_ids, translations):
                                if translation:  # Only update if we got a translation
                                    if self.layer.changeAttributeValue(fid, target_idx, translation):
                                        feature_map[fid]['translated'] = True
                                        self.translated_count += 1
                                    else:
                                        self.failed_features.append(fid)
                                        QgsMessageLog.logMessage(
                                            f"Failed to update feature {fid}",
                                            'Clean Data',
                                            Qgis.Warning
                                        )
                            
                            # Report progress
                            progress = (self.translated_count / self.total_features) * 100
                            self.setProgress(progress)
                            
                            # Call progress callback
                            if self.callback:
                                self.callback(self)
                            
                        except Exception as e:
                            QgsMessageLog.logMessage(
                                f"Error processing batch: {str(e)}",
                                'Clean Data',
                                Qgis.Warning
                            )
                            # Add failed features to list
                            self.failed_features.extend(batch_ids)
                            continue
                        
                        QgsMessageLog.logMessage(
                            f"Translated {self.translated_count}/{self.total_features} features...",
                            'Clean Data',
                            Qgis.Info
                        )
                    
                # Verify results
                untranslated = [
                    fid for fid, data in feature_map.items() 
                    if not data['translated']
                ]
                
                if untranslated:
                    QgsMessageLog.logMessage(
                        f"Warning: {len(untranslated)} features were not translated",
                        'Clean Data',
                        Qgis.Warning
                    )
                
                # Commit changes
                if not self.layer.commitChanges():
                    raise Exception("Failed to commit changes to layer")
                
                # Final verification
                final_count = self.layer.featureCount()
                if final_count != initial_count:
                    raise Exception(
                        f"Layer corruption detected! Initial count: {initial_count}, "
                        f"Final count: {final_count}"
                    )
                
                return True
                
            except Exception as e:
                self.layer.rollBack()
                raise e
            
        except Exception as e:
            self.exception = e
            QgsMessageLog.logMessage(
                f"Translation failed: {str(e)}",
                'Clean Data',
                Qgis.Critical
            )
            return False

    def finished(self, result):
        """Called when the task is complete"""
        if result:
            if self.failed_features:
                QgsMessageLog.logMessage(
                    f"Translation completed with {len(self.failed_features)} failed features",
                    'Clean Data',
                    Qgis.Warning
                )
            else:
                QgsMessageLog.logMessage(
                    "Translation completed successfully",
                    'Clean Data',
                    Qgis.Success
                )
        elif self.exception:
            QgsMessageLog.logMessage(
                f"Translation failed: {str(self.exception)}",
                'Clean Data',
                Qgis.Critical
            )
        else:
            QgsMessageLog.logMessage(
                "Translation was cancelled",
                'Clean Data',
                Qgis.Warning
            )
            
    def process_batch(self, texts, features, target_idx):
        """Process a batch of texts"""
        try:
            # Translate the batch
            translations = self.service.translate(
                texts=texts,
                target_lang=self.target_lang,
                model=self.model,
                batch_mode=self.batch_mode,
                batch_size=len(texts),
                prompt_template=self.prompt_template,
                source_lang=self.source_lang,
                instructions=self.instructions
            )
            
            # Update features
            for feat, trans in zip(features, translations):
                if not self.layer.changeAttributeValue(feat.id(), target_idx, trans):
                    QgsMessageLog.logMessage(
                        f"Failed to update feature {feat.id()}",
                        'Clean Data',
                        Qgis.Warning
                    )
                self.translated_count += 1
                
            # Report progress
            progress = (self.translated_count / self.total_features) * 100
            self.setProgress(progress)
            
            # Call progress callback if provided
            if self.callback:
                self.callback(self)
            
            QgsMessageLog.logMessage(
                f"Translated {self.translated_count}/{self.total_features} features...",
                'Clean Data',
                Qgis.Info
            )
            
            return True
            
        except Exception as e:
            self.exception = e
            QgsMessageLog.logMessage(
                f"Batch translation error: {str(e)}. Continuing with next batch...",
                'Clean Data',
                Qgis.Warning
            )
            return False

class TranslationManager:
    """Manager class for handling translations"""
    
    def __init__(self):
        self.task = None
        
    def get_service(self, service_name):
        """Get translation service instance based on name"""
        service_name = service_name.lower().replace(' ', '')
        if service_name in ['google', 'googletranslate']:
            return GoogleTranslateService()
        elif service_name in ['ollama', 'ollamaapi']:
            return OllamaService()
        else:
            raise ValueError(f"Unknown translation service: {service_name}")
            
    def translate_column(self, layer, source_field, target_field, prompt_template=None, 
                        service_name='Ollama', model=None, source_lang='auto', target_lang='ar', 
                        instructions='', batch_mode=True, batch_size=10, progress_callback=None):
        """Translate a column in a vector layer using background task
        
        Args:
            layer (QgsVectorLayer): The layer containing the field to translate
            source_field (str): Name of the field to translate
            target_field (str): Name of the new field to create with translations
            prompt_template (str, optional): Template for AI services. Defaults to None.
            service_name (str, optional): Translation service to use. Defaults to 'Ollama'.
            model (str, optional): Model name for AI services. Defaults to None.
            source_lang (str, optional): Source language code. Defaults to 'auto'.
            target_lang (str, optional): Target language code. Defaults to 'ar'.
            instructions (str, optional): Additional instructions. Defaults to ''.
            batch_mode (bool, optional): Whether to use batch mode. Defaults to True.
            batch_size (int, optional): Number of texts to translate at once in batch mode. Defaults to 10.
            progress_callback (callable, optional): Callback function for progress updates. Defaults to None.
        """
        try:
            # Get translation service
            service = self.get_service(service_name)
            
            # Get default model if none specified
            if model is None and service_name.lower() == 'ollama':
                model = SettingsManager.get_ollama_model()
                QgsMessageLog.logMessage(
                    f"Using default Ollama model: {model}",
                    'Clean Data',
                    Qgis.Info
                )
            
            # Get default prompt template if none specified
            if prompt_template is None:
                if batch_mode:
                    prompt_template = SettingsManager.get_batch_translation_prompt()
                else:
                    prompt_template = SettingsManager.get_translation_prompt()
            
            # Create and start the translation task
            description = f"Translating {source_field} to {target_field}"
            self.task = TranslationTask(
                description=description,
                layer=layer,
                source_field=source_field,
                target_field=target_field,
                service=service,
                target_lang=target_lang,
                model=model,
                batch_mode=batch_mode,
                batch_size=batch_size,
                prompt_template=prompt_template,
                source_lang=source_lang,
                instructions=instructions,
                callback=progress_callback
            )
            
            QgsApplication.taskManager().addTask(self.task)
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Failed to start translation: {str(e)}",
                'Clean Data',
                Qgis.Critical
            )
