/**
 * Single authoritative configuration source for frontend API communication.
 * Resolves backend API base URL dynamically while preserving local development fallback.
 */

export function getApiBaseUrl() {
    if (typeof window !== 'undefined' && window.APP_CONFIG && window.APP_CONFIG.API_BASE_URL) {
        return window.APP_CONFIG.API_BASE_URL;
    }
    if (typeof window !== 'undefined' && window.location && window.location.hostname) {
        // If served on backend port 8020 directly
        if (window.location.port === "8020") {
            return window.location.origin;
        }
    }
    return "http://127.0.0.1:8020";
}

export const API_BASE_URL = getApiBaseUrl();
