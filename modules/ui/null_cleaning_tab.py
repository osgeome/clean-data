"""
Null cleaning tab UI module for Clean Data QGIS plugin.
"""
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                                QGroupBox, QLabel, QComboBox, QLineEdit, 
                                QPushButton, QCheckBox, QSpacerItem, QSizePolicy)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsMessageLog, Qgis, QgsProject, QgsVectorLayer
from qgis.PyQt.QtWidgets import QMessageBox

class NullCleaningTab(QWidget):
    """Null cleaning tab widget"""
    
    def __init__(self, dialog):
        super().__init__()
        self.dialog = dialog
        self.project = QgsProject.instance()
        self.setup_ui()
        self.populate_layers()
        
    def setup_ui(self):
        """Setup the null cleaning tab UI"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(6)  # Reduce default spacing
        
        # Quick Clean section
        quick_group = QGroupBox("Quick Clean")
        quick_layout = QVBoxLayout()
        quick_layout.setSpacing(6)
        
        help_text = QLabel(
            "Quick clean will remove all columns that contain only null or empty values "
            "from all vector layers in your project."
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #666666; font-size: 11px;")
        quick_layout.addWidget(help_text)
        
        self.quick_clean_btn = QPushButton("Remove Empty Columns")
        self.quick_clean_btn.setToolTip("Scan all layers and remove columns containing only null values")
        quick_layout.addWidget(self.quick_clean_btn)
        
        quick_group.setLayout(quick_layout)
        main_layout.addWidget(quick_group)
        
        # Layer and Field Selection
        selection_group = QGroupBox("Layer and Field Selection")
        selection_grid = QGridLayout()
        selection_grid.setSpacing(6)
        
        # Layer selection
        selection_grid.addWidget(QLabel("Select Layer:"), 0, 0)
        self.layer_combo = QComboBox()
        self.layer_combo.setToolTip("Select the layer to clean")
        selection_grid.addWidget(self.layer_combo, 0, 1)
        
        # Field selection
        selection_grid.addWidget(QLabel("Select Field:"), 1, 0)
        self.field_combo = QComboBox()
        self.field_combo.setToolTip("Select the field to analyze or remove")
        selection_grid.addWidget(self.field_combo, 1, 1)
        
        selection_group.setLayout(selection_grid)
        main_layout.addWidget(selection_group)
        
        # Null Value Settings
        null_group = QGroupBox("Null Value Settings")
        null_grid = QGridLayout()
        null_grid.setSpacing(6)
        
        # Null type selection
        null_grid.addWidget(QLabel("Null Type:"), 0, 0)
        self.null_type = QComboBox()
        self.null_type.addItems(['Empty/NULL Values', 'Specific Value'])
        self.null_type.setToolTip("Choose how to identify null values")
        null_grid.addWidget(self.null_type, 0, 1)
        
        # Specific value input
        null_grid.addWidget(QLabel("Specific Value:"), 1, 0)
        self.specific_value = QLineEdit()
        self.specific_value.setPlaceholderText('Enter value to treat as null (e.g., "N/A", "0", "-")')
        self.specific_value.setEnabled(False)
        null_grid.addWidget(self.specific_value, 1, 1)
        
        # Threshold
        null_grid.addWidget(QLabel("Null Percentage Threshold:"), 2, 0)
        threshold_layout = QHBoxLayout()
        self.threshold = QLineEdit()
        self.threshold.setText("100")
        self.threshold.setToolTip("Remove columns with null percentage >= this value")
        self.threshold.setPlaceholderText("Enter percentage (0-100)")
        threshold_layout.addWidget(self.threshold)
        threshold_layout.addWidget(QLabel("%"))
        null_grid.addLayout(threshold_layout, 2, 1)
        
        null_group.setLayout(null_grid)
        main_layout.addWidget(null_group)
        
        # Action Buttons
        button_group = QGroupBox("Actions")
        button_layout = QVBoxLayout()
        button_layout.setSpacing(6)
        
        # Remove by percentage button
        self.remove_by_percent_btn = QPushButton("Remove Columns by Null Percentage")
        self.remove_by_percent_btn.setToolTip(
            "Remove columns where the percentage of null values exceeds the threshold"
        )
        button_layout.addWidget(self.remove_by_percent_btn)
        
        # Delete column button
        self.delete_column_btn = QPushButton("Delete Selected Column")
        self.delete_column_btn.setToolTip("Delete the currently selected column")
        button_layout.addWidget(self.delete_column_btn)
        
        button_group.setLayout(button_layout)
        main_layout.addWidget(button_group)
        
        # Add stretch to push everything to the top
        main_layout.addStretch()
        
        self.setLayout(main_layout)
        
        # Connect signals
        self.quick_clean_btn.clicked.connect(self.on_quick_clean)
        self.layer_combo.currentIndexChanged.connect(self.on_layer_changed)
        self.null_type.currentTextChanged.connect(self.on_null_type_changed)
        self.remove_by_percent_btn.clicked.connect(self.on_remove_by_percent)
        self.delete_column_btn.clicked.connect(self.on_delete_column)
        
        # Initial update
        self.on_null_type_changed(self.null_type.currentText())
        
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
                
    def on_null_type_changed(self, null_type):
        """Enable/disable specific value input based on null type"""
        is_specific = null_type == 'Specific Value'
        self.specific_value.setEnabled(is_specific)
        self.specific_value.setVisible(is_specific)
        
    def on_quick_clean(self):
        """Handle quick clean button click"""
        reply = QMessageBox.question(
            self,
            'Remove Empty Columns',
            'This will remove all columns that contain only null or empty values from all vector layers. Continue?'
        )
        
        if reply == QMessageBox.Yes:
            try:
                removed_count = 0
                for layer in self.project.mapLayers().values():
                    if isinstance(layer, QgsVectorLayer) and layer.isValid():
                        if self.dialog.cleaning_manager.remove_empty_columns(layer):
                            removed_count += 1
                        layer.commitChanges()
                
                if removed_count > 0:
                    QMessageBox.information(self, 'Clean Data', f'Successfully removed empty columns from {removed_count} layers.')
                else:
                    QMessageBox.information(self, 'Clean Data', 'No empty columns found in any layer.')
                    
                # Update fields in case columns were removed
                self.on_layer_changed(self.layer_combo.currentIndex())
                    
            except Exception as e:
                QMessageBox.warning(self, 'Error', str(e))
                
    def on_remove_by_percent(self):
        """Handle remove by percentage button click"""
        layer = self.layer_combo.currentData()
        field = self.field_combo.currentData()
        
        if not layer or not field:
            QMessageBox.warning(self, "Error", "Please select a layer and field.")
            return
            
        try:
            threshold = float(self.threshold.text()) if self.threshold.text() else 100
            if threshold < 0 or threshold > 100:
                QMessageBox.warning(self, "Error", "Threshold must be between 0 and 100.")
                return
                
            # Get the specific value if needed
            specific_value = None
            if self.null_type.currentText() == 'Specific Value':
                specific_value = self.specific_value.text()
                if not specific_value:
                    QMessageBox.warning(self, "Error", "Please enter a specific value to treat as null.")
                    return
                    
            if self.dialog.cleaning_manager.remove_columns_with_null_percentage(
                layer, field, threshold, specific_value
            ):
                QMessageBox.information(self, "Success", "Field cleaned successfully!")
                # Update fields in case columns were removed
                self.on_layer_changed(self.layer_combo.currentIndex())
            else:
                QMessageBox.information(self, "Info", "No changes were needed.")
                
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))
            
    def on_delete_column(self):
        """Handle delete column button click"""
        layer = self.layer_combo.currentData()
        field = self.field_combo.currentData()
        
        if not layer or not field:
            QMessageBox.warning(self, "Error", "Please select a layer and field.")
            return
            
        # Check if field exists
        if layer.fields().indexFromName(field) == -1:
            QMessageBox.warning(self, "Error", "Please select a valid field.")
            return
            
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            'Confirm Deletion',
            f'Are you sure you want to delete the column "{field}"?'
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Start editing if not already
                if not layer.isEditable():
                    layer.startEditing()
                
                # Delete the field
                if layer.deleteAttribute(layer.fields().indexFromName(field)):
                    layer.commitChanges()
                    
                    # Force layer to refresh its fields
                    layer.updateFields()
                    
                    # Update UI
                    self.on_layer_changed(self.layer_combo.currentIndex())
                    
                    QMessageBox.information(self, "Success", f'Column "{field}" deleted successfully.')
                else:
                    layer.rollBack()
                    QMessageBox.warning(self, "Error", f'Failed to delete column "{field}".')
            except Exception as e:
                layer.rollBack()
                QMessageBox.warning(self, "Error", str(e))
