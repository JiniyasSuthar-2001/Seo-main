/**
 * ApiKeyModal Component
 * Reusable, modern SaaS-styled configuration modal for AI providers,
 * SERP providers, Backlink providers, and Google Ads credentials.
 * 
 * Features:
 * - Dynamic provider registry configuration
 * - Password visibility toggle (Show/Hide)
 * - In-modal error & success banner states (zero browser alert/prompt)
 * - Verification loading spinner & duplicate submission prevention
 * - Full ARIA accessibility and Escape key navigation
 * - Absolute credential safety (zero client-side logging, zero raw key storage)
 */
import { apiClient } from '../services/apiClient.js';

export class ApiKeyModal {
    static getProviderConfig(providerKey) {
        const key = (providerKey || '').toLowerCase().trim();
        const configs = {
            'anthropic': {
                provider: 'claude',
                name: 'Anthropic Claude',
                icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm1 14.5h-2v-2h2zm0-4.5h-2V7h2z"/></svg>`,
                iconBg: 'rgba(217, 119, 6, 0.12)',
                iconColor: '#d97706',
                credentialLabel: 'Anthropic API Key',
                placeholder: 'sk-ant-api03-...',
                description: 'Connect your Anthropic Claude API key for high-precision audit analysis and automated SEO recommendations.',
                endpoint: '/api/integrations/claude/key',
                testEndpoint: '/api/integrations/claude/test',
                helpUrl: 'https://console.anthropic.com/settings/keys',
                helpText: 'Get API Key from Anthropic Console'
            },
            'claude': {
                provider: 'claude',
                name: 'Anthropic Claude',
                icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm1 14.5h-2v-2h2zm0-4.5h-2V7h2z"/></svg>`,
                iconBg: 'rgba(217, 119, 6, 0.12)',
                iconColor: '#d97706',
                credentialLabel: 'Anthropic API Key',
                placeholder: 'sk-ant-api03-...',
                description: 'Connect your Anthropic Claude API key for high-precision audit analysis and automated SEO recommendations.',
                endpoint: '/api/integrations/claude/key',
                testEndpoint: '/api/integrations/claude/test',
                helpUrl: 'https://console.anthropic.com/settings/keys',
                helpText: 'Get API Key from Anthropic Console'
            },
            'openai': {
                provider: 'openai',
                name: 'OpenAI / ChatGPT',
                icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M8 12h8M12 8v8"/></svg>`,
                iconBg: 'rgba(16, 185, 129, 0.12)',
                iconColor: '#10b981',
                credentialLabel: 'OpenAI API Key',
                placeholder: 'sk-proj-...',
                description: 'Connect your OpenAI API key for GPT-4o powered intelligence, structured issue fixes, and audit solutions.',
                endpoint: '/api/integrations/openai/key',
                testEndpoint: '/api/integrations/openai/test',
                helpUrl: 'https://platform.openai.com/api-keys',
                helpText: 'Get API Key from OpenAI Platform'
            },
            'gemini': {
                provider: 'gemini',
                name: 'Google Gemini',
                icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`,
                iconBg: 'rgba(59, 130, 246, 0.12)',
                iconColor: '#3b82f6',
                credentialLabel: 'Google Gemini API Key',
                placeholder: 'AIzaSy...',
                description: 'Connect your Google AI Gemini key to use Gemini 2.5 Flash & Pro for fast technical remediation.',
                endpoint: '/api/integrations/gemini/key',
                testEndpoint: '/api/integrations/gemini/test',
                helpUrl: 'https://aistudio.google.com/app/apikey',
                helpText: 'Get API Key from Google AI Studio'
            },
            'serp': {
                provider: 'serp_provider',
                name: 'SERP & Rank Tracking Provider',
                icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>`,
                iconBg: 'rgba(59, 130, 246, 0.12)',
                iconColor: '#3b82f6',
                credentialLabel: 'SERP Provider API Key',
                placeholder: 'Enter your SERP API Key',
                description: 'Connect an external SERP provider (e.g., SerpApi, DataForSEO) for authentic live keyword ranking tracking.',
                endpoint: '/api/integrations/serp/config',
                testEndpoint: '/api/integrations/serp/test',
                requiresProviderName: true,
                defaultProviderName: 'SerpApi',
                helpUrl: 'https://serpapi.com/manage-api-key',
                helpText: 'Learn more about SERP Provider keys'
            },
            'serp_provider': {
                provider: 'serp_provider',
                name: 'SERP & Rank Tracking Provider',
                icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>`,
                iconBg: 'rgba(59, 130, 246, 0.12)',
                iconColor: '#3b82f6',
                credentialLabel: 'SERP Provider API Key',
                placeholder: 'Enter your SERP API Key',
                description: 'Connect an external SERP provider (e.g., SerpApi, DataForSEO) for authentic live keyword ranking tracking.',
                endpoint: '/api/integrations/serp/config',
                testEndpoint: '/api/integrations/serp/test',
                requiresProviderName: true,
                defaultProviderName: 'SerpApi',
                helpUrl: 'https://serpapi.com/manage-api-key',
                helpText: 'Learn more about SERP Provider keys'
            },
            'backlink': {
                provider: 'backlink_provider',
                name: 'Backlink Intelligence Provider',
                icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>`,
                iconBg: 'rgba(139, 92, 246, 0.12)',
                iconColor: '#8b5cf6',
                credentialLabel: 'Backlink Provider API Key',
                placeholder: 'Enter your Backlink API Key',
                description: 'Connect external backlink data provider (e.g., Ahrefs, Moz, OpenLink) for inbound link discovery.',
                endpoint: '/api/integrations/backlink/config',
                testEndpoint: '/api/integrations/backlink/test',
                requiresProviderName: true,
                defaultProviderName: 'Ahrefs / Backlink API',
                helpUrl: 'https://ahrefs.com/api',
                helpText: 'Learn more about Backlink API keys'
            },
            'backlink_provider': {
                provider: 'backlink_provider',
                name: 'Backlink Intelligence Provider',
                icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>`,
                iconBg: 'rgba(139, 92, 246, 0.12)',
                iconColor: '#8b5cf6',
                credentialLabel: 'Backlink Provider API Key',
                placeholder: 'Enter your Backlink API Key',
                description: 'Connect external backlink data provider (e.g., Ahrefs, Moz, OpenLink) for inbound link discovery.',
                endpoint: '/api/integrations/backlink/config',
                testEndpoint: '/api/integrations/backlink/test',
                requiresProviderName: true,
                defaultProviderName: 'Ahrefs / Backlink API',
                helpUrl: 'https://ahrefs.com/api',
                helpText: 'Learn more about Backlink API keys'
            },
            'google_ads': {
                provider: 'google_ads',
                name: 'Google Ads',
                icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>`,
                iconBg: 'rgba(234, 67, 53, 0.12)',
                iconColor: '#ea4335',
                credentialLabel: 'Google Ads Developer Token',
                placeholder: 'e.g. abcd1234efgh5678',
                description: 'Enter your approved Google Ads API Developer Token. The token is encrypted with AES-256 and never exposed in responses.',
                endpoint: '/api/integrations/google_ads/config',
                isDeveloperToken: true,
                helpUrl: 'https://developers.google.com/google-ads/api/docs/first-call/dev-token',
                helpText: 'How to obtain a Google Ads Developer Token'
            }
        };

        return configs[key] || {
            provider: key,
            name: key.toUpperCase(),
            icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>`,
            iconBg: 'rgba(37, 99, 235, 0.12)',
            iconColor: '#2563eb',
            credentialLabel: `${key.toUpperCase()} API Key`,
            placeholder: 'Enter API Key',
            description: `Configure your ${key} connection.`,
            endpoint: `/api/integrations/${key}/key`,
            testEndpoint: `/api/integrations/${key}/test`
        };
    }

    /**
     * Opens the API Key configuration modal.
     * @param {Object} options
     * @param {string} options.provider - Provider key (e.g., 'anthropic', 'openai', 'gemini', 'serp', 'backlink', 'google_ads')
     * @param {boolean} [options.isConnected=false] - Whether the provider is currently connected
     * @param {string} [options.maskedKey=''] - Existing masked key if connected
     * @param {string} [options.existingName=''] - Existing custom provider name (for SERP/Backlink)
     * @param {Function} [options.onSuccess] - Callback when configuration succeeds
     */
    static open(options = {}) {
        const {
            provider,
            isConnected = false,
            maskedKey = '',
            existingName = '',
            onSuccess = () => {}
        } = options;

        const config = ApiKeyModal.getProviderConfig(provider);
        const modalRootId = 'api-key-config-modal-root';

        // Remove any existing modal
        const existing = document.getElementById(modalRootId);
        if (existing) existing.remove();

        let isSubmitting = false;
        let isPasswordVisible = false;

        const modalBackdrop = document.createElement('div');
        modalBackdrop.id = modalRootId;
        modalBackdrop.setAttribute('role', 'dialog');
        modalBackdrop.setAttribute('aria-modal', 'true');
        modalBackdrop.setAttribute('aria-labelledby', 'api-key-modal-title');
        modalBackdrop.setAttribute('aria-describedby', 'api-key-modal-desc');

        modalBackdrop.style.cssText = `
            position: fixed;
            inset: 0;
            background: rgba(8, 12, 20, 0.72);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            padding: 16px;
            animation: apimodal-fade-in 0.18s ease-out;
        `;

        const modalTitleText = isConnected ? `Update ${config.name} Key` : `Connect ${config.name}`;
        const submitBtnText = isConnected ? 'Verify & Update' : 'Verify & Connect';

        modalBackdrop.innerHTML = `
            <style>
                @keyframes apimodal-fade-in {
                    from { opacity: 0; transform: scale(0.98); }
                    to { opacity: 1; transform: scale(1); }
                }
                .apikey-modal-card {
                    background: var(--bg-card);
                    border: 1px solid var(--border);
                    border-radius: var(--radius-lg, 12px);
                    box-shadow: var(--shadow-lg, 0 12px 28px -4px rgba(0, 0, 0, 0.3));
                    width: 100%;
                    max-width: 480px;
                    max-height: 90vh;
                    overflow-y: auto;
                    color: var(--text-primary);
                    font-family: var(--font-sans, inherit);
                }
                .apikey-input-group {
                    position: relative;
                    display: flex;
                    align-items: center;
                }
                .apikey-input-field {
                    width: 100%;
                    padding: 10px 42px 10px 12px;
                    background: var(--bg-subtle, #f8fafc);
                    border: 1px solid var(--border);
                    border-radius: var(--radius-md, 8px);
                    font-size: 13.5px;
                    font-family: monospace, inherit;
                    color: var(--text-primary);
                    transition: border-color 0.15s ease, box-shadow 0.15s ease;
                    outline: none;
                }
                .apikey-input-field:focus {
                    border-color: var(--primary);
                    box-shadow: 0 0 0 3px var(--primary-light, rgba(37, 99, 235, 0.15));
                }
                .apikey-input-field.input-error {
                    border-color: var(--critical, #ef4444) !important;
                    box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.15) !important;
                }
                .apikey-toggle-btn {
                    position: absolute;
                    right: 8px;
                    background: transparent;
                    border: none;
                    color: var(--text-tertiary);
                    cursor: pointer;
                    padding: 6px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 4px;
                    transition: color 0.15s ease;
                }
                .apikey-toggle-btn:hover {
                    color: var(--text-primary);
                }
                .apikey-spinner {
                    width: 14px;
                    height: 14px;
                    border: 2px solid rgba(255, 255, 255, 0.3);
                    border-top-color: #ffffff;
                    border-radius: 50%;
                    animation: apikey-spin 0.6s linear infinite;
                    display: inline-block;
                }
                @keyframes apikey-spin {
                    to { transform: rotate(360deg); }
                }
            </style>
            <div class="apikey-modal-card">
                <!-- MODAL HEADER -->
                <div style="padding: 20px 24px 16px 24px; border-bottom: 1px solid var(--border); display: flex; align-items: flex-start; justify-content: space-between; gap: 12px;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <div style="width: 42px; height: 42px; border-radius: 10px; background: ${config.iconBg}; color: ${config.iconColor}; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                            ${config.icon}
                        </div>
                        <div>
                            <h2 id="api-key-modal-title" style="font-size: 17px; font-weight: 700; margin: 0; color: var(--text-primary); letter-spacing: -0.01em;">
                                ${modalTitleText}
                            </h2>
                            <p id="api-key-modal-desc" style="font-size: 12.5px; color: var(--text-secondary); margin: 2px 0 0 0;">
                                Enter your API credential for verified integration.
                            </p>
                        </div>
                    </div>
                    <button id="btn-modal-close" aria-label="Close dialog" style="background: transparent; border: none; font-size: 22px; line-height: 1; color: var(--text-tertiary); cursor: pointer; padding: 4px; border-radius: 6px; display: flex; align-items: center; justify-content: center;">
                        &times;
                    </button>
                </div>

                <!-- MODAL BODY & FORM -->
                <form id="form-api-key-config" style="padding: 20px 24px 24px 24px;">
                    <!-- DESCRIPTION -->
                    <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.5; margin: 0 0 16px 0;">
                        ${config.description}
                    </p>

                    <!-- CURRENT STATUS BADGE (IF CONNECTED) -->
                    ${isConnected ? `
                        <div style="margin-bottom: 16px; padding: 10px 14px; background: var(--success-bg, rgba(16, 185, 129, 0.08)); border: 1px solid var(--success-border, rgba(16, 185, 129, 0.25)); border-radius: 8px; display: flex; align-items: center; justify-content: space-between; font-size: 12.5px;">
                            <div style="display: flex; align-items: center; gap: 8px; color: var(--success, #10b981); font-weight: 600;">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                                Currently Connected
                            </div>
                            <code style="font-family: monospace; font-size: 12px; color: var(--text-secondary); background: var(--bg-card); padding: 2px 6px; border-radius: 4px; border: 1px solid var(--border);">
                                ${maskedKey || '••••••••••••'}
                            </code>
                        </div>
                    ` : ''}

                    <!-- IN-MODAL ERROR CONTAINER (Initially Hidden) -->
                    <div id="modal-error-container" role="alert" style="display: none; margin-bottom: 16px; padding: 12px 14px; background: var(--critical-bg, rgba(239, 68, 68, 0.08)); border: 1px solid var(--critical-border, rgba(239, 68, 68, 0.25)); border-radius: 8px; font-size: 12.5px; color: var(--critical, #ef4444); line-height: 1.45;">
                        <div style="display: flex; align-items: flex-start; gap: 8px;">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink: 0; margin-top: 1px;"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                            <span id="modal-error-text">Authentication failed.</span>
                        </div>
                    </div>

                    <!-- IN-MODAL SUCCESS CONTAINER (Initially Hidden) -->
                    <div id="modal-success-container" role="status" style="display: none; margin-bottom: 16px; padding: 12px 14px; background: var(--success-bg, rgba(16, 185, 129, 0.08)); border: 1px solid var(--success-border, rgba(16, 185, 129, 0.25)); border-radius: 8px; font-size: 12.5px; color: var(--success, #10b981); line-height: 1.45;">
                        <div style="display: flex; align-items: center; gap: 8px; font-weight: 600;">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                            <span id="modal-success-text">Connected successfully!</span>
                        </div>
                    </div>

                    <!-- OPTIONAL PROVIDER NAME INPUT (For SERP / Backlink) -->
                    ${config.requiresProviderName ? `
                        <div style="margin-bottom: 14px;">
                            <label for="input-provider-custom-name" style="display: block; font-size: 11.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-secondary); margin-bottom: 6px;">
                                Provider Label
                            </label>
                            <input id="input-provider-custom-name" type="text" value="${existingName || config.defaultProviderName || ''}" required style="width: 100%; padding: 10px 12px; background: var(--bg-subtle, #f8fafc); border: 1px solid var(--border); border-radius: var(--radius-md, 8px); font-size: 13.5px; color: var(--text-primary); outline: none;" placeholder="e.g. SerpApi or Custom Provider">
                        </div>
                    ` : ''}

                    <!-- CREDENTIAL INPUT -->
                    <div style="margin-bottom: 16px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <label for="input-api-key-value" style="font-size: 11.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-secondary);">
                                ${config.credentialLabel}
                            </label>
                            ${config.helpUrl ? `
                                <a href="${config.helpUrl}" target="_blank" rel="noopener noreferrer" style="font-size: 11.5px; color: var(--primary); text-decoration: none; display: inline-flex; align-items: center; gap: 4px;">
                                    ${config.helpText || 'Get key'}
                                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                                </a>
                            ` : ''}
                        </div>
                        <div class="apikey-input-group">
                            <input id="input-api-key-value" type="password" placeholder="${config.placeholder}" required autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" class="apikey-input-field">
                            <button type="button" id="btn-toggle-key-visibility" class="apikey-toggle-btn" aria-label="Toggle password visibility" title="Show/Hide API Key">
                                <svg id="icon-eye-open" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                                <svg id="icon-eye-closed" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display: none;"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                            </button>
                        </div>
                    </div>

                    <!-- SECURITY REASSURANCE NOTE -->
                    <div style="font-size: 11.5px; color: var(--text-tertiary); display: flex; align-items: center; gap: 6px; margin-bottom: 22px; padding: 6px 10px; background: var(--bg-subtle, rgba(0,0,0,0.02)); border-radius: 6px;">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                        <span>Key is encrypted at rest (AES-256) and verified prior to saving.</span>
                    </div>

                    <!-- ACTION BUTTONS -->
                    <div style="display: flex; justify-content: flex-end; gap: 10px; border-top: 1px solid var(--border); padding-top: 16px;">
                        <button type="button" id="btn-modal-cancel" class="btn btn-secondary" style="font-size: 13px;">
                            Cancel
                        </button>
                        <button type="submit" id="btn-modal-submit" class="btn btn-primary" style="font-size: 13px; min-width: 140px; display: inline-flex; align-items: center; justify-content: center; gap: 8px;">
                            <span id="submit-btn-text">${submitBtnText}</span>
                        </button>
                    </div>
                </form>
            </div>
        `;

        document.body.appendChild(modalBackdrop);

        // Elements
        const form = modalBackdrop.querySelector('#form-api-key-config');
        const inputKey = modalBackdrop.querySelector('#input-api-key-value');
        const inputName = modalBackdrop.querySelector('#input-provider-custom-name');
        const btnToggle = modalBackdrop.querySelector('#btn-toggle-key-visibility');
        const iconEyeOpen = modalBackdrop.querySelector('#icon-eye-open');
        const iconEyeClosed = modalBackdrop.querySelector('#icon-eye-closed');
        const btnClose = modalBackdrop.querySelector('#btn-modal-close');
        const btnCancel = modalBackdrop.querySelector('#btn-modal-cancel');
        const btnSubmit = modalBackdrop.querySelector('#btn-modal-submit');
        const submitBtnTextEl = modalBackdrop.querySelector('#submit-btn-text');
        const errorContainer = modalBackdrop.querySelector('#modal-error-container');
        const errorText = modalBackdrop.querySelector('#modal-error-text');
        const successContainer = modalBackdrop.querySelector('#modal-success-container');
        const successText = modalBackdrop.querySelector('#modal-success-text');

        // Focus field
        setTimeout(() => {
            if (inputKey) inputKey.focus();
        }, 50);

        // Helper: Close modal
        const closeModal = () => {
            if (isSubmitting) return;
            // Clear input value from memory
            if (inputKey) inputKey.value = '';
            modalBackdrop.remove();
            document.removeEventListener('keydown', handleKeyDown);
        };

        // Helper: Keyboard navigation (Escape)
        const handleKeyDown = (e) => {
            if (e.key === 'Escape' && !isSubmitting) {
                closeModal();
            }
        };
        document.addEventListener('keydown', handleKeyDown);

        // Close button & Cancel button
        if (btnClose) btnClose.addEventListener('click', closeModal);
        if (btnCancel) btnCancel.addEventListener('click', closeModal);

        // Backdrop click to close (if not clicking inside card)
        modalBackdrop.addEventListener('click', (e) => {
            if (e.target === modalBackdrop && !isSubmitting) {
                closeModal();
            }
        });

        // Show/Hide password toggle
        if (btnToggle) {
            btnToggle.addEventListener('click', () => {
                isPasswordVisible = !isPasswordVisible;
                inputKey.type = isPasswordVisible ? 'text' : 'password';
                iconEyeOpen.style.display = isPasswordVisible ? 'none' : 'block';
                iconEyeClosed.style.display = isPasswordVisible ? 'block' : 'none';
            });
        }

        // Form Submit Handler
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (isSubmitting) return;

            const keyValue = inputKey.value.trim();
            if (!keyValue) {
                inputKey.classList.add('input-error');
                errorContainer.style.display = 'block';
                errorText.innerText = 'Please enter a valid API key.';
                return;
            }

            // Clear errors
            inputKey.classList.remove('input-error');
            errorContainer.style.display = 'none';

            // Loading state
            isSubmitting = true;
            btnSubmit.disabled = true;
            btnCancel.disabled = true;
            btnClose.disabled = true;
            inputKey.disabled = true;
            if (inputName) inputName.disabled = true;
            submitBtnTextEl.innerHTML = `<span class="apikey-spinner"></span> Verifying...`;

            try {
                let payload = {};
                if (config.isDeveloperToken) {
                    payload = { developer_token: keyValue };
                } else if (config.requiresProviderName) {
                    payload = {
                        provider_name: inputName ? inputName.value.trim() : (existingName || config.defaultProviderName),
                        api_key: keyValue
                    };
                } else {
                    payload = { api_key: keyValue };
                }

                const res = await apiClient.post(config.endpoint, payload);

                // Success State
                isSubmitting = false;
                errorContainer.style.display = 'none';
                successContainer.style.display = 'block';
                successText.innerText = res.message || `${config.name} verified and connected successfully!`;
                submitBtnTextEl.innerText = '✓ Connected';
                btnSubmit.style.background = 'var(--success, #10b981)';

                // Clear input value
                inputKey.value = '';

                // Auto-close modal after brief visual confirmation and invoke callback
                setTimeout(async () => {
                    closeModal();
                    if (typeof onSuccess === 'function') {
                        await onSuccess();
                    }
                }, 1100);

            } catch (err) {
                isSubmitting = false;
                btnSubmit.disabled = false;
                btnCancel.disabled = false;
                btnClose.disabled = false;
                inputKey.disabled = false;
                if (inputName) inputName.disabled = false;
                submitBtnTextEl.innerText = isConnected ? 'Verify & Update' : 'Verify & Connect';

                // Display structured error inside modal
                inputKey.classList.add('input-error');
                errorContainer.style.display = 'block';
                errorText.innerText = err.message || 'Verification failed. Please check the credential and try again.';
                inputKey.focus();
            }
        });
    }
}
