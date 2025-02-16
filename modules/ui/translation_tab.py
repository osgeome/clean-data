"""
Translation tab UI module for Clean Data QGIS plugin.
"""
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                                QGroupBox, QLabel, QComboBox, QLineEdit, 
                                QPushButton, QTextEdit, QMessageBox, QSpacerItem,
                                QSizePolicy, QCheckBox, QSpinBox, QRadioButton,
                                QButtonGroup)
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
        
        # Target field options
        target_group = QGroupBox("Target Field")
        target_layout = QVBoxLayout()
        
        # Radio buttons for field selection
        self.field_button_group = QButtonGroup()
        
        # New field option
        new_field_layout = QHBoxLayout()
        self.new_field_radio = QRadioButton("Create New Field:")
        self.new_field_radio.setChecked(True)  # Default to new field
        self.field_button_group.addButton(self.new_field_radio)
        new_field_layout.addWidget(self.new_field_radio)
        
        self.new_field = QLineEdit()
        self.new_field.setPlaceholderText("e.g., name_en, description_fr")
        new_field_layout.addWidget(self.new_field)
        target_layout.addLayout(new_field_layout)
        
        # Existing field option
        existing_field_layout = QHBoxLayout()
        self.existing_field_radio = QRadioButton("Use Existing Field:")
        self.field_button_group.addButton(self.existing_field_radio)
        existing_field_layout.addWidget(self.existing_field_radio)
        
        self.target_field_combo = QComboBox()
        self.target_field_combo.setEnabled(False)  # Disabled by default
        existing_field_layout.addWidget(self.target_field_combo)
        target_layout.addLayout(existing_field_layout)
        
        # Connect radio buttons
        self.new_field_radio.toggled.connect(self.toggle_field_selection)
        
        target_group.setLayout(target_layout)
        layer_grid.addWidget(target_group, 2, 0, 1, 2)
        
        layer_group.setLayout(layer_grid)
        main_layout.addWidget(layer_group)
        
        # Progress label
        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setVisible(False)
        main_layout.addWidget(self.progress_label)
        
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
        self.translate_button = QPushButton("Translate Field")
        self.translate_button.setMinimumWidth(150)
        button_layout.addWidget(self.translate_button)
        button_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        main_layout.addLayout(button_layout)
        
        # Add stretch to push everything to the top
        main_layout.addStretch()
        
        self.setLayout(main_layout)
        
        # Connect signals
        self.layer_combo.currentIndexChanged.connect(self.on_layer_changed)
        self.service.currentTextChanged.connect(self.update_translation_settings)
        self.translate_button.clicked.connect(self.handle_translate)
        
        # Initialize UI state
        self.update_translation_settings()
        
    def populate_layers(self):
        """Populate layer combo with vector layers from QGIS canvas"""
        self.layer_combo.clear()
        
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer) and layer.isValid():
                self.layer_combo.addItem(layer.name(), layer)
                
    def on_layer_changed(self, index):
        """Update field combos when layer changes"""
        self.field_combo.clear()
        self.target_field_combo.clear()
        
        layer = self.layer_combo.currentData()
        if layer:
            for field in layer.fields():
                field_type = field.typeName()
                field_name = field.name()
                field_alias = field.alias() or field_name
                display_text = f"{field_name} ({field_alias}) - {field_type}"
                self.field_combo.addItem(display_text, field_name)
                self.target_field_combo.addItem(display_text, field_name)
                
    def toggle_field_selection(self, checked):
        """Toggle between new field and existing field options"""
        self.new_field.setEnabled(checked)
        self.target_field_combo.setEnabled(not checked)
        
    def get_target_field(self):
        """Get the target field name based on selection"""
        if self.new_field_radio.isChecked():
            return self.new_field.text().strip()
        else:
            # Get the field name from the combo box data, not the display text
            return self.target_field_combo.currentData()
            
    def update_progress(self, task):
        """Update progress label with task progress"""
        if hasattr(task, 'total_features') and hasattr(task, 'translated_count'):
            self.progress_label.setText(
                f"Processing: {task.translated_count}/{task.total_features} features"
            )
            self.progress_label.setVisible(True)
            
    def clear_progress(self):
        """Clear the progress label"""
        self.progress_label.setText("")
        self.progress_label.setVisible(False)
        
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
            
    def handle_translate(self):
        """Handle translate button click"""
        try:
            layer = self.layer_combo.currentData()
            source_field = self.field_combo.currentData()
            target_field = self.get_target_field()
            service_name = self.service.currentText()
            source_lang = self.source_lang.currentText().lower()
            target_lang = self.target_lang.currentText().lower()
            
            if not layer or not source_field or not target_field:
                QMessageBox.warning(
                    self,
                    "Missing Information",
                    "Please select a layer, source field, and target field."
                )
                return
                
            # Validate field name if creating new field
            if self.new_field_radio.isChecked():
                if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', target_field):
                    QMessageBox.warning(
                        self,
                        "Invalid Field Name",
                        "Field name must start with a letter and contain only letters, numbers, and underscores."
                    )
                    return
                    
            # Clear any previous progress
            self.clear_progress()
            
            # Get translation settings
            batch_mode = self.batch_mode.isChecked()
            batch_size = self.batch_size.value()
            prompt_template = self.prompt_template.toPlainText() if service_name in ['OpenAI', 'DeepSeek', 'Ollama'] else None
            
            # Start translation with progress callback
            self.dialog.translation_manager.translate_column(
                layer=layer,
                source_field=source_field,
                target_field=target_field,
                service_name=service_name,
                source_lang=source_lang,
                target_lang=target_lang,
                batch_mode=batch_mode,
                batch_size=batch_size,
                prompt_template=prompt_template,
                progress_callback=self.update_progress
            )
            
            # Show info that translation has started
            QMessageBox.information(
                self,
                "Translation Started",
                "Translation task has started in the background.\nYou can start another translation while this one is running."
            )
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Failed to start translation: {str(e)}",
                'Clean Data',
                Qgis.Critical
            )
            QMessageBox.critical(
                self,
                "Translation Error",
                f"Failed to start translation: {str(e)}"
            )
            
    def task_finished(self, task):
        """Handle task completion"""
        self.clear_progress()
        
        if task.exception:
            QMessageBox.critical(
                self,
                "Translation Error",
                f"Translation failed: {str(task.exception)}"
            )
        else:
            if hasattr(task, 'skipped_features') and task.skipped_features:
                QMessageBox.information(
                    self,
                    "Success",
                    f"Translation completed successfully!\n\nSkipped {len(task.skipped_features)} features that were empty or already translated."
                )
            else:
                QMessageBox.information(
                    self,
                    "Success",
                    "Translation completed successfully!"
                )
