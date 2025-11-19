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
    """Update settings"""
    try:
        data = request.json

        settings = {}
        if data.get('username'):
            settings['username'] = data['username']
            Config.SFDC_USERNAME = data['username']

        if data.get('loginUrl'):
            settings['login_url'] = data['loginUrl']
            Config.SFDC_LOGIN_URL = data['loginUrl']

        if data.get('instanceUrl'):
            settings['instance_url'] = data['instanceUrl']
            Config.SF_INSTANCE_URL = data['instanceUrl']

        if data.get('applicationName'):
            settings['application_name'] = data['applicationName']
            Config.CRMA_APPLICATION_NAME = data['applicationName']

        # Save to file
        Config.save_user_settings(settings)

        # Clear cached auth to force re-authentication with new settings
        from app.routes.api import _auth
        if _auth:
            _auth.token_cache.clear()

        return jsonify({
            'success': True,
            'message': 'Settings updated successfully'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
