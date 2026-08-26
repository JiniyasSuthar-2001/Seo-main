export function renderErrorState(container, errorObj, onRetry = null) {
    if (!container) return;

    let category = "UNKNOWN_ERROR";
    let title = "We couldn't load this information";
    let message = "The service is temporarily unavailable. Please try again.";

    if (typeof errorObj === 'string') {
        if (!errorObj.includes('http://') && !errorObj.includes('localhost') && !errorObj.includes('HTTP 500')) {
            message = errorObj;
        }
    } else if (errorObj && typeof errorObj === 'object') {
        category = errorObj.category || (errorObj.isNetworkError ? "NETWORK_ERROR" : "SERVER_ERROR");
        if (errorObj.status === 401) category = "UNAUTHORIZED";
        if (errorObj.status === 403) category = "FORBIDDEN";
        if (errorObj.status === 404) category = "NOT_FOUND";
        if (errorObj.status >= 500) category = "SERVER_ERROR";
    }

    switch (category) {
        case "NETWORK_ERROR":
            renderBackendOfflineState(container, "The service is temporarily unavailable. Please try again.", onRetry);
            return;
        case "TIMEOUT":
            title = "We couldn't load this information";
            message = "The request took longer than expected. Please try again.";
            break;
        case "UNAUTHORIZED":
            title = "Your session has expired";
            message = "Please sign in again to continue.";
            break;
        case "FORBIDDEN":
            title = "Access Restricted";
            message = "You do not have permission to access this information.";
            break;
        case "NOT_FOUND":
            title = "This information isn't available yet";
            message = "Complete a website scan or connect the required data source.";
            break;
        case "SERVER_ERROR":
            title = "We couldn't load this information";
            message = "The service is temporarily unavailable. Please try again.";
            break;
        case "EMPTY":
            title = "This information isn't available yet";
            message = "Complete a website scan or connect the required data source.";
            break;
    }

    renderFeatureErrorState(container, title, message, onRetry);
}

export function renderBackendOfflineState(container, message = null, onRetry = null) {
    if (!container) return;

    container.innerHTML = `
        <div class="card" style="padding: 40px 24px; text-align: center; max-width: 520px; margin: 32px auto; background: var(--bg-card); border-radius: 14px; border: 1px solid var(--border);">
            <div style="width: 48px; height: 48px; border-radius: 50%; background: rgba(239, 68, 68, 0.15); color: #ef4444; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px;">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
            </div>
            <h3 style="font-size: 18px; font-weight: 700; margin-bottom: 8px; color: var(--text-primary);">We couldn't load this information</h3>
            <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 20px; line-height: 1.5;">
                The service is temporarily unavailable. Please try again.
            </p>
            <div style="display: flex; gap: 12px; justify-content: center;">
                <button id="btn-retry-connection" class="btn btn-primary">Try Again</button>
            </div>
        </div>
    `;

    const retryBtn = container.querySelector('#btn-retry-connection');
    if (retryBtn) {
        retryBtn.addEventListener('click', () => {
            if (typeof onRetry === 'function') {
                onRetry();
            } else {
                window.location.reload();
            }
        });
    }
}

export function renderFeatureErrorState(container, title = "We couldn't load this information", message = "The service is temporarily unavailable. Please try again.", onRetry = null) {
    if (!container) return;

    container.innerHTML = `
        <div class="card" style="padding: 40px 24px; text-align: center; max-width: 520px; margin: 32px auto; background: var(--bg-card); border-radius: 14px; border: 1px solid var(--border);">
            <div style="width: 48px; height: 48px; border-radius: 50%; background: rgba(245, 158, 11, 0.15); color: #f59e0b; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px;">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
            </div>
            <h3 style="font-size: 18px; font-weight: 700; margin-bottom: 8px; color: var(--text-primary);">${escapeHtml(title)}</h3>
            <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 20px; line-height: 1.5;">${escapeHtml(message)}</p>
            ${onRetry ? `
                <div style="display: flex; gap: 12px; justify-content: center;">
                    <button id="btn-retry-feature" class="btn btn-primary">Try Again</button>
                </div>
            ` : ''}
        </div>
    `;

    if (onRetry) {
        const retryBtn = container.querySelector('#btn-retry-feature');
        if (retryBtn) {
            retryBtn.addEventListener('click', () => onRetry());
        }
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
