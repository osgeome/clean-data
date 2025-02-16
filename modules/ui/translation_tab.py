"""
Translation tab UI module for Clean Data QGIS plugin.
"""
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                                QGroupBox, QLabel, QComboBox, QLineEdit, 
                                QPushButton, QTextEdit, QMessageBox, QSpacerItem,
                                QSizePolicy, QCheckBox, QSpinBox)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsMessageLog, Qgis, QgsProject, QgsVectorLayer
import re
from ..settings_manager import SettingsManager  # Fixed import path

class TranslationTab(QWidget):
    """Translation tab widget"""
    
    def __init__(self, dialog):
        super().__init__()
        self.dialog = dialog
        self.project = QgsProject.instance()
        self.setup_ui()
        self.populate_layers()
        
    def setup_ui(self):
        """Setup the translation tab UI"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(6)  # Reduce default spacing
        
        # Layer Settings
        layer_group = QGroupBox("Layer Settings")
        layer_grid = QGridLayout()
        layer_grid.setSpacing(6)
        
        # Layer selection
        layer_grid.addWidget(QLabel("Select Layer:"), 0, 0)
        self.layer_combo = QComboBox()
        layer_grid.addWidget(self.layer_combo, 0, 1)
        
        # Field selection
        layer_grid.addWidget(QLabel("Select Field to Translate:"), 1, 0)
        self.field_combo = QComboBox()
        layer_grid.addWidget(self.field_combo, 1, 1)
        
        # New field name
        layer_grid.addWidget(QLabel("New Field Name:"), 2, 0)
        self.new_field = QLineEdit()
        self.new_field.setPlaceholderText("e.g., name_en, description_fr")
        layer_grid.addWidget(self.new_field, 2, 1)
        
        layer_group.setLayout(layer_grid)
        main_layout.addWidget(layer_group)
        
        # Translation Settings
        trans_group = QGroupBox("Translation Settings")
        trans_layout = QVBoxLayout()
        trans_layout.setSpacing(6)
        
        # Service selection with tooltip
        service_layout = QHBoxLayout()
        service_layout.addWidget(QLabel("Translation Service:"))
        self.service = QComboBox()
        self.service.addItems(['Google Translate', 'OpenAI', 'DeepSeek', 'Ollama'])
        self.service.setToolTip("Select the service to use for translation")
        service_layout.addWidget(self.service)
        trans_layout.addLayout(service_layout)
        
        # Language selection in a grid
        lang_grid = QGridLayout()
        lang_grid.setSpacing(6)
        
        # From language
        lang_grid.addWidget(QLabel("From:"), 0, 0)
        self.source_lang = QComboBox()
        self.source_lang.addItems(['Auto', 'ar', 'en', 'fr', 'es', 'de'])
        self.source_lang.setToolTip("Source language (Auto will attempt to detect)")
        lang_grid.addWidget(self.source_lang, 0, 1)
        
        # To language
        lang_grid.addWidget(QLabel("To:"), 0, 2)
        self.target_lang = QComboBox()
        self.target_lang.addItems(['en', 'ar', 'fr', 'es', 'de'])
        self.target_lang.setToolTip("Target language for translation")
        lang_grid.addWidget(self.target_lang, 0, 3)
        
        trans_layout.addLayout(lang_grid)
        
        # Batch mode option
        batch_layout = QHBoxLayout()
        self.batch_mode = QCheckBox("Use Batch Mode")
        self.batch_mode.setToolTip("Process multiple translations at once (faster but may be less accurate)")
        self.batch_mode.setChecked(True)  # Enable by default
        batch_layout.addWidget(self.batch_mode)
        
        # Batch size spinbox
        batch_layout.addWidget(QLabel("Batch Size:"))
        self.batch_size = QSpinBox()
        self.batch_size.setRange(1, 100)
        self.batch_size.setValue(10)
        self.batch_size.setToolTip("Number of texts to translate at once in batch mode")
        batch_layout.addWidget(self.batch_size)
        
        trans_layout.addLayout(batch_layout)
        trans_group.setLayout(trans_layout)
        main_layout.addWidget(trans_group)
        
        # AI Prompt Settings
        prompt_group = QGroupBox("AI Prompt Settings")
        prompt_layout = QVBoxLayout()
        prompt_layout.setSpacing(6)
        
        # Help text with better formatting
        help_text = QLabel(
            "Customize how the AI model should handle the translation.\n\n"
            "Available variables:\n"
            "• {text} - The text to translate\n"
            "• {source_lang} - Source language code\n"
            "• {target_lang} - Target language code"
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #666666; font-size: 11px;")
        prompt_layout.addWidget(help_text)
        
        # Prompt template
        self.prompt_template = QTextEdit()
        self.prompt_template.setPlaceholderText("Enter custom translation prompt...")
        self.prompt_template.setText(SettingsManager.get_translation_prompt())
        prompt_layout.addWidget(self.prompt_template)
        
        prompt_group.setLayout(prompt_layout)
        main_layout.addWidget(prompt_group)
        
        # Translate button with some padding
        button_layout = QHBoxLayout()
        button_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.translate_btn = QPushButton("Translate Field")
        self.translate_btn.setMinimumWidth(150)
        button_layout.addWidget(self.translate_btn)
        button_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        main_layout.addLayout(button_layout)
        
        # Add stretch to push everything to the top
        main_layout.addStretch()
        
        self.setLayout(main_layout)
        
        # Connect signals
        self.layer_combo.currentIndexChanged.connect(self.on_layer_changed)
        self.service.currentTextChanged.connect(self.update_translation_settings)
        self.translate_btn.clicked.connect(self.on_translate)
        
        # Initialize UI state
        self.update_translation_settings()
        
    def populate_layers(self):
        """Populate layer combo with vector layers"""
        self.layer_combo.clear()
        for layer in self.project.mapLayers().values():
            if isinstance(layer, QgsVectorLayer) and layer.isValid():
                self.layer_combo.addItem(layer.name(), layer)
                
    def on_layer_changed(self, index):
        """Update fields when layer changes"""
        self.field_combo.clear()
        layer = self.layer_combo.currentData()
        if layer:
            for field in layer.fields():
                field_type = field.typeName()
                field_name = field.name()
                field_alias = field.alias() or field_name
                display_text = f"{field_name} ({field_alias}) - {field_type}"
                self.field_combo.addItem(display_text, field_name)
                
    def update_translation_settings(self):
        """Update UI based on selected service"""
        service = self.service.currentText()
        
        # Show/hide prompt settings based on service
        is_ai_service = service in ['OpenAI', 'DeepSeek', 'Ollama']
        prompt_group = self.prompt_template.parent()
        if prompt_group:
            prompt_group.setVisible(is_ai_service)
        
        # Update language options
        if service == 'Google Translate':
            self.source_lang.clear()
            self.source_lang.addItems(['auto', 'ar', 'en', 'fr', 'es', 'de', 'it', 'ja', 'ko', 'ru', 'zh'])
            self.target_lang.clear()
            self.target_lang.addItems(['ar', 'en', 'fr', 'es', 'de', 'it', 'ja', 'ko', 'ru', 'zh'])
        else:
            self.source_lang.clear()
            self.source_lang.addItems(['Auto', 'ar', 'en', 'fr', 'es', 'de'])
            self.target_lang.clear()
            self.target_lang.addItems(['en', 'ar', 'fr', 'es', 'de'])
            
    def on_translate(self):
        """Handle translate button click"""
        layer = self.layer_combo.currentData()
        source_field = self.field_combo.currentData()
        target_field = self.new_field.text().strip()
        service_name = self.service.currentText()
        source_lang = self.source_lang.currentText().lower()
        target_lang = self.target_lang.currentText().lower()
        
        # Basic validation
        if not layer or not source_field:
            QMessageBox.warning(self, "Error", "Please select a layer and field to translate.")
            return
            
        if not target_field:
            QMessageBox.warning(self, "Error", "Please enter a name for the new translated field.")
            return
            
        # Validate field name
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', target_field):
            QMessageBox.warning(
                self,
                "Invalid Field Name",
                "Field name must start with a letter and contain only letters, numbers, and underscores."
            )
            return
            
        try:
            # Get the appropriate prompt template based on batch mode
            if self.batch_mode.isChecked():
                prompt_template = SettingsManager.get_batch_translation_prompt()
            else:
                prompt_template = SettingsManager.get_translation_prompt()
            
            # Call the translation manager
            self.dialog.translation_manager.translate_column(
                layer=layer,
                source_field=source_field,
                target_field=target_field,
                prompt_template=prompt_template,
                service_name=service_name,
                source_lang=source_lang,
                target_lang=target_lang,
                batch_mode=self.batch_mode.isChecked(),
                batch_size=self.batch_size.value() if self.batch_mode.isChecked() else 1
            )
            
            QMessageBox.information(self, "Success", "Translation completed successfully!")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
