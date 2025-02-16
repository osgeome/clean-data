from qgis.core import QgsVectorLayer, QgsField, QgsFeature, QgsMessageLog
from PyQt5.QtCore import QVariant
import requests
import json
from typing import Dict, Set, Optional, Union
import re
from .settings_manager import SettingsManager
import asyncio
import sys


def log_message(message: str, level: int = 0):
    """Log a message to QGIS message log"""
    QgsMessageLog.logMessage(message, 'Clean Data', level)


def remove_columns_with_null_percentage(layer: QgsVectorLayer, threshold: float, 
                                     null_value: Optional[str] = None) -> bool:
    """
    Remove columns where the percentage of null values exceeds the threshold
    Args:
        layer: QGIS vector layer
        threshold: percentage threshold (0-100)
        null_value: optional specific value to treat as null
    Returns:
        bool: True if columns were removed, False otherwise
    """
    if not layer.isValid():
        return False

    # Get field indices and names
    fields = layer.fields()
    field_indices = [i for i in range(fields.count())]
    field_names = [fields.field(i).name() for i in field_indices]

    # Calculate null percentages
    null_counts = {name: 0 for name in field_names}
    total_features = layer.featureCount()

    for feature in layer.getFeatures():
        for name in field_names:
            value = feature[name]
            is_null = False
            
            if null_value is not None:
                # Check for specific null value
                if isinstance(value, (int, float)):
                    # Convert numeric values to string for comparison
                    is_null = str(value).strip() == null_value
                else:
                    # For string values, compare directly
                    is_null = str(value or '').strip() == null_value
            else:
                # Check for empty/NULL values
                is_null = value is None or str(value).strip() == ''
                
            if is_null:
                null_counts[name] += 1

    # Identify fields to remove
    fields_to_remove = [
        name for name, count in null_counts.items()
        if (count / total_features) * 100 > threshold
    ]

    if not fields_to_remove:
        return False

    # Remove fields
    layer.startEditing()
    for name in fields_to_remove:
        idx = fields.indexOf(name)
        if idx >= 0:
            layer.deleteAttribute(idx)
    layer.commitChanges()

    return True


def normalize_value(value: str, strip_zeros: bool = False) -> str:
    """Normalize a value for comparison"""
    if value is None:
        return ""
    value = str(value).strip()
    if strip_zeros:
        value = value.lstrip('0')
    return value


def find_and_replace_values(source_layer: QgsVectorLayer, source_field: str,
                          ref_layer: QgsVectorLayer, find_field: str,
                          replace_field: str, pattern_match: bool = False,
                          custom_pattern: Optional[str] = None,
                          strip_zeros: bool = False) -> bool:
    """
    Replace values in source layer based on reference layer mapping
    Args:
        source_layer: Layer to update
        source_field: Field in source layer to update
        ref_layer: Layer containing replacement mapping
        find_field: Field in reference layer to match against
        replace_field: Field in reference layer containing replacement values
        pattern_match: Whether to use pattern matching for comparison
        custom_pattern: Custom regex pattern to use (if pattern_match is True)
        strip_zeros: Whether to strip leading zeros before comparison
    Returns:
        bool: True if values were replaced, False otherwise
    """
    if not all([source_layer.isValid(), ref_layer.isValid()]):
        return False

    # Build replacement mapping
    replacements = {}
    patterns = {}  # Only used if pattern_match is True
    
    for feature in ref_layer.getFeatures():
        find_value = normalize_value(feature[find_field], strip_zeros)
        replace_value = str(feature[replace_field])
        
        if find_value and replace_value:
            if pattern_match:
                try:
                    # If custom pattern is provided, use it as a template
                    if custom_pattern:
                        pattern_str = custom_pattern.replace('{value}', re.escape(find_value))
                    else:
                        pattern_str = find_value
                    pattern = re.compile(pattern_str)
                    patterns[find_value] = (pattern, replace_value)
                except re.error:
                    # If pattern is invalid, treat it as literal
                    replacements[find_value] = replace_value
            else:
                replacements[find_value] = replace_value

    if not (replacements or patterns):
        return False

    # Apply replacements
    source_layer.startEditing()
    changes_made = False

    for feature in source_layer.getFeatures():
        original_value = str(feature[source_field])
        normalized_value = normalize_value(original_value, strip_zeros)
        
        new_value = None
        
        if pattern_match:
            # Try pattern matching first
            for pattern_str, (pattern, replacement) in patterns.items():
                if pattern.search(normalized_value):  # Changed from match to search
                    new_value = replacement
                    break
            
            # If no pattern matched and no custom pattern, try exact matching
            if new_value is None and not custom_pattern and normalized_value in replacements:
                new_value = replacements[normalized_value]
        else:
            # Simple exact matching
            if normalized_value in replacements:
                new_value = replacements[normalized_value]
        
        if new_value is not None and new_value != original_value:
            feature[source_field] = new_value
            source_layer.updateFeature(feature)
            changes_made = True
    
    source_layer.commitChanges()
    return changes_made


