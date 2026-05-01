// API Client for Golden Idea App
// Prefer same-origin API to avoid mixed-content/CORS issues (e.g. https site calling http API).
// Fallback to localhost for local dev or file:// usage.
const API_BASE = (() => {
  try {
    const origin = window?.location?.origin;
    if (origin && origin !== 'null') return `${origin}/api`;
  } catch {
    // ignore
  }
  return 'http://localhost:8015/api';
})();

const api = {
  // Submit new idea
  async submitIdea(formData) {
    try {
      const response = await fetch(`${API_BASE}/ideas/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'L\u1ed7i khi g\u1eedi \u00fd t\u01b0\u1edfng');
      }

      return await response.json();
    } catch (error) {
      console.error('Submit idea error:', error);
      throw error;
    }
  },

  // Upload attachment
  async uploadAttachment(ideaId, file) {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE}/ideas/${ideaId}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || `Lỗi khi tải file lên: ${file?.name || 'unknown file'}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Upload error:', error);
      throw error;
    }
  },

  // Get units
  async getUnits() {
    try {
      const response = await fetch(`${API_BASE}/units/`);
      if (!response.ok) {
        throw new Error('Kh\u00f4ng t\u1ea3i \u0111\u01b0\u1ee3c danh s\u00e1ch \u0111\u01a1n v\u1ecb');
      }
      return await response.json();
    } catch (error) {
      console.error('Get units error:', error);
      throw error;
    }
  },

  // List users
  async listUsers() {
    try {
      const response = await fetch(`${API_BASE}/users/`);
      if (!response.ok) {
        throw new Error('Kh\u00f4ng t\u1ea3i \u0111\u01b0\u1ee3c danh s\u00e1ch user');
      }
      return await response.json();
    } catch (error) {
      console.error('List users error:', error);
      throw error;
    }
  },

  // Get user by employee_code (returns null if not found)
  async getUserByCode(employeeCode) {
    try {
      const code = (employeeCode || '').trim();
      if (!code) return null;
      const response = await fetch(`${API_BASE}/users/by-code/${encodeURIComponent(code)}`);
      if (response.status === 404) return null;
      if (!response.ok) throw new Error('Kh\u00f4ng t\u1ea3i \u0111\u01b0\u1ee3c th\u00f4ng tin user');
      return await response.json();
    } catch (error) {
      console.error('Get user by code error:', error);
      throw error;
    }
  },

  // Dashboard: ideas by unit
  async getIdeasByUnit(params = {}) {
    try {
      const qs = new URLSearchParams();
      Object.entries(params || {}).forEach(([k, v]) => {
        if (v === null || v === undefined || v === "") return;
        qs.set(k, String(v));
      });
      const suffix = qs.toString() ? `?${qs.toString()}` : "";
      const response = await fetch(`${API_BASE}/dashboard/ideas-by-unit${suffix}`);
      if (!response.ok) throw new Error('Kh\u00f4ng t\u1ea3i \u0111\u01b0\u1ee3c dashboard');
      return await response.json();
    } catch (error) {
      console.error('Dashboard error:', error);
      throw error;
    }
  },

  async getIdeaMetrics() {
    try {
      const response = await fetch(`${API_BASE}/dashboard/idea-metrics`);
      if (!response.ok) throw new Error('Kh\u00f4ng t\u1ea3i \u0111\u01b0\u1ee3c metrics');
      return await response.json();
    } catch (error) {
      console.error('Idea metrics error:', error);
      throw error;
    }
  },

  async getIdeasByCategory() {
    try {
      const response = await fetch(`${API_BASE}/dashboard/ideas-by-category`);
      if (!response.ok) throw new Error('Kh\u00f4ng t\u1ea3i \u0111\u01b0\u1ee3c chart data');
      return await response.json();
    } catch (error) {
      console.error('Ideas by category error:', error);
      throw error;
    }
  },

  async listLibraryIdeas(params = {}) {
    try {
      const qs = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => {
        if (v === null || v === undefined || v === '') return;
        qs.set(k, String(v));
      });
      const response = await fetch(`${API_BASE}/library/ideas?${qs.toString()}`);
      if (!response.ok) throw new Error('Kh\u00f4ng t\u1ea3i \u0111\u01b0\u1ee3c d\u1eef li\u1ec7u \u00fd t\u01b0\u1edfng');
      return await response.json();
    } catch (error) {
      console.error('List library ideas error:', error);
      throw error;
    }
  },

  async getLibraryIdeaDetail(ideaId) {
    try {
      const response = await fetch(`${API_BASE}/library/ideas/${ideaId}`);
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Kh\u00f4ng t\u1ea3i \u0111\u01b0\u1ee3c chi ti\u1ebft \u00fd t\u01b0\u1edfng');
      }
      return await response.json();
    } catch (error) {
      console.error('Get library idea detail error:', error);
      throw error;
    }
  },

  // Bulk upsert users
  async upsertUsersBulk(users) {
    try {
      const response = await fetch(`${API_BASE}/users/bulk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(users),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'L\u1ed7i khi l\u01b0u danh s\u00e1ch user');
      }
      return await response.json();
    } catch (error) {
      console.error('Upsert users bulk error:', error);
      throw error;
    }
  },

  async getApprovalQueue(employeeCode, statusValue = '') {
    try {
      const qs = new URLSearchParams({ employee_code: (employeeCode || '').trim().toUpperCase() });
      if (statusValue) qs.set('status', statusValue);
      const response = await fetch(`${API_BASE}/reviews/pending?${qs.toString()}`);
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Kh\u00f4ng t\u1ea3i \u0111\u01b0\u1ee3c danh s\u00e1ch ph\u00ea duy\u1ec7t');
      }
      return await response.json();
    } catch (error) {
      console.error('Get approval queue error:', error);
      throw error;
    }
  },

  async getApprovalDetail(ideaId, employeeCode) {
    try {
      const qs = new URLSearchParams({ employee_code: (employeeCode || '').trim().toUpperCase() });
      const response = await fetch(`${API_BASE}/reviews/${ideaId}/detail?${qs.toString()}`);
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Kh\u00f4ng t\u1ea3i \u0111\u01b0\u1ee3c chi ti\u1ebft phi\u1ebfu');
      }
      return await response.json();
    } catch (error) {
      console.error('Get approval detail error:', error);
      throw error;
    }
  },

  async submitApprovalReview(payload) {
    try {
      const normalizedPayload = {
        ...payload,
        employee_code: (payload?.employee_code || '').trim().toUpperCase(),
      };
      const response = await fetch(`${API_BASE}/reviews/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(normalizedPayload),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Kh\u00f4ng l\u01b0u \u0111\u01b0\u1ee3c quy\u1ebft \u0111\u1ecbnh ph\u00ea duy\u1ec7t');
      }
      return await response.json();
    } catch (error) {
      console.error('Submit approval review error:', error);
      throw error;
    }
  },

  async saveActualBenefit(ideaId, payload) {
    try {
      const normalizedPayload = {
        ...payload,
        employee_code: (payload?.employee_code || '').trim().toUpperCase(),
      };
      const response = await fetch(`${API_BASE}/reviews/${ideaId}/actual-benefit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(normalizedPayload),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Kh\u00f4ng l\u01b0u \u0111\u01b0\u1ee3c gi\u00e1 tr\u1ecb l\u00e0m l\u1ee3i th\u1ef1c t\u1ebf');
      }
      return await response.json();
    } catch (error) {
      console.error('Save actual benefit error:', error);
      throw error;
    }
  },

  getPaymentSlipPdfUrl(ideaId, employeeCode) {
    const qs = new URLSearchParams({ employee_code: (employeeCode || '').trim().toUpperCase() });
    return `${API_BASE}/payments/slips/idea/${ideaId}/pdf?${qs.toString()}`;
  },

  async getRegisterBonuses(employeeCode) {
    try {
      const qs = new URLSearchParams({ employee_code: (employeeCode || '').trim().toUpperCase() });
      const response = await fetch(`${API_BASE}/payments/register-bonuses?${qs.toString()}`);
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Không tải được danh sách chi thưởng');
      }
      return await response.json();
    } catch (error) {
      console.error('Get register bonuses error:', error);
      throw error;
    }
  },

  async settleRegisterBonus(ideaId, employeeCode, paid) {
    try {
      const qs = new URLSearchParams({
        employee_code: (employeeCode || '').trim().toUpperCase(),
        paid: paid ? 'true' : 'false',
      });
      const response = await fetch(`${API_BASE}/payments/register-bonuses/${ideaId}/settle?${qs.toString()}`, {
        method: 'POST',
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Không cập nhật được trạng thái chi thưởng');
      }
      return await response.json();
    } catch (error) {
      console.error('Settle register bonus error:', error);
      throw error;
    }
  },

  async createRewardBatch(payload) {
    try {
      const normalizedPayload = {
        ...payload,
        employee_code: (payload?.employee_code || '').trim().toUpperCase(),
      };
      const response = await fetch(`${API_BASE}/reward-batches/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(normalizedPayload),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Không tạo được đợt khen thưởng');
      }
      return await response.json();
    } catch (error) {
      console.error('Create reward batch error:', error);
      throw error;
    }
  },

  async listRewardBatches() {
    try {
      const response = await fetch(`${API_BASE}/reward-batches/`);
      if (!response.ok) throw new Error('Không tải được danh sách đợt khen thưởng');
      return await response.json();
    } catch (error) {
      console.error('List reward batches error:', error);
      throw error;
    }
  },

  async getRewardBatchCandidates(quarter, year) {
    try {
      const qs = new URLSearchParams({
        quarter: String(quarter),
        year: String(year),
      });
      const response = await fetch(`${API_BASE}/reward-batches/candidates?${qs.toString()}`);
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Không tải được danh sách ý tưởng đủ điều kiện');
      }
      return await response.json();
    } catch (error) {
      console.error('Get reward batch candidates error:', error);
      throw error;
    }
  },

  async getRewardBatchReport(batchId) {
    try {
      const response = await fetch(`${API_BASE}/reward-batches/${batchId}/report`);
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Không tải được báo cáo khen thưởng');
      }
      return await response.json();
    } catch (error) {
      console.error('Get reward batch report error:', error);
      throw error;
    }
  },

  async getScoreCriteria() {
    try {
      const response = await fetch(`${API_BASE}/scores/guide/criteria`);
      if (!response.ok) throw new Error('Kh\u00f4ng t\u1ea3i \u0111\u01b0\u1ee3c ti\u00eau ch\u00ed ch\u1ea5m \u0111i\u1ec3m');
      return await response.json();
    } catch (error) {
      console.error('Get score criteria error:', error);
      throw error;
    }
  },

  async listCriteriaSets(employeeCode) {
    try {
      const qs = new URLSearchParams({ employee_code: (employeeCode || '').trim().toUpperCase() });
      const response = await fetch(`${API_BASE}/scores/criteria-sets?${qs.toString()}`);
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Không tải được danh sách bộ tiêu chí');
      }
      return await response.json();
    } catch (error) {
      console.error('List criteria sets error:', error);
      throw error;
    }
  },

  async getCriteriaSet(criteriaSetId, employeeCode) {
    try {
      const qs = new URLSearchParams({ employee_code: (employeeCode || '').trim().toUpperCase() });
      const response = await fetch(`${API_BASE}/scores/criteria-sets/${criteriaSetId}?${qs.toString()}`);
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Không tải được bộ tiêu chí');
      }
      return await response.json();
    } catch (error) {
      console.error('Get criteria set error:', error);
      throw error;
    }
  },

  async createCriteriaSet(payload) {
    try {
      const normalizedPayload = {
        ...payload,
        employee_code: (payload?.employee_code || '').trim().toUpperCase(),
      };
      const response = await fetch(`${API_BASE}/scores/criteria-sets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(normalizedPayload),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Không tạo được bộ tiêu chí');
      }
      return await response.json();
    } catch (error) {
      console.error('Create criteria set error:', error);
      throw error;
    }
  },

  async updateCriteriaSet(criteriaSetId, payload) {
    try {
      const normalizedPayload = {
        ...payload,
        employee_code: (payload?.employee_code || '').trim().toUpperCase(),
      };
      const response = await fetch(`${API_BASE}/scores/criteria-sets/${criteriaSetId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(normalizedPayload),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Không cập nhật được bộ tiêu chí');
      }
      return await response.json();
    } catch (error) {
      console.error('Update criteria set error:', error);
      throw error;
    }
  },

  // Get categories
  getCategories() {
    return [
      { value: 'TOOLS', label: 'C\u00f4ng c\u1ee5 (C\u1eef g\u00e1, r\u00e1p form, ph\u1ee5 tr\u1ee3)' },
      { value: 'PROCESS', label: 'Ph\u01b0\u01a1ng ph\u00e1p quy tr\u00ecnh' },
      { value: 'DIGITIZATION', label: 'S\u1ed1 h\u00f3a' },
      { value: 'OTHER', label: 'Kh\u00e1c' },
    ];
  },
};

