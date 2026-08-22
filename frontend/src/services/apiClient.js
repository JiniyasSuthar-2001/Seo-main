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
        const url = `${API_BASE_URL}${endpoint}`;
        
        const defaultHeaders = {
            'Content-Type': 'application/json',
        };

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
                err.isNetworkError = false; // Server responded!
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
            body: JSON.stringify(data) 
        });
    }

    put(endpoint, data, options = {}) {
        return this.request(endpoint, { 
            ...options, 
            method: 'PUT',
            body: JSON.stringify(data) 
        });
    }

    delete(endpoint, options = {}) {
        return this.request(endpoint, { ...options, method: 'DELETE' });
    }
}

export const apiClient = new ApiClient();
