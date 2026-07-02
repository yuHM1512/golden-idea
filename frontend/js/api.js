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

function formatApiError(error, fallback) {
  const detail = error?.detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const path = Array.isArray(item?.loc) ? item.loc.join('.') : '';
        return [path, item?.msg].filter(Boolean).join(': ');
      })
      .filter(Boolean)
      .join('; ') || fallback;
  }
  if (detail && typeof detail === 'object') {
    return detail.message || JSON.stringify(detail);
  }
  return detail || fallback;
}

let ideaTaxonomyCache = null;

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
  async uploadAttachment(ideaId, file, attachmentType = 'after') {
    try {
      const sessionResponse = await fetch(`${API_BASE}/ideas/${ideaId}/upload-session`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          original_filename: file?.name || '',
          file_size: file?.size || 0,
          content_type: file?.type || 'application/octet-stream',
          attachment_type: attachmentType || 'after',
        }),
      });
      if (!sessionResponse.ok) {
        const error = await sessionResponse.json().catch(() => ({}));
        throw new Error(error.detail || `Không tạo được phiên tải file: ${file?.name || 'unknown file'}`);
      }

      const session = await sessionResponse.json();
      let driveFileId = '';
      let uploadFetchError = null;

      try {
        const uploadResponse = await fetch(session.session_url, {
          method: 'PUT',
          headers: {
            'Content-Type': file?.type || 'application/octet-stream',
          },
          body: file,
        });
        if (!uploadResponse.ok) {
          const rawError = await uploadResponse.text().catch(() => '');
          throw new Error(rawError || `Google Drive từ chối file: ${file?.name || 'unknown file'}`);
        }

        const uploadedMeta = await uploadResponse.json().catch(() => null);
        driveFileId = uploadedMeta?.id || '';
      } catch (error) {
        uploadFetchError = error;
      }

      const finalizeEndpoint = driveFileId
        ? `${API_BASE}/ideas/${ideaId}/attachments/complete`
        : `${API_BASE}/ideas/${ideaId}/attachments/complete-from-folder`;
      const finalizeResponse = await fetch(finalizeEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          drive_file_id: driveFileId,
          original_filename: file?.name || '',
          file_size: file?.size || 0,
          content_type: file?.type || 'application/octet-stream',
          attachment_type: attachmentType || 'after',
        }),
      });
      if (!finalizeResponse.ok) {
        const error = await finalizeResponse.json().catch(() => ({}));
        throw new Error(
          error.detail ||
          uploadFetchError?.message ||
          `Không thể ghi nhận file đã tải lên: ${file?.name || 'unknown file'}`
        );
      }

      return await finalizeResponse.json();
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

  async getIdeasByCategory(params = {}) {
    try {
      const qs = new URLSearchParams();
      Object.entries(params || {}).forEach(([k, v]) => {
        if (v === null || v === undefined || v === "") return;
        qs.set(k, String(v));
      });
      const suffix = qs.toString() ? `?${qs.toString()}` : "";
      const response = await fetch(`${API_BASE}/dashboard/ideas-by-category${suffix}`);
      if (!response.ok) throw new Error('Kh\u00f4ng t\u1ea3i \u0111\u01b0\u1ee3c chart data');
      return await response.json();
    } catch (error) {
      console.error('Ideas by category error:', error);
      throw error;
    }
  },

  async getReplicationsByUnit() {
    try {
      const response = await fetch(`${API_BASE}/dashboard/replications-by-unit`);
      if (!response.ok) throw new Error('Không tải được thống kê nhân rộng theo đơn vị');
      return await response.json();
    } catch (error) {
      console.error('Replications by unit error:', error);
      throw error;
    }
  },

  async getTopReplicatedIdeas(limit = 5) {
    try {
      const response = await fetch(`${API_BASE}/dashboard/top-replicated-ideas?limit=${encodeURIComponent(limit)}`);
      if (!response.ok) throw new Error('Không tải được thống kê top ý tưởng nhân rộng');
      return await response.json();
    } catch (error) {
      console.error('Top replicated ideas error:', error);
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

  async getLibraryIdeaDetail(ideaId, params = {}) {
    try {
      const qs = new URLSearchParams();
      Object.entries(params || {}).forEach(([k, v]) => {
        if (v === null || v === undefined || v === '') return;
        qs.set(k, String(v));
      });
      const suffix = qs.toString() ? `?${qs.toString()}` : '';
      const response = await fetch(`${API_BASE}/library/ideas/${ideaId}${suffix}`);
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

  async createStandardizedIdeaReplication(payload) {
    try {
      const response = await fetch(`${API_BASE}/library/replications`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...payload,
          employee_code: (payload?.employee_code || '').trim().toUpperCase(),
        }),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Không tạo được yêu cầu nhân rộng ý tưởng');
      }
      return await response.json();
    } catch (error) {
      console.error('Create standardized idea replication error:', error);
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

  async updateUser(employeeCode, payload) {
    try {
      const code = (employeeCode || '').trim().toUpperCase();
      const response = await fetch(`${API_BASE}/users/${encodeURIComponent(code)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Lỗi khi cập nhật user');
      }
      return await response.json();
    } catch (error) {
      console.error('Update user error:', error);
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

  async getMyIdeas(employeeCode) {
    try {
      const qs = new URLSearchParams({ employee_code: (employeeCode || '').trim().toUpperCase() });
      const response = await fetch(`${API_BASE}/reviews/mine?${qs.toString()}`);
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Không tải được danh sách ý tưởng của bạn');
      }
      return await response.json();
    } catch (error) {
      console.error('Get my ideas error:', error);
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

  async updateIeScore(ideaId, payload) {
    try {
      const normalizedPayload = {
        ...payload,
        employee_code: (payload?.employee_code || '').trim().toUpperCase(),
      };
      const response = await fetch(`${API_BASE}/reviews/${ideaId}/ie-score`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(normalizedPayload),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(formatApiError(error, 'Không cập nhật được nội dung chấm điểm Ban cải tiến'));
      }
      return await response.json();
    } catch (error) {
      console.error('Update IE score error:', error);
      throw error;
    }
  },

  async updateIeReview(ideaId, payload) {
    try {
      const normalizedPayload = {
        ...payload,
        employee_code: (payload?.employee_code || '').trim().toUpperCase(),
      };
      const response = await fetch(`${API_BASE}/reviews/${ideaId}/ie-review`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(normalizedPayload),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(formatApiError(error, 'Không cập nhật được duyệt cấp 2 của Ban cải tiến'));
      }
      return await response.json();
    } catch (error) {
      console.error('Update IE review error:', error);
      throw error;
    }
  },

  async approveBodRegisterSlip(ideaId, employeeCode) {
    try {
      const response = await fetch(`${API_BASE}/reviews/${ideaId}/register-slip-approval`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          employee_code: (employeeCode || '').trim().toUpperCase(),
        }),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Không duyệt được phiếu nhận tiền');
      }
      return await response.json();
    } catch (error) {
      console.error('Approve BOD register slip error:', error);
      throw error;
    }
  },

  async submitCouncilFinalScore(ideaId, payload) {
    try {
      const response = await fetch(`${API_BASE}/reviews/${ideaId}/council-final-score`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...payload,
          employee_code: (payload?.employee_code || '').trim().toUpperCase(),
        }),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Không lưu được điểm Hội đồng');
      }
      return await response.json();
    } catch (error) {
      console.error('Submit council final score error:', error);
      throw error;
    }
  },

  async getReplicationApprovalQueue(employeeCode) {
    try {
      const qs = new URLSearchParams({ employee_code: (employeeCode || '').trim().toUpperCase() });
      const response = await fetch(`${API_BASE}/reviews/replications/pending?${qs.toString()}`);
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Không tải được danh sách duyệt nhân rộng');
      }
      return await response.json();
    } catch (error) {
      console.error('Get replication approval queue error:', error);
      throw error;
    }
  },

  async approveReplication(replicationId, employeeCode) {
    try {
      const response = await fetch(`${API_BASE}/reviews/replications/${replicationId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          employee_code: (employeeCode || '').trim().toUpperCase(),
        }),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Không duyệt được nhân rộng ý tưởng');
      }
      return await response.json();
    } catch (error) {
      console.error('Approve replication error:', error);
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

  async settleRegisterBonus(ideaId, employeeCode, paid, payoutSlipCreatedOn = '') {
    try {
      const qs = new URLSearchParams({
        employee_code: (employeeCode || '').trim().toUpperCase(),
        paid: paid ? 'true' : 'false',
      });
      if (payoutSlipCreatedOn) {
        qs.set('payout_slip_created_on', payoutSlipCreatedOn);
      }
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

  getRewardBatchMinutesPdfUrl(batchId, employeeCode) {
    const qs = new URLSearchParams({ employee_code: (employeeCode || '').trim().toUpperCase() });
    return `${API_BASE}/reward-batches/${batchId}/minutes-pdf?${qs.toString()}`;
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

  async getAdminSettings(employeeCode) {
    try {
      const qs = new URLSearchParams({ employee_code: (employeeCode || '').trim().toUpperCase() });
      const response = await fetch(`${API_BASE}/settings/admin?${qs.toString()}`);
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Không tải được cấu hình admin');
      }
      return await response.json();
    } catch (error) {
      console.error('Get admin settings error:', error);
      throw error;
    }
  },

  async getLaborSecondPrices(employeeCode) {
    try {
      const qs = new URLSearchParams({ employee_code: (employeeCode || '').trim().toUpperCase() });
      const response = await fetch(`${API_BASE}/settings/labor-second-prices?${qs.toString()}`);
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Không tải được cấu hình đơn giá giây');
      }
      return await response.json();
    } catch (error) {
      console.error('Get labor second prices error:', error);
      throw error;
    }
  },

  async updateLaborSecondPrices(employeeCode, items) {
    try {
      const response = await fetch(`${API_BASE}/settings/labor-second-prices`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          employee_code: (employeeCode || '').trim().toUpperCase(),
          items: Array.isArray(items) ? items : [],
        }),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Không cập nhật được cấu hình đơn giá giây');
      }
      return await response.json();
    } catch (error) {
      console.error('Update labor second prices error:', error);
      throw error;
    }
  },

  async updateEmailAutomation(employeeCode, enabled) {
    try {
      const response = await fetch(`${API_BASE}/settings/admin/email-automation`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          employee_code: (employeeCode || '').trim().toUpperCase(),
          enabled: Boolean(enabled),
        }),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Không cập nhật được trạng thái gửi email');
      }
      return await response.json();
    } catch (error) {
      console.error('Update email automation error:', error);
      throw error;
    }
  },

  async getIdeaTaxonomy(forceRefresh = false) {
    try {
      if (!forceRefresh && ideaTaxonomyCache) {
        return ideaTaxonomyCache;
      }
      const response = await fetch(`${API_BASE}/settings/idea-taxonomy`);
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Không tải được cấu hình chủ đề ý tưởng');
      }
      ideaTaxonomyCache = await response.json();
      return ideaTaxonomyCache;
    } catch (error) {
      console.error('Get idea taxonomy error:', error);
      throw error;
    }
  },

  async updateIdeaTaxonomy(employeeCode, payload) {
    try {
      const response = await fetch(`${API_BASE}/settings/admin/idea-taxonomy`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          employee_code: (employeeCode || '').trim().toUpperCase(),
          categories: Array.isArray(payload?.categories) ? payload.categories : [],
          stages: Array.isArray(payload?.stages) ? payload.stages : [],
        }),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Không cập nhật được cấu hình chủ đề ý tưởng');
      }
      ideaTaxonomyCache = await response.json();
      return ideaTaxonomyCache;
    } catch (error) {
      console.error('Update idea taxonomy error:', error);
      throw error;
    }
  },

  async hardDeleteIdea(ideaId, employeeCode) {
    try {
      const qs = new URLSearchParams({ employee_code: (employeeCode || '').trim().toUpperCase() });
      const response = await fetch(`${API_BASE}/settings/admin/ideas/${encodeURIComponent(ideaId)}?${qs.toString()}`, {
        method: 'DELETE',
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Không xóa được ý tưởng');
      }
      return await response.json();
    } catch (error) {
      console.error('Hard delete idea error:', error);
      throw error;
    }
  },

  async listAdminIdeas(employeeCode) {
    try {
      const qs = new URLSearchParams({ employee_code: (employeeCode || '').trim().toUpperCase() });
      const response = await fetch(`${API_BASE}/settings/admin/ideas?${qs.toString()}`);
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Không tải được danh sách ý tưởng');
      }
      return await response.json();
    } catch (error) {
      console.error('List admin ideas error:', error);
      throw error;
    }
  },

  async hardDeleteAllIdeas(employeeCode) {
    try {
      const qs = new URLSearchParams({ employee_code: (employeeCode || '').trim().toUpperCase() });
      const response = await fetch(`${API_BASE}/settings/admin/ideas?${qs.toString()}`, {
        method: 'DELETE',
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Không xóa được toàn bộ ý tưởng');
      }
      return await response.json();
    } catch (error) {
      console.error('Hard delete all ideas error:', error);
      throw error;
    }
  },

  async hardDeleteSelectedIdeas(employeeCode, ideaIds) {
    try {
      const response = await fetch(`${API_BASE}/settings/admin/ideas/bulk-delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          employee_code: (employeeCode || '').trim().toUpperCase(),
          idea_ids: Array.isArray(ideaIds) ? ideaIds : [],
        }),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Không xóa được các ý tưởng đã chọn');
      }
      return await response.json();
    } catch (error) {
      console.error('Hard delete selected ideas error:', error);
      throw error;
    }
  },

  // Get categories
  getCategories() {
    const categories = Array.isArray(ideaTaxonomyCache?.categories)
      ? ideaTaxonomyCache.categories
      : [
          { name: 'Số hoá', requires_stage: false },
          { name: 'Quy trình', requires_stage: true },
          { name: 'Thiết bị', requires_stage: true },
          { name: 'Phụ trợ', requires_stage: true },
          { name: 'Chuẩn bị', requires_stage: true },
          { name: 'Cử gá', requires_stage: true },
          { name: 'Form', requires_stage: true },
          { name: 'Thao tác', requires_stage: true },
        ];
    return categories.map((item) => ({
      value: item?.name || '',
      label: item?.name || '',
      requires_stage: item?.requires_stage !== false,
    })).filter((item) => item.value);
  },

  getIdeaStages() {
    return Array.isArray(ideaTaxonomyCache?.stages) ? ideaTaxonomyCache.stages : [];
  },

  categoryRequiresStage(categoryName) {
    const normalized = String(categoryName || '').trim();
    const categories = this.getCategories();
    const matched = categories.find((item) => item.value === normalized);
    return matched ? matched.requires_stage !== false : true;
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

