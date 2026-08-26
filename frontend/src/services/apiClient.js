import { API_BASE_URL } from '../config/api.js';

class ApiClient {
    constructor() {
        this.status = 'ONLINE'; // 'ONLINE', 'OFFLINE', 'DEGRADED'
        this.lastChecked = null;
        this.listeners = new Set();
    }

    onStatusChange(callback) {
        this.listeners.add(callback);
        return () => this.listeners.delete(callback);
    }

    setStatus(newStatus, detail = {}) {
        if (this.status !== newStatus) {
            this.status = newStatus;
            this.listeners.forEach(fn => {
                try { fn(newStatus, detail); } catch (e) {}
            });
        }
    }

    async checkHealth() {
        const url = `${API_BASE_URL}/api/health`;
        try {
            const response = await fetch(url, { method: 'GET', cache: 'no-store' });
            this.lastChecked = new Date();
            
            if (response.ok) {
                this.setStatus('ONLINE', { status: response.status });
                return { online: true, status: response.status };
            } else {
                this.setStatus('DEGRADED', { status: response.status });
                return { online: true, status: response.status, degraded: true };
            }
        } catch (error) {
            this.lastChecked = new Date();
            this.setStatus('OFFLINE', { error: error.message });
            return { online: false, error: error.message };
        }
    }

    async request(endpoint, options = {}) {
        if (endpoint.includes('/projects/undefined') || endpoint.includes('/projects/null') || endpoint.includes('/projects/{project_id}')) {
            const err = new Error("Invalid API Request: Project ID is unresolvable.");
            err.status = 400;
            err.isNetworkError = false;
            throw err;
        }
        const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;

        const defaultHeaders = {
            'Content-Type': 'application/json',
        };

        // Use canonical application session token key
        const token = localStorage.getItem('seo_auth_token') || localStorage.getItem('jwt_token');

        if (token && token.trim()) {
            defaultHeaders['Authorization'] = `Bearer ${token.trim()}`;
        }

        const config = {
            ...options,
            headers: {
                ...defaultHeaders,
                ...options.headers,
            },
        };

        try {
            const response = await fetch(url, config);
            
            if (response.ok) {
                this.setStatus('ONLINE', { endpoint, status: response.status });
            } else if (response.status >= 500) {
                this.setStatus('DEGRADED', { endpoint, status: response.status });
            }

            if (!response.ok) {
                let errorMsg = `HTTP Error: ${response.status}`;
                let errorData = null;
                try {
                    errorData = await response.json();
                    if (errorData.detail) {
                        errorMsg = typeof errorData.detail === 'string' 
                            ? errorData.detail 
                            : JSON.stringify(errorData.detail);
                    }
                } catch (e) {}
                
                const err = new Error(errorMsg);
                err.status = response.status;
                err.isNetworkError = false;
                err.data = errorData;
                throw err;
            }

            return await response.json();
        } catch (error) {
            if (error.name === 'TypeError' || error.message.includes('fetch') || error.message.includes('Failed to fetch')) {
                error.isNetworkError = true;
                this.setStatus('OFFLINE', { endpoint, error: error.message });
            } else if (error.isNetworkError === undefined) {
                error.isNetworkError = false;
            }
            console.error(`[API Client Error] ${options.method || 'GET'} ${url}`, error);
            throw error;
        }
    }

    // AJAX helper alias
    ajax(endpoint, options = {}) {
        return this.request(endpoint, options);
    }

    get(endpoint, options = {}) {
        return this.request(endpoint, { ...options, method: 'GET' });
    }

    post(endpoint, data, options = {}) {
        return this.request(endpoint, { 
            ...options, 
            method: 'POST',
            body: data ? JSON.stringify(data) : undefined
        });
    }

    put(endpoint, data, options = {}) {
        return this.request(endpoint, { 
            ...options, 
            method: 'PUT',
            body: data ? JSON.stringify(data) : undefined
        });
    }

    patch(endpoint, data, options = {}) {
        return this.request(endpoint, { 
            ...options, 
            method: 'PATCH',
            body: data ? JSON.stringify(data) : undefined
        });
    }

    delete(endpoint, options = {}) {
        return this.request(endpoint, { ...options, method: 'DELETE' });
    }

    async downloadFile(endpoint, fallbackFilename = 'export.file', triggerButton = null) {
        if (!endpoint || endpoint.includes('/projects/undefined') || endpoint.includes('/projects/null') || endpoint.includes('/projects/{project_id}')) {
            const err = new Error("Invalid Download Request: Project ID is unresolvable.");
            err.status = 400;
            alert(err.message);
            throw err;
        }

        const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;
        const token = localStorage.getItem('seo_auth_token') || localStorage.getItem('jwt_token');

        const headers = {};
        if (token && token.trim()) {
            headers['Authorization'] = `Bearer ${token.trim()}`;
        }

        let originalText = '';
        if (triggerButton) {
            triggerButton.disabled = true;
            originalText = triggerButton.innerHTML;
            triggerButton.innerHTML = `<span style="display:inline-block;animation:spin 0.8s linear infinite;">⌛</span> Preparing...`;
        }

        try {
            const response = await fetch(url, { method: 'GET', headers });

            if (response.status === 401) {
                const err = new Error("Your session has expired or is invalid. Please sign in again to download this file.");
                err.status = 401;
                alert(err.message);
                window.location.href = '/login';
                throw err;
            }

            if (response.status === 403) {
                const err = new Error("Access denied. You don't have permission to download this project's data.");
                err.status = 403;
                alert(err.message);
                throw err;
            }

            if (!response.ok) {
                let errorMsg = `Download failed (HTTP ${response.status})`;
                try {
                    const errData = await response.json();
                    if (errData.detail) errorMsg = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
                } catch (e) {}
                const err = new Error(errorMsg);
                err.status = response.status;
                alert(errorMsg);
                throw err;
            }

            // Extract filename from Content-Disposition header if present
            let filename = fallbackFilename;
            const disposition = response.headers.get('Content-Disposition') || response.headers.get('content-disposition');
            if (disposition && disposition.includes('filename=')) {
                const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
                if (matches != null && matches[1]) {
                    filename = matches[1].replace(/['"]/g, '').trim();
                }
            }

            const blob = await response.blob();
            const blobUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = blobUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();

            setTimeout(() => {
                window.URL.revokeObjectURL(blobUrl);
                document.body.removeChild(a);
            }, 500);

            return { success: true, filename };
        } catch (error) {
            console.error(`[Download Error] GET ${url}`, error);
            throw error;
        } finally {
            if (triggerButton) {
                triggerButton.disabled = false;
                triggerButton.innerHTML = originalText;
            }
        }
    }
}

export const apiClient = new ApiClient();
export const ajax = (endpoint, options = {}) => apiClient.request(endpoint, options);
