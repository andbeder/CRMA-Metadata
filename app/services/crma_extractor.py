"""
CRMA Metadata Extractor Service
Implements all parsing logic from requirements document
"""
import re
import json
import html
import requests
from typing import List, Dict, Set, Tuple, Any


class CRMAExtractor:
    """Extract CRMA metadata from Salesforce"""

    def __init__(self, access_token, instance_url, api_version='v60.0'):
        self.access_token = access_token
        self.instance_url = instance_url
        self.api_version = api_version
        self.base_url = f"{instance_url}/services/data/{api_version}/wave"
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

    def _make_request(self, endpoint, method='GET', params=None, data=None):
        """Make HTTP request to Salesforce API with retry logic"""
        # Build URL - ensure proper path joining
        if endpoint.startswith('http'):
            url = endpoint  # Full URL provided
        else:
            url = f"{self.base_url}/{endpoint}"
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                if method == 'GET':
                    response = requests.get(url, headers=self.headers, params=params, timeout=30)
                elif method == 'POST':
                    response = requests.post(url, headers=self.headers, json=data, timeout=30)
                elif method == 'PUT':
                    response = requests.put(url, headers=self.headers, json=data, timeout=30)

                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                retry_count += 1
                if retry_count >= max_retries:
                    raise Exception(f"Request failed after {max_retries} retries: {str(e)}")
                import time
                time.sleep(2 ** retry_count)  # Exponential backoff

    def _paginate(self, endpoint, params=None):
        """Paginate through API results"""
        results = []
        next_url = endpoint

        while next_url:
            data = self._make_request(next_url, params=params)
            if 'dashboards' in data:
                results.extend(data.get('dashboards', []))
            elif 'datasets' in data:
                results.extend(data.get('datasets', []))
            else:
                results.extend(data.get('records', []))

            next_url = data.get('nextPageUrl')
            if next_url:
                # Use relative path
                next_url = next_url.replace(f'/services/data/{self.api_version}/wave/', '')
            params = None  # Clear params for subsequent requests

        return results

    def get_dashboards(self):
        """
        Retrieve all dashboards
        Returns: List of dashboard metadata
        """
        print("Loading dashboards...")
        dashboards = self._paginate('dashboards')

        result = []
        for db in dashboards:
            result.append({
                'DashboardName': db.get('name'),
                'Application': db.get('folderName', db.get('folder', {}).get('name')),
                'MasterLabel': db.get('label'),
                'Id': db.get('id'),
                'CreatedBy': db.get('createdBy', {}).get('name') if isinstance(db.get('createdBy'), dict) else db.get('createdBy'),
                'LastModifiedBy': db.get('lastModifiedBy', {}).get('name') if isinstance(db.get('lastModifiedBy'), dict) else db.get('lastModifiedBy'),
                'url': db.get('url')
            })

        return result

    def get_datasets(self):
        """
        Retrieve all datasets
        Returns: List of dataset metadata
        """
        print("Loading datasets...")
        datasets = self._paginate('datasets')

        result = []
        for ds in datasets:
            result.append({
                'DatasetName': ds.get('name'),
                'MasterLabel': ds.get('label'),
                'Id': ds.get('id'),
                'Application': ds.get('folderName', ds.get('folder', {}).get('name')),
                'currentVersionUrl': ds.get('currentVersionUrl'),
                'url': ds.get('url')
            })

        return result

    def get_folders(self):
        """
        Retrieve all CRMA folders/applications
        Returns: List of folder metadata
        """
        print("Loading CRMA folders...")
        folders = self._paginate('folders')

        result = []
        for folder in folders:
            result.append({
                'Id': folder.get('id'),
                'Name': folder.get('name'),
                'Label': folder.get('label'),
                'Type': folder.get('type', 'folder')
            })

        # Sort by label for easier selection
        result.sort(key=lambda x: x['Label'])
        return result

    def get_dashboard_fields(self, dashboard_id):
        """
        Extract all fields used in a dashboard
        Implements UC-1 through UC-5 parsing logic
        """
        print(f"Extracting fields from dashboard {dashboard_id}...")

        # Get dashboard JSON
        dashboard_data = self._make_request(f"dashboards/{dashboard_id}")
        state = dashboard_data.get('state', {})

        fields = []  # List of (step_name, dataset_name, field_name) tuples
        dataset_set = set()  # Track datasets used

        # Extract from global filters (UC-5)
        filters = state.get('filters', [])
        for filter_obj in filters:
            dataset_name = filter_obj.get('dataset', {}).get('name')
            if dataset_name:
                dataset_set.add(dataset_name)
                filter_fields = filter_obj.get('fields', [])
                for field in filter_fields:
                    fields.append(('GlobalFilter', dataset_name, field))

        # Extract from data source links
        links_info = state.get('dataSourceLinksInfo', {})
        links = links_info.get('links', [])
        for link in links:
            link_fields = link.get('fields', [])
            for field_obj in link_fields:
                ds_name = field_obj.get('dataSourceName')
                field_name = field_obj.get('fieldName')
                if ds_name and field_name:
                    dataset_set.add(ds_name)
                    fields.append(('DataSourceLink', ds_name, field_name))

        # Extract from steps
        steps = state.get('steps', {})
        for step_key, step_data in steps.items():
            step_name = step_data.get('label', step_key)
            step_fields = self._extract_step_fields(step_data, step_name)
            fields.extend(step_fields)
            # Track datasets
            for _, ds, _ in step_fields:
                if ds:
                    dataset_set.add(ds)

        # Deduplicate
        unique_fields = list(set(fields))

        return {
            'fields': [{'StepName': s, 'DatasetName': d, 'FieldName': f}
                      for s, d, f in unique_fields],
            'datasets': list(dataset_set)
        }

    def _extract_step_fields(self, step_data, step_name, dataset_context=None):
        """
        Recursively extract fields from a step
        Handles UC-1 through UC-4
        """
        fields = []

        # Recursively scan for query definitions
        if isinstance(step_data, dict):
            for key, value in step_data.items():
                # UC-4: SAQL in "saql" or "pigql" keys
                if key in ['saql', 'pigql'] and isinstance(value, str):
                    saql_fields = self._extract_saql_fields(value)
                    fields.extend([(step_name, ds, f) for ds, f in saql_fields])

                # UC-1, UC-2: "query" key
                elif key == 'query':
                    if isinstance(value, dict):
                        # UC-1: Native compact JSON
                        compact_fields = self._extract_compact_json_fields(value, dataset_context)
                        fields.extend([(step_name, ds, f) for ds, f in compact_fields])

                        # Check for embedded pigql (UC-3)
                        if 'pigql' in value and isinstance(value['pigql'], str):
                            saql_fields = self._extract_saql_fields(value['pigql'])
                            fields.extend([(step_name, ds, f) for ds, f in saql_fields])

                    elif isinstance(value, str):
                        # UC-2: Escaped JSON string or UC-4: SAQL string
                        # Try to parse as JSON first
                        try:
                            unescaped = html.unescape(value)
                            parsed = json.loads(unescaped)
                            compact_fields = self._extract_compact_json_fields(parsed, dataset_context)
                            fields.extend([(step_name, ds, f) for ds, f in compact_fields])
                        except (json.JSONDecodeError, ValueError):
                            # Treat as SAQL
                            saql_fields = self._extract_saql_fields(value)
                            fields.extend([(step_name, ds, f) for ds, f in saql_fields])

                # Recurse into nested objects
                elif isinstance(value, dict):
                    # Track dataset context if this is a dataset reference
                    new_context = dataset_context
                    if 'dataset' in value:
                        ds_ref = value['dataset']
                        if isinstance(ds_ref, dict) and 'name' in ds_ref:
                            new_context = ds_ref['name']
                        elif isinstance(ds_ref, str):
                            new_context = ds_ref

                    nested_fields = self._extract_step_fields(value, step_name, new_context)
                    fields.extend(nested_fields)

                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, (dict, list)):
                            nested_fields = self._extract_step_fields(item, step_name, dataset_context)
                            fields.extend(nested_fields)

        elif isinstance(step_data, list):
            for item in step_data:
                if isinstance(item, (dict, list)):
                    nested_fields = self._extract_step_fields(item, step_name, dataset_context)
                    fields.extend(nested_fields)

        return fields

    def _extract_compact_json_fields(self, query_obj, dataset_context=None):
        """
        Extract fields from compact JSON query object (UC-1)
        Returns: List of (dataset, field) tuples
        """
        fields = []

        # Get dataset name
        dataset = dataset_context
        if 'dataset' in query_obj:
            ds_ref = query_obj['dataset']
            if isinstance(ds_ref, dict):
                dataset = ds_ref.get('name', dataset)
            elif isinstance(ds_ref, str):
                dataset = ds_ref

        # Extract from measures, groups, values, filters
        for key in ['measures', 'groups', 'values', 'filters']:
            if key in query_obj:
                items = query_obj[key]
                if isinstance(items, list):
                    for item in items:
                        field_names = self._extract_field_from_item(item)
                        for field in field_names:
                            fields.append((dataset, field))

        return fields

    def _extract_field_from_item(self, item):
        """Extract field names from various item formats"""
        fields = []

        if isinstance(item, str):
            fields.append(item)
        elif isinstance(item, list):
            for sub_item in item:
                if isinstance(sub_item, str):
                    fields.append(sub_item)
                elif isinstance(sub_item, list):
                    # Nested arrays
                    fields.extend(self._extract_field_from_item(sub_item))
        elif isinstance(item, dict):
            # Could be field reference
            if 'field' in item:
                fields.append(item['field'])

        return fields

    def _extract_saql_fields(self, saql_script):
        """
        Extract fields from SAQL script (UC-3, UC-4)
        Returns: List of (dataset, field) tuples
        """
        fields = []

        # Find all load statements
        load_pattern = r'load\s+"([^"]+)"'
        datasets = re.findall(load_pattern, saql_script, re.IGNORECASE)

        # For each dataset, find field references
        # Field references are typically in quotes: 'FieldName'
        field_pattern = r"'([^']+)'"
        field_matches = re.findall(field_pattern, saql_script)

        # Associate fields with datasets (simplified - assign to all datasets)
        for dataset in datasets:
            for field in field_matches:
                # Filter out non-field strings (like operators, values)
                if not field.lower() in ['true', 'false', 'null'] and not field.isdigit():
                    fields.append((dataset, field))

        return fields

    def get_dataset_fields(self, dataset_id):
        """
        Get field definitions from dataset XMD metadata
        Returns: List of field definitions with labels and types
        """
        print(f"Extracting fields from dataset {dataset_id}...")

        # Get dataset details
        dataset = self._make_request(f"datasets/{dataset_id}")
        current_version_url = dataset.get('currentVersionUrl')

        if not current_version_url:
            raise Exception(f"No currentVersionUrl found for dataset {dataset_id}")

        # Extract version ID from URL
        version_id = current_version_url.split('/')[-1]

        # Get XMD metadata
        xmd_url = f"{self.instance_url}/services/data/{self.api_version}/wave/datasets/{dataset_id}/versions/{version_id}/xmds/main"
        response = requests.get(xmd_url, headers=self.headers, timeout=30)
        response.raise_for_status()
        xmd = response.json()

        fields = []

        # Extract date fields
        dates = xmd.get('dates', [])
        for date_obj in dates:
            date_fields = date_obj.get('fields', {})
            full_field = date_fields.get('fullField')
            if full_field:
                fields.append({
                    'FieldName': full_field,
                    'Label': date_obj.get('label', full_field),
                    'Type': 'Date'
                })

        # Extract dimensions
        dimensions = xmd.get('dimensions', [])
        for dim in dimensions:
            field = dim.get('field')
            if field:
                fields.append({
                    'FieldName': field,
                    'Label': dim.get('label', field),
                    'Type': 'Dimension'
                })

        # Extract measures
        measures = xmd.get('measures', [])
        for measure in measures:
            field = measure.get('field')
            if field:
                fields.append({
                    'FieldName': field,
                    'Label': measure.get('label', field),
                    'Type': 'Measure'
                })

        return fields
