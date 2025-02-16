"""
Translation module for the Clean Data QGIS plugin.
Handles all translation-related functionality.
"""

from qgis.core import (QgsTask, QgsApplication, QgsMessageLog, Qgis, 
                      QgsVectorLayer, QgsField, QgsFeature, QgsFeatureRequest)
from PyQt5.QtCore import QVariant
import requests
import re
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
            raise ValueError("Google Cloud API key not configured. Please add your API key in Settings.")
            
        self.api_key = api_key
        self.base_url = "https://translation.googleapis.com/language/translate/v2"
        
    def _verify_api_key(self):
        """Verify the API key works"""
        try:
            # Try a simple translation to verify the key
            params = {
                'q': 'test',
                'target': 'ar',
                'key': self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=5)
            if response.status_code == 403:
                raise ValueError(
                    "Invalid or restricted Google API key. Please check:\n"
                    "1. The API key is correct\n"
                    "2. Cloud Translation API is enabled for your project\n"
                    "3. The API key has permission to use Cloud Translation API\n"
                    "4. You have billing enabled for your Google Cloud project"
                )
            
            response.raise_for_status()
            
            result = response.json()
            if 'error' in result:
                error_msg = result['error'].get('message', 'Unknown error')
                raise ValueError(f"API key verification failed: {error_msg}")
                
            QgsMessageLog.logMessage(
                "Google Translate API key verified successfully",
                'Clean Data',
                Qgis.Info
            )
            
        except requests.exceptions.RequestException as e:
            if '403' in str(e):
                raise ValueError(
                    "Invalid or restricted Google API key. Please check:\n"
                    "1. The API key is correct\n"
                    "2. Cloud Translation API is enabled for your project\n"
                    "3. The API key has permission to use Cloud Translation API\n"
                    "4. You have billing enabled for your Google Cloud project"
                )
            raise ValueError(f"Failed to verify Google Translate API key: {str(e)}")
            
    def translate(self, texts, target_lang, batch_mode=True, batch_size=50, 
                 source_lang='auto', **kwargs):
        """Translate texts using Google Cloud Translation API"""
        if not texts:
            return []
            
        # First verify API key to fail fast
        try:
            self._verify_api_key()
        except ValueError as e:
            QgsMessageLog.logMessage(
                f"Google Translate API verification failed: {str(e)}",
                'Clean Data',
                Qgis.Critical
            )
            # Return empty strings for all texts since we can't translate
            return [""] * len(texts)
            
        # Clean and validate input texts
        texts = [str(t).strip() for t in texts]
        texts = [t for t in texts if t]  # Remove empty texts
        
        if not texts:
            return []
            
        # Use a reasonable batch size (Google's limit is 128)
        batch_size = min(batch_size, 100)  # Use 100 as safe limit
        
        if not batch_mode or len(texts) == 1:
            return [self._translate_single(text, target_lang, source_lang)
                   for text in texts]
        
        # Process in batches
        all_translations = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                batch_translations = self._translate_batch(batch, target_lang, source_lang)
                if batch_translations:
                    all_translations.extend(batch_translations)
                else:
                    # If batch fails, try one by one
                    QgsMessageLog.logMessage(
                        f"Batch translation failed, falling back to single mode for {len(batch)} texts",
                        'Clean Data',
                        Qgis.Warning
                    )
                    for text in batch:
                        trans = self._translate_single(text, target_lang, source_lang)
                        all_translations.append(trans if trans else "")
                        
            except Exception as e:
                if '403' in str(e):
                    QgsMessageLog.logMessage(
                        "Google API authentication failed. Please check your API key and permissions.",
                        'Clean Data',
                        Qgis.Critical
                    )
                    # Fill remaining translations with empty strings
                    remaining = len(texts) - len(all_translations)
                    all_translations.extend([""] * remaining)
                    break  # Stop processing on auth error
                else:
                    QgsMessageLog.logMessage(
                        f"Error in batch {i//batch_size + 1}: {str(e)}",
                        'Clean Data',
                        Qgis.Warning
                    )
                    # Add empty strings for failed batch
                    all_translations.extend([""] * len(batch))
                
            # Log progress
            QgsMessageLog.logMessage(
                f"Translated {len(all_translations)}/{len(texts)} texts",
                'Clean Data',
                Qgis.Info
            )
            
        return all_translations
        
    def _translate_single(self, text, target_lang, source_lang='auto'):
        """Translate a single text"""
        if not text:
            return ""
            
        try:
            params = {
                'q': text,
                'target': target_lang,
                'key': self.api_key
            }
            
            if source_lang.lower() != 'auto':
                params['source'] = source_lang
                
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if 'data' in result and 'translations' in result['data']:
                translation = result['data']['translations'][0].get('translatedText', '')
                return translation.strip()
            else:
                QgsMessageLog.logMessage(
                    f"Invalid response format: {result}",
                    'Clean Data',
                    Qgis.Warning
                )
                return ""
                
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Translation failed: {str(e)}",
                'Clean Data',
                Qgis.Critical
            )
            return ""
            
    def _translate_batch(self, texts, target_lang, source_lang='auto'):
        """Translate a batch of texts"""
        if not texts:
            return []
            
        try:
            # Build query parameters
            params = {
                'q': texts,  # Google API accepts list of strings
                'target': target_lang,
                'key': self.api_key
            }
            
            if source_lang.lower() != 'auto':
                params['source'] = source_lang
                
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if 'data' in result and 'translations' in result['data']:
                return [t.get('translatedText', '').strip() for t in result['data']['translations']]
            else:
                QgsMessageLog.logMessage(
                    f"Invalid response format: {result}",
                    'Clean Data',
                    Qgis.Warning
                )
                return [""] * len(texts)
                
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Batch translation failed: {str(e)}",
                'Clean Data',
                Qgis.Critical
            )
            return [""] * len(texts)

