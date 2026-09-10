let currentUser = null;
let targetGroups = [];
let targetUnits = [];
let excludedUnits = [];
let editingGroupId = null;
let loadVersion = 0;

function logout() {
  localStorage.removeItem('is_logged_in');
  localStorage.removeItem('employee_code');
  window.location.href = '/pages/login';
}

function resetTargetForm(group = null) {
  editingGroupId = group?.id ?? null;
  document.getElementById('ideaTargetName').value = group?.name ?? '';
  document.getElementById('ideaTargetCount').value = group?.target_count ?? '';
  document.getElementById('ideaTargetHeadcount').value = group?.headcount ?? '';
  document.getElementById('ideaTargetPercent').value = group?.target_percent ?? '';
  document.getElementById('targetFormTitle').textContent = group ? `Chỉnh sửa: ${group.name}` : 'Thêm mục tiêu';
  const select = document.getElementById('ideaTargetUnit');
  select.replaceChildren();
  const occupied = new Set(targetGroups.filter(g => g.id !== editingGroupId).flatMap(g => g.unit_ids));
  targetUnits.filter(u => !excludedUnits.includes(u.id)).forEach(unit => {
    const option = new Option(unit.name + (occupied.has(unit.id) ? ' — đã thuộc nhóm khác' : ''), unit.id);
    option.disabled = occupied.has(unit.id);
    option.selected = group?.unit_ids.includes(unit.id) ?? false;
    select.add(option);
  });
}

function renderTargetGroups() {
  const body = document.getElementById('targetGroupRows');
  body.replaceChildren();
  targetGroups.forEach(group => {
    const tr = document.createElement('tr');
    [group.name, group.unit_ids.map(id => targetUnits.find(u => u.id === id)?.name ?? id).join(' + '),
      group.headcount ?? '—', group.target_count, group.target_percent === null ? '—' : `${group.target_percent}%`].forEach(value => {
      const td = document.createElement('td');
      td.className = 'px-4 py-3 border-b border-slate-100';
      td.textContent = value;
      tr.appendChild(td);
    });
    const td = document.createElement('td');
    const edit = document.createElement('button');
    edit.type = 'button';
    edit.className = 'px-4 py-2 text-blue-800 font-semibold';
    edit.textContent = 'Chỉnh sửa';
    edit.onclick = () => { resetTargetForm(group); document.getElementById('targetFormTitle').scrollIntoView({block:'center'}); };
    td.appendChild(edit);
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'px-3 py-2 text-red-700';
    remove.textContent = 'Xóa nhóm';
    remove.onclick = async () => {
      if (!confirm(`Xóa mục tiêu nhóm ${group.name}? Các đơn vị thành viên sẽ có thể được chọn cho nhóm khác. Dữ liệu ý tưởng vẫn được giữ nguyên.`)) return;
      remove.disabled = true;
      try {
        await api.deleteIdeaTargetGroup(currentUser.employee_code, group.id);
        await loadUnitIdeaTargets();
      } catch (error) { showNotification(error.message, 'error'); remove.disabled = false; }
    };
    td.appendChild(remove);
    tr.appendChild(td);
    body.appendChild(tr);
  });
  document.getElementById('targetTotals').textContent = `${targetGroups.length} nhóm • LĐTT: ${targetGroups.reduce((n, g) => n + (g.headcount ?? 0), 0).toLocaleString('vi-VN')} • Tổng mục tiêu: ${targetGroups.reduce((n, g) => n + g.target_count, 0)}`;
  document.getElementById('targetExclusions').textContent = excludedUnits.length
    ? `Không theo dõi mục tiêu năm này: ${targetUnits.filter(u => excludedUnits.includes(u.id)).map(u => u.name).join(', ')} (ngừng hoạt động).` : '';
}

async function loadUnitIdeaTargets() {
  const version = ++loadVersion;
  const year = Number(document.getElementById('ideaTargetYear').value);
  document.getElementById('targetFields').disabled = true;
  targetGroups = [];
  excludedUnits = [];
  resetTargetForm();
  renderTargetGroups();
  if (!Number.isInteger(year) || year < 2000 || year > 2100) return;
  try {
    const result = await api.getUnitIdeaTargets(currentUser.employee_code, year);
    if (version !== loadVersion) return;
    targetGroups = result.items;
    excludedUnits = result.excluded_unit_ids || [];
    resetTargetForm();
    renderTargetGroups();
    document.getElementById('targetFields').disabled = false;
  } catch (error) {
    if (version === loadVersion) showNotification(error.message, 'error');
  }
}

async function saveUnitIdeaTarget(event) {
  event.preventDefault();
  const year = document.getElementById('ideaTargetYear');
  const optionalNumber = id => document.getElementById(id).value === '' ? null : Number(document.getElementById(id).value);
  const payload = {
    employee_code: currentUser.employee_code, year: Number(year.value), group_id: editingGroupId,
    name: document.getElementById('ideaTargetName').value.trim(),
    unit_ids: [...document.getElementById('ideaTargetUnit').selectedOptions].map(o => Number(o.value)),
    target_count: Number(document.getElementById('ideaTargetCount').value),
    headcount: optionalNumber('ideaTargetHeadcount'), target_percent: optionalNumber('ideaTargetPercent'),
  };
  if (!payload.name || !payload.unit_ids.length) return;
  document.getElementById('targetFields').disabled = true;
  year.disabled = true;
  try {
    await api.updateIdeaTargetGroup(payload);
    showNotification('Đã lưu mục tiêu của nhóm đơn vị', 'success');
    await loadUnitIdeaTargets();
  } catch (error) {
    showNotification(error.message, 'error');
    document.getElementById('targetFields').disabled = false;
  } finally {
    year.disabled = false;
  }
}

async function init() {
  if (localStorage.getItem('is_logged_in') !== 'true') { location.href = '/pages/login'; return; }
  currentUser = await api.getUserByCode((localStorage.getItem('employee_code') || '').trim());
  if (!currentUser || !['admin', 'ie_manager'].includes(currentUser.role)) { location.href = '/pages/menu'; return; }
  targetUnits = await api.getUnits();
  document.getElementById('ideaTargetYear').value = new Intl.DateTimeFormat('en-CA', {timeZone:'Asia/Bangkok', year:'numeric'}).format(new Date());
  await loadUnitIdeaTargets();
}
init().catch(error => showNotification(error.message, 'error'));
