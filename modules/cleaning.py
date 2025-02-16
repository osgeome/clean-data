"""
Cleaning module for the Clean Data QGIS plugin.
Handles all data cleaning functionality.
"""

from qgis.core import QgsVectorLayer, QgsMessageLog, Qgis, QgsField, QgsFeature
from PyQt5.QtCore import QVariant

class ColumnCleaner:
    """Handles column-level cleaning operations"""
    
    @staticmethod
    def remove_empty_columns(layer):
        """Remove columns that contain only null or empty values"""
        if not isinstance(layer, QgsVectorLayer):
            return False
            
        if not layer.isEditable():
            layer.startEditing()
        
        provider = layer.dataProvider()
        fields = provider.fields()
        columns_to_delete = []
        
        QgsMessageLog.logMessage(
            f"Checking for empty columns in layer {layer.name()}", 
            'Clean Data', 
            Qgis.Info
        )
        
        for field in fields:
            field_name = field.name()
            all_null = True
            
            for feature in layer.getFeatures():
                value = feature[field_name]
                if value not in [None, "", QVariant()]:
                    all_null = False
                    break
            
            if all_null:
                columns_to_delete.append(field_name)
        
        if columns_to_delete:
            indices = [fields.indexFromName(col) for col in columns_to_delete]
            provider.deleteAttributes(indices)
            layer.updateFields()
            QgsMessageLog.logMessage(
                f"Removed empty columns: {columns_to_delete}", 
                'Clean Data', 
                Qgis.Success
            )
            return True
        else:
            QgsMessageLog.logMessage(
                f"No empty columns found", 
                'Clean Data', 
                Qgis.Info
            )
            return False

    @staticmethod
    def remove_columns_with_null_percentage(layer, field_name, threshold=100):
        """Remove columns based on null percentage threshold"""
        if not isinstance(layer, QgsVectorLayer):
            return False
            
        if not layer.isEditable():
            layer.startEditing()
            
        if field_name not in [field.name() for field in layer.fields()]:
            raise ValueError(f"Field '{field_name}' not found in layer")
            
        total_features = layer.featureCount()
        if total_features == 0:
            return False
            
        null_count = 0
        field_idx = layer.fields().indexFromName(field_name)
        
        for feature in layer.getFeatures():
            value = feature[field_idx]
            if value in [None, "", QVariant()]:
                null_count += 1
                
        null_percentage = (null_count / total_features) * 100
        
        if null_percentage >= threshold:
            provider = layer.dataProvider()
            provider.deleteAttributes([field_idx])
            layer.updateFields()
            QgsMessageLog.logMessage(
                f"Removed field {field_name} with {null_percentage:.1f}% null values", 
                'Clean Data', 
                Qgis.Success
            )
            return True
            
        QgsMessageLog.logMessage(
            f"Field {field_name} has {null_percentage:.1f}% null values (below threshold of {threshold}%)", 
            'Clean Data', 
            Qgis.Info
        )
        return False

