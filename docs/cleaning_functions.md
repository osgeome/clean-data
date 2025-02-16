# Clean Data Plugin Functions

## Null Value Cleaning

### Remove Empty Columns
Removes columns that contain only null or empty values from selected layers.

**How to use:**
1. Click "Quick Clean" button
2. Confirm the operation
3. Plugin will scan all vector layers and remove completely empty columns

### Remove Columns by Null Percentage
Removes columns that have a percentage of null values above a specified threshold.

**How to use:**
1. Select a layer
2. Select a field to check
3. Enter threshold percentage (0-100)
4. Click "Remove Columns by Null Percentage"
5. Columns with null percentage above threshold will be removed

## Find and Replace

### Pattern Matching
The plugin provides powerful pattern matching capabilities using regular expressions.

**Default Pattern: `\d+`**
- Matches any sequence of digits
- Perfect for standardizing ID fields
- Works with varying length numbers

**Common Patterns:**
- `\d+` : Match any sequence of digits (default)
- `^\d+` : Match digits at start of text
- `\d+$` : Match digits at end of text
- `[A-Z]+` : Match uppercase letters

**Options:**
- Strip Leading Zeros: Ignore leading zeros when matching
- Create New Column: Save results in a new field
- Pad Numbers: Add leading zeros to standardize length

### Reference Layer Matching
Match and replace values using a reference layer.

**How to use:**
1. Select source layer and field to modify
2. Select reference layer
3. Choose Find Field (to match against)
4. Choose Replace Field (to get new values from)
5. Enable pattern matching if needed
6. Click "Find and Replace"

**Example: ID Standardization**
1. Source: Field with values like "1", "2", "10"
2. Reference: Field with values like "001", "002", "010"
3. Enable pattern matching (uses `\d+` by default)
4. Check "Strip Leading Zeros"
5. Result: IDs will match reference format

## Translation

### Field Translation
Translate text in a field to another language.

**How to use:**
1. Select layer and field to translate
2. Choose translation service:
   - Google Translate (direct API)
   - OpenAI
   - DeepSeek
   - Ollama
3. Set source and target languages
4. Configure batch size and API settings
5. Click "Translate Field"

## Tips and Best Practices

1. **Pattern Matching**
   - Use `\d+` for numeric IDs (default)
   - Test patterns on a small dataset first
   - Use "Create New Column" to preserve original data

2. **Reference Layer Tips**
   - Ensure reference data is complete
   - Use pattern matching for flexible matching
   - Strip leading zeros when matching IDs

3. **Data Types**
   - Create new columns when changing data formats
   - Match data types between source and reference
   - Use appropriate patterns for data type
