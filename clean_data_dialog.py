from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QComboBox, QPushButton, QLineEdit, QFormLayout,
                               QTabWidget, QWidget, QTextEdit, QSpinBox, QMessageBox,
                               QCheckBox, QGroupBox, QPlainTextEdit)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject, QgsVectorLayer, QgsMapLayerType
from .clean_data_utils import remove_columns_with_null_percentage, find_and_replace_values, translate_column
from .settings_manager import SettingsManager
import re

class CleanDataDialog(QDialog):
    def __init__(self, iface, parent=None):
        super(CleanDataDialog, self).__init__(parent)
        self.iface = iface
        self.project = QgsProject.instance()
        self.setWindowTitle('Clean Data')
        
        # Store references to layer combos for easy updates
        self.layer_combos = []
        
        self.setup_ui()
        self.connect_signals()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Add tabs
        self.tab_widget.addTab(self.create_null_cleaning_tab(), "Null Cleaning")
        self.tab_widget.addTab(self.create_find_replace_tab(), "Find & Replace")
        self.tab_widget.addTab(self.create_translation_tab(), "Translation")
        self.tab_widget.addTab(self.create_settings_tab(), "Settings")
        
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)
        self.setMinimumWidth(400)
        
        # Initialize fields for all tabs
        self.update_all_fields()

    def create_settings_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        # Google Translate settings
        google_group = QWidget()
        google_layout = QFormLayout()
        google_group.setLayout(google_layout)
        
        self.google_api_key = QLineEdit()
        self.google_api_key.setEchoMode(QLineEdit.Password)
        google_layout.addRow('API Key:', self.google_api_key)
        
        layout.addWidget(QLabel('Google Translate Settings:'))
        layout.addWidget(google_group)

        # OpenAI settings
        openai_group = QWidget()
        openai_layout = QFormLayout()
        openai_group.setLayout(openai_layout)
        
        self.openai_api_key = QLineEdit()
        self.openai_api_key.setEchoMode(QLineEdit.Password)
        openai_layout.addRow('API Key:', self.openai_api_key)
        
        self.openai_model = QLineEdit()
        self.openai_model.setPlaceholderText('gpt-3.5-turbo')
        openai_layout.addRow('Model:', self.openai_model)
        
        layout.addWidget(QLabel('OpenAI Settings:'))
        layout.addWidget(openai_group)

        # DeepSeek settings
        deepseek_group = QWidget()
        deepseek_layout = QFormLayout()
        deepseek_group.setLayout(deepseek_layout)
        
        self.deepseek_api_key = QLineEdit()
        self.deepseek_api_key.setEchoMode(QLineEdit.Password)
        deepseek_layout.addRow('API Key:', self.deepseek_api_key)
        
        self.deepseek_model = QLineEdit()
        self.deepseek_model.setPlaceholderText('deepseek-chat')
        deepseek_layout.addRow('Model:', self.deepseek_model)
        
        layout.addWidget(QLabel('DeepSeek Settings:'))
        layout.addWidget(deepseek_group)

        # Ollama settings
        ollama_group = QWidget()
        ollama_layout = QFormLayout()
        ollama_group.setLayout(ollama_layout)
        
        self.ollama_url = QLineEdit()
        self.ollama_url.setPlaceholderText('http://localhost:11434')
        ollama_layout.addRow('URL:', self.ollama_url)
        
        self.ollama_model = QLineEdit()
        self.ollama_model.setPlaceholderText('aya')
        ollama_layout.addRow('Model:', self.ollama_model)
        
        self.ollama_batch_size = QSpinBox()
        self.ollama_batch_size.setRange(1, 100)
        self.ollama_batch_size.setValue(10)
        ollama_layout.addRow('Batch Size:', self.ollama_batch_size)
        
        layout.addWidget(QLabel('Ollama Settings:'))
        layout.addWidget(ollama_group)

        # Save button
        self.save_settings_button = QPushButton('Save Settings')
        self.save_settings_button.clicked.connect(self.save_settings)
        layout.addWidget(self.save_settings_button)

        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def create_null_cleaning_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        # Layer selection
        self.null_layer_combo = QComboBox()
        self.populate_layers(self.null_layer_combo)
        layout.addWidget(QLabel('Select Layer:'))
        layout.addWidget(self.null_layer_combo)

        # Field selection for column deletion
        self.null_field_combo = QComboBox()
        layout.addWidget(QLabel('Select Field:'))
        layout.addWidget(self.null_field_combo)
        
        # Null value type group
        null_group = QWidget()
        null_layout = QVBoxLayout()
        null_group.setLayout(null_layout)
        
        # Null type selection
        self.null_type = QComboBox()
        self.null_type.addItems(['Empty/NULL Values', 'Specific Value'])
        null_layout.addWidget(QLabel('Null Type:'))
        null_layout.addWidget(self.null_type)
        
        # Specific value input
        self.null_value = QLineEdit()
        self.null_value.setPlaceholderText('Enter value to treat as null (e.g., "N/A", "0", "-")')
        self.null_value.setEnabled(False)
        null_layout.addWidget(QLabel('Specific Value:'))
        null_layout.addWidget(self.null_value)
        
        layout.addWidget(null_group)

        # Null percentage threshold
        self.null_threshold = QLineEdit()
        self.null_threshold.setPlaceholderText('100')
        layout.addWidget(QLabel('Null Percentage Threshold:'))
        layout.addWidget(self.null_threshold)

        # Clean button
        self.clean_button = QPushButton('Remove Columns by Null Percentage')
        layout.addWidget(self.clean_button)
        
        # Delete column button
        self.delete_column_button = QPushButton('Delete Selected Column')
        layout.addWidget(self.delete_column_button)

        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def create_find_replace_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        # Source layer
        self.fr_source_layer = QComboBox()
        self.populate_layers(self.fr_source_layer)
        layout.addWidget(QLabel('Source Layer:'))
        layout.addWidget(self.fr_source_layer)

        # Source field
        self.fr_source_field = QComboBox()
        layout.addWidget(QLabel('Source Field:'))
        layout.addWidget(self.fr_source_field)

        # Reference layer
        self.fr_ref_layer = QComboBox()
        self.populate_layers(self.fr_ref_layer)
        layout.addWidget(QLabel('Reference Layer:'))
        layout.addWidget(self.fr_ref_layer)

        # Reference fields (find and replace)
        self.fr_find_field = QComboBox()
        self.fr_replace_field = QComboBox()
        layout.addWidget(QLabel('Find Field (in Reference):'))
        layout.addWidget(self.fr_find_field)
        layout.addWidget(QLabel('Replace Field (in Reference):'))
        layout.addWidget(self.fr_replace_field)

        # Pattern matching options
        pattern_group = QWidget()
        pattern_layout = QVBoxLayout()
        pattern_group.setLayout(pattern_layout)
        
        self.fr_pattern_match = QCheckBox('Enable Pattern Matching')
        pattern_layout.addWidget(self.fr_pattern_match)
        
        self.fr_pattern_help = QLabel(
            'Pattern Examples:\n'
            '- "^abc": Matches values starting with "abc"\n'
            '- "xyz$": Matches values ending with "xyz"\n'
            '- "\\d+": Matches one or more digits\n'
            '- "[A-Z]+": Matches one or more uppercase letters'
        )
        self.fr_pattern_help.setVisible(False)
        pattern_layout.addWidget(self.fr_pattern_help)
        
        self.fr_pattern = QLineEdit()
        self.fr_pattern.setPlaceholderText('Enter custom pattern (e.g., ^ABC\\d+)')
        self.fr_pattern.setEnabled(False)
        pattern_layout.addWidget(QLabel('Custom Pattern:'))
        pattern_layout.addWidget(self.fr_pattern)
        
        layout.addWidget(pattern_group)
        
        self.fr_strip_zeros = QCheckBox('Strip Leading Zeros')
        layout.addWidget(self.fr_strip_zeros)

        # Replace button
        self.replace_button = QPushButton('Find and Replace')
        layout.addWidget(self.replace_button)

        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def create_translation_tab(self):
        """Create the translation tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Layer and field selection
        layer_group = QGroupBox("Layer Settings")
        layer_layout = QVBoxLayout()
        layer_group.setLayout(layer_layout)
        
        # Layer selection
        self.trans_layer_combo = QComboBox()
        self.populate_layers(self.trans_layer_combo)
        layer_layout.addWidget(QLabel('Select Layer:'))
        layer_layout.addWidget(self.trans_layer_combo)

        # Field selection
        self.trans_field_combo = QComboBox()
        layer_layout.addWidget(QLabel('Select Field to Translate:'))
        layer_layout.addWidget(self.trans_field_combo)

        # New field name
        self.trans_new_field = QLineEdit()
        self.trans_new_field.setPlaceholderText('e.g., field_name_ar')
        layer_layout.addWidget(QLabel('New Field Name:'))
        layer_layout.addWidget(self.trans_new_field)
        
        layout.addWidget(layer_group)
        
        # Translation settings
        trans_settings = QGroupBox("Translation Settings")
        trans_layout = QVBoxLayout()
        trans_settings.setLayout(trans_layout)
        
        # Source and target language
        lang_group = QWidget()
        lang_layout = QHBoxLayout()
        lang_group.setLayout(lang_layout)
        
        self.source_lang = QLineEdit()
        self.source_lang.setPlaceholderText('auto')
        lang_layout.addWidget(QLabel('Source Language:'))
        lang_layout.addWidget(self.source_lang)
        
        self.target_lang = QLineEdit()
        self.target_lang.setPlaceholderText('ar')
        lang_layout.addWidget(QLabel('Target Language:'))
        lang_layout.addWidget(self.target_lang)
        
        trans_layout.addWidget(lang_group)
        
        # Translation service selection
        service_group = QWidget()
        service_layout = QVBoxLayout()
        service_group.setLayout(service_layout)
        
        self.service_combo = QComboBox()
        self.service_combo.addItems(['Google Translate', 'OpenAI', 'DeepSeek', 'Ollama'])
        service_layout.addWidget(QLabel('Translation Service:'))
        service_layout.addWidget(self.service_combo)
        self.service_combo.currentTextChanged.connect(self.update_prompt_template)
        
        trans_layout.addWidget(service_group)
        layout.addWidget(trans_settings)

        # Prompt template
        prompt_group = QGroupBox("Translation Prompt")
        prompt_layout = QVBoxLayout()
        prompt_group.setLayout(prompt_layout)
        
        prompt_help = QLabel("This is the prompt that will be sent to the translation model. You can modify it to customize the translation behavior, but make sure to keep the placeholders like {target_lang}, {batch_size}, {texts}, etc.")
        prompt_help.setWordWrap(True)
        prompt_layout.addWidget(prompt_help)
        
        self.trans_prompt = QPlainTextEdit()
        self.trans_prompt.setMinimumHeight(200)
        prompt_layout.addWidget(self.trans_prompt)
        
        layout.addWidget(prompt_group)
        
        # Translate button
        self.translate_button = QPushButton('Translate Field')
        layout.addWidget(self.translate_button)
        
        layout.addStretch()
        tab.setLayout(layout)
        
        # Set initial prompt template
        self.update_prompt_template(self.service_combo.currentText())
        
        # Connect layer combo to field update
        self.trans_layer_combo.currentIndexChanged.connect(lambda: self.update_fields(self.trans_layer_combo))
        
        return tab

    def update_prompt_template(self, service):
        """Update the prompt template based on selected service"""
        if service == 'Google Translate':
            self.trans_prompt.setPlainText("Google Translate API will be used directly.\nNo prompt template needed.")
            self.trans_prompt.setEnabled(False)
        else:
            self.trans_prompt.setEnabled(True)
            
            if service == 'Ollama':
                template = """Human: Translate these {batch_size} numbered texts to {target_lang}.

