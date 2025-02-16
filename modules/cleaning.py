"""
Cleaning module for the Clean Data QGIS plugin.
Handles all data cleaning functionality.
"""

from qgis.core import QgsVectorLayer, QgsMessageLog, Qgis, QgsField, QgsFeature
from PyQt5.QtCore import QVariant
from PyQt5.QtCore import QByteArray

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
    def find_and_replace_values(source_layer, source_field, ref_layer=None, find_field=None, 
                              replace_field=None, pattern_match=False, custom_pattern=None,
                              strip_zeros=False, pad_zeros=False, pad_length=8,
                              create_new_column=False, new_column_name=None, new_column_type='TEXT'):
        """Find and replace values in a field"""
        if not source_layer or not source_field:
            return 0
            
        # Start editing if not already
        if not source_layer.isEditable():
            source_layer.startEditing()
            
        # Create lookup table from reference layer if provided
        lookup = {}
        if ref_layer and find_field and replace_field:
            for feature in ref_layer.getFeatures():
                find_value = str(feature[find_field])
                replace_value = str(feature[replace_field])
                
                # Handle pattern matching in reference values
                if pattern_match and custom_pattern:
                    try:
                        import re
                        pattern = re.compile(custom_pattern)
                        match = pattern.search(find_value)
                        if match:
                            find_value = match.group()
                    except re.error:
                        QgsMessageLog.logMessage(f"Invalid pattern: {custom_pattern}", "Clean Data", Qgis.Warning)
                        return 0
                        
                # Handle zero stripping in reference values
                if strip_zeros:
                    find_value = find_value.lstrip('0')
                    
                lookup[find_value] = replace_value
                
            QgsMessageLog.logMessage(f"Lookup table created with {len(lookup)} entries: {str(dict(list(lookup.items())[:10]))}", "Clean Data", Qgis.Info)
            
        # Create new field if requested
        field_idx = source_layer.fields().indexFromName(source_field)
        if create_new_column:
            # Use provided name or generate one
            new_name = new_column_name or f"{source_field}_new"
            
            # Map GeoPackage types to QVariant types
            type_map = {
                # Text types
                'TEXT': QVariant.String,
                # Integer types
                'INTEGER': QVariant.Int,
                'INT': QVariant.Int,
                'SMALLINT': QVariant.Int,
                'MEDIUMINT': QVariant.Int,
                'TINYINT': QVariant.Int,
                # Decimal types
                'DOUBLE': QVariant.Double,
                'FLOAT': QVariant.Double,
                'REAL': QVariant.Double,
                # Date/Time types
                'DATE': QVariant.Date,
                'DATETIME': QVariant.DateTime,
                # Other types
                'BOOLEAN': QVariant.Bool,
                'BLOB': QVariant.ByteArray
            }
            field_type = type_map.get(new_column_type.upper(), QVariant.String)
            
            # Add new field with specified type
            source_layer.addAttribute(QgsField(new_name, field_type))
            source_layer.updateFields()
            new_field_idx = source_layer.fields().indexFromName(new_name)
            
        # Process features
        count = 0
        features = source_layer.getFeatures()
        total_features = source_layer.featureCount()
        
        for feature in features:
            value = str(feature[source_field])
            original_value = value
            matched = False
            
            # Handle pattern matching in source values
            if pattern_match and custom_pattern:
                try:
                    import re
                    pattern = re.compile(custom_pattern)
                    match = pattern.search(value)
                    if match:
                        value = match.group()
                        matched = True
                except re.error:
                    continue
                    
            # Handle zero stripping in source values
            if strip_zeros:
                stripped_value = value.lstrip('0')
                QgsMessageLog.logMessage(f"Processing: {value} -> {stripped_value} (stripped)", "Clean Data", Qgis.Info)
                value = stripped_value
                
            # Look up replacement value
            new_value = None
            if value in lookup:
                new_value = lookup[value]
                matched = True
            elif not ref_layer:  # If no reference layer, just use the matched pattern
                new_value = value
                matched = True
                
            # Handle zero padding for output
            if matched and pad_zeros and new_value:
                try:
                    # Remove any existing leading zeros
                    num_str = str(int(new_value))
                    # Pad to specified length
                    new_value = num_str.zfill(pad_length)
                except ValueError:
                    # If not a number, skip padding
                    pass
                    
            if matched and new_value:
                QgsMessageLog.logMessage(f"Matched: {original_value} -> {value} (stripped) -> {new_value}", "Clean Data", Qgis.Info)
                
                # Convert value based on target field type
                if create_new_column:
                    try:
                        new_column_type = new_column_type.upper()
                        if new_column_type in ['INTEGER', 'INT', 'SMALLINT', 'MEDIUMINT', 'TINYINT']:
                            new_value = int(new_value)
                            # Check range limits
                            if new_column_type == 'SMALLINT' and not (-32768 <= new_value <= 32767):
                                raise ValueError("Value out of range for SMALLINT")
                            elif new_column_type == 'MEDIUMINT' and not (-8388608 <= new_value <= 8388607):
                                raise ValueError("Value out of range for MEDIUMINT")
                            elif new_column_type == 'TINYINT' and not (-128 <= new_value <= 127):
                                raise ValueError("Value out of range for TINYINT")
                        elif new_column_type in ['DOUBLE', 'FLOAT', 'REAL']:
                            new_value = float(new_value)
                        elif new_column_type == 'BOOLEAN':
                            new_value = new_value.lower() in ['true', '1', 't', 'yes', 'y']
                        elif new_column_type == 'DATE':
                            from datetime import datetime
                            new_value = datetime.strptime(new_value, '%Y-%m-%d').date()
                        elif new_column_type == 'DATETIME':
                            from datetime import datetime
                            new_value = datetime.strptime(new_value, '%Y-%m-%d %H:%M:%S')
                        elif new_column_type == 'BLOB':
                            new_value = QByteArray(new_value.encode())
                        # TEXT type needs no conversion
                    except (ValueError, TypeError) as e:
                        QgsMessageLog.logMessage(f"Warning: Could not convert '{new_value}' to {new_column_type}: {str(e)}", "Clean Data", Qgis.Warning)
                        continue
                
                # Update the value
                if create_new_column:
                    source_layer.changeAttributeValue(feature.id(), new_field_idx, new_value)
                else:
                    source_layer.changeAttributeValue(feature.id(), field_idx, new_value)
                count += 1
            else:
                QgsMessageLog.logMessage(f"No match found for: {original_value} -> {value} (stripped)", "Clean Data", Qgis.Warning)
                
        QgsMessageLog.logMessage(f"Replaced {count} values out of {total_features} features", "Clean Data", Qgis.Info)
        return count

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
                               pattern_match=False, custom_pattern=None, strip_zeros=False, pad_zeros=False, pad_length=8,
                               create_new_column=False, new_column_name=None, new_column_type='TEXT'):
        """Find and replace values in a field"""
        return self.value_cleaner.find_and_replace_values(layer, source_field, ref_layer, find_field, replace_field,
                                                         pattern_match, custom_pattern, strip_zeros, pad_zeros, pad_length,
                                                         create_new_column, new_column_name, new_column_type)
    
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
                        operation.get('pad_length', 8),
                        operation.get('create_new_column', False),
                        operation.get('new_column_name'),
                        operation.get('new_column_type', 'TEXT')
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