window.api = api;

// Helper: Show notification
function showNotification(message, type = 'success') {
  const notification = document.createElement('div');
  const bgColor = type === 'success' ? 'bg-green-500' : 'bg-red-500';
  notification.className = `fixed top-4 right-4 ${bgColor} text-white px-6 py-3 rounded-lg shadow-lg z-50`;
  notification.textContent = message;
  document.body.appendChild(notification);

  setTimeout(() => {
    notification.remove();
  }, 3000);
}

// Helper: Show loading
function showLoading(show = true, message = '\u0110ang x\u1eed l\u00fd...') {
  let loader = document.getElementById('loader');
  if (!loader && show) {
    loader = document.createElement('div');
    loader.id = 'loader';
    loader.className = 'fixed inset-0 bg-black/50 flex items-center justify-center z-50';
    loader.innerHTML = `
      <div class="bg-white rounded-lg p-8 text-center">
        <div class="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full mx-auto mb-4"></div>
        <p id="loaderMessage" class="text-on-surface font-body-lg">${message}</p>
      </div>
    `;
    document.body.appendChild(loader);
  } else if (loader && show) {
    const messageEl = document.getElementById('loaderMessage');
    if (messageEl) {
      messageEl.textContent = message;
    }
  } else if (loader && !show) {
    loader.remove();
  }
}

