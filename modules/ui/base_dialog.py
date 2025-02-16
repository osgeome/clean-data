"""
Base dialog for Clean Data QGIS plugin.
"""
from qgis.PyQt.QtWidgets import QDialog, QTabWidget, QVBoxLayout, QMessageBox
from qgis.core import QgsProject, QgsVectorLayer, QgsMessageLog, Qgis

from ..translation import TranslationManager
from ..settings_manager import SettingsManager
from .translation_tab import TranslationTab
from .null_cleaning_tab import NullCleaningTab
from .find_replace_tab import FindReplaceTab
from .settings_tab import SettingsTab

class CleanDataDialog(QDialog):
    """Main dialog for the Clean Data plugin"""
    
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.translation_manager = TranslationManager()
        self.settings_manager = SettingsManager()
        self.project = QgsProject.instance()
        
        # Store references to layer combos for easy updates
        self.layer_combos = []
        
        self.setup_ui()
        self.connect_signals()
        self.load_settings()
        
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle('Clean Data')
        self.setMinimumWidth(500)  # Wider dialog for better readability
        
        layout = QVBoxLayout()
        layout.setSpacing(10)  # Add spacing between widgets
        layout.setContentsMargins(10, 10, 10, 10)  # Add margins
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Add tabs in specified order:
        # 1. Translation
        # 2. Null Cleaning
        # 3. Find Replace
        # 4. Settings
        self.translation_tab = TranslationTab(self)
        self.tab_widget.addTab(self.translation_tab, "Translation")
        
        self.null_tab = NullCleaningTab(self)
        self.tab_widget.addTab(self.null_tab, "Null Cleaning")
        
        self.find_replace_tab = FindReplaceTab(self)
        self.tab_widget.addTab(self.find_replace_tab, "Find Replace")
        
        self.settings_tab = SettingsTab(self)
        self.tab_widget.addTab(self.settings_tab, "Settings")
        
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)
        
    def connect_signals(self):
        """Connect signals to slots"""
        # Project layer signals
        self.project.layersAdded.connect(self.update_all_layer_combos)
        self.project.layersRemoved.connect(self.update_all_layer_combos)
    
    def update_all_layer_combos(self):
        """Update all layer combo boxes when project layers change"""
        for combo in self.layer_combos:
            current_layer = combo.currentData()
            self.populate_layers(combo)
            if current_layer:
                index = combo.findData(current_layer)
                if index >= 0:
                    combo.setCurrentIndex(index)
    
    def populate_layers(self, combo):
        """Populate a combo box with vector layers from the project"""
        combo.clear()
        layers = self.project.mapLayers().values()
        vector_layers = [layer for layer in layers 
                        if isinstance(layer, QgsVectorLayer) and layer.isValid()]
        
        # Sort layers by name for better organization
        vector_layers.sort(key=lambda x: x.name().lower())
        
        for layer in vector_layers:
            combo.addItem(layer.name(), layer)
        
        if combo not in self.layer_combos:
            self.layer_combos.append(combo)
    
    def update_fields(self, combo, field_combo=None):
        """Update fields for a layer combo box"""
        layer = combo.currentData()
        if not layer or not isinstance(layer, QgsVectorLayer):
            return
            
        if field_combo:
            current = field_combo.currentData()  # Store current selection
            field_combo.clear()
            
            # Group fields by type for better organization
            text_fields = []
            number_fields = []
            date_fields = []
            other_fields = []
            
            for field in layer.fields():
                field_type = field.typeName()
                field_name = field.name()
                field_alias = field.alias() or field_name
                display_text = f"{field_name} ({field_alias}) - {field_type}"
                
                field_item = (display_text, field_name, field_type)
                
                # Categorize fields
                if field_type.upper() in ['STRING', 'TEXT', 'VARCHAR']:
                    text_fields.append(field_item)
                elif field_type.upper() in ['INTEGER', 'INT', 'DOUBLE', 'REAL', 'FLOAT']:
                    number_fields.append(field_item)
                elif field_type.upper() in ['DATE', 'DATETIME', 'TIME']:
                    date_fields.append(field_item)
                else:
                    other_fields.append(field_item)
            
            # Add fields in groups with separators
            if text_fields:
                field_combo.addItem('--- Text Fields ---', None)
                for display, name, _ in sorted(text_fields):
                    field_combo.addItem(display, name)
                    
            if number_fields:
                field_combo.addItem('--- Number Fields ---', None)
                for display, name, _ in sorted(number_fields):
                    field_combo.addItem(display, name)
                    
            if date_fields:
                field_combo.addItem('--- Date Fields ---', None)
                for display, name, _ in sorted(date_fields):
                    field_combo.addItem(display, name)
                    
            if other_fields:
                field_combo.addItem('--- Other Fields ---', None)
                for display, name, _ in sorted(other_fields):
                    field_combo.addItem(display, name)
            
            # Try to restore previous selection if field still exists
            if current:
                idx = field_combo.findData(current)
                if idx >= 0:
                    field_combo.setCurrentIndex(idx)
                else:
                    # Find first non-separator item
                    for i in range(field_combo.count()):
                        if field_combo.itemData(i) is not None:
                            field_combo.setCurrentIndex(i)
                            break
    
    def get_layer_and_validate(self, combo, field_combo=None):
        """Get layer from combo and validate it"""
        layer = combo.currentData()
        if not isinstance(layer, QgsVectorLayer) or not layer.isValid():
            QMessageBox.warning(self, "Error", "Please select a valid vector layer.")
            return None
            
        if field_combo:
            field = field_combo.currentData()
            if not field or field not in layer.fields().names():
                QMessageBox.warning(self, "Error", "Please select a valid field.")
                return None
                
        return layer
    
    def get_selected_field_name(self, combo):
        """Get the actual field name from combo box selection"""
        if not combo:
            return None
        return combo.currentData()
    
    def load_settings(self):
        """Load settings from QgsSettings"""
        # Load settings and update all tabs
        self.settings_tab.load_settings()
    
    def save_settings(self):
        """Save settings to QgsSettings"""
        # Save settings from all tabs
        self.settings_tab.save_settings()
