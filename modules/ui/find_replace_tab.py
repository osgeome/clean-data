"""
Find and Replace tab UI module for Clean Data QGIS plugin.
"""
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                                QGroupBox, QLabel, QComboBox, QLineEdit, 
                                QPushButton, QCheckBox, QSpinBox, QMessageBox)
from qgis.PyQt.QtCore import Qt
from PyQt5.QtCore import QVariant
from qgis.core import QgsMessageLog, Qgis, QgsProject, QgsVectorLayer

class FindReplaceTab(QWidget):
    """Find and Replace tab widget"""
    
    def __init__(self, dialog):
        super().__init__()
        self.dialog = dialog
        self.setup_ui()
        self.populate_layers()
        self.connect_signals()
        
    def setup_ui(self):
        """Setup the find and replace tab UI"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(6)  # Reduce default spacing
        
        # Create grid layout for better organization
        grid = QGridLayout()
        grid.setSpacing(6)
        
        # Source Layer section
        grid.addWidget(QLabel("Source Layer:"), 0, 0)
        self.source_layer_combo = QComboBox()
        grid.addWidget(self.source_layer_combo, 0, 1)
        
        # Source Field
        grid.addWidget(QLabel("Source Field:"), 1, 0)
        self.source_field_combo = QComboBox()
        grid.addWidget(self.source_field_combo, 1, 1)
        
        # New Column Options in horizontal layout
        new_col_group = QGroupBox("New Column Options")
        new_col_layout = QHBoxLayout()
        new_col_layout.setSpacing(6)
        
        self.create_new_column = QCheckBox("Create New Column")
        self.create_new_column.stateChanged.connect(self.on_create_new_column_changed)
        new_col_layout.addWidget(self.create_new_column)
        
        self.new_column_name = QLineEdit()
        self.new_column_name.setPlaceholderText("New column name")
        self.new_column_name.setEnabled(False)
        new_col_layout.addWidget(self.new_column_name)
        
        self.new_column_type = QComboBox()
        data_types = [
            'TEXT', 'INTEGER', 'INT', 'SMALLINT', 'MEDIUMINT', 'TINYINT',
            'DOUBLE', 'FLOAT', 'REAL', 'DATE', 'DATETIME', 'BOOLEAN', 'BLOB'
        ]
        self.new_column_type.addItems(data_types)
        self.new_column_type.setEnabled(False)
        
        # Add tooltip explaining each type
        type_tooltip = (
            "Data Types:\n"
            "TEXT: String of any length\n"
            "INTEGER/INT: Standard integer\n"
            "SMALLINT: Small integer (-32768 to 32767)\n"
            "MEDIUMINT: Medium integer (-8388608 to 8388607)\n"
            "TINYINT: Tiny integer (-128 to 127)\n"
            "DOUBLE: Double precision floating point\n"
            "FLOAT: Single precision floating point\n"
            "REAL: Real number\n"
            "DATE: Date value (YYYY-MM-DD)\n"
            "DATETIME: Date and time value\n"
            "BOOLEAN: True/False value\n"
            "BLOB: Binary data"
        )
        self.new_column_type.setToolTip(type_tooltip)
        new_col_layout.addWidget(self.new_column_type)
        
        new_col_group.setLayout(new_col_layout)
        
        # Reference Layer section
        grid.addWidget(QLabel("Reference Layer:"), 2, 0)
        self.ref_layer_combo = QComboBox()
        grid.addWidget(self.ref_layer_combo, 2, 1)
        
        # Find and Replace Fields in horizontal layout
        fields_layout = QHBoxLayout()
        fields_layout.setSpacing(6)
        
        find_layout = QVBoxLayout()
        find_layout.setSpacing(3)
        find_layout.addWidget(QLabel("Find Field (in Reference):"))
        self.find_field_combo = QComboBox()
        find_layout.addWidget(self.find_field_combo)
        fields_layout.addLayout(find_layout)
        
        replace_layout = QVBoxLayout()
        replace_layout.setSpacing(3)
        replace_layout.addWidget(QLabel("Replace Field (in Reference):"))
        self.replace_field_combo = QComboBox()
        replace_layout.addWidget(self.replace_field_combo)
        fields_layout.addLayout(replace_layout)
        
        # Pattern Matching section
        pattern_group = QGroupBox("Pattern Matching")
        pattern_layout = QGridLayout()
        pattern_layout.setSpacing(6)
        
        self.pattern_match = QCheckBox("Use Pattern Matching")
        self.pattern_match.stateChanged.connect(self.on_pattern_match_changed)
        pattern_layout.addWidget(self.pattern_match, 0, 0, 1, 2)
        
        patterns_help = QLabel(
            "Common Patterns:\n"
            "- \\d+ : Match any sequence of digits (default)\n"
            "- ^\\d+ : Match digits at start of text\n"
            "- \\d+$ : Match digits at end of text\n"
            "- [A-Z]+ : Match uppercase letters"
        )
        patterns_help.setStyleSheet('color: gray; font-size: 11px;')
        pattern_layout.addWidget(patterns_help, 1, 0, 1, 2)
        
        pattern_layout.addWidget(QLabel("Custom Pattern:"), 2, 0)
        self.custom_pattern = QLineEdit()
        self.custom_pattern.setPlaceholderText("\\d+")
        self.custom_pattern.setEnabled(False)
        pattern_layout.addWidget(self.custom_pattern, 2, 1)
        
        pattern_group.setLayout(pattern_layout)
        
        # Zero Handling section in horizontal layout
        zero_group = QGroupBox("Zero Handling")
        zero_layout = QHBoxLayout()
        zero_layout.setSpacing(6)
        
        self.strip_zeros = QCheckBox("Strip Leading Zeros When Matching")
        zero_layout.addWidget(self.strip_zeros)
        
        self.pad_zeros = QCheckBox("Pad Numbers with Zeros")
        self.pad_zeros.stateChanged.connect(self.on_pad_zeros_changed)
        zero_layout.addWidget(self.pad_zeros)
        
        pad_length_layout = QHBoxLayout()
        pad_length_layout.addWidget(QLabel("Pad Length:"))
        self.pad_length = QSpinBox()
        self.pad_length.setMinimum(1)
        self.pad_length.setMaximum(20)
        self.pad_length.setValue(8)
        self.pad_length.setEnabled(False)
        pad_length_layout.addWidget(self.pad_length)
        zero_layout.addLayout(pad_length_layout)
        
        zero_group.setLayout(zero_layout)
        
        # Find and Replace button
        self.find_replace_btn = QPushButton("Find and Replace")
        self.find_replace_btn.clicked.connect(self.on_find_replace)
        
        # Add all layouts to main layout
        main_layout.addLayout(grid)
        main_layout.addWidget(new_col_group)
        main_layout.addLayout(fields_layout)
        main_layout.addWidget(pattern_group)
        main_layout.addWidget(zero_group)
        main_layout.addWidget(self.find_replace_btn)
        main_layout.addStretch()
        
        self.setLayout(main_layout)
        
    def connect_signals(self):
        """Connect all signals"""
        self.source_layer_combo.currentIndexChanged.connect(self.on_source_layer_changed)
        self.ref_layer_combo.currentIndexChanged.connect(self.on_ref_layer_changed)
        
    def populate_layers(self):
        """Populate layer combos with vector layers from QGIS canvas"""
        self.source_layer_combo.clear()
        self.ref_layer_combo.clear()
        
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer) and layer.isValid():
                self.source_layer_combo.addItem(layer.name(), layer)
                self.ref_layer_combo.addItem(layer.name(), layer)
                
    def on_source_layer_changed(self, index):
        """Update source field combo when source layer changes"""
        self.source_field_combo.clear()
        layer = self.source_layer_combo.currentData()
        if layer:
            for field in layer.fields():
                field_type = field.typeName()
                field_name = field.name()
                field_alias = field.alias() or field_name
                display_text = f"{field_name} ({field_alias}) - {field_type}"
                self.source_field_combo.addItem(display_text, field_name)
                
    def on_ref_layer_changed(self, index):
        """Update find and replace field combos when reference layer changes"""
        self.find_field_combo.clear()
        self.replace_field_combo.clear()
        layer = self.ref_layer_combo.currentData()
        if layer:
            for field in layer.fields():
                field_type = field.typeName()
                field_name = field.name()
                field_alias = field.alias() or field_name
                display_text = f"{field_name} ({field_alias}) - {field_type}"
                self.find_field_combo.addItem(display_text, field_name)
                self.replace_field_combo.addItem(display_text, field_name)
                
    def on_pattern_match_changed(self, state):
        """Handle pattern match checkbox state change"""
        is_checked = state == Qt.Checked
        self.custom_pattern.setEnabled(is_checked)
        if is_checked and not self.custom_pattern.text():
            self.custom_pattern.setText('\\d+')  # Set default pattern
            
    def on_pad_zeros_changed(self, state):
        """Handle pad zeros checkbox state change"""
        is_checked = state == Qt.Checked
        self.pad_length.setEnabled(is_checked)
        
        # If enabling pad zeros, suggest pattern matching with \d+
        if is_checked and not self.pattern_match.isChecked():
            reply = QMessageBox.question(
                self,
                "Enable Pattern Matching?",
                "Would you like to enable pattern matching with '\\d+' for better number detection?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self.pattern_match.setChecked(True)
                self.custom_pattern.setText('\\d+')
                
    def on_create_new_column_changed(self, state):
        """Handle create new column checkbox state change"""
        is_checked = state == Qt.Checked
        self.new_column_name.setEnabled(is_checked)
        self.new_column_type.setEnabled(is_checked)
        
        if not is_checked:
            self.new_column_name.clear()
        elif not self.new_column_name.text():
            # Suggest a name based on the current field
            source_field = self.source_field_combo.currentData()
            if source_field:
                self.new_column_name.setText(f"{source_field}_formatted")
                # Set default type to TEXT for ID fields
                self.new_column_type.setCurrentText('TEXT')
                
    def on_find_replace(self):
        """Handle find and replace button click"""
        source_layer = self.source_layer_combo.currentData()
        source_field = self.source_field_combo.currentData()
        ref_layer = self.ref_layer_combo.currentData()
        find_field = self.find_field_combo.currentData()
        replace_field = self.replace_field_combo.currentData()
        
        if not source_layer or not source_field:
            QMessageBox.warning(self, "Error", "Please select a source layer and field.")
            return
            
        if ref_layer and (not find_field or not replace_field):
            QMessageBox.warning(self, "Error", "Please select both find and replace fields from the reference layer.")
            return
            
        try:
            # Check field type
            field_idx = source_layer.fields().indexFromName(source_field)
            field = source_layer.fields()[field_idx]
            is_integer = field.type() in [QVariant.Int, QVariant.LongLong, QVariant.UInt, QVariant.ULongLong]
            
            pattern_match = self.pattern_match.isChecked()
            custom_pattern = self.custom_pattern.text() if pattern_match else None
            strip_zeros = self.strip_zeros.isChecked()
            pad_zeros = self.pad_zeros.isChecked()
            pad_length = self.pad_length.value()
            
            create_new = self.create_new_column.isChecked()
            new_name = self.new_column_name.text() if create_new else None
            
            # If trying to pad zeros on an integer field, suggest creating a new string field
            if pad_zeros and is_integer and not create_new:
                reply = QMessageBox.question(
                    self,
                    "Data Type Warning",
                    f"The field '{source_field}' is an integer field which cannot store leading zeros. "
                    "Would you like to create a new text field for the padded values?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    create_new = True
                    new_name = f"{source_field}_formatted"
                else:
                    if not QMessageBox.question(
                        self,
                        "Continue?",
                        "Without creating a new field, leading zeros will be lost. Continue anyway?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    ) == QMessageBox.Yes:
                        return
            
            if create_new and not new_name:
                new_name = f"{source_field}_new"
            
            if pattern_match and custom_pattern:
                import re
                try:
                    re.compile(custom_pattern)
                except re.error as e:
                    QMessageBox.warning(self, "Error", f"Invalid regular expression pattern: {str(e)}")
                    return
            
            # Call the cleaning manager's find_and_replace function
            self.dialog.cleaning_manager.find_and_replace_values(
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
                new_column_name=new_name,
                new_column_type=self.new_column_type.currentText() if create_new else None
            )
            
            QMessageBox.information(self, "Success", "Find and replace operation completed successfully!")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
