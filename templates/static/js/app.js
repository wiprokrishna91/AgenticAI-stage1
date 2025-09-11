// Repository Manager JavaScript
class RepositoryManager {
    constructor() {
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadRepositories();
    }

    bindEvents() {
        const cloneForm = document.getElementById('cloneForm');
        if (cloneForm) {
            cloneForm.addEventListener('submit', (e) => this.handleCloneRepo(e));
        }

        const scanBtn = document.getElementById('scanBtn');
        if (scanBtn) {
            scanBtn.addEventListener('click', () => this.handleScanRepos());
        }

        const analyzeBtn = document.getElementById('analyzeBtn');
        if (analyzeBtn) {
            analyzeBtn.addEventListener('click', () => this.handleAnalyzeRepos());
        }
    }

    async handleCloneRepo(event) {
        event.preventDefault();
        
        const repoUrl = document.getElementById('repoUrl').value;
        const repoName = document.getElementById('repoName').value;
        
        if (!repoUrl || !repoName) {
            this.showStatus('Please fill in all fields', 'error');
            return;
        }

        this.showStatus('Cloning repository...', 'loading');
        
        try {
            const response = await fetch('/clone-repo', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    repo_url: repoUrl,
                    repo_name: repoName
                })
            });

            const result = await response.json();
            
            if (response.ok) {
                this.showStatus('Repository cloned successfully!', 'success');
                this.loadRepositories();
                document.getElementById('cloneForm').reset();
            } else {
                this.showStatus(result.error || 'Failed to clone repository', 'error');
            }
        } catch (error) {
            this.showStatus('Error cloning repository: ' + error.message, 'error');
        }
    }

    async handleScanRepos() {
        this.showStatus('Scanning repositories...', 'loading');
        
        try {
            const response = await fetch('/scan-repos', {
                method: 'POST'
            });

            const result = await response.json();
            
            if (response.ok) {
                this.showStatus('Repositories scanned successfully!', 'success');
                this.displayScanResults(result.results);
            } else {
                this.showStatus(result.error || 'Failed to scan repositories', 'error');
            }
        } catch (error) {
            this.showStatus('Error scanning repositories: ' + error.message, 'error');
        }
    }

    async handleAnalyzeRepos() {
        this.showStatus('Analyzing with Bedrock...', 'loading');
        
        try {
            const response = await fetch('/analyze-repos', {
                method: 'POST'
            });

            const result = await response.json();
            
            if (response.ok) {
                this.showStatus('Analysis completed successfully!', 'success');
                this.displayAnalysisResults(result.analysis);
            } else {
                this.showStatus(result.error || 'Failed to analyze repositories', 'error');
            }
        } catch (error) {
            this.showStatus('Error analyzing repositories: ' + error.message, 'error');
        }
    }

    async loadRepositories() {
        try {
            const response = await fetch('/repos');
            const repos = await response.json();
            this.displayRepositories(repos);
        } catch (error) {
            console.error('Error loading repositories:', error);
        }
    }

    displayRepositories(repos) {
        const repoList = document.getElementById('repoList');
        if (!repoList) return;

        if (repos.length === 0) {
            repoList.innerHTML = '<p>No repositories found. Clone a repository to get started.</p>';
            return;
        }

        repoList.innerHTML = repos.map(repo => `
            <div class="repo-item">
                <div class="repo-name">${repo.repo_name}</div>
                <div class="repo-url">${repo.repo_url}</div>
                <span class="repo-status ${repo.status}">${repo.status}</span>
            </div>
        `).join('');
    }

    displayScanResults(results) {
        const resultsDiv = document.getElementById('scanResults');
        if (!resultsDiv) return;

        resultsDiv.innerHTML = `
            <h3>Scan Results</h3>
            <pre>${JSON.stringify(results, null, 2)}</pre>
        `;
        resultsDiv.classList.remove('hidden');
    }

    displayAnalysisResults(analysis) {
        const resultsDiv = document.getElementById('analysisResults');
        if (!resultsDiv) return;

        resultsDiv.innerHTML = `
            <h3>Bedrock Analysis</h3>
            <div class="analysis-content">${analysis}</div>
        `;
        resultsDiv.classList.remove('hidden');
    }

    showStatus(message, type) {
        const statusDiv = document.getElementById('status');
        if (!statusDiv) return;

        statusDiv.textContent = message;
        statusDiv.className = `status ${type}`;
        statusDiv.classList.remove('hidden');

        if (type !== 'loading') {
            setTimeout(() => {
                statusDiv.classList.add('hidden');
            }, 5000);
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new RepositoryManager();
});