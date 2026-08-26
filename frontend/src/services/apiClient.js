import { API_BASE_URL } from '../config/api.js';

class ApiClient {
    constructor() {
        this.status = 'ONLINE';
        this.statusListeners = new Set();
    }

    onStatusChange(listener) {
        this.statusListeners.add(listener);
        return () => this.statusListeners.delete(listener);
    }

    async checkHealth() {
        try {
            const data = await this.get('/api/health');
            if (data && (data.status === 'ok' || data.status === 'healthy' || data.online === true)) {
                this.setStatus('ONLINE', data);
                return { status: 'online', ...data };
            } else {
                this.setStatus('DEGRADED', data);
                return { status: 'degraded', ...data };
            }
        } catch (err) {
            this.setStatus('OFFLINE', { error: err.message });
            return { status: 'offline', error: err.message };
        }
    }

    setStatus(newStatus, detail = null) {
        if (this.status !== newStatus) {
            this.status = newStatus;
            this.statusListeners.forEach(listener => listener(newStatus, detail));
        }
    }

    async request(endpoint, options = {}) {
        const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;
        
        const defaultHeaders = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        };

        const token = localStorage.getItem('seo_auth_token') || 
                      localStorage.getItem('auth_token') || 
                      localStorage.getItem('jwt_token') || 
                      sessionStorage.getItem('seo_auth_token') || 
                      sessionStorage.getItem('auth_token');
                      
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

    async downloadFile(endpoint, fallbackFilename = 'export.file', triggerButton = null, options = {}) {
        if (!endpoint || endpoint.includes('/projects/undefined') || endpoint.includes('/projects/null') || endpoint.includes('/projects/{project_id}')) {
            const err = new Error("Invalid Download Request: Project ID is unresolvable.");
            err.status = 400;
            alert(err.message);
            throw err;
        }

        const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;
        const token = localStorage.getItem('seo_auth_token') || 
                      localStorage.getItem('auth_token') || 
                      localStorage.getItem('jwt_token') || 
                      sessionStorage.getItem('seo_auth_token') || 
                      sessionStorage.getItem('auth_token');

        const headers = { ...options.headers };
        if (token && token.trim()) {
            headers['Authorization'] = `Bearer ${token.trim()}`;
        }

        const method = options.method || 'GET';
        const body = options.body;
        if (body && !headers['Content-Type']) {
            headers['Content-Type'] = 'application/json';
        }

        let originalText = '';
        if (triggerButton) {
            triggerButton.disabled = true;
            originalText = triggerButton.innerHTML;
            triggerButton.innerHTML = `<span style="display:inline-block;animation:spin 0.8s linear infinite;">⌛</span> Preparing...`;
        }

        try {
            const response = await fetch(url, { method, headers, body });

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
            console.error(`[Download Error] ${method} ${url}`, error);
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
