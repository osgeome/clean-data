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
    """Google Translate API implementation"""
    def __init__(self):
        self.base_url = "https://translation.googleapis.com/language/translate/v2"
        
    def translate(self, texts, target_lang, source_lang='auto', **kwargs):
        """Translate texts using Google Translate API
        
        Args:
            texts (list): List of texts to translate
            target_lang (str): Target language code
            source_lang (str): Source language code, defaults to 'auto'
            **kwargs: Additional arguments
            
        Returns:
            list: List of translated texts
            
        Raises:
            ValueError: If API key is not configured
            Exception: If translation fails
        """
        api_key = SettingsManager.get_google_api_key()
        if not api_key:
            raise ValueError("Google Translate API key not configured. Please add your API key in Settings.")
            
        translations = []
        for text in texts:
            # Skip empty texts
            if not text:
                translations.append("")
                continue
                
            try:
                params = {
                    'q': text,
                    'target': target_lang,
                    'key': api_key
                }
                
                if source_lang and source_lang != 'auto':
                    params['source'] = source_lang
                    
                response = requests.post(self.base_url, params=params)
                response.raise_for_status()
                
                data = response.json()
                if 'data' in data and 'translations' in data['data']:
                    translation = data['data']['translations'][0]['translatedText']
                    translations.append(translation)
                else:
                    raise Exception("Invalid response format from Google Translate API")
                    
            except requests.exceptions.RequestException as e:
                QgsMessageLog.logMessage(
                    f"Google Translate API error: {str(e)}",
                    'Clean Data',
                    Qgis.Warning
                )
                translations.append("")
                
        return translations

