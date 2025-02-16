# Clean Data Plugin Examples

## Find and Replace Examples

### Example 1: City ID Standardization
Convert city IDs to standard format with leading zeros.

**Source Layer:**
- Field: City_ID
- Values: "703002", "7", "123"

**Reference Layer:**
- Find Field: CITY_ID
- Values: "00703002", "00000007", "00000123"

**Settings:**
1. Enable Pattern Matching (uses `\d+` by default)
2. Check "Strip Leading Zeros"
3. Optional: Create new column "City_ID_Formatted"

**Result:**
- "703002" → "00703002"
- "7" → "00000007"
- "123" → "00000123"

**Why This Works:**
1. `\d+` pattern matches any sequence of digits
2. Strip Leading Zeros helps match "703002" with "00703002"
3. Reference format is preserved in output

### Example 2: Region ID Mapping
Map simple IDs to region names.

**Source Layer:**
- Field: Region_ID
- Values: "1", "2", "3", "10"

**Reference Layer:**
- Find Field: ID
- Values: "001", "002", "003", "010"
- Replace Field: Name
- Values: "North", "South", "East", "West"

**Settings:**
1. Enable Pattern Matching (uses `\d+` by default)
2. Check "Strip Leading Zeros"
3. Create new column "Region_Name"

**Result:**
- "1" → "North"
- "2" → "South"
- "3" → "East"
- "10" → "West"

### Example 3: Mixed Text Cleaning
Clean up mixed text and number fields.

**Source Values:**
- "ID-123-A"
- "ID-456-B"
- "ID-789-C"

**Settings:**
1. Enable Pattern Matching
2. Pattern: `\d+` (matches just the numbers)
3. Create new column for clean values

**Result:**
- "ID-123-A" → "123"
- "ID-456-B" → "456"
- "ID-789-C" → "789"

## Null Cleaning Examples

### Example 1: Remove Empty Columns
Remove completely empty columns from a layer.

**Settings:**
1. Click "Quick Clean"
2. Confirm operation

**Result:**
- Empty columns removed
- Layer structure simplified

### Example 2: Clean by Threshold
Remove columns with high null percentage.

**Settings:**
1. Select field
2. Set threshold (e.g., 80%)
3. Click "Clean"

**Result:**
- Columns with > 80% nulls removed
- Data quality improved

## Translation Examples

### Example 1: Place Names
Translate place names to Arabic.

**Settings:**
1. Select name field
2. Target: Arabic
3. Service: Google Translate

**Result:**
- "New York" → "نيويورك"
- "London" → "لندن"
