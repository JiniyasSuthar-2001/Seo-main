/**
 * AIChatModal.js — Evidence-Grounded Floating AI SEO Assistant Panel
 * Anchored to the bottom-right of the viewport. Non-intrusive floating panel.
 */

import { projectStore } from '../core/projectStore.js';
import { apiClient } from '../services/apiClient.js';
import { renderAIBadge, renderViewEvidenceButton } from './AIBadge.js';

export class AIChatModal {
  constructor() {
    this.container = null;
    this.messages = [];
    this.isSubmitting = false;
    this.abortController = null;
  }

  open() {
    if (!this.container) {
      this.renderModal();
    }
    this.container.style.display = 'flex';
    const input = document.getElementById('ai-chat-input');
    if (input) input.focus();
  }

  close() {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
    if (this.container) {
      this.container.style.display = 'none';
    }
  }

  toggle() {
    if (this.container && this.container.style.display === 'flex') {
      this.close();
    } else {
      this.open();
    }
  }

  renderModal() {
    this.container = document.createElement('div');
    this.container.id = 'ai-chat-panel-container';
    this.container.style.cssText = `
      position: fixed; bottom: 80px; right: 24px; width: 420px; max-width: calc(100vw - 32px);
      height: 560px; max-height: calc(100vh - 110px);
      background: var(--bg-card); border-radius: 14px; border: 1px solid var(--border);
      box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.05);
      display: flex; flex-direction: column; overflow: hidden; z-index: 99995;
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
      animation: slideUpIn 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    `;

    const selectedProj = projectStore.getSelectedProject() || {};
    const domain = selectedProj.domain || selectedProj.url || 'Your Website';

    this.container.innerHTML = `
      <style>
        @keyframes slideUpIn {
          from { opacity: 0; transform: translateY(12px) scale(0.98); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
      </style>
      
      <!-- HEADER -->
      <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; background: var(--bg-subtle);">
        <div>
          <div style="display: flex; align-items: center; gap: 8px;">
            <h3 style="font-size: 15px; font-weight: 700; color: var(--text-primary); margin: 0;">AI SEO Assistant</h3>
            ${renderAIBadge('analysis')}
          </div>
          <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">
            Grounded in real evidence for <strong>${this.escapeHtml(domain)}</strong>
          </div>
        </div>
        <button onclick="window.closeAIChatModal()" style="font-size: 22px; color: var(--text-tertiary); cursor: pointer; border: none; background: none; line-height: 1;">&times;</button>
      </div>

      <!-- TRANSPARENCY NOTICE BANNER -->
      <div style="background: rgba(124, 58, 237, 0.08); border-bottom: 1px solid rgba(139, 92, 246, 0.2); padding: 8px 16px; font-size: 11px; color: var(--text-secondary);">
        💡 <strong>AI Output Transparency:</strong> Answers are AI interpretations generated from your website crawl evidence. Click <strong>View Evidence</strong> to see source facts.
      </div>

      <!-- CHAT MESSAGES STREAM CONTAINER -->
      <div id="ai-chat-messages-container" style="flex: 1; padding: 16px; overflow-y: auto; display: flex; flex-direction: column; gap: 14px;">
        <div style="background: var(--bg-subtle); padding: 12px 14px; border-radius: 10px; border: 1px solid var(--border); font-size: 12.5px; color: var(--text-secondary);">
          👋 Hi! Ask me any question about your website SEO audit, missing meta descriptions, crawl issues, or technical improvements.
        </div>
      </div>

      <!-- INPUT FORM -->
      <form onsubmit="window.submitAIChatQuery(event)" style="padding: 12px 16px; border-top: 1px solid var(--border); background: var(--bg-subtle); display: flex; gap: 8px;">
        <input id="ai-chat-input" type="text" placeholder="Ask a question about your SEO data..." required style="flex: 1; padding: 9px 12px; border: 1px solid var(--border); border-radius: 8px; font-size: 13px; background: var(--bg-card); color: var(--text-primary); outline: none;">
        <button type="submit" id="ai-chat-submit-btn" class="btn btn-primary btn-sm" style="padding: 0 14px; font-weight: 600; font-size: 12.5px;">Ask AI</button>
      </form>
    `;

    document.body.appendChild(this.container);

    window.closeAIChatModal = () => this.close();
    window.submitAIChatQuery = (e) => this.handleSubmit(e);
  }

