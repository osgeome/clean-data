# Clean Data QGIS Plugin

A powerful QGIS plugin for cleaning, transforming, and managing vector layer data with advanced features including field translation using AI models.

## Features

### 1. Field Translation
- Translate field contents to multiple languages using various translation services:
  - Google Translate API
  - Ollama (Local LLM)
  - OpenAI
  - DeepSeek
- Batch processing support for efficient translation of large datasets
- Customizable translation prompts and rules
- Support for source and target language specification

### 2. Null Value Cleaning
- Identify and clean null values in vector layers
- Multiple cleaning options:
  - Delete rows with null values
  - Replace nulls with specific values
  - Custom null value handling

### 3. Find and Replace
- Advanced find and replace functionality for field contents
- Pattern matching support
- Reference layer-based replacements

## Requirements

- QGIS 3.x
- Python 3.x
- Required Python packages (see [requirements.txt](requirements.txt)):
  ```
  requests>=2.31.0
  googletrans>=4.0.2
  deep-translator==1.11.4
  ```

## Installation

1. Download the plugin from QGIS Plugin Repository or clone this repository
2. Place the plugin in your QGIS plugins directory:
   ```
   ~/.qgis3/python/plugins/clean-data/
   ```
3. Enable the plugin in QGIS:
   - Open QGIS
   - Go to Plugins > Manage and Install Plugins
   - Find "Clean Data" and check the box to enable it

## Configuration

### Translation Services Setup

#### Google Translate
- Requires a Google Cloud API key
- Set your API key in the plugin settings

#### Ollama
- Requires local Ollama installation
- Configure Ollama URL in settings (default: http://localhost:11434)
- Recommended model: aya

#### OpenAI/DeepSeek
- Requires respective API keys
- Configure in plugin settings

## Usage

### Field Translation

1. Select the vector layer containing the field to translate
2. Choose the field to translate
3. Enter a name for the new translated field
4. Select translation service
5. Configure source and target languages
6. Customize translation prompt if needed
7. Click "Translate Field"

### Null Value Cleaning

1. Select layer and field containing null values
2. Choose cleaning method
3. Configure replacement values if applicable
4. Apply changes

### Find and Replace

1. Select source layer and field
2. Configure search pattern
3. Set replacement options
4. Apply replacements

## Best Practices

1. Always backup your data before making changes
2. Test translations on a small subset first
3. Review translated content for accuracy
4. Use appropriate language codes (e.g., 'ar' for Arabic)

## Troubleshooting

### Common Issues

1. Translation service not responding:
   - Check API key configuration
   - Verify network connection
   - Ensure service endpoints are accessible

2. Missing translations:
   - Verify field contents are not empty
   - Check language code validity
   - Review translation prompt format

3. Null cleaning issues:
   - Verify field data types match
   - Check for valid replacement values

## Contributing

Contributions are welcome! Please feel free to submit pull requests or create issues for bugs and feature requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- QGIS Development Team
- Ollama Project
- Google Cloud Platform
- OpenAI
- DeepSeek

## Support

For support, please:
1. Check the documentation
2. Search existing issues
3. Create a new issue with:
   - QGIS version
   - Plugin version
   - Error messages
   - Steps to reproduce
