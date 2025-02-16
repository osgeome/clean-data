"""
Main dialog for the Clean Data QGIS plugin.
"""

from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QComboBox, QLabel,
                               QPushButton, QLineEdit, QMessageBox, QTabWidget,
                               QCheckBox, QGroupBox, QPlainTextEdit, QHBoxLayout, QFormLayout, QSpinBox, QWidget, QTextEdit)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject, QgsVectorLayer, QgsMapLayerType, QgsMessageLog, Qgis

from .modules import (
    TranslationManager,
    CleaningManager,
    SettingsManager
)

import re

class CleanDataDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.translation_manager = TranslationManager()
        self.cleaning_manager = CleaningManager()
        self.settings_manager = SettingsManager()
        self.project = QgsProject.instance()
        self.setWindowTitle('Clean Data')
        
        # Store references to layer combos for easy updates
        self.layer_combos = []
        
        self.setup_ui()
        self.connect_signals()
        self.load_settings()

    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout()
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Add tabs
        self.tab_widget.addTab(self.create_translation_tab(), 'Translation')
        self.tab_widget.addTab(self.create_null_cleaning_tab(), 'Null Cleaning')
        self.tab_widget.addTab(self.create_find_replace_tab(), 'Find & Replace')
        self.tab_widget.addTab(self.create_settings_tab(), 'Settings')
        
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
        """Create the null cleaning tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Quick clean section
        quick_clean_group = QGroupBox("Quick Clean")
        quick_clean_layout = QVBoxLayout()
        quick_clean_group.setLayout(quick_clean_layout)
        
        quick_clean_help = QLabel("Quick clean will remove all columns that contain only null or empty values.")
        quick_clean_help.setWordWrap(True)
        quick_clean_layout.addWidget(quick_clean_help)
        
        quick_clean_button = QPushButton("Remove Empty Columns")
        quick_clean_button.clicked.connect(self.on_quick_clean_clicked)
        quick_clean_layout.addWidget(quick_clean_button)
        
        layout.addWidget(quick_clean_group)
        
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
        self.clean_button.clicked.connect(self.on_clean_clicked)
        layout.addWidget(self.clean_button)
        
        # Delete column button
        self.delete_column_button = QPushButton('Delete Selected Column')
        self.delete_column_button.clicked.connect(self.on_delete_column_clicked)
        layout.addWidget(self.delete_column_button)

        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def create_find_replace_tab(self):
        """Create the find and replace tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Source Layer
        self.source_layer_combo = QComboBox()
        self.populate_layers(self.source_layer_combo)
        layout.addWidget(QLabel('Source Layer:'))
        layout.addWidget(self.source_layer_combo)
        
        # Source Field
        self.source_field_combo = QComboBox()
        layout.addWidget(QLabel('Source Field:'))
        layout.addWidget(self.source_field_combo)
        
        # New Column Option
        new_column_group = QWidget()
        new_column_layout = QHBoxLayout()
        new_column_group.setLayout(new_column_layout)
        
        self.create_new_column = QCheckBox('Create New Column')
        new_column_layout.addWidget(self.create_new_column)
        
        self.new_column_name = QLineEdit()
        self.new_column_name.setPlaceholderText('New column name (optional)')
        self.new_column_name.setEnabled(False)
        new_column_layout.addWidget(self.new_column_name)
        
        layout.addWidget(new_column_group)
        
        # Reference Layer
        self.ref_layer_combo = QComboBox()
        self.populate_layers(self.ref_layer_combo)
        layout.addWidget(QLabel('Reference Layer:'))
        layout.addWidget(self.ref_layer_combo)
        
        # Reference Fields
        self.find_field_combo = QComboBox()
        layout.addWidget(QLabel('Find Field (in Reference):'))
        layout.addWidget(self.find_field_combo)
        
        self.replace_field_combo = QComboBox()
        layout.addWidget(QLabel('Replace Field (in Reference):'))
        layout.addWidget(self.replace_field_combo)
        
        # Pattern Matching
        pattern_group = QWidget()
        pattern_layout = QVBoxLayout()
        pattern_group.setLayout(pattern_layout)
        
        self.pattern_match = QCheckBox('Use Pattern Matching')
        pattern_layout.addWidget(self.pattern_match)
        
        # Pattern help
        pattern_help = QLabel(
            'Common Patterns:\n'
            '- \\d+ : Match any sequence of digits (default)\n'
            '- ^\\d+ : Match digits at start of text\n'
            '- \\d+$ : Match digits at end of text\n'
            '- [A-Z]+ : Match uppercase letters'
        )
        pattern_help.setStyleSheet('color: gray; font-size: 11px;')
        pattern_layout.addWidget(pattern_help)
        
        # Custom Pattern
        self.custom_pattern = QLineEdit()
        self.custom_pattern.setText('\\d+')  # Set default pattern
        self.custom_pattern.setEnabled(False)
        pattern_layout.addWidget(QLabel('Custom Pattern:'))
        pattern_layout.addWidget(self.custom_pattern)
        
        layout.addWidget(pattern_group)
        
        # Zero Handling
        self.strip_zeros = QCheckBox('Strip Leading Zeros When Matching')
        layout.addWidget(self.strip_zeros)
        
        self.pad_zeros = QCheckBox('Pad Numbers with Zeros')
        layout.addWidget(self.pad_zeros)
        
        # Pad Length
        self.pad_length = QSpinBox()
        self.pad_length.setMinimum(1)
        self.pad_length.setMaximum(10)
        self.pad_length.setValue(3)
        layout.addWidget(QLabel('Pad Length:'))
        layout.addWidget(self.pad_length)
        
        # Replace button
        self.replace_button = QPushButton('Find and Replace')
        self.replace_button.clicked.connect(self.on_find_replace_clicked)
        layout.addWidget(self.replace_button)
        
        # Connect signals
        self.source_layer_combo.currentIndexChanged.connect(
            lambda: self.update_fields(self.source_layer_combo, self.source_field_combo)
        )
        self.ref_layer_combo.currentIndexChanged.connect(
            lambda: self.update_fields(self.ref_layer_combo, self.find_field_combo)
        )
        self.ref_layer_combo.currentIndexChanged.connect(
            lambda: self.update_fields(self.ref_layer_combo, self.replace_field_combo)
        )
        self.pattern_match.stateChanged.connect(self.on_pattern_match_changed)
        self.create_new_column.stateChanged.connect(self.on_new_column_changed)
        
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
        self.service_combo.currentTextChanged.connect(self.update_translation_settings)
        
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
        self.translate_button.clicked.connect(self.on_translate_clicked)
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
        self.null_layer_combo.currentIndexChanged.connect(lambda: self.update_fields(self.null_layer_combo))
        self.null_type.currentIndexChanged.connect(self.on_null_type_changed)
        
        # Find and replace
        self.source_layer_combo.currentIndexChanged.connect(lambda: self.update_fields(self.source_layer_combo))
        self.ref_layer_combo.currentIndexChanged.connect(lambda: self.update_fields(self.ref_layer_combo))
        self.pattern_match.stateChanged.connect(self.on_pattern_match_changed)
        
        # Translation
        self.trans_layer_combo.currentIndexChanged.connect(lambda: self.update_fields(self.trans_layer_combo))
        self.service_combo.currentTextChanged.connect(self.update_translation_settings)
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
        if service == 'Google Translate' and not self.settings_manager.get_google_api_key():
            QMessageBox.warning(self, "Error", "Please configure Google Translate API key in settings.")
            return
        elif service == 'OpenAI' and not self.settings_manager.get_openai_api_key():
            QMessageBox.warning(self, "Error", "Please configure OpenAI API key in settings.")
            return
        elif service == 'DeepSeek' and not self.settings_manager.get_deepseek_api_key():
            QMessageBox.warning(self, "Error", "Please configure DeepSeek API key in settings.")
            return
        elif service == 'Ollama' and not self.settings_manager.get_ollama_url():
            QMessageBox.warning(self, "Error", "Please configure Ollama URL in settings.")
            return

        try:
            if self.translation_manager.translate_column(layer, field, new_field, prompt, service, 
                              self.settings_manager.get_ollama_model() if service == 'Ollama' else None,
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
        self.update_fields(self.source_layer_combo)
        self.update_fields(self.ref_layer_combo)
        self.update_fields(self.trans_layer_combo)

    def update_fields(self, combo, field_combo=None):
        """Update fields for a layer combo box"""
        layer = combo.currentData()
        if not isinstance(layer, QgsVectorLayer) or not layer.isValid():
            return

        # Determine which field combos to update based on the source combo
        field_combos = []
        if combo == self.null_layer_combo:
            field_combos = [self.null_field_combo]
        elif combo == self.source_layer_combo:
            field_combos = [self.source_field_combo]
        elif combo == self.ref_layer_combo:
            field_combos = [self.find_field_combo, self.replace_field_combo]
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
        """Handle clean button click"""
        layer = self.null_layer_combo.currentData()
        field = self.null_field_combo.currentText()
        
        if not layer or not field:
            QMessageBox.warning(self, "Error", "Please select a layer and field.")
            return
            
        try:
            threshold = float(self.null_threshold.text()) if self.null_threshold.text() else 100
            if threshold < 0 or threshold > 100:
                QMessageBox.warning(self, "Error", "Threshold must be between 0 and 100.")
                return
                
            if self.cleaning_manager.remove_columns_with_null_percentage(layer, field, threshold):
                QMessageBox.information(self, "Success", "Field cleaned successfully!")
                # Update fields in case columns were removed
                self.update_fields(self.null_layer_combo)
            else:
                QMessageBox.information(self, "Info", "No changes were needed.")
                
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
            self,
            'Confirm Deletion',
            f'Are you sure you want to delete the column "{field}"?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
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

    def on_find_replace_clicked(self):
        source_layer = self.source_layer_combo.currentData()
        source_field = self.source_field_combo.currentText()
        ref_layer = self.ref_layer_combo.currentData()
        find_field = self.find_field_combo.currentText()
        replace_field = self.replace_field_combo.currentText()
        
        if not source_layer or not source_field:
            QMessageBox.warning(self, "Error", "Please select a source layer and field.")
            return
            
        if ref_layer and (not find_field or not replace_field):
            QMessageBox.warning(self, "Error", "Please select both find and replace fields from the reference layer.")
            return
            
        try:
            pattern_match = self.pattern_match.isChecked()
            custom_pattern = self.custom_pattern.text() if pattern_match else None
            strip_zeros = self.strip_zeros.isChecked()
            pad_zeros = self.pad_zeros.isChecked()
            pad_length = self.pad_length.value()
            
            create_new = self.create_new_column.isChecked()
            new_name = self.new_column_name.text() if create_new else None
            
            if create_new and not new_name:
                new_name = f"{source_field}_new"
            
            if pattern_match and custom_pattern:
                import re
                try:
                    re.compile(custom_pattern)
                except re.error as e:
                    QMessageBox.warning(self, "Error", f"Invalid regular expression pattern: {str(e)}")
                    return
            
            count = self.cleaning_manager.find_and_replace_values(
                source_layer,
                source_field,
                ref_layer,
                find_field,
                replace_field,
                pattern_match,
                custom_pattern,
                strip_zeros,
                pad_zeros,
                pad_length,
                create_new_column=create_new,
                new_column_name=new_name
            )
            
            if count > 0:
                msg = f"Replaced {count} values successfully!"
                if create_new:
                    msg += f"\nCreated new column: {new_name}"
                    # Refresh all field combos that show this layer
                    self.update_all_fields()
                QMessageBox.information(self, "Success", msg)
                source_layer.commitChanges()
            else:
                QMessageBox.information(self, "Info", "No matches found.")
                source_layer.rollBack()
                
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
            source_layer.rollBack()
            
    def update_all_fields(self):
        """Update fields for all tabs"""
        # Store current selections
        null_layer = self.null_layer_combo.currentData()
        null_field = self.null_field_combo.currentText()
        source_layer = self.source_layer_combo.currentData()
        source_field = self.source_field_combo.currentText()
        ref_layer = self.ref_layer_combo.currentData()
        ref_find = self.find_field_combo.currentText()
        ref_replace = self.replace_field_combo.currentText()
        trans_layer = self.trans_layer_combo.currentData()
        trans_field = self.trans_field_combo.currentText()
        
        # Update all fields
        if null_layer:
            self.update_fields(self.null_layer_combo)
            # Restore selection if field still exists
            idx = self.null_field_combo.findText(null_field)
            if idx >= 0:
                self.null_field_combo.setCurrentIndex(idx)
                
        if source_layer:
            self.update_fields(self.source_layer_combo)
            idx = self.source_field_combo.findText(source_field)
            if idx >= 0:
                self.source_field_combo.setCurrentIndex(idx)
                
        if ref_layer:
            self.update_fields(self.ref_layer_combo)
            idx = self.find_field_combo.findText(ref_find)
            if idx >= 0:
                self.find_field_combo.setCurrentIndex(idx)
            idx = self.replace_field_combo.findText(ref_replace)
            if idx >= 0:
                self.replace_field_combo.setCurrentIndex(idx)
                
        if trans_layer:
            self.update_fields(self.trans_layer_combo)
            idx = self.trans_field_combo.findText(trans_field)
            if idx >= 0:
                self.trans_field_combo.setCurrentIndex(idx)

    def on_pattern_match_changed(self, state):
        """Handle pattern match checkbox state change"""
        self.custom_pattern.setEnabled(state)
        if not state:
            self.custom_pattern.clear()

    def on_new_column_changed(self, state):
        """Handle new column checkbox state change"""
        self.new_column_name.setEnabled(bool(state))
        if not state:
            self.new_column_name.clear()

    def load_settings(self):
        """Load settings from QgsSettings"""
        # API Keys
        self.google_api_key.setText(self.settings_manager.get_google_api_key() or '')
        self.ollama_url.setText(self.settings_manager.get_ollama_url() or '')
        self.openai_api_key.setText(self.settings_manager.get_openai_api_key() or '')
        self.deepseek_api_key.setText(self.settings_manager.get_deepseek_api_key() or '')
        
        # Model Names
        self.ollama_model.setText(self.settings_manager.get_ollama_model() or '')
        self.openai_model.setText(self.settings_manager.get_openai_model() or '')
        self.deepseek_model.setText(self.settings_manager.get_deepseek_model() or '')
        
        # Batch Settings
        self.ollama_batch_size.setValue(self.settings_manager.get_batch_size())
        
    def save_settings(self):
        """Save settings to QgsSettings"""
        # API Keys
        self.settings_manager.set_google_api_key(self.google_api_key.text())
        self.settings_manager.set_ollama_url(self.ollama_url.text())
        self.settings_manager.set_openai_api_key(self.openai_api_key.text())
        self.settings_manager.set_deepseek_api_key(self.deepseek_api_key.text())
        
        # Model Names
        self.settings_manager.set_ollama_model(self.ollama_model.text())
        self.settings_manager.set_openai_model(self.openai_model.text())
        self.settings_manager.set_deepseek_model(self.deepseek_model.text())
        
        # Batch Settings
        self.settings_manager.set_batch_size(self.ollama_batch_size.value())        
        QMessageBox.information(self, "Settings", "Settings saved successfully!")

    def on_null_type_changed(self):
        """Enable/disable specific value input based on null type"""
        self.null_value.setEnabled(self.null_type.currentText() == 'Specific Value')

    def on_quick_clean_clicked(self):
        """Handle quick clean button click"""
        reply = QMessageBox.question(
            self,
            'Remove Empty Columns',
            'This will remove all columns that contain only null or empty values from all vector layers. Continue?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            project = QgsProject.instance()
            layers = project.mapLayers().values()
            removed_count = 0
            
            for layer in layers:
                if isinstance(layer, QgsVectorLayer):
                    if self.cleaning_manager.remove_empty_columns(layer):
                        removed_count += 1
                    layer.commitChanges()
            
            if removed_count > 0:
                QMessageBox.information(
                    self,
                    'Clean Data',
                    f'Successfully removed empty columns from {removed_count} layers.'
                )
            else:
                QMessageBox.information(
                    self,
                    'Clean Data',
                    'No empty columns found in any layer.'
                )

    def on_clean_field_clicked(self):
        """Handle clean field button click"""
        layer = self.get_layer_and_validate(self.null_layer_combo, self.null_field_combo)
        if not layer:
            return
            
        field = self.null_field_combo.currentText()
        if not field:
            QMessageBox.warning(self, "Error", "Please select a field to clean.")
            return
            
        try:
            threshold = float(self.null_threshold.text()) if self.null_threshold.text() else 100
            if threshold < 0 or threshold > 100:
                QMessageBox.warning(self, "Error", "Threshold must be between 0 and 100.")
                return
                
            if self.cleaning_manager.remove_columns_with_null_percentage(layer, field, threshold):
                QMessageBox.information(self, "Success", "Field cleaned successfully!")
                # Update fields in case columns were removed
                self.update_fields(self.null_layer_combo)
            else:
                QMessageBox.information(self, "Info", "No changes were needed.")
                
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))
