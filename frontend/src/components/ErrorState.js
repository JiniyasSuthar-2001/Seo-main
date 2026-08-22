import { API_BASE_URL } from '../config/api.js';
import { apiClient } from '../services/apiClient.js';

export function renderErrorState(container, errorObj, onRetry = null) {
    if (!container) return;

    let category = "UNKNOWN_ERROR";
    let title = "Feature Error";
    let message = "An unexpected error occurred while fetching data.";

    if (typeof errorObj === 'string') {
        message = errorObj;
    } else if (errorObj && typeof errorObj === 'object') {
        category = errorObj.category || (errorObj.isNetworkError ? "NETWORK_ERROR" : "SERVER_ERROR");
        message = errorObj.message || message;
        if (errorObj.status === 401) category = "UNAUTHORIZED";
        if (errorObj.status === 403) category = "FORBIDDEN";
        if (errorObj.status === 404) category = "NOT_FOUND";
        if (errorObj.status >= 500) category = "SERVER_ERROR";
    }

    switch (category) {
        case "NETWORK_ERROR":
            renderBackendOfflineState(container, "Unable to reach the SEO API server.", onRetry);
            return;
        case "TIMEOUT":
            title = "Request Timed Out";
            message = "The SEO API request timed out. Please try again.";
            break;
        case "UNAUTHORIZED":
            title = "Authentication Required";
            message = "Authentication required. Please sign in or reconnect your user session.";
            break;
        case "FORBIDDEN":
            title = "Access Restricted";
            message = "You do not have permission to access this SEO resource.";
            break;
        case "NOT_FOUND":
            title = "Resource Not Found";
            message = "The requested project, crawl snapshot, or SEO resource was not found.";
            break;
        case "SERVER_ERROR":
            title = "SEO API Server Error";
            message = `The SEO API returned a server error (${errorObj?.status || 500}). ${message}`;
            break;
        case "EMPTY":
            title = "No SEO Data Available";
            message = "No SEO data is available yet for this section.";
            break;
    }

    renderFeatureErrorState(container, title, message, onRetry);
}

export function renderBackendOfflineState(container, message = null, onRetry = null) {
    if (!container) return;
    const finalMessage = message || `Unable to reach the SEO API server at ${API_BASE_URL}.`;

    container.innerHTML = `
        <div class="card" style="padding: 36px 24px; text-align: center; max-width: 520px; margin: 32px auto; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-color, #334155);">
            <div style="width: 48px; height: 48px; border-radius: 50%; background: rgba(239, 68, 68, 0.15); color: #ef4444; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px;">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
            </div>
            <h3 style="font-size: 18px; font-weight: 700; margin-bottom: 8px;">Network Connection Unavailable</h3>
            <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 20px; line-height: 1.5;">
                ${escapeHtml(finalMessage)}<br/>
                <span style="font-size: 12px; color: var(--text-tertiary);">API Endpoint: <code>${API_BASE_URL}</code> | Status: <strong id="offline-status-pill" style="color: #ef4444;">Unreachable</strong></span>
            </p>
            <div id="retry-feedback" style="display: none; margin-bottom: 16px; padding: 10px; border-radius: 6px; font-size: 13px;"></div>
            <div style="display: flex; gap: 12px; justify-content: center;">
                <button id="btn-retry-health" class="btn btn-primary">Retry Connection</button>
            </div>
        </div>
    `;

    const retryBtn = container.querySelector('#btn-retry-health');
    const feedbackDiv = container.querySelector('#retry-feedback');

    if (retryBtn) {
        retryBtn.addEventListener('click', async () => {
            retryBtn.disabled = true;
            retryBtn.innerText = 'Checking Health...';
            if (feedbackDiv) feedbackDiv.style.display = 'none';

            const result = await apiClient.checkHealth();

            if (result.online) {
                if (feedbackDiv) {
                    feedbackDiv.style.display = 'block';
                    feedbackDiv.style.background = 'rgba(16, 185, 129, 0.15)';
                    feedbackDiv.style.color = '#10b981';
                    feedbackDiv.innerText = 'Backend is ONLINE! Reloading data...';
                }
                setTimeout(() => {
                    if (typeof onRetry === 'function') {
                        onRetry();
                    } else {
                        window.location.reload();
                    }
                }, 800);
            } else {
                if (feedbackDiv) {
                    feedbackDiv.style.display = 'block';
                    feedbackDiv.style.background = 'rgba(239, 68, 68, 0.15)';
                    feedbackDiv.style.color = '#ef4444';
                    feedbackDiv.innerText = `Backend server at ${API_BASE_URL} is unreachable. Ensure backend server is running.`;
                }
                retryBtn.disabled = false;
                retryBtn.innerText = 'Retry Connection';
            }
        });
    }
}

export function renderFeatureErrorState(container, title = "Feature Unavailable", message = "Unable to load feature data.", onRetry = null) {
    if (!container) return;

    container.innerHTML = `
        <div class="card" style="padding: 32px 24px; text-align: center; max-width: 540px; margin: 32px auto; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-color, #334155);">
            <div style="display: inline-flex; align-items: center; gap: 8px; background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.2); padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; color: #10b981; margin-bottom: 16px;">
                <span style="width: 6px; height: 6px; border-radius: 50%; background: #10b981;"></span>
                Backend Connection: ONLINE (${API_BASE_URL})
            </div>
            <h3 style="font-size: 18px; font-weight: 700; margin-bottom: 8px; color: var(--text-primary);">${escapeHtml(title)}</h3>
            <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 20px; line-height: 1.5;">
                ${escapeHtml(message)}
            </p>
            ${typeof onRetry === 'function' ? `
                <div style="display: flex; gap: 12px; justify-content: center;">
                    <button id="btn-feature-retry" class="btn btn-primary">Try Again</button>
                </div>
            ` : ''}
        </div>
    `;

    const retryBtn = container.querySelector('#btn-feature-retry');
    if (retryBtn && typeof onRetry === 'function') {
        retryBtn.addEventListener('click', () => onRetry());
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
