"""
API routes for CRMA operations
"""
from flask import Blueprint, jsonify, request, send_file
from app.auth import SalesforceJWTAuth
from app.services import CRMAExtractor, CSVHandler
from config import Config
import io

bp = Blueprint('api', __name__, url_prefix='/api')

# Global auth instance (will be initialized on first use)
_auth = None

def get_auth():
    """Get or create authentication instance"""
    global _auth
    if _auth is None:
        _auth = SalesforceJWTAuth()
    return _auth

@bp.route('/status', methods=['GET'])
def status():
    """Check connection status"""
    try:
        auth = get_auth()
        token_info = auth.get_token()
        return jsonify({
            'status': 'connected',
            'instanceUrl': token_info['instanceUrl']
        })
    except Exception as e:
        return jsonify({
            'status': 'disconnected',
            'error': str(e)
        }), 500

@bp.route('/dashboards', methods=['GET'])
def get_dashboards():
    """Get all dashboards"""
    try:
        auth = get_auth()
        token_info = auth.get_token()

        extractor = CRMAExtractor(
            token_info['accessToken'],
            token_info['instanceUrl']
        )

        dashboards = extractor.get_dashboards()
        return jsonify({'dashboards': dashboards})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/datasets', methods=['GET'])
def get_datasets():
    """Get all datasets"""
    try:
        auth = get_auth()
        token_info = auth.get_token()

        extractor = CRMAExtractor(
            token_info['accessToken'],
            token_info['instanceUrl']
        )

        datasets = extractor.get_datasets()
        return jsonify({'datasets': datasets})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/folders', methods=['GET'])
def get_folders():
    """Get all CRMA folders/applications"""
    try:
        auth = get_auth()
        token_info = auth.get_token()

        extractor = CRMAExtractor(
            token_info['accessToken'],
            token_info['instanceUrl']
        )

        folders = extractor.get_folders()
        return jsonify({'folders': folders})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/extract/dashboard/<dashboard_id>', methods=['GET'])
def extract_dashboard(dashboard_id):
    """Extract metadata for a specific dashboard"""
    try:
        auth = get_auth()
        token_info = auth.get_token()

        extractor = CRMAExtractor(
            token_info['accessToken'],
            token_info['instanceUrl']
        )

        result = extractor.get_dashboard_fields(dashboard_id)
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/extract/dataset/<dataset_id>', methods=['GET'])
def extract_dataset(dataset_id):
    """Extract metadata for a specific dataset"""
    try:
        auth = get_auth()
        token_info = auth.get_token()

        extractor = CRMAExtractor(
            token_info['accessToken'],
            token_info['instanceUrl']
        )

        fields = extractor.get_dataset_fields(dataset_id)
        return jsonify({'fields': fields})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/extract/all-dashboard-fields', methods=['GET'])
def extract_all_dashboard_fields():
    """Extract fields from ALL dashboards"""
    try:
        auth = get_auth()
        token_info = auth.get_token()

        extractor = CRMAExtractor(
            token_info['accessToken'],
            token_info['instanceUrl']
        )

        # Get all dashboards
        dashboards = extractor.get_dashboards()
        all_fields = []

        # Extract fields from each dashboard
        for dashboard in dashboards:
            try:
                result = extractor.get_dashboard_fields(dashboard['Id'])
                # Add dashboard name to each field
                for field in result['fields']:
                    all_fields.append({
                        'DashboardName': dashboard['DashboardName'],
                        'StepName': field['StepName'],
                        'DatasetName': field['DatasetName'],
                        'FieldName': field['FieldName']
                    })
            except Exception as e:
                print(f"Error extracting fields from dashboard {dashboard['DashboardName']}: {e}")
                continue

        return jsonify({'fields': all_fields, 'count': len(all_fields)})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/extract/all-dataset-fields', methods=['GET'])
def extract_all_dataset_fields():
    """Extract fields from ALL datasets"""
    try:
        auth = get_auth()
        token_info = auth.get_token()

        extractor = CRMAExtractor(
            token_info['accessToken'],
            token_info['instanceUrl']
        )

        # Get all datasets
        datasets = extractor.get_datasets()
        all_fields = []

        # Extract fields from each dataset
        for dataset in datasets:
            try:
                fields = extractor.get_dataset_fields(dataset['Id'])
                # Add dataset name to each field
                for field in fields:
                    all_fields.append({
                        'DatasetName': dataset['DatasetName'],
                        'FieldName': field['FieldName'],
                        'Label': field['Label'],
                        'Type': field['Type']
                    })
            except Exception as e:
                print(f"Error extracting fields from dataset {dataset['DatasetName']}: {e}")
                continue

        return jsonify({'fields': all_fields, 'count': len(all_fields)})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/extract/dashboard-dataset-junction', methods=['GET'])