class ValueCleaner:
    """Handles value-level cleaning operations"""
    
    @staticmethod
    def find_and_replace_values(layer, source_field, ref_layer=None, find_field=None, replace_field=None,
                               pattern_match=False, custom_pattern=None, strip_zeros=False, pad_zeros=False, pad_length=3,
                               create_new_column=False, new_column_name=None):
        """Find and replace values in a field
        
        Args:
            layer: The layer to modify
            source_field: The field to modify
            ref_layer: Reference layer for lookups (optional)
            find_field: Field in reference layer to match against (optional)
            replace_field: Field in reference layer to get replacement values from (optional)
            pattern_match: Whether to use regex pattern matching
            custom_pattern: Custom regex pattern to use
            strip_zeros: Whether to strip leading zeros when matching
            pad_zeros: Whether to pad numbers with zeros
            pad_length: Length to pad numbers to (default 3)
            create_new_column: Whether to create a new column for results
            new_column_name: Name for the new column (optional)
        """
        if not isinstance(layer, QgsVectorLayer):
            return 0
            
        if not layer.isEditable():
            layer.startEditing()
            
        field_idx = layer.fields().indexFromName(source_field)
        if field_idx < 0:
            raise ValueError(f"Field '{source_field}' not found in layer")
            
        # Create new field if requested
        if create_new_column:
            if not new_column_name:
                new_column_name = f"{source_field}_new"
                
            # Check if field already exists
            if layer.fields().indexFromName(new_column_name) >= 0:
                raise ValueError(f"Field '{new_column_name}' already exists")
                
            # Add new field with same type as source
            field = layer.fields()[field_idx]
            provider = layer.dataProvider()
            provider.addAttributes([QgsField(new_column_name, field.type(), field.typeName())])
            layer.updateFields()
            
            # Get index of new field
            new_field_idx = layer.fields().indexFromName(new_column_name)
            
        # Build lookup dictionary from reference layer if provided
        lookup = {}
        reverse_lookup = {}  # Store original values for debugging
        if ref_layer and find_field and replace_field:
            for feature in ref_layer.getFeatures():
                find_val = str(feature[find_field])
                replace_val = str(feature[replace_field])
                if strip_zeros:
                    stripped_val = find_val.lstrip('0')
                    lookup[stripped_val] = replace_val
                    reverse_lookup[stripped_val] = find_val  # Store original for debugging
                else:
                    lookup[find_val] = replace_val
                    reverse_lookup[find_val] = find_val
                
            # Log lookup table for debugging
            QgsMessageLog.logMessage(
                f"Lookup table created with {len(lookup)} entries: {lookup}",
                'Clean Data',
                Qgis.Info
            )
        
        # Process features
        replaced_count = 0
        for feature in layer.getFeatures():
            value = str(feature[field_idx])
            new_value = None
            original_value = value
            
            if pattern_match and custom_pattern:
                # Use custom regex pattern
                import re
                if re.search(custom_pattern, value):
                    if ref_layer:
                        # Try to find a match in the lookup dictionary
                        match = re.search(r'\d+', value)
                        if match:
                            num = match.group()
                            if strip_zeros:
                                num = num.lstrip('0')
                            if num in lookup:
                                new_value = lookup[num]
                                # Log successful match
                                QgsMessageLog.logMessage(
                                    f"Matched: {original_value} -> {num} (stripped) -> {new_value}",
                                    'Clean Data',
                                    Qgis.Info
                                )
                            else:
                                # Log failed match
                                QgsMessageLog.logMessage(
                                    f"No match found for: {original_value} -> {num} (stripped)",
                                    'Clean Data',
                                    Qgis.Warning
                                )
                    else:
                        # Use regex substitution
                        new_value = re.sub(custom_pattern, replace_field or '', value)
            
            elif ref_layer:
                # Direct lookup
                lookup_val = value
                if strip_zeros:
                    lookup_val = lookup_val.lstrip('0')
                if lookup_val in lookup:
                    new_value = lookup[lookup_val]
                    # Log successful match
                    QgsMessageLog.logMessage(
                        f"Direct match: {original_value} -> {lookup_val} (stripped) -> {new_value}",
                        'Clean Data',
                        Qgis.Info
                    )
                else:
                    # Log failed match
                    QgsMessageLog.logMessage(
                        f"No direct match found for: {original_value} -> {lookup_val} (stripped)",
                        'Clean Data',
                        Qgis.Warning
                    )
            
            elif pad_zeros:
                # Pad numbers with zeros
                try:
                    num = int(value)
                    new_value = str(num).zfill(pad_length)
                except ValueError:
                    pass
            
            else:
                # Simple find and replace
                if value == find_field:
                    new_value = replace_field
            
            if new_value is not None and new_value != value:
                if create_new_column:
                    layer.changeAttributeValue(feature.id(), new_field_idx, new_value)
                else:
                    layer.changeAttributeValue(feature.id(), field_idx, new_value)
                replaced_count += 1
                
        # Log summary
        QgsMessageLog.logMessage(
            f"Replaced {replaced_count} values out of {layer.featureCount()} features",
            'Clean Data',
            Qgis.Info
        )
                
        return replaced_count

class CleaningManager:
    """Manager class for cleaning operations"""
    
    def __init__(self):
        self.column_cleaner = ColumnCleaner()
        self.value_cleaner = ValueCleaner()
    
    def remove_empty_columns(self, layer):
        """Remove columns that contain only null or empty values"""
        return self.column_cleaner.remove_empty_columns(layer)
        
    def remove_columns_with_null_percentage(self, layer, field_name, threshold=100):
        """Remove columns based on null percentage threshold"""
        return self.column_cleaner.remove_columns_with_null_percentage(layer, field_name, threshold)
        
    def find_and_replace_values(self, layer, source_field, ref_layer=None, find_field=None, replace_field=None,
                               pattern_match=False, custom_pattern=None, strip_zeros=False, pad_zeros=False, pad_length=3,
                               create_new_column=False, new_column_name=None):
        """Find and replace values in a field"""
        return self.value_cleaner.find_and_replace_values(layer, source_field, ref_layer, find_field, replace_field,
                                                         pattern_match, custom_pattern, strip_zeros, pad_zeros, pad_length,
                                                         create_new_column, new_column_name)
    
    def clean_layer(self, layer, operations):
        """Apply multiple cleaning operations to a layer"""
        if not isinstance(layer, QgsVectorLayer):
            return False
            
        if not layer.isEditable():
            layer.startEditing()
            
        success = True
        for operation in operations:
            try:
                if operation['type'] == 'remove_empty_columns':
                    success &= self.remove_empty_columns(layer)
                elif operation['type'] == 'remove_null_columns':
                    success &= self.remove_columns_with_null_percentage(
                        layer,
                        operation['field'],
                        operation.get('threshold', 100)
                    )
                elif operation['type'] == 'find_replace':
                    count = self.find_and_replace_values(
                        layer,
                        operation['field'],
                        operation.get('ref_layer'),
                        operation.get('find'),
                        operation.get('replace'),
                        operation.get('pattern_match', False),
                        operation.get('custom_pattern'),
                        operation.get('strip_zeros', False),
                        operation.get('pad_zeros', False),
                        operation.get('pad_length', 3),
                        operation.get('create_new_column', False),
                        operation.get('new_column_name')
                    )
                    success &= count > 0
            except Exception as e:
                QgsMessageLog.logMessage(
                    f"Error in cleaning operation {operation['type']}: {str(e)}", 
                    'Clean Data', 
                    Qgis.Critical
                )
                success = False
                
        if success:
            layer.commitChanges()
        else:
            layer.rollBack()
            
        return success