class OllamaService(TranslationService):
    """Ollama API implementation"""
    
    def __init__(self):
        """Initialize Ollama service"""
        # Get base URL from settings
        base_url = SettingsManager.get_ollama_url()
        if not base_url:
            raise ValueError("Ollama URL not configured. Please set it in Settings.")
            
        self.base_url = base_url.rstrip('/')
        self.url = f"{self.base_url}/api/generate"
        
        # Get default model from settings
        self.default_model = SettingsManager.get_ollama_model()
        
        self._check_connection()
        
    def _check_connection(self):
        """Check connection to Ollama server and get available models"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            
            models = [model['name'] for model in response.json()['models']]
            QgsMessageLog.logMessage(
                f"Connected to Ollama server at {self.base_url}. Available models: {', '.join(models)}",
                'Clean Data',
                Qgis.Info
            )
            
            # Verify our default model is available
            if self.default_model not in models:
                QgsMessageLog.logMessage(
                    f"Warning: Default model '{self.default_model}' not found. Available models: {', '.join(models)}",
                    'Clean Data',
                    Qgis.Warning
                )
                # Use first available model as fallback
                self.default_model = models[0]
                
            QgsMessageLog.logMessage(
                f"Using Ollama model: {self.default_model}",
                'Clean Data',
                Qgis.Info
            )
            
        except Exception as e:
            raise ValueError(f"Failed to connect to Ollama server at {self.base_url}: {str(e)}")
            
    def translate(self, texts, target_lang, model=None, batch_mode=True, batch_size=5,
                 prompt_template=None, source_lang='auto', instructions=''):
        """Translate texts using Ollama API"""
        if not texts:
            return []
            
        # Use default model if none specified
        model = model or self.default_model
        
        # Convert all texts to strings and clean them
        texts = [str(text).strip() if text is not None else "" for text in texts]
        texts = [text for text in texts if text]  # Remove empty texts
        
        if not texts:
            return []
            
        # Use default prompt if none provided
        if not prompt_template:
            prompt_template = (
                "Translate the following text to {target_lang}. "
                "Only return the translation, no explanations:\n\n{text}"
            )
            
        # Process in batches or single mode
        if not batch_mode or len(texts) == 1:
            return [self._translate_single(text, target_lang, model, prompt_template)
                   for text in texts]
                   
        # Process in batches
        translations = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_translations = self._translate_batch(batch, target_lang, model, prompt_template)
            if batch_translations:
                translations.extend(batch_translations)
            else:
                # If batch fails, try one by one
                QgsMessageLog.logMessage(
                    f"Batch translation failed, falling back to single mode for {len(batch)} texts",
                    'Clean Data',
                    Qgis.Warning
                )
                for text in batch:
                    trans = self._translate_single(text, target_lang, model, prompt_template)
                    translations.append(trans if trans else "")
                    
        return translations
        
    def _translate_single(self, text, target_lang, model, prompt_template):
        """Translate a single text"""
        if not text:
            return ""
            
        try:
            # Format prompt with text
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
            QgsMessageLog.logMessage(
                f"Translation failed: {str(e)}",
                'Clean Data',
                Qgis.Critical
            )
            return ""
            
    def _translate_batch(self, texts, target_lang, model, prompt_template):
        """Translate a batch of texts"""
        if not texts:
            return []
            
        try:
            # Join texts with numbering for better context
            numbered_texts = "\n".join(f"{i+1}. {text}" for i, text in enumerate(texts))
            
            # Format prompt with all texts
            prompt = prompt_template.format(
                target_lang=target_lang,
                text=numbered_texts
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
                
            # Split response by numbers and clean up
            translation = result['response'].strip()
            translations = []
            
            # Try to split by numbered lines first
            lines = translation.split('\n')
            current_translation = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Check if line starts with a number
                if line[0].isdigit() and '. ' in line:
                    if current_translation:
                        translations.append(' '.join(current_translation))
                        current_translation = []
                    # Remove the number prefix
                    text = line.split('. ', 1)[1]
                    current_translation.append(text)
                else:
                    current_translation.append(line)
                    
            # Add the last translation
            if current_translation:
                translations.append(' '.join(current_translation))
                
            # If we didn't get the right number of translations, try simple line splitting
            if len(translations) != len(texts):
                translations = [line.strip() for line in translation.split('\n') if line.strip()]
                
            # Ensure we have the right number of translations
            if len(translations) != len(texts):
                QgsMessageLog.logMessage(
                    f"Got {len(translations)} translations, expected {len(texts)}",
                    'Clean Data',
                    Qgis.Warning
                )
                # Pad with empty strings if needed
                while len(translations) < len(texts):
                    translations.append("")
                # Truncate if we got too many
                translations = translations[:len(texts)]
                
            return translations
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Batch translation failed: {str(e)}",
                'Clean Data',
                Qgis.Critical
            )
            return [""] * len(texts)

class TranslationTask(QgsTask):
    """Task for handling translations in background"""
    
    def __init__(self, description, layer, source_field, target_field, service, 
                 target_lang='ar', model=None, batch_mode=True, batch_size=10,
                 prompt_template=None, source_lang='auto', instructions='', 
                 callback=None, skip_values=None):
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
        
        # Parse skip values
        self.skip_values = set()
        if skip_values:
            # Split by comma and strip whitespace
            self.skip_values = {v.strip() for v in skip_values.split(',')}
        
        # Initialize state
        self.features_to_translate = []
        self.total_features = 0
        self.translated_count = 0
        self.exception = None
        self.failed_features = []
        self.skipped_features = []
        
    def _should_skip_text(self, text, existing_translation=None):
        """Check if text should be skipped"""
        if text is None or str(text).strip() == "":
            return True
            
        # Skip if text matches any of the skip values
        if str(text).strip() in self.skip_values:
            return True
            
        # Skip if already translated
        if existing_translation and str(existing_translation).strip():
            return True
            
        return False
        
    def run(self):
        """Run the translation task"""
        try:
            # First, get all features and store them in memory
            all_features = []
            feature_map = {}
            
            # Get field indices
            source_idx = self.layer.fields().indexOf(self.source_field)
            if source_idx < 0:
                raise ValueError(f"Source field '{self.source_field}' not found in layer")
            
            # Create target field if it doesn't exist
            target_idx = self.layer.fields().indexOf(self.target_field)
            if target_idx < 0:
                if not self.layer.startEditing():
                    raise ValueError("Failed to start editing layer")
                self.layer.addAttribute(QgsField(self.target_field, QVariant.String))
                if not self.layer.commitChanges():
                    raise ValueError("Failed to add target field to layer")
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
            request.setSubsetOfAttributes([source_idx, target_idx])  # Get both source and target fields
            
            for feature in self.layer.getFeatures(request):
                fid = feature.id()
                source_text = feature[source_idx]
                existing_translation = feature[target_idx]
                
                # Skip if conditions are met
                if self._should_skip_text(source_text, existing_translation):
                    self.skipped_features.append(fid)
                    continue
                    
                # Store feature data
                feature_data = {
                    'id': fid,
                    'text': str(source_text).strip(),
                    'translated': False
                }
                
                all_features.append(feature_data)
                feature_map[fid] = feature_data
            
            self.total_features = len(feature_map)
            if self.total_features == 0:
                QgsMessageLog.logMessage(
                    f"No features to translate (skipped {len(self.skipped_features)} features)",
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
                raise ValueError("Failed to start editing layer")
            
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
                            # Don't continue retrying if it's an auth error
                            if '403' in str(e):
                                QgsMessageLog.logMessage(
                                    "Authentication error - stopping translation",
                                    'Clean Data',
                                    Qgis.Critical
                                )
                                self.layer.rollBack()
                                self.exception = ValueError(
                                    "Google API authentication failed. Please check your API key and permissions."
                                )
                                return False
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
                    raise ValueError("Failed to commit changes to layer")
                
                # Final verification
                final_count = self.layer.featureCount()
                if final_count != initial_count:
                    raise ValueError(
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
        # Always call the callback one last time to ensure UI is updated
        if self.callback:
            self.callback(self)
            
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
            # Add failed features to list
            self.failed_features.extend([feat.id() for feat in features])
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
                        instructions='', batch_mode=True, batch_size=10, progress_callback=None, skip_values=None):
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
            skip_values (str, optional): Comma-separated values to skip translation for. Defaults to None.
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
                callback=progress_callback,
                skip_values=skip_values
            )
            
            QgsApplication.taskManager().addTask(self.task)
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Failed to start translation: {str(e)}",
                'Clean Data',
                Qgis.Critical
            )
