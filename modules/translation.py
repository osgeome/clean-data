"""
Translation module for the Clean Data QGIS plugin.
Handles all translation-related functionality.
"""

from qgis.core import (QgsTask, QgsApplication, QgsMessageLog, Qgis, 
                      QgsVectorLayer, QgsField, QgsFeature)
from PyQt5.QtCore import QVariant
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
                 prompt_template=None, source_lang='auto', instructions=''):
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
        
        # Initialize state
        self.features_to_translate = []
        self.total_features = 0
        self.translated_count = 0
        self.exception = None
        
    def prepare_features(self):
        """Get features that need translation"""
        source_idx = self.layer.fields().indexOf(self.source_field)
        target_idx = self.layer.fields().indexOf(self.target_field)
        
        # Add target field if it doesn't exist
        if target_idx == -1:
            self.layer.dataProvider().addAttributes([QgsField(self.target_field, QVariant.String)])
            self.layer.updateFields()
            target_idx = self.layer.fields().indexOf(self.target_field)
            
        # Get features needing translation
        for feature in self.layer.getFeatures():
            source_text = feature[self.source_field]
            target_text = feature[self.target_field]
            
            # Skip if source is empty or target already has value
            if not source_text or (target_text and str(target_text).strip()):
                continue
                
            self.features_to_translate.append(feature)
            
        self.total_features = len(self.features_to_translate)
        return self.total_features > 0
        
    def run(self):
        """Run the task in background"""
        try:
            if not self.prepare_features():
                return True
                
            QgsMessageLog.logMessage(
                f"Starting translation of {self.total_features} features...",
                'Clean Data',
                Qgis.Info
            )
            
            # Process in batches
            current_batch = []
            batch_features = []
            target_idx = self.layer.fields().indexOf(self.target_field)
            
            self.layer.startEditing()
            
            for feature in self.features_to_translate:
                if self.isCanceled():
                    return False
                    
                text = str(feature[self.source_field])
                if text:
                    current_batch.append(text)
                    batch_features.append(feature)
                    
                    # Process batch when it reaches size limit
                    if len(current_batch) >= self.batch_size:
                        success = self.process_batch(current_batch, batch_features, target_idx)
                        if not success:
                            return False
                        current_batch = []
                        batch_features = []
                        
            # Process remaining items
            if current_batch and not self.isCanceled():
                success = self.process_batch(current_batch, batch_features, target_idx)
                if not success:
                    return False
                    
            return True
            
        except Exception as e:
            self.exception = e
            return False
            
    def process_batch(self, texts, features, target_idx):
        """Process a batch of texts"""
        try:
            translations = self.service.translate(
                texts=texts,
                target_lang=self.target_lang,
                model=self.model,
                batch_mode=self.batch_mode,
                batch_size=self.batch_size,
                prompt_template=self.prompt_template,
                source_lang=self.source_lang,
                instructions=self.instructions
            )
            
            # Update features with translations
            for feat, trans in zip(features, translations):
                self.layer.changeAttributeValue(feat.id(), target_idx, trans)
                self.translated_count += 1
                
            # Commit changes after each batch
            if not self.layer.commitChanges():
                QgsMessageLog.logMessage(
                    "Failed to commit changes to layer",
                    'Clean Data',
                    Qgis.Warning
                )
            self.layer.startEditing()
            
            # Report progress
            progress = (self.translated_count / self.total_features) * 100
            self.setProgress(progress)
            
            QgsMessageLog.logMessage(
                f"Translated {self.translated_count}/{self.total_features} features...",
                'Clean Data',
                Qgis.Info
            )
            
            return True
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Batch translation error: {str(e)}. Continuing with next batch...",
                'Clean Data',
                Qgis.Warning
            )
            return False
            
    def finished(self, result):
        """Called when the task is complete"""
        if result:
            QgsMessageLog.logMessage(
                f"Successfully translated {self.translated_count} out of {self.total_features} features",
                'Clean Data',
                Qgis.Success
            )
        else:
            if self.exception:
                QgsMessageLog.logMessage(
                    f"Translation failed: {str(self.exception)}",
                    'Clean Data',
                    Qgis.Critical
                )
            else:
                QgsMessageLog.logMessage(
                    "Translation was canceled",
                    'Clean Data',
                    Qgis.Warning
                )
                
    def cancel(self):
        QgsMessageLog.logMessage(
            "Translation task was canceled by user",
            'Clean Data',
            Qgis.Info
        )
        super().cancel()

class TranslationManager:
    """Manager class for handling translations"""
    
    def __init__(self):
        self.task = None
        
    def get_service(self, service_name):
        """Get translation service instance based on name"""
        if service_name.lower() == 'google':
            return GoogleTranslateService()
        elif service_name.lower() == 'ollama':
            return OllamaService()
        else:
            raise ValueError(f"Unknown translation service: {service_name}")
            
    def translate_column(self, layer, source_field, target_field, prompt_template=None, 
                        service_name='Ollama', model=None, source_lang='auto', target_lang='ar', 
                        instructions='', batch_mode=True, batch_size=10):
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
                instructions=instructions
            )
            
            QgsApplication.taskManager().addTask(self.task)
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Failed to start translation: {str(e)}",
                'Clean Data',
                Qgis.Critical
            )
