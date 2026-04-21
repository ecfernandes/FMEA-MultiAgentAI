"""
Internationalization (i18n) module for Risk AI Analyst
Supports: English (EN), French (FR), Brazilian Portuguese (PT-BR)
"""

import json
import os
from typing import Dict, Any

class Translator:
    """
    Simple translator class for multilingual support
    """
    
    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'fr': 'Français',
        'pt-br': 'Portuguese (Brazil)'
    }
    
    def __init__(self, language: str = 'en'):
        """
        Initialize translator with specified language
        
        Args:
            language: Language code (en, fr, pt-br)
        """
        self.language = language.lower()
        self.translations = self._load_translations()
    
    def _load_translations(self) -> Dict[str, Any]:
        """Load translation file for current language"""
        translations_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'translations')
        
        # Try to load translation file
        file_path = os.path.join(translations_dir, f'{self.language}.json')
        
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Fallback to English
            fallback_path = os.path.join(translations_dir, 'en.json')
            if os.path.exists(fallback_path):
                with open(fallback_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
    
    def t(self, key: str, **kwargs) -> str:
        """
        Translate a key
        
        Args:
            key: Translation key (dot notation supported: 'section.subsection.key')
            **kwargs: Format arguments for string interpolation
        
        Returns:
            Translated string
        """
        # Navigate nested dictionary using dot notation
        keys = key.split('.')
        value = self.translations
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, key)
            else:
                return key
        
        # Apply string formatting if arguments provided
        if kwargs and isinstance(value, str):
            try:
                return value.format(**kwargs)
            except KeyError:
                return value
        
        return value if isinstance(value, str) else key
    
    def change_language(self, language: str):
        """
        Change current language
        
        Args:
            language: New language code
        """
        if language.lower() in self.SUPPORTED_LANGUAGES:
            self.language = language.lower()
            self.translations = self._load_translations()
    
    def get_current_language(self) -> str:
        """Get current language code"""
        return self.language
    
    def get_current_language_name(self) -> str:
        """Get current language display name"""
        return self.SUPPORTED_LANGUAGES.get(self.language, 'English')


# Global translator instance
_translator = None

def init_translator(language: str = 'en') -> Translator:
    """
    Initialize global translator instance
    
    Args:
        language: Language code
    
    Returns:
        Translator instance
    """
    global _translator
    _translator = Translator(language)
    return _translator

def get_translator() -> Translator:
    """
    Get global translator instance
    
    Returns:
        Translator instance (creates one if doesn't exist)
    """
    global _translator
    if _translator is None:
        _translator = Translator()
    return _translator

def t(key: str, **kwargs) -> str:
    """
    Shorthand for translation
    
    Args:
        key: Translation key
        **kwargs: Format arguments
    
    Returns:
        Translated string
    """
    return get_translator().t(key, **kwargs)
