import { API_BASE_URL } from '../config/api.js';

class ApiClient {
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
            
            if (!response.ok) {
                // Try to parse standard FastAPI error format
                let errorMsg = `HTTP Error: ${response.status}`;
                try {
                    const errorData = await response.json();
                    if (errorData.detail) {
                        errorMsg = typeof errorData.detail === 'string' 
                            ? errorData.detail 
                            : JSON.stringify(errorData.detail);
                    }
                } catch (e) {
                    // Ignore parsing error, stick to default message
                }
                throw new Error(errorMsg);
            }

            return await response.json();
        } catch (error) {
            console.error(`[API Client Error] ${options.method || 'GET'} ${url}`, error);
            throw error; // Re-throw for components to handle
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
