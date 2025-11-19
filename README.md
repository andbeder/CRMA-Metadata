# CRMA Metadata Extractor

A Python + Flask web application for extracting CRM Analytics (CRMA) metadata from Salesforce, including dashboards and datasets. Export metadata as CSV files or upload directly back to CRMA.

## Features

- **JWT Authentication**: Secure authentication using Salesforce Connected App with encrypted JWT keys
- **Dashboard Extraction**: Extract all fields used in dashboards (global filters, data-source links, step queries)
- **Dataset Extraction**: Extract field definitions from dataset XMD metadata
- **CSV Export**: Download metadata as CSV files for individual or all dashboards/datasets
- **CRMA Upload**: Directly upload extracted metadata as new CRMA datasets
- **Web Interface**: User-friendly interface at `localhost:4000`
- **Settings Management**: Configure Salesforce credentials via UI (overrides environment variables)

## Architecture

```
crma-metadata/
├── app/
│   ├── auth/                    # JWT authentication module
│   ├── services/                # CRMA extraction and CSV handling
│   ├── routes/                  # Flask API routes
│   ├── static/                  # CSS and JavaScript
│   └── templates/               # HTML templates
├── config.py                    # Configuration management
├── run.py                       # Application entry point
└── requirements.txt             # Python dependencies
```

## Prerequisites

1. **Python 3.8+**
2. **Salesforce CLI** (`sf`): Required for JWT authentication
   ```bash
   npm install -g @salesforce/cli
   ```
3. **Salesforce Connected App**: With JWT Bearer Flow enabled
4. **Encrypted JWT Key**: Your private key encrypted with OpenSSL

## Installation

1. Clone the repository:
   ```bash
   cd C:\Users\andbe\git\crma-metadata
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up **required** environment variables:
   ```bash
   set SFDC_CLIENT_ID=your_connected_app_client_id
   set KEY_PASS=your_jwt_key_decryption_password
   ```

   **Security Note:** Client ID and KEY_PASS can ONLY be set via environment variables for security.

4. (Optional) Set additional environment variables or configure via Settings UI:
   ```bash
   set SFDC_USERNAME=your_salesforce_username
   set SFDC_LOGIN_URL=https://login.salesforce.com
   set CRMA_APPLICATION_NAME=CRMA_Metadata
   ```

4. Ensure your encrypted JWT key is at `../jwt.key.enc` (or update path in `config.py`)

## Usage

### Start the Application

```bash
python run.py
```

The application will be available at: **http://localhost:4000**

### Configure Settings

1. Navigate to the **Settings** tab
2. Enter your configuration:
   - **Username**: Your Salesforce username
   - **Login URL**: Use `https://test.salesforce.com` for sandboxes
   - **Instance URL**: Optional, auto-detected after login
   - **Application Name**: Select from dropdown of existing CRMA folders/applications (click "Refresh" to reload)
3. Click **Save Settings**
4. Click **Test Connection** to verify

**Notes:**
- Client ID must be set via `SFDC_CLIENT_ID` environment variable for security
- The application dropdown loads all available CRMA folders from your org
- If you select an application that doesn't exist in the list, it will be saved as a custom value

### Extract Dataset Metadata

1. Go to the **Datasets** tab
2. Click **Refresh Datasets** to load all datasets
3. For each dataset, you can:
   - **Export CSV**: Download field definitions as CSV
   - **Upload to CRMA**: Upload metadata directly to CRMA as a new dataset

### Extract Dashboard Metadata

1. Go to the **Dashboards** tab
2. Click **Refresh Dashboards** to load all dashboards
3. For each dashboard, you can:
   - **Export CSV**: Download all fields used in the dashboard
   - **Upload to CRMA**: Upload metadata directly to CRMA

### Upload to CRMA

When you click "Upload to CRMA" for any metadata type, the dataset will be created with a **fixed naming convention**:

| Tab | Dataset Name | Fields |
|-----|--------------|--------|
| Dashboards | `Dashboards` | DashboardName, Application, MasterLabel, Id, CreatedBy, LastModifiedBy |
| Datasets | `Datasets` | DatasetName, MasterLabel, Id, Application |
| Applications | `Applications` | AppLabel, AppName |
| Recipes | `Recipes` | RecipeName, Schedule, MasterLabel, Id |
| Dashboard Fields | `DashboardFields` | DashboardName, StepName, DatasetName, FieldName |
| Dataset Fields | `Fields` | DatasetName, FieldName, Label, Type |
| Dashboard-Dataset Junction | `DashboardDatasetJunction` | DashboardName, DatasetName |

