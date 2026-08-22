/**
 * Single authoritative configuration source for frontend API communication.
 * Resolves backend API base URL dynamically while preserving local development fallback.
 */

function resolveApiBaseUrl() {
    if (typeof window !== 'undefined' && window.APP_CONFIG && window.APP_CONFIG.API_BASE_URL) {
        return window.APP_CONFIG.API_BASE_URL;
    }
    if (typeof window !== 'undefined' && window.location && window.location.hostname) {
        if (window.location.port === "8020") {
            return window.location.origin;
        }
    }
    return "http://127.0.0.1:8020";
}

export const API_BASE_URL = resolveApiBaseUrl();

export function getApiBaseUrl() {
    return API_BASE_URL;
}
