import { apiClient } from './apiClient.js';

export const MasterService = {
  async getDashboard(rangeType = '30d') {
    return apiClient.get(`/api/master/dashboard?range_type=${rangeType}`);
  },

  async getCustomers(search = '', status = 'all', page = 1) {
    return apiClient.get(`/api/master/customers?search=${encodeURIComponent(search)}&status=${status}&page=${page}`);
  },

  async getCustomerDetail(customerId) {
    return apiClient.get(`/api/master/customers/${customerId}`);
  },

  async getAIControl() {
    return apiClient.get('/api/master/ai/control');
  },

  async updateAIControl(payload) {
    return apiClient.patch('/api/master/ai/control', payload);
  },

  async getCreditsOverview(search = '', page = 1) {
    return apiClient.get(`/api/master/credits?search=${encodeURIComponent(search)}&page=${page}`);
  },

  async getCustomerWallet(customerId) {
    return apiClient.get(`/api/master/customers/${customerId}/wallet`);
  },

  async getCustomerCreditTransactions(customerId, page = 1) {
    return apiClient.get(`/api/master/customers/${customerId}/credit-transactions?page=${page}`);
  },

  async allocateCustomerCredits(customerId, amount, transactionType, reason) {
    return apiClient.post(`/api/master/customers/${customerId}/credits`, {
      amount,
      transaction_type: transactionType,
      reason
    });
  },

  async updateCustomerAISettings(customerId, payload) {
    return apiClient.patch(`/api/master/customers/${customerId}/ai-settings`, payload);
  },

  async getBudgets() {
    return apiClient.get('/api/master/budgets');
  },

  async updateBudgets(payload) {
    return apiClient.patch('/api/master/budgets', payload);
  },

  async updateProviderRouting(payload) {
    return apiClient.patch('/api/master/providers/routing', payload);
  }
};