class OllamaService(TranslationService):
    """Ollama API implementation"""
    def __init__(self):
        base_url = SettingsManager.get_ollama_url()
        if not base_url:
            raise ValueError("Ollama URL not configured")
        # Remove any trailing slashes and add the correct endpoint
        self.url = base_url.rstrip('/') + '/api/generate'

    def translate(self, texts, target_lang, model='aya', batch_mode=True, batch_size=10, 
                 prompt_template=None, max_retries=2, **kwargs):
        """Translate texts using Ollama API
        
        Args:
            texts (list): List of texts to translate
            target_lang (str): Target language code
            model (str): Model name to use
            batch_mode (bool): Whether to use batch mode
            batch_size (int): Number of texts to translate at once in batch mode
            prompt_template (str): Template for the prompt
            max_retries (int): Maximum number of retries per batch
            **kwargs: Additional arguments
            
        Returns:
            list: List of translated texts
        """
        if not batch_mode:
            # Process one text at a time
            translations = []
            for text in texts:
                trans = self._translate_single(
                    text, 
                    target_lang, 
                    model, 
                    prompt_template,
                    max_retries
                )
                translations.append(trans)
            return translations
            
        # Process in batches
        translations = []
        total_texts = len(texts)
        processed = 0
        
        for i in range(0, total_texts, batch_size):
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

    def _translate_single(self, text, target_lang, model, prompt_template, max_retries):
        """Translate a single text"""
        retries = 0
        translation = None
        
        while retries <= max_retries and translation is None:
            try:
                # Format the prompt template
                prompt = prompt_template.format(
                    text=text,
                    target_lang=target_lang
                )
                
                data = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                }
                
                response = requests.post(self.url, json=data)
                response.raise_for_status()
                result = response.json()
                
                # Get the response content
                translation = result['response'].strip()
                
            except Exception as e:
                QgsMessageLog.logMessage(
                    f"Warning: Translation attempt {retries + 1} failed: {str(e)}", 
                    'Clean Data', 
                    Qgis.Warning
                )
                retries += 1
                
        if translation is None:
            raise ValueError(f"Failed to translate text after {max_retries} retries")
            
        return translation

    def _translate_batch(self, batch, target_lang, model, prompt_template, max_retries):
        """Translate a batch of texts"""
        batch_translations = None
        retries = 0
        
        QgsMessageLog.logMessage(
            f"Starting batch translation of {len(batch)} texts to {target_lang} using model {model}",
            'Clean Data',
            Qgis.Info
        )
        
        while retries <= max_retries and (batch_translations is None or len(batch_translations) != len(batch)):
            try:
                # Create indexed texts
                indexed_texts = [f"{idx+1}. {text}" for idx, text in enumerate(batch)]
                texts_str = "\n".join(indexed_texts)
                
                QgsMessageLog.logMessage(
                    f"Prepared batch input:\n{texts_str}",
                    'Clean Data',
                    Qgis.Info
                )
                
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
                
                QgsMessageLog.logMessage(
                    f"Sending request with prompt:\n{batch_prompt}",
                    'Clean Data',
                    Qgis.Info
                )
                
                data = {
                    "model": model,
                    "prompt": batch_prompt,
                    "stream": False
                }
                
                QgsMessageLog.logMessage(
                    f"Request payload:\n{str(data)}",
                    'Clean Data',
                    Qgis.Info
                )
                
                response = requests.post(self.url, json=data)
                response.raise_for_status()
                result = response.json()
                
                QgsMessageLog.logMessage(
                    f"Raw API response:\n{str(result)}",
                    'Clean Data',
                    Qgis.Info
                )
                
                # Parse and clean the response
                batch_translations = self._parse_translations_list(result['response'], len(batch))
                
                if batch_translations:
                    QgsMessageLog.logMessage(
                        f"Parsed translations ({len(batch_translations)}):\n" +
                        "\n".join(f"{i+1}. {t}" for i, t in enumerate(batch_translations)),
                        'Clean Data',
                        Qgis.Info
                    )
                else:
                    QgsMessageLog.logMessage(
                        "Failed to parse any translations from response",
                        'Clean Data',
                        Qgis.Warning
                    )
                
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
        """Parse the response text into a list of translations"""
        QgsMessageLog.logMessage(
            f"Starting to parse response text:\n{response_text}",
            'Clean Data',
            Qgis.Info
        )
        
        translations = []
        
        # Clean up the response text
        response_text = response_text.strip()
        QgsMessageLog.logMessage(
            f"Cleaned response text:\n{response_text}",
            'Clean Data',
            Qgis.Info
        )
        
        # Try to split by newlines first
        lines = [line.strip() for line in response_text.split('\n') if line.strip()]
        QgsMessageLog.logMessage(
            f"Split into {len(lines)} lines:\n" + "\n".join(f"Line {i+1}: {line}" for i, line in enumerate(lines)),
            'Clean Data',
            Qgis.Info
        )
        
        # Process each line
        for i, line in enumerate(lines):
            original_line = line
            # Remove common list markers and numbering
            line = line.strip()
            # Remove numbered prefixes like "1.", "2.", etc.
            line = line.lstrip('0123456789.- ')
            # Remove list markers
            line = line.lstrip('*•-[] ')
            
            QgsMessageLog.logMessage(
                f"Processing line {i+1}:\nOriginal: {original_line}\nCleaned: {line}",
                'Clean Data',
                Qgis.Info
            )
            
            if line:
                translations.append(line)
        
        # Log final results
        QgsMessageLog.logMessage(
            f"Parsed {len(translations)} translations, expected {expected_count}:\n" +
            "\n".join(f"{i+1}. {t}" for i, t in enumerate(translations)),
            'Clean Data',
            Qgis.Info
        )
        
        # Ensure we have exactly the expected number of translations
        if len(translations) >= expected_count:
            return translations[:expected_count]
        
        # If we don't have enough translations, return None to trigger a retry
        QgsMessageLog.logMessage(
            f"Not enough translations: got {len(translations)}, expected {expected_count}",
            'Clean Data',
            Qgis.Warning
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
        self.batch_size = batch_size
        self.prompt_template = prompt_template
        self.source_lang = source_lang
        self.instructions = instructions
        self.callback = callback
        
        # Initialize state
        self.features_to_translate = []
        self.total_features = 0
        self.translated_count = 0
        self.exception = None
        
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
                
                # Store feature data
                feature_data = {
                    'id': fid,
                    'text': text,
                    'translated': False
                }
                
                all_features.append(feature_data)
                if text:  # Only track non-empty values for translation
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
            
            # Process in smaller chunks
            chunk_size = 25  # Even smaller chunks
            batch_size = min(2, self.batch_size)  # Minimal batch size
            
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
                            if not self.layer.changeAttributeValue(fid, target_idx, translation):
                                QgsMessageLog.logMessage(
                                    f"Failed to update feature {fid}",
                                    'Clean Data',
                                    Qgis.Warning
                                )
                            else:
                                feature_map[fid]['translated'] = True
                                self.translated_count += 1
                        
                        # Report progress
                        progress = (self.translated_count / self.total_features) * 100
                        self.setProgress(progress)
                        
                        # Call progress callback
                        if self.callback:
                            self.callback(self)
                        
                        QgsMessageLog.logMessage(
                            f"Translated {self.translated_count}/{self.total_features} features...",
                            'Clean Data',
                            Qgis.Info
                        )
                    
                    QgsMessageLog.logMessage(
                        f"Processed chunk {chunk_start}-{chunk_end}",
                        'Clean Data',
                        Qgis.Info
                    )
                
                # Verify all features were translated
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
