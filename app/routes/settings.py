"""
Settings routes
"""
from flask import Blueprint, jsonify, request
from config import Config
import os

bp = Blueprint('settings', __name__, url_prefix='/api/settings')

@bp.route('/', methods=['GET'])
def get_settings():
    """Get current settings"""
    return jsonify({
        'username': Config.SFDC_USERNAME,
        'loginUrl': Config.SFDC_LOGIN_URL,
        'instanceUrl': Config.SF_INSTANCE_URL,
        'applicationName': Config.CRMA_APPLICATION_NAME
    })

@bp.route('/', methods=['POST'])
def update_settings():
    """Update settings (supports partial updates)"""
    try:
        data = request.json

        # Load existing settings first to merge
        existing_settings = {}
        if os.path.exists(Config.SETTINGS_FILE):
            try:
                import json
                with open(Config.SETTINGS_FILE, 'r') as f:
                    existing_settings = json.load(f)
            except Exception:
                pass

        # Update only the provided fields
        if data.get('username') is not None:
            existing_settings['username'] = data['username']

        if data.get('loginUrl') is not None:
            existing_settings['login_url'] = data['loginUrl']

        if data.get('instanceUrl') is not None:
            existing_settings['instance_url'] = data['instanceUrl']

        if data.get('applicationName') is not None:
            existing_settings['application_name'] = data['applicationName']

        # Save merged settings to file
        if not Config.save_user_settings(existing_settings):
            return jsonify({'error': 'Failed to save settings'}), 500

        # Reload user settings to update Config class attributes
        Config.load_user_settings()

        # Clear cached auth instance to force re-initialization with new settings
        import app.routes.api as api_module
        api_module._auth = None

        return jsonify({
            'success': True,
            'message': 'Settings updated successfully'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
