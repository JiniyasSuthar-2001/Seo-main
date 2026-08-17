import { API_BASE_URL } from '../config/api.js';

export function renderBackendOfflineState(container, message = "Unable to load data from backend server.") {
    if (!container) return;
    container.innerHTML = `
        <div class="card" style="padding: 36px 24px; text-align: center; max-width: 520px; margin: 32px auto;">
            <div style="width: 48px; height: 48px; border-radius: 50%; background: var(--critical-bg); color: var(--critical); display: flex; align-items: center; justify-content: center; margin: 0 auto 16px;">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
            </div>
            <h3 style="font-size: 18px; font-weight: 700; margin-bottom: 8px;">Backend Connection Unavailable</h3>
            <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 20px; line-height: 1.5;">
                ${message}<br/>
                <span style="font-size: 12px; color: var(--text-tertiary);">API Endpoint: <code>${API_BASE_URL}</code> | Status: <strong>Offline</strong></span>
            </p>
            <div style="display: flex; gap: 12px; justify-content: center;">
                <button class="btn btn-primary" onclick="window.location.reload()">Retry Connection</button>
            </div>
        </div>
    `;
}
