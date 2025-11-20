// CRMA Metadata Extractor Frontend

class CRMAApp {
    constructor() {
        this.dashboards = [];
        this.datasets = [];
        this.applications = [];
        this.recipes = [];
        this.dashboardFields = [];
        this.datasetFields = [];
        this.junctionData = [];
        this.currentUploadType = null;
        this.currentUploadData = null;

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkStatus();
        this.loadSettings();
        this.loadFolders();
    }

    setupEventListeners() {
        // Tab switching
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        // Navigation from home cards
        document.querySelectorAll('[data-nav]').forEach(button => {
            button.addEventListener('click', (e) => this.navigate(e.target.dataset.nav));
        });

        // Automated extraction
        document.getElementById('start-automated').addEventListener('click', () => this.startAutomatedExtraction());

        // Dashboards
        document.getElementById('load-dashboards').addEventListener('click', () => this.loadDashboards());
        document.getElementById('export-dashboards-csv').addEventListener('click', () => this.exportCSV('dashboards', this.dashboards));
        document.getElementById('upload-dashboards-crma').addEventListener('click', () => this.showUploadModal('dashboards', this.dashboards));

        // Datasets
        document.getElementById('load-datasets').addEventListener('click', () => this.loadDatasets());
        document.getElementById('export-datasets-csv').addEventListener('click', () => this.exportCSV('datasets', this.datasets));
        document.getElementById('upload-datasets-crma').addEventListener('click', () => this.showUploadModal('datasets', this.datasets));

        // Applications
        document.getElementById('load-applications').addEventListener('click', () => this.loadApplications());
        document.getElementById('export-applications-csv').addEventListener('click', () => this.exportCSV('applications', this.applications));
        document.getElementById('upload-applications-crma').addEventListener('click', () => this.showUploadModal('applications', this.applications));

        // Recipes
        document.getElementById('load-recipes').addEventListener('click', () => this.loadRecipes());
        document.getElementById('export-recipes-csv').addEventListener('click', () => this.exportCSV('recipes', this.recipes));
        document.getElementById('upload-recipes-crma').addEventListener('click', () => this.showUploadModal('recipes', this.recipes));

        // Dashboard Fields
        document.getElementById('load-dashboard-fields').addEventListener('click', () => this.loadDashboardFields());
        document.getElementById('export-dashboard-fields-csv').addEventListener('click', () => this.exportCSV('dashboard-fields', this.dashboardFields));
        document.getElementById('upload-dashboard-fields-crma').addEventListener('click', () => this.showUploadModal('dashboard-fields', this.dashboardFields));

        // Dataset Fields
        document.getElementById('load-dataset-fields').addEventListener('click', () => this.loadDatasetFields());
        document.getElementById('export-dataset-fields-csv').addEventListener('click', () => this.exportCSV('dataset-fields', this.datasetFields));
        document.getElementById('upload-dataset-fields-crma').addEventListener('click', () => this.showUploadModal('dataset-fields', this.datasetFields));

        // Junction
        document.getElementById('load-junction').addEventListener('click', () => this.loadJunction());
        document.getElementById('export-junction-csv').addEventListener('click', () => this.exportCSV('junction', this.junctionData));
        document.getElementById('upload-junction-crma').addEventListener('click', () => this.showUploadModal('junction', this.junctionData));

        // Settings
        document.getElementById('connection-settings-form').addEventListener('submit', (e) => this.saveConnectionSettings(e));
        document.getElementById('application-settings-form').addEventListener('submit', (e) => this.saveApplicationSettings(e));
        document.getElementById('test-connection').addEventListener('click', () => this.testConnection());
        document.getElementById('refresh-folders').addEventListener('click', () => this.loadFolders());

        // Modal
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', () => this.closeModal());
        });
        document.getElementById('confirm-upload').addEventListener('click', () => this.confirmUpload());
    }

    navigate(destination) {
        if (destination === 'manual') {
            // Show manual tabs navigation
            document.getElementById('main-tabs').classList.add('hidden');
            document.getElementById('manual-tabs').classList.remove('hidden');

            // Hide all main tabs, show first manual tab
            document.querySelectorAll('.tab-content:not(.manual-content)').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.manual-content').forEach(el => el.classList.remove('active'));
            document.getElementById('dashboards-tab').classList.add('active');
        } else if (destination === 'home') {
            // Show main tabs navigation
            document.getElementById('main-tabs').classList.remove('hidden');
            document.getElementById('manual-tabs').classList.add('hidden');

            // Show home tab
            this.switchTab('home');
        } else {
            // Regular tab navigation
            this.switchTab(destination);
        }
    }

    switchTab(tabName) {
        // Update active tab button in visible nav
        const visibleNav = document.getElementById('main-tabs').classList.contains('hidden') ?
            document.getElementById('manual-tabs') : document.getElementById('main-tabs');

        visibleNav.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
        const targetBtn = visibleNav.querySelector(`[data-tab="${tabName}"]`);
        if (targetBtn) targetBtn.classList.add('active');

        // Handle tab content visibility
        if (tabName === 'manual') {
            // Switching to manual mode
            this.navigate('manual');
        } else {
            // Regular tab switching
            document.querySelectorAll('.tab-content:not(.manual-content)').forEach(content => content.classList.remove('active'));
            const targetTab = document.getElementById(`${tabName}-tab`);
            if (targetTab) targetTab.classList.add('active');

            // If we're in manual mode and switching manual tabs
            if (!document.getElementById('manual-tabs').classList.contains('hidden')) {
                document.querySelectorAll('.manual-content').forEach(content => content.classList.remove('active'));
                const manualTab = document.getElementById(`${tabName}-tab`);
                if (manualTab && manualTab.classList.contains('manual-content')) {
                    manualTab.classList.add('active');
                }
            }

            // Update application name in automated tab
            if (tabName === 'automated') {
                this.updateAutomatedApplicationName();
            }
        }
    }

    async checkStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();

            const indicator = document.getElementById('status-indicator');
            const statusText = document.getElementById('status-text');

            if (data.status === 'connected') {
                indicator.className = 'status-connected';
                statusText.textContent = 'Connected';
            } else {
                indicator.className = 'status-disconnected';
                statusText.textContent = 'Disconnected';
            }
        } catch (error) {
            console.error('Status check failed:', error);
        }
    }

    async loadDashboards() {
        const loading = document.getElementById('dashboards-loading');
        const error = document.getElementById('dashboards-error');
        const count = document.getElementById('dashboards-count');
        const tbody = document.getElementById('dashboards-tbody');
        const exportBtn = document.getElementById('export-dashboards-csv');
        const uploadBtn = document.getElementById('upload-dashboards-crma');

        loading.classList.remove('hidden');
        error.classList.add('hidden');
        count.classList.add('hidden');

        try {
            const response = await fetch('/api/dashboards');
            const data = await response.json();

            if (data.error) throw new Error(data.error);

            this.dashboards = data.dashboards;
            this.renderDashboards();

            count.textContent = `Loaded ${this.dashboards.length} dashboards`;
            count.classList.remove('hidden');
            exportBtn.disabled = false;
            uploadBtn.disabled = false;
            this.checkStatus();

        } catch (err) {
            error.textContent = `Error: ${err.message}`;
            error.classList.remove('hidden');
            tbody.innerHTML = '<tr><td colspan="6" class="no-data">Failed to load dashboards</td></tr>';
        } finally {
            loading.classList.add('hidden');
        }
    }

    renderDashboards() {
        const tbody = document.getElementById('dashboards-tbody');
        if (this.dashboards.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="no-data">No dashboards found</td></tr>';
            return;
        }

        tbody.innerHTML = this.dashboards.map(db => `
            <tr>
                <td>${this.escapeHtml(db.DashboardName)}</td>
                <td>${this.escapeHtml(db.Application || '-')}</td>
                <td>${this.escapeHtml(db.MasterLabel)}</td>
                <td>${this.escapeHtml(db.Id)}</td>
                <td>${this.escapeHtml(db.CreatedBy || '-')}</td>
                <td>${this.escapeHtml(db.LastModifiedBy || '-')}</td>
            </tr>
        `).join('');
    }

    async loadDatasets() {
        const loading = document.getElementById('datasets-loading');
        const error = document.getElementById('datasets-error');
        const count = document.getElementById('datasets-count');
        const tbody = document.getElementById('datasets-tbody');
        const exportBtn = document.getElementById('export-datasets-csv');
        const uploadBtn = document.getElementById('upload-datasets-crma');

        loading.classList.remove('hidden');
        error.classList.add('hidden');
        count.classList.add('hidden');

        try {
            const response = await fetch('/api/datasets');
            const data = await response.json();

            if (data.error) throw new Error(data.error);

            this.datasets = data.datasets;
            this.renderDatasets();

            count.textContent = `Loaded ${this.datasets.length} datasets`;
            count.classList.remove('hidden');
            exportBtn.disabled = false;
            uploadBtn.disabled = false;
            this.checkStatus();

        } catch (err) {
            error.textContent = `Error: ${err.message}`;
            error.classList.remove('hidden');
            tbody.innerHTML = '<tr><td colspan="4" class="no-data">Failed to load datasets</td></tr>';
        } finally {
            loading.classList.add('hidden');
        }
    }

    renderDatasets() {
        const tbody = document.getElementById('datasets-tbody');
        if (this.datasets.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="no-data">No datasets found</td></tr>';
            return;
        }

        tbody.innerHTML = this.datasets.map(ds => `
            <tr>
                <td>${this.escapeHtml(ds.DatasetName)}</td>
                <td>${this.escapeHtml(ds.MasterLabel)}</td>
                <td>${this.escapeHtml(ds.Id)}</td>
                <td>${this.escapeHtml(ds.Application || '-')}</td>
            </tr>
        `).join('');
    }

    async loadApplications() {
        const loading = document.getElementById('applications-loading');
        const error = document.getElementById('applications-error');
        const count = document.getElementById('applications-count');
        const tbody = document.getElementById('applications-tbody');
        const exportBtn = document.getElementById('export-applications-csv');
        const uploadBtn = document.getElementById('upload-applications-crma');

        loading.classList.remove('hidden');
        error.classList.add('hidden');
        count.classList.add('hidden');

        try {
            const response = await fetch('/api/applications');
            const data = await response.json();

            if (data.error) throw new Error(data.error);

            this.applications = data.applications;
            this.renderApplications();

            count.textContent = `Loaded ${this.applications.length} applications`;
            count.classList.remove('hidden');
            exportBtn.disabled = false;
            uploadBtn.disabled = false;
            this.checkStatus();

        } catch (err) {
            error.textContent = `Error: ${err.message}`;
            error.classList.remove('hidden');
            tbody.innerHTML = '<tr><td colspan="2" class="no-data">Failed to load applications</td></tr>';
        } finally {
            loading.classList.add('hidden');
        }
    }

    renderApplications() {
        const tbody = document.getElementById('applications-tbody');
        if (this.applications.length === 0) {
            tbody.innerHTML = '<tr><td colspan="2" class="no-data">No applications found</td></tr>';
            return;
        }

        tbody.innerHTML = this.applications.map(app => `
            <tr>
                <td>${this.escapeHtml(app.AppLabel)}</td>
                <td>${this.escapeHtml(app.AppName)}</td>
            </tr>
        `).join('');
    }

    async loadRecipes() {
        const loading = document.getElementById('recipes-loading');
        const error = document.getElementById('recipes-error');
        const count = document.getElementById('recipes-count');
        const tbody = document.getElementById('recipes-tbody');
        const exportBtn = document.getElementById('export-recipes-csv');
        const uploadBtn = document.getElementById('upload-recipes-crma');

        loading.classList.remove('hidden');
        error.classList.add('hidden');
        count.classList.add('hidden');

        try {
            const response = await fetch('/api/recipes');
            const data = await response.json();

            if (data.error) throw new Error(data.error);

            this.recipes = data.recipes;
            this.renderRecipes();

            count.textContent = `Loaded ${this.recipes.length} recipes`;
            count.classList.remove('hidden');
            exportBtn.disabled = false;
            uploadBtn.disabled = false;
            this.checkStatus();

        } catch (err) {
            error.textContent = `Error: ${err.message}`;
            error.classList.remove('hidden');
            tbody.innerHTML = '<tr><td colspan="4" class="no-data">Failed to load recipes</td></tr>';
        } finally {
            loading.classList.add('hidden');
        }
    }

    renderRecipes() {
        const tbody = document.getElementById('recipes-tbody');
        if (this.recipes.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="no-data">No recipes found</td></tr>';
            return;
        }

        tbody.innerHTML = this.recipes.map(recipe => `
            <tr>
                <td>${this.escapeHtml(recipe.RecipeName)}</td>
                <td>${this.escapeHtml(recipe.Schedule)}</td>
                <td>${this.escapeHtml(recipe.MasterLabel)}</td>
                <td>${this.escapeHtml(recipe.Id)}</td>
            </tr>
        `).join('');
    }

    async loadDashboardFields() {
        const loading = document.getElementById('dashboard-fields-loading');
        const error = document.getElementById('dashboard-fields-error');
        const count = document.getElementById('dashboard-fields-count');
        const tbody = document.getElementById('dashboard-fields-tbody');
        const exportBtn = document.getElementById('export-dashboard-fields-csv');
        const uploadBtn = document.getElementById('upload-dashboard-fields-crma');

        loading.classList.remove('hidden');
        error.classList.add('hidden');
        count.classList.add('hidden');

        try {
            const response = await fetch('/api/extract/all-dashboard-fields');
            const data = await response.json();

            if (data.error) throw new Error(data.error);

            this.dashboardFields = data.fields;
            this.renderDashboardFields();

            count.textContent = `Loaded ${this.dashboardFields.length} field references`;
            count.classList.remove('hidden');
            exportBtn.disabled = false;
            uploadBtn.disabled = false;

        } catch (err) {
            error.textContent = `Error: ${err.message}`;
            error.classList.remove('hidden');
            tbody.innerHTML = '<tr><td colspan="4" class="no-data">Failed to load dashboard fields</td></tr>';
        } finally {
            loading.classList.add('hidden');
        }
    }

    renderDashboardFields() {
        const tbody = document.getElementById('dashboard-fields-tbody');
        if (this.dashboardFields.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="no-data">No dashboard fields found</td></tr>';
            return;
        }

        tbody.innerHTML = this.dashboardFields.map(field => `
            <tr>
                <td>${this.escapeHtml(field.DashboardName)}</td>
                <td>${this.escapeHtml(field.StepName)}</td>
                <td>${this.escapeHtml(field.DatasetName)}</td>
                <td>${this.escapeHtml(field.FieldName)}</td>
            </tr>
        `).join('');
    }

    async loadDatasetFields() {
        const loading = document.getElementById('dataset-fields-loading');
        const error = document.getElementById('dataset-fields-error');
        const count = document.getElementById('dataset-fields-count');
        const tbody = document.getElementById('dataset-fields-tbody');
        const exportBtn = document.getElementById('export-dataset-fields-csv');
        const uploadBtn = document.getElementById('upload-dataset-fields-crma');

        loading.classList.remove('hidden');
        error.classList.add('hidden');
        count.classList.add('hidden');

        try {
            const response = await fetch('/api/extract/all-dataset-fields');
            const data = await response.json();

            if (data.error) throw new Error(data.error);

            this.datasetFields = data.fields;
            this.renderDatasetFields();

            count.textContent = `Loaded ${this.datasetFields.length} fields`;
            count.classList.remove('hidden');
            exportBtn.disabled = false;
            uploadBtn.disabled = false;

        } catch (err) {
            error.textContent = `Error: ${err.message}`;
            error.classList.remove('hidden');
            tbody.innerHTML = '<tr><td colspan="4" class="no-data">Failed to load dataset fields</td></tr>';
        } finally {
            loading.classList.add('hidden');
        }
    }

    renderDatasetFields() {
        const tbody = document.getElementById('dataset-fields-tbody');
        if (this.datasetFields.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="no-data">No dataset fields found</td></tr>';
            return;
        }

        tbody.innerHTML = this.datasetFields.map(field => `
            <tr>
                <td>${this.escapeHtml(field.DatasetName)}</td>
                <td>${this.escapeHtml(field.FieldName)}</td>
                <td>${this.escapeHtml(field.Label)}</td>
                <td>${this.escapeHtml(field.Type)}</td>
            </tr>
        `).join('');
    }

    async loadJunction() {
        const loading = document.getElementById('junction-loading');
        const error = document.getElementById('junction-error');
        const count = document.getElementById('junction-count');
        const tbody = document.getElementById('junction-tbody');
        const exportBtn = document.getElementById('export-junction-csv');
        const uploadBtn = document.getElementById('upload-junction-crma');

        loading.classList.remove('hidden');
        error.classList.add('hidden');
        count.classList.add('hidden');

        try {
            const response = await fetch('/api/extract/dashboard-dataset-junction');
            const data = await response.json();

            if (data.error) throw new Error(data.error);

            this.junctionData = data.relationships;
            this.renderJunction();

            count.textContent = `Loaded ${this.junctionData.length} relationships`;
            count.classList.remove('hidden');
            exportBtn.disabled = false;
            uploadBtn.disabled = false;

        } catch (err) {
            error.textContent = `Error: ${err.message}`;
            error.classList.remove('hidden');
            tbody.innerHTML = '<tr><td colspan="2" class="no-data">Failed to load relationships</td></tr>';
        } finally {
            loading.classList.add('hidden');
        }
    }

    renderJunction() {
        const tbody = document.getElementById('junction-tbody');
        if (this.junctionData.length === 0) {
            tbody.innerHTML = '<tr><td colspan="2" class="no-data">No relationships found</td></tr>';
            return;
        }

        tbody.innerHTML = this.junctionData.map(rel => `
            <tr>
                <td>${this.escapeHtml(rel.DashboardName)}</td>
                <td>${this.escapeHtml(rel.DatasetName)}</td>
            </tr>
        `).join('');
    }

    async exportCSV(type, data) {
        try {
            const response = await fetch('/api/export-csv', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type, data })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Export failed');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = response.headers.get('content-disposition')?.split('filename=')[1] || `${type}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

        } catch (err) {
            alert(`Export failed: ${err.message}`);
        }
    }

    showUploadModal(type, data) {
        this.currentUploadType = type;
        this.currentUploadData = data;

        const typeConfig = {
            'dashboards': {
                name: 'Dashboards',
                datasetName: 'Dashboards'
            },
            'datasets': {
                name: 'Datasets',
                datasetName: 'Datasets'
            },
            'applications': {
                name: 'Applications',
                datasetName: 'Applications'
            },
            'recipes': {
                name: 'Recipes',
                datasetName: 'Recipes'
            },
            'dashboard-fields': {
                name: 'Dashboard Fields',
                datasetName: 'DashboardFields'
            },
            'dataset-fields': {
                name: 'Dataset Fields',
                datasetName: 'Fields'
            },
            'junction': {
                name: 'Dashboard-Dataset Junction',
                datasetName: 'DashboardDatasetJunction'
            }
        };

        const config = typeConfig[type];
        const appName = document.getElementById('applicationName').value || 'Not selected';

        document.getElementById('upload-description').textContent =
            `Upload ${config.name} metadata to CRMA`;
        document.getElementById('upload-dataset-name').textContent = config.datasetName;
        document.getElementById('upload-application-name').textContent = appName;
        document.getElementById('upload-modal').classList.remove('hidden');
    }

    closeModal() {
        document.getElementById('upload-modal').classList.add('hidden');
        this.currentUploadType = null;
        this.currentUploadData = null;
    }

    async confirmUpload() {
        const typeConfig = {
            'dashboards': 'Dashboards',
            'datasets': 'Datasets',
            'applications': 'Applications',
            'recipes': 'Recipes',
            'dashboard-fields': 'DashboardFields',
            'dataset-fields': 'Fields',
            'junction': 'DashboardDatasetJunction'
        };

        const datasetName = typeConfig[this.currentUploadType];
        const appName = document.getElementById('applicationName').value;

        if (!appName) {
            alert('Please select an Application Name in Settings first');
            return;
        }

        const confirmBtn = document.getElementById('confirm-upload');
        confirmBtn.disabled = true;
        confirmBtn.textContent = 'Uploading...';

        try {
            const response = await fetch('/api/upload-crma', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type: this.currentUploadType,
                    data: this.currentUploadData,
                    datasetName: datasetName
                })
            });

            const result = await response.json();

            if (result.error) throw new Error(result.error);

            alert(`Upload initiated successfully!\nJob ID: ${result.jobId}\nDataset: ${result.datasetName}\nApplication: ${appName}\nStatus: ${result.status}`);
            this.closeModal();

        } catch (err) {
            alert(`Upload failed: ${err.message}`);
        } finally {
            confirmBtn.disabled = false;
            confirmBtn.textContent = 'Upload';
        }
    }

    async loadFolders() {
        const select = document.getElementById('applicationName');
        const refreshBtn = document.getElementById('refresh-folders');
        const currentValue = select.value;

        refreshBtn.disabled = true;
        refreshBtn.textContent = 'Loading...';

        try {
            const response = await fetch('/api/folders');
            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            // Clear and populate dropdown
            select.innerHTML = '<option value="">-- Select Application --</option>';

            data.folders.forEach(folder => {
                const option = document.createElement('option');
                option.value = folder.Name;
                option.textContent = folder.Label;
                select.appendChild(option);
            });

            // Restore previous selection if it exists
            if (currentValue && Array.from(select.options).some(opt => opt.value === currentValue)) {
                select.value = currentValue;
            }

        } catch (err) {
            console.error('Failed to load folders:', err);
            select.innerHTML = '<option value="">Failed to load applications</option>';
        } finally {
            refreshBtn.disabled = false;
            refreshBtn.textContent = 'Refresh';
        }
    }

    async loadSettings() {
        try {
            const response = await fetch('/api/settings');
            const settings = await response.json();

            document.getElementById('username').value = settings.username || '';
            document.getElementById('loginUrl').value = settings.loginUrl || 'https://login.salesforce.com';
            document.getElementById('instanceUrl').value = settings.instanceUrl || '';

            // Set application name after folders are loaded
            const appName = settings.applicationName || 'CRMA_Metadata';
            const select = document.getElementById('applicationName');

            // Wait a bit for folders to load, then set value
            setTimeout(() => {
                if (Array.from(select.options).some(opt => opt.value === appName)) {
                    select.value = appName;
                } else {
                    // If not found in list, add it as a custom option
                    const option = document.createElement('option');
                    option.value = appName;
                    option.textContent = `${appName} (custom)`;
                    select.appendChild(option);
                    select.value = appName;
                }
            }, 1000);

        } catch (err) {
            console.error('Failed to load settings:', err);
        }
    }

    async saveConnectionSettings(e) {
        e.preventDefault();

        const settings = {
            username: document.getElementById('username').value,
            loginUrl: document.getElementById('loginUrl').value,
            instanceUrl: document.getElementById('instanceUrl').value
        };

        try {
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(settings)
            });

            const result = await response.json();

            const messageDiv = document.getElementById('connection-message');
            if (result.error) {
                messageDiv.className = 'error';
                messageDiv.textContent = `Error: ${result.error}`;
            } else {
                messageDiv.className = 'success';
                messageDiv.textContent = 'Connection settings saved successfully! You can now test the connection and refresh folders.';
                this.checkStatus();
            }
            messageDiv.classList.remove('hidden');

            setTimeout(() => messageDiv.classList.add('hidden'), 5000);

        } catch (err) {
            alert(`Failed to save connection settings: ${err.message}`);
        }
    }

    async saveApplicationSettings(e) {
        e.preventDefault();

        const applicationName = document.getElementById('applicationName').value;

        if (!applicationName) {
            alert('Please select an application from the dropdown');
            return;
        }

        const settings = {
            applicationName: applicationName
        };

        try {
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(settings)
            });

            const result = await response.json();

            const messageDiv = document.getElementById('application-message');
            if (result.error) {
                messageDiv.className = 'error';
                messageDiv.textContent = `Error: ${result.error}`;
            } else {
                messageDiv.className = 'success';
                messageDiv.textContent = 'Application saved successfully!';
            }
            messageDiv.classList.remove('hidden');

            setTimeout(() => messageDiv.classList.add('hidden'), 5000);

        } catch (err) {
            alert(`Failed to save application: ${err.message}`);
        }
    }

    async testConnection() {
        const btn = document.getElementById('test-connection');
        btn.disabled = true;
        btn.textContent = 'Testing...';

        try {
            const response = await fetch('/api/status');
            const data = await response.json();

            const messageDiv = document.getElementById('connection-message');
            if (data.status === 'connected') {
                messageDiv.className = 'success';
                messageDiv.textContent = `Connection successful! Instance: ${data.instanceUrl}`;
            } else {
                messageDiv.className = 'error';
                messageDiv.textContent = `Connection failed: ${data.error || 'Unknown error'}`;
            }
            messageDiv.classList.remove('hidden');

            setTimeout(() => messageDiv.classList.add('hidden'), 5000);
            this.checkStatus();

        } catch (err) {
            alert(`Connection test failed: ${err.message}`);
        } finally {
            btn.disabled = false;
            btn.textContent = 'Test Connection';
        }
    }

    updateAutomatedApplicationName() {
        const appName = document.getElementById('applicationName').value || 'Not configured';
        document.getElementById('auto-application-name').textContent = appName;
    }

    async startAutomatedExtraction() {
        const appName = document.getElementById('applicationName').value;

        if (!appName) {
            alert('Please configure an application in Settings first');
            this.navigate('settings');
            return;
        }

        const startBtn = document.getElementById('start-automated');
        startBtn.disabled = true;
        startBtn.textContent = 'Running...';

        // Show progress section
        document.getElementById('automated-progress').classList.remove('hidden');
        document.getElementById('automated-summary').classList.add('hidden');

        // Reset all progress
        this.resetProgress();

        // Run all extractions sequentially
        const results = [];

        results.push(await this.extractAndUpload('dashboards', 'Dashboards'));
        results.push(await this.extractAndUpload('datasets', 'Datasets'));
        results.push(await this.extractAndUpload('applications', 'Applications'));
        results.push(await this.extractAndUpload('recipes', 'Recipes'));
        results.push(await this.extractAndUpload('dashboard-fields', 'DashboardFields'));
        results.push(await this.extractAndUpload('dataset-fields', 'Fields'));
        results.push(await this.extractAndUpload('junction', 'DashboardDatasetJunction'));

        // Show summary
        this.showSummary(results);

        startBtn.disabled = false;
        startBtn.textContent = 'Extract All & Upload';
    }

    async extractAndUpload(type, datasetName) {
        const typeKey = type === 'junction' ? 'junction' :
                       type === 'dashboard-fields' ? 'dashboard-fields' :
                       type === 'dataset-fields' ? 'dataset-fields' : type;

        try {
            // Update status to extracting
            this.updateProgress(typeKey, 'extracting', 33);

            // Extract data
            let data;
            let endpoint;

            if (type === 'dashboard-fields') {
                endpoint = '/api/extract/all-dashboard-fields';
            } else if (type === 'dataset-fields') {
                endpoint = '/api/extract/all-dataset-fields';
            } else if (type === 'junction') {
                endpoint = '/api/extract/dashboard-dataset-junction';
            } else {
                endpoint = `/api/${type}`;
            }

            const extractResponse = await fetch(endpoint);
            const extractData = await extractResponse.json();

            if (extractData.error) throw new Error(extractData.error);

            // Get the actual data array
            if (type === 'dashboard-fields') {
                data = extractData.fields;
            } else if (type === 'dataset-fields') {
                data = extractData.fields;
            } else if (type === 'junction') {
                data = extractData.relationships;
            } else {
                data = extractData[type];
            }

            this.updateProgress(typeKey, 'uploading', 66);

            // Upload to CRMA
            const uploadResponse = await fetch('/api/upload-crma', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type: type,
                    data: data,
                    datasetName: datasetName
                })
            });

            const uploadResult = await uploadResponse.json();

            if (uploadResult.error) throw new Error(uploadResult.error);

            this.updateProgress(typeKey, 'completed', 100);

            return {
                type: datasetName,
                success: true,
                count: data.length,
                jobId: uploadResult.jobId
            };

        } catch (error) {
            this.updateProgress(typeKey, 'error', 100);
            return {
                type: datasetName,
                success: false,
                error: error.message
            };
        }
    }

    resetProgress() {
        const types = ['dashboards', 'datasets', 'applications', 'recipes',
                      'dashboard-fields', 'dataset-fields', 'junction'];

        types.forEach(type => {
            const status = document.getElementById(`status-${type}`);
            const progress = document.getElementById(`progress-${type}`);

            status.textContent = 'Pending';
            status.className = 'progress-status pending';
            progress.style.width = '0%';
            progress.className = 'progress-fill';
        });
    }

    updateProgress(type, status, percentage) {
        const statusEl = document.getElementById(`status-${type}`);
        const progressEl = document.getElementById(`progress-${type}`);

        const statusText = {
            'pending': 'Pending',
            'extracting': 'Extracting...',
            'uploading': 'Uploading...',
            'completed': 'Completed',
            'error': 'Error'
        };

        statusEl.textContent = statusText[status];
        statusEl.className = `progress-status ${status}`;
        progressEl.style.width = `${percentage}%`;

        if (status === 'completed') {
            progressEl.classList.add('completed');
        } else if (status === 'error') {
            progressEl.classList.add('error');
        }
    }

    showSummary(results) {
        const summaryContent = document.getElementById('summary-content');
        const successCount = results.filter(r => r.success).length;
        const totalCount = results.length;

        let html = `<p><strong>${successCount} of ${totalCount} datasets uploaded successfully</strong></p>`;

        results.forEach(result => {
            const className = result.success ? 'summary-item' : 'summary-item error';
            const icon = result.success ? '✓' : '✗';
            const message = result.success ?
                `${result.count} records uploaded (Job ID: ${result.jobId})` :
                `Failed: ${result.error}`;

            html += `<div class="${className}">
                <strong>${icon} ${result.type}</strong>: ${message}
            </div>`;
        });

        summaryContent.innerHTML = html;
        document.getElementById('automated-summary').classList.remove('hidden');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize app
const app = new CRMAApp();
