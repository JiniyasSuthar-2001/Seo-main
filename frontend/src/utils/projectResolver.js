import { projectStore } from '../core/projectStore.js';

/**
 * Shared, robust Project ID resolution helper.
 * Prevents broken API requests such as /api/projects/undefined/keywords or /api/projects/null/pages.
 * 
 * @param {string|null|undefined} explicitProjectId - Project ID explicitly passed to a service call.
 * @returns {string|null} Canonical project ID string or null if unresolvable.
 */
export function resolveProjectId(explicitProjectId) {
    if (explicitProjectId && typeof explicitProjectId === 'string') {
        const clean = explicitProjectId.trim();
        if (clean && clean !== 'undefined' && clean !== 'null' && clean !== '[object Object]') {
            return clean;
        }
    }

    const selectedId = projectStore.getSelectedProjectId();
    if (selectedId && typeof selectedId === 'string') {
        const cleanSelected = selectedId.trim();
        if (cleanSelected && cleanSelected !== 'undefined' && cleanSelected !== 'null') {
            return cleanSelected;
        }
    }

    return null;
}
