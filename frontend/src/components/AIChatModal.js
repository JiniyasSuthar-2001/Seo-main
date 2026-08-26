/**
 * AIChatModal.js — Evidence-Grounded AI SEO Assistant Drawer
 * Fully transparent AI output with model identification & View Evidence panels.
 */

import { projectStore } from '../core/projectStore.js';
import { apiClient } from '../services/apiClient.js';
import { renderAIBadge, renderViewEvidenceButton } from './AIBadge.js';

export class AIChatModal {
  constructor() {
    this.container = null;
    this.messages = [];
    this.isSubmitting = false;
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
    if (this.container) {
      this.container.style.display = 'none';
    }
  }

  renderModal() {
    this.container = document.createElement('div');
    this.container.id = 'ai-chat-drawer-overlay';
    this.container.style.cssText = `
      position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
      background: rgba(8, 12, 20, 0.6); backdrop-filter: blur(4px);
      display: flex; justify-content: flex-end; z-index: 99999;
    `;

    const selectedProj = projectStore.getSelectedProject() || {};
    const domain = selectedProj.domain || selectedProj.url || 'Your Website';

    this.container.innerHTML = `
      <div style="background: var(--bg-card); width: 100%; max-width: 520px; height: 100%; display: flex; flex-direction: column; border-left: 1px solid var(--border); box-shadow: var(--shadow-lg);">
        
        <!-- HEADER -->
        <div style="padding: 20px 24px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; background: var(--bg-subtle);">
          <div>
            <div style="display: flex; align-items: center; gap: 8px;">
              <h3 style="font-size: 17px; font-weight: 700; color: var(--text-primary); margin: 0;">AI SEO Assistant</h3>
              ${renderAIBadge('analysis')}
            </div>
            <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">
              Grounding queries in real project evidence for <strong>${domain}</strong>
            </div>
          </div>
          <button onclick="window.closeAIChatModal()" style="font-size: 24px; color: var(--text-tertiary); cursor: pointer; border: none; background: none;">&times;</button>
        </div>

        <!-- TRANSPARENCY NOTICE BANNER -->
        <div style="background: rgba(124, 58, 237, 0.08); border-bottom: 1px solid rgba(139, 92, 246, 0.2); padding: 10px 20px; font-size: 11.5px; color: var(--text-secondary);">
          💡 <strong>AI Output Transparency:</strong> Responses are AI interpretations generated from your website crawl evidence. Click <strong>View Evidence</strong> under answers to see the underlying source facts.
        </div>

        <!-- CHAT MESSAGES STREAM CONTAINER -->
        <div id="ai-chat-messages-container" style="flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px;">
          <div style="background: var(--bg-subtle); padding: 14px 16px; border-radius: 10px; border: 1px solid var(--border); font-size: 13px; color: var(--text-secondary);">
            👋 Hi! Ask me any question about your website SEO audit, missing meta descriptions, crawl issues, or content improvements.
          </div>
        </div>

        <!-- INPUT FORM -->
        <form onsubmit="window.submitAIChatQuery(event)" style="padding: 16px 20px; border-top: 1px solid var(--border); background: var(--bg-subtle); display: flex; gap: 10px;">
          <input id="ai-chat-input" type="text" placeholder="Ask a question about your SEO data..." required style="flex: 1; padding: 10px 14px; border: 1px solid var(--border); border-radius: 8px; font-size: 13.5px; background: var(--bg-card); color: var(--text-primary);">
          <button type="submit" id="ai-chat-submit-btn" class="btn btn-primary btn-sm" style="padding: 0 16px; font-weight: 600;">Ask AI</button>
        </form>
      </div>
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

    // Append user message
    const userBubble = document.createElement('div');
    userBubble.style.cssText = 'align-self: flex-end; background: var(--primary); color: #fff; padding: 10px 14px; border-radius: 10px 10px 0 10px; max-width: 80%; font-size: 13px;';
    userBubble.innerText = query;
    msgContainer.appendChild(userBubble);

    input.value = '';
    this.isSubmitting = true;
    btn.disabled = true;
    btn.innerText = 'Thinking...';

    // Loading placeholder
    const aiBubble = document.createElement('div');
    aiBubble.style.cssText = 'align-self: flex-start; background: var(--bg-subtle); border: 1px solid var(--border); padding: 14px 16px; border-radius: 10px 10px 10px 0; max-width: 90%; font-size: 13px;';
    aiBubble.innerHTML = `<div style="display: flex; align-items: center; gap: 8px;">${renderAIBadge('analysis')} <span style="color: var(--text-tertiary);">Analyzing project evidence...</span></div>`;
    msgContainer.appendChild(aiBubble);
    msgContainer.scrollTop = msgContainer.scrollHeight;

    try {
      const res = await apiClient.post(`/api/projects/${projectId}/ai/chat`, { query });
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
          <span style="font-size: 10.5px; color: var(--text-tertiary);">Provider: ${provider.toUpperCase()}</span>
        </div>
        <div style="color: var(--text-primary); line-height: 1.5; white-space: pre-wrap; margin-bottom: 10px;">${answerText}</div>
        ${renderViewEvidenceButton(evidenceList, `chat-ev-${Math.random().toString(36).substring(2, 7)}`)}
      `;
    } catch (err) {
      aiBubble.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
          ${renderAIBadge('analysis')}
          <span style="color: var(--critical); font-weight: 600;">Unable to complete query</span>
        </div>
        <div style="color: var(--text-secondary); font-size: 12.5px;">${err.message || "Please check backend AI service status."}</div>
      `;
    } finally {
      this.isSubmitting = false;
      btn.disabled = false;
      btn.innerText = 'Ask AI';
      msgContainer.scrollTop = msgContainer.scrollHeight;
    }
  }
}

export const aiChatModal = new AIChatModal();