def translate_column(layer, field_name, new_field_name, prompt_template=None, service='Google Translate', 
                 model=None, source_lang='auto', target_lang='ar', instructions=None):
    """Translate a field in the layer using the specified translation service"""
    
    # Add the new field
    layer.dataProvider().addAttributes([QgsField(new_field_name, QVariant.String)])
    layer.updateFields()
    
    # Get field index
    field_idx = layer.fields().indexOf(field_name)
    new_field_idx = layer.fields().indexOf(new_field_name)
    
    if field_idx == -1 or new_field_idx == -1:
        return False
    
    # Get all values to translate
    texts = []
    feature_ids = []
    for feature in layer.getFeatures():
        text = feature[field_idx]
        if text:
            texts.append(str(text))
            feature_ids.append(feature.id())
    
    try:
        # Translate texts based on selected service
        if service == 'Google Translate':
            translations = translate_with_google(texts, target_lang)
        elif service == 'OpenAI':
            translations = translate_with_llm(texts, target_lang, prompt_template, instructions, 'openai')
        elif service == 'DeepSeek':
            translations = translate_with_llm(texts, target_lang, prompt_template, instructions, 'deepseek')
        elif service == 'Ollama':
            translations = translate_with_ollama(texts, target_lang, prompt_template, model, instructions=instructions)
        else:
            raise ValueError(f"Unknown translation service: {service}")
        
        # Update features with translations
        layer.startEditing()
        for fid, translation in zip(feature_ids, translations):
            layer.changeAttributeValue(fid, new_field_idx, translation)
        layer.commitChanges()
        
        return True
        
    except Exception as e:
        QgsMessageLog.logMessage(f"Translation failed: {str(e)}", 'Clean Data', 2)
        return False


def parse_translations_list(response_text, expected_count):
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
    clean_text = re.sub(r'^.*?\[', '[', clean_text, flags=re.DOTALL)  # Remove everything before first [
    clean_text = re.sub(r'\].*?$', ']', clean_text, flags=re.DOTALL)  # Remove everything after last ]
    
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


def translate_with_ollama(texts, target_lang, prompt_template, model='aya', batch_size=10, instructions=None, max_retries=2):
    """
    Translate texts using Ollama API with batch processing
    """
    url = SettingsManager.get_ollama_url()
    if not url:
        raise ValueError("Ollama URL not configured")
    
    if not url.endswith('/api/generate'):
        url = url.rstrip('/') + '/api/generate'
    
    QgsMessageLog.logMessage(f"Using Ollama with model: {model}", 'Clean Data', 0)
    
    translations = []
    total_texts = len(texts)
    processed = 0
    
    # Process texts in batches
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_translations = None
        retries = 0
        
        while retries <= max_retries and (batch_translations is None or len(batch_translations) != len(batch)):
            try:
                # Create indexed texts
                indexed_texts = [f"{idx+1}. {text}" for idx, text in enumerate(batch)]
                texts_str = "\n".join(indexed_texts)
                
                # Format the prompt template with our variables
                instructions_str = instructions if instructions else ""
                batch_prompt = prompt_template.format(
                    batch_size=len(batch),
                    target_lang=target_lang,
                    instructions=instructions_str,
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
                
                response = requests.post(url, json=data)
                response.raise_for_status()
                result = response.json()
                
                # Log the raw response for debugging
                QgsMessageLog.logMessage(f"Raw response for batch {i//batch_size + 1}: {result['response']}", 'Clean Data', 0)
                
                # Parse and clean the response
                batch_translations = parse_translations_list(result['response'], len(batch))
                
                # Validate batch result length
                if len(batch_translations) != len(batch):
                    if retries < max_retries:
                        QgsMessageLog.logMessage(f"Retry {retries + 1}: Got {len(batch_translations)} translations, expected {len(batch)}", 'Clean Data', 1)
                        retries += 1
                        continue
                    else:
                        raise ValueError(f"Expected {len(batch)} translations but got {len(batch_translations)}")
                
                translations.extend(batch_translations)
                processed += len(batch)
                QgsMessageLog.logMessage(f"Translated {processed}/{total_texts} features...", 'Clean Data', 0)
                break
                
            except Exception as e:
                if retries < max_retries:
                    QgsMessageLog.logMessage(f"Retry {retries + 1}: {str(e)}", 'Clean Data', 1)
                    retries += 1
                    continue
                QgsMessageLog.logMessage(f"Translation error: {str(e)}", 'Clean Data', 2)
                raise
    
    return translations


def translate_with_llm(texts, target_lang, prompt_template, instructions, service):
    """Translate using LLM API"""
    translations = []
    for text in texts:
        prompt = prompt_template.format(text=text, target_lang=target_lang, instructions=instructions)
        try:
            if service == 'OpenAI':
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {SettingsManager.get_openai_api_key()}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": SettingsManager.get_openai_model(),
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3
                    }
                )
                if response.status_code == 200:
                    result = response.json()
                    translations.append(result["choices"][0]["message"]["content"].strip())
            elif service == 'DeepSeek':
                response = requests.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {SettingsManager.get_deepseek_api_key()}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": SettingsManager.get_deepseek_model(),
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3
                    }
                )
                if response.status_code == 200:
                    result = response.json()
                    translations.append(result["choices"][0]["message"]["content"].strip())
        except Exception as e:
            QgsMessageLog.logMessage(f"Translation error for value '{text}': {str(e)}", 'Clean Data', 1)
            continue
    
    return translations


def translate_with_google(texts, target_lang):
    """Translate using Google Translate API"""
    translations = []
    api_key = SettingsManager.get_google_api_key()
    
    for text in texts:
        try:
            response = requests.post(
                "https://translation.googleapis.com/language/translate/v2",
                params={"key": api_key},
                json={
                    "q": text,
                    "target": target_lang
                }
            )
            if response.status_code == 200:
                result = response.json()
                translations.append(result["data"]["translations"][0]["translatedText"])
        except Exception as e:
            QgsMessageLog.logMessage(f"Translation error for value '{text}': {str(e)}", 'Clean Data', 1)
            continue
    
    return translations
