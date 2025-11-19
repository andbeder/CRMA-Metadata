"""
CSV Handler Service
Generate and upload CSV files
"""
import csv
import io
import base64
import requests
from typing import List, Dict


class CSVHandler:
    """Handle CSV generation and CRMA uploads"""

    def __init__(self, access_token=None, instance_url=None, api_version='v60.0'):
        self.access_token = access_token
        self.instance_url = instance_url
        self.api_version = api_version

    def generate_csv(self, data: List[Dict], headers: List[str]) -> str:
        """
        Generate CSV from data
        Args:
            data: List of dictionaries
            headers: List of header names
        Returns: CSV string
        """
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()

    def generate_dashboards_csv(self, dashboards: List[Dict]) -> str:
        """Generate CSV for dashboards"""
        headers = ['DashboardName', 'Application', 'MasterLabel', 'Id', 'CreatedBy', 'LastModifiedBy']
        return self.generate_csv(dashboards, headers)

    def generate_datasets_csv(self, datasets: List[Dict]) -> str:
        """Generate CSV for datasets"""
        headers = ['DatasetName', 'MasterLabel', 'Id', 'Application']
        return self.generate_csv(datasets, headers)

    def generate_dashboard_fields_csv(self, dashboard_name: str, fields: List[Dict]) -> str:
        """Generate CSV for dashboard fields"""
        headers = ['DashboardName', 'StepName', 'DatasetName', 'FieldName']
        # Add dashboard name to each row
        data = [{**field, 'DashboardName': dashboard_name} for field in fields]
        return self.generate_csv(data, headers)

    def generate_dataset_fields_csv(self, dataset_name: str, fields: List[Dict]) -> str:
        """Generate CSV for dataset fields"""
        headers = ['DatasetName', 'FieldName', 'Label', 'Type']
        # Add dataset name to each row
        data = [{**field, 'DatasetName': dataset_name} for field in fields]
        return self.generate_csv(data, headers)

    def generate_dashboard_dataset_junction_csv(self, dashboard_name: str, datasets: List[str]) -> str:
        """Generate CSV for dashboard-dataset junction"""
        headers = ['DashboardName', 'DatasetName']
        data = [{'DashboardName': dashboard_name, 'DatasetName': ds} for ds in datasets]
        return self.generate_csv(data, headers)

    def upload_to_crma(self, dataset_name: str, csv_data: str, operation='Overwrite', application_name=None):
        """
        Upload CSV data to CRMA as a dataset
        Args:
            dataset_name: Name of the dataset to create/update
            csv_data: CSV data as string
            operation: 'Overwrite', 'Append', or 'Upsert'
            application_name: CRMA folder/application name (optional)
        Returns: Upload job details
        """
        if not self.access_token or not self.instance_url:
            raise ValueError("Access token and instance URL required for CRMA upload")

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

        base_url = f"{self.instance_url}/services/data/{self.api_version}/wave"

        # Step 1: Create InsightsExternalData record
        metadata = {
            'Format': 'CSV',
            'EdgemartAlias': dataset_name,
            'Operation': operation,
            'Action': 'None',
            'EdgemartLabel': dataset_name
        }

        # Add application/folder if specified
        if application_name:
            metadata['EdgemartContainer'] = application_name

        response = requests.post(
            f"{base_url}/dataConnectors",
            headers=headers,
            json=metadata,
            timeout=30
        )
        response.raise_for_status()
        data_connector = response.json()
        job_id = data_connector['id']

        # Step 2: Upload CSV data in chunks (max 1MB per chunk)
        csv_bytes = csv_data.encode('utf-8')
        chunk_size = 1024 * 1024  # 1MB
        part_number = 1

        for i in range(0, len(csv_bytes), chunk_size):
            chunk = csv_bytes[i:i + chunk_size]
            encoded_chunk = base64.b64encode(chunk).decode('utf-8')

            upload_data = {
                'InsightsExternalDataId': job_id,
                'PartNumber': part_number,
                'DataFile': encoded_chunk
            }

            response = requests.post(
                f"{base_url}/dataConnectorIngestionJobs/{job_id}/dataConnectorIngestionJobParts",
                headers=headers,
                json=upload_data,
                timeout=60
            )
            response.raise_for_status()
            part_number += 1

        # Step 3: Trigger processing
        process_data = {'Action': 'Process'}
        response = requests.patch(
            f"{base_url}/dataConnectors/{job_id}",
            headers=headers,
            json=process_data,
            timeout=30
        )
        response.raise_for_status()

        return {
            'jobId': job_id,
            'status': 'Processing',
            'datasetName': dataset_name
        }
