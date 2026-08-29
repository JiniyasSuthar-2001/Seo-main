import { aiChatModal } from './AIChatModal.js';

export class AIFloatingButton {
    constructor() {
        this.element = null;
    }

    render() {
        if (this.element) return this.element;

        this.element = document.createElement('div');
        this.element.id = 'ai-assistant-fab-container';
        this.element.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 99990;
            display: flex;
            align-items: center;
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
        `;

        this.element.innerHTML = `
            <style>
                .ai-fab-button {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 10px 16px;
                    border-radius: 30px;
                    background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%);
                    color: #ffffff;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    box-shadow: 0 8px 24px -4px rgba(37, 99, 235, 0.45), 0 4px 12px rgba(0, 0, 0, 0.2);
                    cursor: pointer;
                    font-size: 13px;
                    font-weight: 700;
                    letter-spacing: -0.01em;
                    transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease, filter 0.2s ease;
                    user-select: none;
                    outline: none;
                }
                .ai-fab-button:hover {
                    transform: translateY(-3px) scale(1.03);
                    box-shadow: 0 12px 28px -4px rgba(37, 99, 235, 0.55), 0 6px 16px rgba(0, 0, 0, 0.3);
                    filter: brightness(1.08);
                }
                .ai-fab-button:active {
                    transform: translateY(0) scale(0.97);
                    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
                }
                .ai-fab-icon {
                    width: 20px;
                    height: 20px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    flex-shrink: 0;
                }
                @media (max-width: 640px) {
                    #ai-assistant-fab-container {
                        bottom: 16px;
                        right: 16px;
                    }
                    .ai-fab-button {
                        padding: 10px;
                        border-radius: 50%;
                    }
                    .ai-fab-button span {
                        display: none;
                    }
                }
            </style>

            <button type="button" class="ai-fab-button" id="btn-ai-fab-trigger" title="Ask AI SEO Assistant" aria-label="Open AI SEO Assistant">
                <div class="ai-fab-icon">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
                        <circle cx="12" cy="12" r="4"/>
                    </svg>
                </div>
                <span>AI Assistant</span>
            </button>
        `;

        this.element.querySelector('#btn-ai-fab-trigger')?.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            aiChatModal.toggle();
        });

        return this.element;
    }
}

export const aiFloatingButton = new AIFloatingButton();
