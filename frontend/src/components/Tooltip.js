/**
 * Global Information Tooltip System
 * Plain-English usability tooltips with dictionary lookup, automatic viewport positioning,
 * touch/keyboard support, and full accessibility.
 */

export const TOOLTIP_DICTIONARY = {
    websiteHealthScore: "A score from 0–100 showing how healthy your website is based on technical checks performed during the latest scan.",
    checksPerformed: "The total number of technical rules evaluated across all scanned website pages.",
    problemsFound: "The total number of technical issues or warnings detected during the latest website scan.",
    pagesScanned: "The total count of HTML pages fetched and analyzed during your website scan.",
    internalLinks: "Links on your website that point to other pages on your own website.",
    externalLinks: "Links on your website that point to external websites.",
    backlinks: "Links from external websites that point to your website.",
    referringDomains: "Unique website domain names linking to your website.",
    keywordFrequency: "How often a specific search term appears in your website content.",
    searchRanking: "Your page's organic position on Google search engine results pages.",
    indexability: "Whether search engines like Google are permitted to store and show a page in search results.",
    canonicalUrl: "The primary preferred address specified for a page to prevent duplicate content issues.",
    metaDescription: "The short page summary displayed beneath your page title in Google search results.",
    h1Heading: "The main headline of your web page visible to readers and search engines.",
    imageAltText: "Text descriptions attached to images so search engines and screen readers understand them.",
    contentDepth: "Word count and textual depth of your page content.",
    orphanPage: "A page on your website that has zero internal links pointing to it from other pages.",
    linkDepth: "The minimum number of clicks required to reach a page starting from your homepage."
};

/**
 * Renders an inline ⓘ tooltip icon.
 * @param {string} keyOrText - A dictionary key or a custom text explanation.
 */
export function renderTooltip(keyOrText) {
    if (!keyOrText) return '';

    const text = TOOLTIP_DICTIONARY[keyOrText] || keyOrText;
    const safeText = String(text).replace(/"/g, '&quot;').replace(/'/g, '&#39;');

    return `
        <span class="info-tooltip-wrapper" 
              tabindex="0" 
              role="button" 
              aria-label="Information: ${safeText}"
              data-tooltip="${safeText}" 
              style="display: inline-flex; align-items: center; justify-content: center; cursor: help; margin-left: 5px; vertical-align: middle; outline: none;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" style="color: var(--text-tertiary, #94a3b8); transition: color 0.15s ease;">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
            </svg>
        </span>
    `;
}

/**
 * Initializes global tooltip event listeners and dynamic positioning logic.
 */
export function initTooltipListeners(container = document) {
    // Inject global stylesheet if not present
    if (!document.getElementById('info-tooltip-styles')) {
        const style = document.createElement('style');
        style.id = 'info-tooltip-styles';
        style.innerHTML = `
            .info-tooltip-wrapper:hover svg,
            .info-tooltip-wrapper:focus svg {
                color: var(--primary, #3b82f6) !important;
            }
            .global-tooltip-popover {
                position: fixed;
                background: #0f172a;
                color: #ffffff;
                padding: 8px 12px;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 500;
                line-height: 1.45;
                max-width: 260px;
                z-index: 999999;
                box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.1);
                pointer-events: none;
                opacity: 0;
                transform: translateY(4px);
                transition: opacity 0.18s ease, transform 0.18s ease;
                text-align: left;
                word-wrap: break-word;
            }
            .global-tooltip-popover.visible {
                opacity: 1;
                transform: translateY(0);
            }
        `;
        document.head.appendChild(style);
    }

    let activePopover = null;

    const hideTooltip = () => {
        if (activePopover) {
            activePopover.classList.remove('visible');
            setTimeout(() => {
                if (activePopover && activePopover.parentNode) {
                    activePopover.parentNode.removeChild(activePopover);
                }
                activePopover = null;
            }, 180);
        }
    };

    const showTooltip = (targetEl) => {
        const text = targetEl.getAttribute('data-tooltip');
        if (!text) return;

        hideTooltip();

        const popover = document.createElement('div');
        popover.className = 'global-tooltip-popover';
        popover.setAttribute('role', 'tooltip');
        popover.innerText = text;
        document.body.appendChild(popover);

        const rect = targetEl.getBoundingClientRect();
        const popoverRect = popover.getBoundingClientRect();

        let top = rect.top - popoverRect.height - 8;
        let left = rect.left + (rect.width / 2) - (popoverRect.width / 2);

        // Viewport boundary collision detection
        if (top < 10) {
            top = rect.bottom + 8; // Flip to bottom if clipping top
        }

        if (left < 10) {
            left = 10;
        } else if (left + popoverRect.width > window.innerWidth - 10) {
            left = window.innerWidth - popoverRect.width - 10;
        }

        popover.style.top = `${top}px`;
        popover.style.left = `${left}px`;

        requestAnimationFrame(() => {
            popover.classList.add('visible');
        });

        activePopover = popover;
    };

    // Event Delegation for Tooltip Triggers
    const wrappers = container.querySelectorAll('.info-tooltip-wrapper');
    wrappers.forEach(w => {
        w.addEventListener('mouseenter', () => showTooltip(w));
        w.addEventListener('mouseleave', () => hideTooltip());
        w.addEventListener('focus', () => showTooltip(w));
        w.addEventListener('blur', () => hideTooltip());
        w.addEventListener('touchstart', (e) => {
            e.stopPropagation();
            if (activePopover) {
                hideTooltip();
            } else {
                showTooltip(w);
            }
        });
    });

    document.addEventListener('touchstart', (e) => {
        if (!e.target.closest('.info-tooltip-wrapper')) {
            hideTooltip();
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            hideTooltip();
        }
    });
}