Input texts:
{texts}

Rules:
1. Return translations as a Python list with EXACTLY {batch_size} items
2. Keep translations in the SAME ORDER as input numbers
3. Include ONLY the translations, no numbers or original text
4. Each translation should be on a single line
5. Do not add any explanations
6. Count your translations before returning

Example format:
['الترجمة الأولى', 'الترجمة الثانية', 'الترجمة الثالثة']"""
            else:
                template = """Translate this text to {target_lang}.

Text: {text}

Rules:
1. Return ONLY the translation
2. Do not add any explanations or notes
3. Maintain the same format (keep numbers, punctuation, etc.)"""
            
            self.trans_prompt.setPlainText(template)

    def connect_signals(self):
        # Project layer signals
        self.project.layersAdded.connect(self.update_all_layer_combos)
        self.project.layersRemoved.connect(self.update_all_layer_combos)
        
        # Null cleaning
        self.clean_button.clicked.connect(self.on_clean_clicked)
        self.delete_column_button.clicked.connect(self.on_delete_column_clicked)
        self.null_layer_combo.currentIndexChanged.connect(lambda: self.update_fields(self.null_layer_combo))
        self.null_type.currentIndexChanged.connect(self.on_null_type_changed)
        
        # Find and replace
        self.fr_source_layer.currentIndexChanged.connect(lambda: self.update_fields(self.fr_source_layer))
        self.fr_ref_layer.currentIndexChanged.connect(lambda: self.update_fields(self.fr_ref_layer))
        self.replace_button.clicked.connect(self.on_replace_clicked)
        self.fr_pattern_match.stateChanged.connect(self.on_pattern_match_changed)
        
        # Translation
        self.trans_layer_combo.currentIndexChanged.connect(lambda: self.update_fields(self.trans_layer_combo))
        self.service_combo.currentTextChanged.connect(self.update_translation_settings)
        self.translate_button.clicked.connect(self.on_translate_clicked)
        self.source_lang.textChanged.connect(self.update_translation_settings)
        self.target_lang.textChanged.connect(self.update_translation_settings)

    def update_translation_settings(self):
        """Update translation UI based on selected service and languages"""
        service = self.service_combo.currentText()
        target_lang = self.target_lang.text() or 'ar'
        
        # Map language codes to names for better prompts
        lang_names = {
            'ar': 'Arabic', 'en': 'English', 'fr': 'French', 
            'es': 'Spanish', 'de': 'German', 'it': 'Italian',
            'ja': 'Japanese', 'ko': 'Korean', 'ru': 'Russian',
            'zh': 'Chinese'
        }
        target_name = lang_names.get(target_lang, target_lang)
        
        if service == 'Google Translate':
            self.trans_prompt.clear()
            self.trans_prompt.setEnabled(False)
        elif service == 'Ollama':
            self.trans_prompt.setEnabled(True)
            self.trans_prompt.setPlainText(
                f'Human: Please translate the following text to {target_name}. '
                f'Provide ONLY the translation, without any additional text or explanations:\n\n'
                '{text}\n\n'
                'Assistant:'
            )
        else:
            self.trans_prompt.setEnabled(True)
            self.trans_prompt.setPlainText(
                f'Translate the following text to {target_name}. '
                f'Provide only the translation without any additional text:\n\n'
                '{text}'
            )

    def on_translate_clicked(self):
        layer = self.get_layer_and_validate(self.trans_layer_combo, self.trans_field_combo)
        if not layer:
            return
            
        field = self.trans_field_combo.currentText()
        new_field = self.trans_new_field.text()
        service = self.service_combo.currentText()
        
        if not all([field, new_field]):
            QMessageBox.warning(self, "Error", "Please fill in all required fields.")
            return

        # Validate field name
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', new_field):
            QMessageBox.warning(self, "Error", "Invalid field name. Use only letters, numbers, and underscores.")
            return
            
        # Get translation settings
        source_lang = self.source_lang.text() or 'auto'
        target_lang = self.target_lang.text() or 'ar'
        prompt = self.trans_prompt.toPlainText() if service != 'Google Translate' else None
        instructions = ''
            
        # Validate API keys and settings
        if service == 'Google Translate' and not SettingsManager.get_google_api_key():
            QMessageBox.warning(self, "Error", "Please configure Google Translate API key in settings.")
            return
        elif service == 'OpenAI' and not SettingsManager.get_openai_api_key():
            QMessageBox.warning(self, "Error", "Please configure OpenAI API key in settings.")
            return
        elif service == 'DeepSeek' and not SettingsManager.get_deepseek_api_key():
            QMessageBox.warning(self, "Error", "Please configure DeepSeek API key in settings.")
            return
        elif service == 'Ollama' and not SettingsManager.get_ollama_url():
            QMessageBox.warning(self, "Error", "Please configure Ollama URL in settings.")
            return

        try:
            if translate_column(layer, field, new_field, prompt, service, 
                              SettingsManager.get_ollama_model() if service == 'Ollama' else None,
                              source_lang=source_lang, target_lang=target_lang, instructions=instructions):
                QMessageBox.information(self, "Success", "Field translated successfully!")
                # Update fields to include the new translated field
                self.update_fields(self.trans_layer_combo)
            else:
                QMessageBox.warning(self, "Error", "Translation failed. Please check the QGIS message log for details.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Translation error: {str(e)}")

    def populate_layers(self, combo):
        """Populate a combo box with vector layers from the project"""
        combo.clear()
        layers = self.project.mapLayers().values()
        vector_layers = [layer for layer in layers 
                        if layer.type() == QgsMapLayerType.VectorLayer and layer.isValid()]
        
        for layer in vector_layers:
            combo.addItem(layer.name(), layer)
        
        if combo not in self.layer_combos:
            self.layer_combos.append(combo)

    def update_all_layer_combos(self):
        """Update all layer combo boxes when project layers change"""
        for combo in self.layer_combos:
            current_layer = combo.currentData()
            self.populate_layers(combo)
            
            # Try to restore the previously selected layer
            if current_layer:
                index = combo.findData(current_layer)
                if index >= 0:
                    combo.setCurrentIndex(index)
        
        # Update fields after updating layers
        self.update_all_fields()

    def update_all_fields(self):
        """Update fields for all tabs"""
        self.update_fields(self.null_layer_combo)
        self.update_fields(self.fr_source_layer)
        self.update_fields(self.fr_ref_layer)
        self.update_fields(self.trans_layer_combo)

    def update_fields(self, combo):
        """Update fields for a layer combo box"""
        layer = combo.currentData()
        if not isinstance(layer, QgsVectorLayer) or not layer.isValid():
            return

        # Determine which field combos to update based on the source combo
        field_combos = []
        if combo == self.null_layer_combo:
            field_combos = [self.null_field_combo]
        elif combo == self.fr_source_layer:
            field_combos = [self.fr_source_field]
        elif combo == self.fr_ref_layer:
            field_combos = [self.fr_find_field, self.fr_replace_field]
        elif combo == self.trans_layer_combo:
            field_combos = [self.trans_field_combo]
        
        # Update each field combo
        fields = layer.fields()
        for field_combo in field_combos:
            current_field = field_combo.currentText()
            field_combo.clear()
            
            for field in fields:
                field_combo.addItem(field.name())
            
            # Try to restore the previously selected field
            if current_field:
                index = field_combo.findText(current_field)
                if index >= 0:
                    field_combo.setCurrentIndex(index)

    def get_layer_and_validate(self, combo, field_combo=None):
        """Get layer from combo and validate it"""
        layer = combo.currentData()
        if not isinstance(layer, QgsVectorLayer) or not layer.isValid():
            QMessageBox.warning(self, "Error", "Please select a valid vector layer.")
            return None
            
        if field_combo:
            field = field_combo.currentText()
            if not field or field not in layer.fields().names():
                QMessageBox.warning(self, "Error", "Please select a valid field.")
                return None
                
        return layer

    def on_clean_clicked(self):
        layer = self.get_layer_and_validate(self.null_layer_combo)
        if not layer:
            return
            
        try:
            threshold = float(self.null_threshold.text() or 100)  # Default to 100 if empty
            if threshold < 0 or threshold > 100:
                raise ValueError("Threshold must be between 0 and 100")
            
            # Get null value configuration
            is_specific_value = self.null_type.currentText() == 'Specific Value'
            null_value = self.null_value.text() if is_specific_value else None
                
            if remove_columns_with_null_percentage(layer, threshold, null_value):
                QMessageBox.information(self, "Success", "Columns cleaned successfully!")
                # Update fields in case columns were removed
                self.update_fields(self.null_layer_combo)
            else:
                QMessageBox.information(self, "Info", "No columns met the threshold for removal.")
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))

    def on_delete_column_clicked(self):
        """Delete a specific column from the layer"""
        layer = self.get_layer_and_validate(self.null_layer_combo, self.null_field_combo)
        if not layer:
            return
            
        field = self.null_field_combo.currentText()
        if not field:
            QMessageBox.warning(self, "Error", "Please select a field to delete.")
            return
            
        # Confirm deletion
        reply = QMessageBox.question(
            self, 'Confirm Deletion',
            f'Are you sure you want to delete the column "{field}"?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Delete the field
            field_index = layer.fields().indexOf(field)
            if field_index >= 0:
                layer.startEditing()
                layer.deleteAttribute(field_index)
                layer.commitChanges()
                
                QMessageBox.information(self, "Success", f'Column "{field}" deleted successfully!')
                # Update fields after deletion
                self.update_fields(self.null_layer_combo)
            else:
                QMessageBox.warning(self, "Error", f'Could not find field "{field}".')

    def on_replace_clicked(self):
        source_layer = self.get_layer_and_validate(self.fr_source_layer, self.fr_source_field)
        if not source_layer:
            return
            
        ref_layer = self.get_layer_and_validate(self.fr_ref_layer)
        if not ref_layer:
            return
            
        source_field = self.fr_source_field.currentText()
        find_field = self.fr_find_field.currentText()
        replace_field = self.fr_replace_field.currentText()
        
        if not all([find_field, replace_field]):
            QMessageBox.warning(self, "Error", "Please select all required fields.")
            return
            
        pattern_match = self.fr_pattern_match.isChecked()
        pattern = self.fr_pattern.text() if pattern_match else None
        strip_zeros = self.fr_strip_zeros.isChecked()
        
        try:
            if pattern_match and pattern:
                # Validate pattern
                try:
                    re.compile(pattern)
                except re.error as e:
                    QMessageBox.warning(self, "Error", f"Invalid regular expression pattern: {str(e)}")
                    return
            
            if find_and_replace_values(source_layer, source_field, ref_layer, find_field, replace_field,
                                     pattern_match=pattern_match, custom_pattern=pattern,
                                     strip_zeros=strip_zeros):
                QMessageBox.information(self, "Success", "Values replaced successfully!")
            else:
                QMessageBox.warning(self, "Error", "No values were replaced.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def load_settings(self):
        """Load settings from QgsSettings"""
        self.google_api_key.setText(SettingsManager.get_google_api_key() or '')
        self.openai_api_key.setText(SettingsManager.get_openai_api_key() or '')
        self.openai_model.setText(SettingsManager.get_openai_model() or '')
        self.deepseek_api_key.setText(SettingsManager.get_deepseek_api_key() or '')
        self.deepseek_model.setText(SettingsManager.get_deepseek_model() or '')
        self.ollama_url.setText(SettingsManager.get_ollama_url() or '')
        self.ollama_model.setText(SettingsManager.get_ollama_model() or '')
        self.ollama_batch_size.setValue(int(SettingsManager.get_ollama_batch_size()))

    def save_settings(self):
        """Save settings to QgsSettings"""
        SettingsManager.set_setting(SettingsManager.GOOGLE_API_KEY, self.google_api_key.text())
        SettingsManager.set_setting(SettingsManager.OPENAI_API_KEY, self.openai_api_key.text())
        SettingsManager.set_setting(SettingsManager.OPENAI_MODEL, self.openai_model.text())
        SettingsManager.set_setting(SettingsManager.DEEPSEEK_API_KEY, self.deepseek_api_key.text())
        SettingsManager.set_setting(SettingsManager.DEEPSEEK_MODEL, self.deepseek_model.text())
        SettingsManager.set_setting(SettingsManager.OLLAMA_URL, self.ollama_url.text())
        SettingsManager.set_setting(SettingsManager.OLLAMA_MODEL, self.ollama_model.text())
        SettingsManager.set_setting(SettingsManager.OLLAMA_BATCH_SIZE, str(self.ollama_batch_size.value()))
        QMessageBox.information(self, "Settings", "Settings saved successfully!")

    def on_null_type_changed(self):
        """Enable/disable specific value input based on null type"""
        self.null_value.setEnabled(self.null_type.currentText() == 'Specific Value')

    def on_pattern_match_changed(self, state):
        """Enable/disable pattern input based on checkbox state"""
        is_checked = bool(state)
        self.fr_pattern.setEnabled(is_checked)
        self.fr_pattern_help.setVisible(is_checked)

    def update_translation_settings(self):
        """Update translation settings based on selected service and languages"""
        service = self.service_combo.currentText()
        target_lang = self.target_lang.text() or 'ar'
        
        # Update prompt template if not already set
        if not self.trans_prompt.toPlainText() or self.trans_prompt.toPlainText().startswith("Google Translate API"):
            self.update_prompt_template(service)
            
    def update_prompt_template(self, service):
        """Update the prompt template based on selected service"""
        if service == 'Google Translate':
            self.trans_prompt.setPlainText("Google Translate API will be used directly.\nNo prompt template needed.")
            self.trans_prompt.setEnabled(False)
        else:
            self.trans_prompt.setEnabled(True)
            
            if service == 'Ollama':
                template = """Human: Translate these {batch_size} numbered texts to {target_lang}.

Input texts:
{texts}

Rules:
1. Return translations as a Python list with EXACTLY {batch_size} items
2. Keep translations in the SAME ORDER as input numbers
3. Include ONLY the translations, no numbers or original text
4. Each translation should be on a single line
5. Do not add any explanations
6. Count your translations before returning

Example format:
['الترجمة الأولى', 'الترجمة الثانية', 'الترجمة الثالثة']"""
            else:
                template = """Translate this text to {target_lang}.

Text: {text}

Rules:
1. Return ONLY the translation
2. Do not add any explanations or notes
3. Maintain the same format (keep numbers, punctuation, etc.)"""
            
            self.trans_prompt.setPlainText(template)