**Schedule Field:** For Recipes, the Schedule field is `Y` if the recipe has a schedule configured, `N` if it runs on demand only.

All datasets are uploaded to the application/folder specified in Settings → Application Name.

**Operation:** Overwrite (existing datasets with the same name will be replaced)

## API Endpoints

### Authentication & Status

- `GET /api/status` - Check connection status

### Data Retrieval

- `GET /api/datasets` - List all datasets
- `GET /api/dashboards` - List all dashboards
- `GET /api/extract/dataset/<dataset_id>` - Extract fields from dataset
- `GET /api/extract/dashboard/<dashboard_id>` - Extract fields from dashboard

### Export & Upload

- `POST /api/export-csv` - Generate and download CSV
  ```json
  {
    "type": "dataset|dashboard|datasets|dashboards",
    "id": "dataset_or_dashboard_id",
    "name": "item_name"
  }
  ```

- `POST /api/upload-crma` - Upload to CRMA
  ```json
  {
    "type": "dataset|dashboard",
    "id": "item_id",
    "name": "item_name",
    "datasetName": "target_dataset_name"
  }
  ```

### Settings

- `GET /api/settings` - Get current settings
- `POST /api/settings` - Update settings

## Technical Details

### JWT Authentication

The application uses the same JWT authentication flow as `sfdcJwtAuth.js`:

1. Decrypts the encrypted JWT key using AES-256-CBC with PBKDF2
2. Creates a temporary key file with restricted permissions
3. Authenticates using Salesforce CLI (`sf org login jwt`)
4. Caches the access token in memory (2-hour expiry)
5. Securely deletes the temporary key file

### CRMA Parsing Logic

Implements all parsing requirements from the specification:

- **UC-1**: Native compact JSON queries
- **UC-2**: Escaped JSON strings (unescapes HTML entities)
- **UC-3**: Embedded SAQL in `pigql` property
- **UC-4**: Standalone SAQL scripts
- **UC-5**: Nested arrays and filters

### Field Extraction

- **Global Filters**: Extracts from `state.filters[]`
- **Data-Source Links**: Extracts from `state.dataSourceLinksInfo.links[]`
- **Step Queries**: Recursively scans `state.steps.*` for all query definitions
- **SAQL Parsing**: Uses regex to extract `load` statements and field references

### CSV Output Formats

1. **Dashboards**: `DashboardName, Application, MasterLabel, Id, CreatedBy, LastModifiedBy`
2. **Datasets**: `DatasetName, MasterLabel, Id, Application`
3. **Dashboard Fields**: `DashboardName, StepName, DatasetName, FieldName`
4. **Dataset Fields**: `DatasetName, FieldName, Label, Type`

### CRMA Upload Process

1. Creates `InsightsExternalData` record via `/wave/dataConnectors`
2. Uploads CSV data in 1MB Base64-encoded chunks
3. Triggers processing with `Action: Process`
4. Returns job ID for tracking

## Configuration Files

### `config.py`

Central configuration with environment variable support and user settings persistence.

### `user_settings.json`

Automatically created to store UI-configured settings (overrides environment variables).

## Error Handling

- **Authentication**: Retries with exponential backoff (up to 3 attempts)
- **API Calls**: Automatic retry on transient failures
- **Parsing Errors**: Logs context and continues processing other items
- **Token Expiry**: Automatic token refresh when cached token expires

## Security

- JWT keys are decrypted in memory and temporarily written with `0o600` permissions
- Temporary key files are overwritten with random data before deletion
- Access tokens cached in memory (never written to disk in this Python version)
- User settings stored in plain JSON (exclude from version control if containing sensitive data)

## Troubleshooting

### "No accessToken found"
- Ensure Salesforce CLI is installed: `sf --version`
- Verify Connected App has JWT Bearer Flow enabled
- Check that username matches the certificate subject

### "Failed to decrypt JWT key"
- Verify `KEY_PASS` environment variable is correct
- Ensure `jwt.key.enc` is encrypted with OpenSSL AES-256-CBC

### "Connection test failed"
- Check network connectivity to Salesforce
- Verify Login URL (use `test.salesforce.com` for sandboxes)
- Review Salesforce Connected App settings

## Development

### Run in Debug Mode

Debug mode is enabled by default. To disable:

```python
# In config.py
DEBUG = False
```

### Extend Extraction Logic

To add custom field extraction:

1. Edit `app/services/crma_extractor.py`
2. Add new parsing methods to `CRMAExtractor` class
3. Call from `_extract_step_fields()` or create new endpoint

## License

See LICENSE file for details.

## Support

For issues and questions, refer to the requirements document or Salesforce Analytics REST API documentation.