def extract_dashboard_dataset_junction():
    """Extract dashboard-dataset relationships"""
    try:
        auth = get_auth()
        token_info = auth.get_token()

        extractor = CRMAExtractor(
            token_info['accessToken'],
            token_info['instanceUrl']
        )

        # Get all dashboards
        dashboards = extractor.get_dashboards()
        junction_data = []

        # Extract datasets used by each dashboard
        for dashboard in dashboards:
            try:
                result = extractor.get_dashboard_fields(dashboard['Id'])
                # Get unique dataset names
                datasets = result.get('datasets', [])
                for dataset in datasets:
                    junction_data.append({
                        'DashboardName': dashboard['DashboardName'],
                        'DatasetName': dataset
                    })
            except Exception as e:
                print(f"Error extracting datasets from dashboard {dashboard['DashboardName']}: {e}")
                continue

        return jsonify({'relationships': junction_data, 'count': len(junction_data)})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/export-csv', methods=['POST'])
def export_csv():
    """Generate and download CSV"""
    try:
        data = request.json
        export_type = data.get('type')
        export_data = data.get('data')  # Actual data to export

        csv_handler = CSVHandler()

        if export_type == 'dashboards':
            headers = ['DashboardName', 'Application', 'MasterLabel', 'Id', 'CreatedBy', 'LastModifiedBy']
            csv_data = csv_handler.generate_csv(export_data, headers)
            filename = 'dashboards.csv'

        elif export_type == 'datasets':
            headers = ['DatasetName', 'MasterLabel', 'Id', 'Application']
            csv_data = csv_handler.generate_csv(export_data, headers)
            filename = 'datasets.csv'

        elif export_type == 'dashboard-fields':
            headers = ['DashboardName', 'StepName', 'DatasetName', 'FieldName']
            csv_data = csv_handler.generate_csv(export_data, headers)
            filename = 'dashboard_fields.csv'

        elif export_type == 'dataset-fields':
            headers = ['DatasetName', 'FieldName', 'Label', 'Type']
            csv_data = csv_handler.generate_csv(export_data, headers)
            filename = 'dataset_fields.csv'

        elif export_type == 'junction':
            headers = ['DashboardName', 'DatasetName']
            csv_data = csv_handler.generate_csv(export_data, headers)
            filename = 'dashboard_dataset_junction.csv'

        else:
            return jsonify({'error': 'Invalid export type'}), 400

        # Send as downloadable file
        return send_file(
            io.BytesIO(csv_data.encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/upload-crma', methods=['POST'])
def upload_crma():
    """Upload CSV data to CRMA"""
    try:
        data = request.json
        export_type = data.get('type')
        export_data = data.get('data')  # Actual data to upload
        dataset_name = data.get('datasetName')  # User-specified dataset name

        auth = get_auth()
        token_info = auth.get_token()

        csv_handler = CSVHandler(
            token_info['accessToken'],
            token_info['instanceUrl']
        )

        # Generate CSV based on type
        if export_type == 'dashboards':
            headers = ['DashboardName', 'Application', 'MasterLabel', 'Id', 'CreatedBy', 'LastModifiedBy']
            csv_data = csv_handler.generate_csv(export_data, headers)

        elif export_type == 'datasets':
            headers = ['DatasetName', 'MasterLabel', 'Id', 'Application']
            csv_data = csv_handler.generate_csv(export_data, headers)

        elif export_type == 'dashboard-fields':
            headers = ['DashboardName', 'StepName', 'DatasetName', 'FieldName']
            csv_data = csv_handler.generate_csv(export_data, headers)

        elif export_type == 'dataset-fields':
            headers = ['DatasetName', 'FieldName', 'Label', 'Type']
            csv_data = csv_handler.generate_csv(export_data, headers)

        elif export_type == 'junction':
            headers = ['DashboardName', 'DatasetName']
            csv_data = csv_handler.generate_csv(export_data, headers)

        else:
            return jsonify({'error': 'Invalid export type'}), 400

        # Upload to CRMA with application name
        upload_result = csv_handler.upload_to_crma(
            dataset_name,
            csv_data,
            application_name=Config.CRMA_APPLICATION_NAME
        )

        return jsonify({
            'success': True,
            'jobId': upload_result['jobId'],
            'datasetName': upload_result['datasetName'],
            'status': upload_result['status']
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
