"""
Settings tab UI module for Clean Data QGIS plugin.
"""
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QLabel,
                                QLineEdit, QPushButton, QSpinBox, QMessageBox)
from qgis.PyQt.QtCore import Qt

class SettingsTab(QWidget):
    """Settings tab widget"""
    
    def __init__(self, dialog):
        super().__init__()
        self.dialog = dialog
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the settings tab UI"""
        layout = QVBoxLayout()
        
        # Google Translate Settings
        google_group = QGroupBox("Google Translate Settings:")
        google_layout = QVBoxLayout()
        
        google_key_label = QLabel("API Key:")
        self.google_key = QLineEdit()
        self.google_key.setEchoMode(QLineEdit.Password)
        
        google_layout.addWidget(google_key_label)
        google_layout.addWidget(self.google_key)
        google_group.setLayout(google_layout)
        layout.addWidget(google_group)
        
        # OpenAI Settings
        openai_group = QGroupBox("OpenAI Settings:")
        openai_layout = QVBoxLayout()
        
        openai_key_label = QLabel("API Key:")
        self.openai_key = QLineEdit()
        self.openai_key.setEchoMode(QLineEdit.Password)
        
        openai_model_label = QLabel("Model:")
        self.openai_model = QLineEdit()
        self.openai_model.setText("gpt-3.5-turbo")
        
        openai_layout.addWidget(openai_key_label)
        openai_layout.addWidget(self.openai_key)
        openai_layout.addWidget(openai_model_label)
        openai_layout.addWidget(self.openai_model)
        openai_group.setLayout(openai_layout)
        layout.addWidget(openai_group)
        
        # DeepSeek Settings
        deepseek_group = QGroupBox("DeepSeek Settings:")
        deepseek_layout = QVBoxLayout()
        
        deepseek_key_label = QLabel("API Key:")
        self.deepseek_key = QLineEdit()
        self.deepseek_key.setEchoMode(QLineEdit.Password)
        
        deepseek_model_label = QLabel("Model:")
        self.deepseek_model = QLineEdit()
        self.deepseek_model.setText("deepseek-chat")
        
        deepseek_layout.addWidget(deepseek_key_label)
        deepseek_layout.addWidget(self.deepseek_key)
        deepseek_layout.addWidget(deepseek_model_label)
        deepseek_layout.addWidget(self.deepseek_model)
        deepseek_group.setLayout(deepseek_layout)
        layout.addWidget(deepseek_group)
        
        # Ollama Settings
        ollama_group = QGroupBox("Ollama Settings:")
        ollama_layout = QVBoxLayout()
        
        url_label = QLabel("URL:")
        self.ollama_url = QLineEdit()
        self.ollama_url.setText("https://llmh.geomda.ai/")
        
        model_label = QLabel("Model:")
        self.ollama_model = QLineEdit()
        self.ollama_model.setText("aya")
        
        batch_label = QLabel("Batch Size:")
        self.batch_size = QSpinBox()
        self.batch_size.setMinimum(1)
        self.batch_size.setMaximum(100)
        self.batch_size.setValue(15)
        
        ollama_layout.addWidget(url_label)
        ollama_layout.addWidget(self.ollama_url)
        ollama_layout.addWidget(model_label)
        ollama_layout.addWidget(self.ollama_model)
        ollama_layout.addWidget(batch_label)
        ollama_layout.addWidget(self.batch_size)
        ollama_group.setLayout(ollama_layout)
        layout.addWidget(ollama_group)
        
        # Save button
        self.save_btn = QPushButton("Save Settings")
        layout.addWidget(self.save_btn)
        
        self.setLayout(layout)
        
        # Connect signals
        self.save_btn.clicked.connect(self.save_settings)
        
        # Load current settings
        self.load_settings()
        
    def load_settings(self):
        """Load settings from QgsSettings"""
        settings = self.dialog.settings_manager
        
        # Google Translate
        self.google_key.setText(settings.get_google_api_key() or '')
        
        # OpenAI
        self.openai_key.setText(settings.get_openai_api_key() or '')
        self.openai_model.setText(settings.get_openai_model() or 'gpt-3.5-turbo')
        
        # DeepSeek
        self.deepseek_key.setText(settings.get_deepseek_api_key() or '')
        self.deepseek_model.setText(settings.get_deepseek_model() or 'deepseek-chat')
        
        # Ollama
        self.ollama_url.setText(settings.get_ollama_url() or 'https://llmh.geomda.ai/')
        self.ollama_model.setText(settings.get_ollama_model() or 'aya')
        self.batch_size.setValue(settings.get_batch_size() or 15)
        
    def save_settings(self):
        """Save settings to QgsSettings"""
        settings = self.dialog.settings_manager
        
        # Google Translate
        settings.set_google_api_key(self.google_key.text())
        
        # OpenAI
        settings.set_openai_api_key(self.openai_key.text())
        settings.set_openai_model(self.openai_model.text())
        
        # DeepSeek
        settings.set_deepseek_api_key(self.deepseek_key.text())
        settings.set_deepseek_model(self.deepseek_model.text())
        
        # Ollama
        settings.set_ollama_url(self.ollama_url.text())
        settings.set_ollama_model(self.ollama_model.text())
        settings.set_batch_size(self.batch_size.value())
        
        QMessageBox.information(self, "Success", "Settings saved successfully!")
