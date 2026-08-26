/**
 * Tooltip & Plain-English Explanation Component
 * Renders an inline ⓘ icon with hover/click explanations for plain-English usability.
 */

export function renderTooltip(text) {
    if (!text) return '';
    const safeText = String(text).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    return `
        <span class="info-tooltip-wrapper" tabindex="0" data-tooltip="${safeText}" style="display: inline-flex; align-items: center; justify-content: center; cursor: help; margin-left: 4px; vertical-align: middle;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: var(--text-tertiary, #94a3b8);"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
        </span>
    `;
}

export function initTooltipListeners(container = document) {
    // Tooltip style injection
    if (!document.getElementById('info-tooltip-styles')) {
        const style = document.createElement('style');
        style.id = 'info-tooltip-styles';
        style.innerHTML = `
            .info-tooltip-wrapper {
                position: relative;
            }
            .info-tooltip-wrapper:hover::after,
            .info-tooltip-wrapper:focus::after {
                content: attr(data-tooltip);
                position: absolute;
                bottom: 125%;
                left: 50%;
                transform: translateX(-50%);
                background: #0f172a;
                color: #ffffff;
                padding: 6px 10px;
                border-radius: 6px;
                font-size: 11.5px;
                font-weight: 500;
                white-space: normal;
                width: max-content;
                max-width: 240px;
                z-index: 99999;
                box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3);
                line-height: 1.4;
                text-align: center;
                pointer-events: none;
            }
        `;
        document.head.appendChild(style);
    }
}