  async handleSubmit(e) {
    e.preventDefault();
    if (this.isSubmitting) return;

    const input = document.getElementById('ai-chat-input');
    const btn = document.getElementById('ai-chat-submit-btn');
    const msgContainer = document.getElementById('ai-chat-messages-container');

    const query = (input.value || '').trim();
    if (!query) return;

    const projectId = projectStore.getSelectedProjectId();
    if (!projectId) {
      alert("Please select a project workspace first.");
      return;
    }

    if (this.abortController) {
      this.abortController.abort();
    }
    this.abortController = new AbortController();
    const signal = this.abortController.signal;

    // Append user message
    const userBubble = document.createElement('div');
    userBubble.style.cssText = 'align-self: flex-end; background: var(--primary); color: #fff; padding: 9px 13px; border-radius: 10px 10px 0 10px; max-width: 82%; font-size: 12.5px;';
    userBubble.innerText = query;
    msgContainer.appendChild(userBubble);

    input.value = '';
    this.isSubmitting = true;
    btn.disabled = true;
    btn.innerText = 'Thinking...';

    // Loading placeholder
    const aiBubble = document.createElement('div');
    aiBubble.style.cssText = 'align-self: flex-start; background: var(--bg-subtle); border: 1px solid var(--border); padding: 12px 14px; border-radius: 10px 10px 10px 0; max-width: 90%; font-size: 12.5px;';
    aiBubble.innerHTML = `<div style="display: flex; align-items: center; gap: 8px;">${renderAIBadge('analysis')} <span style="color: var(--text-tertiary);">Analyzing project evidence...</span></div>`;
    msgContainer.appendChild(aiBubble);
    msgContainer.scrollTop = msgContainer.scrollHeight;

    try {
      const res = await apiClient.post(`/api/projects/${projectId}/ai/chat`, { 
        query,
        current_page: window.location.pathname
      }, { signal });
      const answerText = res.answer || res.message || "No answer generated.";
      const provider = res.provider || 'AI Engine';
      const evidence = res.context_used || { domain: projectStore.getSelectedProject()?.domain, pages_analyzed: 1 };

      const evidenceList = [
        { label: 'Target Website Domain', value: evidence.domain || 'Target Project', source: 'Crawled Data' },
        { label: 'Pages Analyzed in Context', value: `${evidence.pages_analyzed || 0} pages`, source: 'Crawled Data' }
      ];

      aiBubble.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          ${renderAIBadge('analysis')}
          <span style="font-size: 10px; color: var(--text-tertiary);">Provider: ${provider.toUpperCase()}</span>
        </div>
        <div style="color: var(--text-primary); line-height: 1.5; white-space: pre-wrap; margin-bottom: 10px;">${this.escapeHtml(answerText)}</div>
        ${renderViewEvidenceButton(evidenceList, `chat-ev-${Math.random().toString(36).substring(2, 7)}`)}
      `;
    } catch (err) {
      if (err.name === 'AbortError' || err.message === 'canceled') {
        if (aiBubble && aiBubble.parentNode) {
          aiBubble.parentNode.removeChild(aiBubble);
        }
        return;
      }
      aiBubble.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
          ${renderAIBadge('analysis')}
          <span style="color: var(--critical); font-weight: 600;">Unable to complete query</span>
        </div>
        <div style="color: var(--text-secondary); font-size: 12px;">${this.escapeHtml(err.message || "Please check backend AI service status.")}</div>
      `;
    } finally {
      this.isSubmitting = false;
      btn.disabled = false;
      btn.innerText = 'Ask AI';
      this.abortController = null;
      msgContainer.scrollTop = msgContainer.scrollHeight;
    }
  }

  escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
}

export const aiChatModal = new AIChatModal();
