"""
Configuration management for CRMA Metadata Extractor
"""
import os
import json

class Config:
    """Application configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Server configuration
    HOST = '127.0.0.1'
    PORT = 4000
    DEBUG = True

    # Salesforce configuration (defaults from environment)
    SFDC_CLIENT_ID = os.environ.get('SFDC_CLIENT_ID', '')  # Security: Only from environment
    SFDC_USERNAME = os.environ.get('SFDC_USERNAME', '')
    SFDC_LOGIN_URL = os.environ.get('SFDC_LOGIN_URL', 'https://login.salesforce.com')
    SF_INSTANCE_URL = os.environ.get('SF_INSTANCE_URL', '')
    KEY_PASS = os.environ.get('KEY_PASS', '')  # Security: Only from environment
    # Update this path to point to your actual JWT key file location
    ENCRYPTED_KEY_FILE = os.environ.get('ENCRYPTED_KEY_FILE',
                                        os.path.join(os.path.dirname(__file__), '..', 'jwt.key.enc'))

    # CRMA Application/Folder for metadata datasets
    CRMA_APPLICATION_NAME = os.environ.get('CRMA_APPLICATION_NAME', 'CRMA_Metadata')

    # API configuration
    SALESFORCE_API_VERSION = 'v60.0'

    # Settings file for user overrides
    SETTINGS_FILE = os.path.join(os.path.dirname(__file__), 'user_settings.json')

    @classmethod
    def load_user_settings(cls):
        """Load user settings from file"""
        if os.path.exists(cls.SETTINGS_FILE):
            try:
                with open(cls.SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)
                    # Override with user settings if provided
                    if settings.get('username'):
                        cls.SFDC_USERNAME = settings['username']
                    if settings.get('login_url'):
                        cls.SFDC_LOGIN_URL = settings['login_url']
                    if settings.get('instance_url'):
                        cls.SF_INSTANCE_URL = settings['instance_url']
                    if settings.get('application_name'):
                        cls.CRMA_APPLICATION_NAME = settings['application_name']
            except Exception as e:
                print(f"Warning: Could not load user settings: {e}")

    @classmethod
    def save_user_settings(cls, settings):
        """Save user settings to file"""
        try:
            with open(cls.SETTINGS_FILE, 'w') as f:
                json.dump(settings, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving user settings: {e}")
            return False
