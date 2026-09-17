// uiStateStore.js — Per-project view UI state persistence store (BUG 5)

class UIStateStore {
    constructor() {
        this.states = new Map();
    }

    _getKey(projectId, viewName) {
        return `${projectId || 'global'}_${viewName}`;
    }

    get(projectId, viewName) {
        const key = this._getKey(projectId, viewName);
        return this.states.get(key) || null;
    }

    save(projectId, viewName, stateObj) {
        const key = this._getKey(projectId, viewName);
        const existing = this.states.get(key) || {};
        this.states.set(key, { ...existing, ...stateObj });
    }

    clear(projectId, viewName) {
        if (projectId && viewName) {
            this.states.delete(this._getKey(projectId, viewName));
        } else if (projectId) {
            for (const k of this.states.keys()) {
                if (k.startsWith(`${projectId}_`)) {
                    this.states.delete(k);
                }
            }
        } else {
            this.states.clear();
        }
    }
}

export const uiStateStore = new UIStateStore();
