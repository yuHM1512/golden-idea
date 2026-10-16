let report = { summary: [], items: [] };
let currentUser = null;
const K1_CODES = ['A1', 'A2', 'A3'];
const K2_CODES = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6'];
const K3_CODES = Array.from({ length: 14 }, (_, index) => `C${index + 1}`);
const CRITERIA_CODES = [...K1_CODES, ...K2_CODES, ...K3_CODES];
const CLASSIFICATION_LABELS = { unit: 'Đơn vị tự xét', company: 'Công ty xét', not_considered: 'Không xét', pending: 'Chờ xét' };
const REPORT_ROLES = new Set(['admin', 'ie_manager', 'digital_manager', 'bod_manager']);
const byId = (id) => document.getElementById(id);
const safe = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
const number = (value) => Number(value || 0).toLocaleString('vi-VN');
const optionalNumber = (value) => value == null ? '—' : number(value);
const annualPlan = (headcount, target) => target == null ? '—' : headcount == null ? number(target) : `${number(headcount)} / ${number(target)}`;
const periodLabel = (quarter, year) => quarter && year ? `Q${quarter}/${year}` : '—';
const classificationLabel = (value) => CLASSIFICATION_LABELS[value] || '—';
const dateLabel = (value) => {
  if (!value) return '—';
  const date = new Date(/(Z|[+-]\d{2}:?\d{2})$/.test(value) ? value : `${value}Z`);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleDateString('vi-VN', { timeZone: 'Asia/Bangkok' });
};

function notify(message, error = false) {
  const element = byId('message');
  element.textContent = message;
  element.className = `rounded-2xl px-5 py-3 text-sm font-semibold ${error ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'}`;
}

function renderCriteriaHeaders() {
  const cellClass = (code) => code.startsWith('A') ? 'bg-blue-50 text-blue-900' : code.startsWith('B') ? 'bg-cyan-50 text-cyan-900' : 'bg-amber-50 text-amber-900';
  byId('criteriaHeaderCodes').innerHTML = CRITERIA_CODES.map((code) => `<th class="border-l border-white px-2 py-2 text-center ${cellClass(code)}">${code}</th>`).join('');
}

function renderSummary() {
  const rows = report.summary || [];
  byId('summaryBody').innerHTML = rows.length ? rows.map((row) => `
    <tr class="hover:bg-slate-50"><td class="px-5 py-3 font-semibold">${safe(row.unit_name)}</td><td class="number px-4 py-3 text-right">${annualPlan(row.annual_headcount, row.annual_target)}</td><td class="number px-4 py-3 text-right font-bold">${number(row.idea_count)}</td><td class="number px-4 py-3 text-right">${number(row.unit_review_count)}</td><td class="number px-4 py-3 text-right">${number(row.company_review_count)}</td><td class="number px-4 py-3 text-right">${row.company_scored_count ? number(row.company_score) : '—'}</td><td class="number px-5 py-3 text-right">${row.benefit_count ? number(row.benefit_value) : '—'}</td></tr>`).join('') : '<tr><td colspan="7" class="px-5 py-8 text-center text-slate-500">Chưa có dữ liệu trong kỳ này.</td></tr>';
  const sum = (key) => rows.reduce((total, row) => total + Number(row[key] || 0), 0);
  const planned = rows.filter(row => row.annual_target != null);
  byId('summaryFoot').innerHTML = `<tr><td class="px-5 py-4">Tổng cộng</td><td class="number px-4 py-4 text-right">${planned.length ? annualPlan(planned.every(row => row.annual_headcount != null) ? sum('annual_headcount') : null, sum('annual_target')) : '—'}</td><td class="number px-4 py-4 text-right">${number(sum('idea_count'))}</td><td class="number px-4 py-4 text-right">${number(sum('unit_review_count'))}</td><td class="number px-4 py-4 text-right">${number(sum('company_review_count'))}</td><td class="number px-4 py-4 text-right">${rows.some(row => row.company_scored_count) ? number(sum('company_score')) : '—'}</td><td class="number px-5 py-4 text-right">${rows.some(row => row.benefit_count) ? number(sum('benefit_value')) : '—'}</td></tr>`;
  byId('totalIdeas').textContent = number(sum('idea_count'));
  byId('companyIdeas').textContent = number(sum('company_review_count'));
  byId('companyScore').textContent = rows.some(row => row.company_scored_count) ? number(sum('company_score')) : '—';
}

function criteriaCells(item) {
  const scores = item.criteria_scores || {};
  return CRITERIA_CODES.map((code) => {
    const color = code.startsWith('A') ? 'bg-blue-50/30' : code.startsWith('B') ? 'bg-cyan-50/30' : 'bg-amber-50/30';
    const value = Object.prototype.hasOwnProperty.call(scores, code) ? number(scores[code]) : '—';
    return `<td class="number border-l border-slate-100 px-2 py-3 text-center ${color}">${value}</td>`;
  }).join('');
}

function renderDetail() {
  const term = byId('search').value.trim().toLocaleLowerCase('vi-VN');
  const rows = (report.items || []).filter((item) => [item.idea_id, item.title, item.full_name, item.employee_code, item.unit_name].some((value) => String(value ?? '').toLocaleLowerCase('vi-VN').includes(term)));
  byId('detailBody').innerHTML = rows.length ? rows.map((item) => `
    <tr class="hover:bg-blue-50/50"><td class="whitespace-nowrap px-4 py-3">${safe(dateLabel(item.submitted_at))}</td><td class="max-w-[320px] px-3 py-3"><span class="font-bold text-[#002b73]">#${item.idea_id}</span><span class="ml-2 text-slate-500">${safe(item.product_code || '')}</span><div class="mt-1 line-clamp-2 font-semibold">${safe(item.title)}</div></td><td class="px-3 py-3">${safe(item.full_name)}<div class="text-slate-500">${safe(item.employee_code || '')}</div></td><td class="px-3 py-3">${safe(item.unit_name)}</td><td class="px-3 py-3">${classificationLabel(item.classification)}</td>${criteriaCells(item)}<td class="number px-3 py-3 text-right font-semibold">${optionalNumber(item.ie_score)}</td><td class="number px-3 py-3 text-right font-semibold">${optionalNumber(item.council_score)}</td><td class="number px-3 py-3 text-right">${optionalNumber(item.benefit_value)}</td><td class="px-4 py-3"><span class="font-bold">${safe(periodLabel(item.report_quarter, item.report_year))}</span>${item.period_note ? `<div class="mt-1 max-w-40 break-words text-slate-500" title="${safe(item.period_note)}">${safe(item.period_note)}</div>` : ''}</td></tr>`).join('') : '<tr><td colspan="32" class="px-5 py-8 text-center text-slate-500">Không tìm thấy ý tưởng phù hợp.</td></tr>';
  byId('detailCount').textContent = `Hiển thị ${rows.length} / ${(report.items || []).length} ý tưởng`;
}

async function loadReport() {
  const year = Number(byId('year').value);
  const quarter = Number(byId('quarter').value);
  if (!Number.isInteger(year) || year < 2020 || year > 2100) return notify('Năm phải từ 2020 đến 2100.', true);
  byId('refresh').disabled = true;
  try {
    report = await api.getQuarterlyReport(quarter, year, currentUser.employee_code);
    renderSummary(); renderDetail(); byId('message').classList.add('hidden');
  } catch (error) { notify(error.message || 'Không tải được báo cáo.', true); }
  finally { byId('refresh').disabled = false; }
}

const BORDER = { top: { style: 'thin', color: { argb: 'FFB7C9D6' } }, left: { style: 'thin', color: { argb: 'FFB7C9D6' } }, bottom: { style: 'thin', color: { argb: 'FFB7C9D6' } }, right: { style: 'thin', color: { argb: 'FFB7C9D6' } } };
function downloadBlob(filename, blob) {
  const url = URL.createObjectURL(blob); const anchor = document.createElement('a');
  anchor.href = url; anchor.download = filename; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function styleTitle(worksheet, lastColumn, title, subtitle) {
  worksheet.mergeCells(1, 1, 1, lastColumn); worksheet.getCell(1, 1).value = title;
  worksheet.getCell(1, 1).font = { name: 'Calibri', size: 16, bold: true, color: { argb: 'FFFFFFFF' } };
  worksheet.getCell(1, 1).alignment = { horizontal: 'center', vertical: 'middle' };
  worksheet.getCell(1, 1).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF1F4E78' } }; worksheet.getRow(1).height = 28;
  worksheet.mergeCells(2, 1, 2, lastColumn); worksheet.getCell(2, 1).value = subtitle;
  worksheet.getCell(2, 1).font = { italic: true, color: { argb: 'FF52606D' } }; worksheet.getCell(2, 1).alignment = { horizontal: 'center' };
}
function styleTable(worksheet, headerRows, firstDataRow) {
  worksheet.eachRow((row, rowNumber) => row.eachCell({ includeEmpty: true }, (cell) => {
    if (rowNumber >= headerRows[0]) cell.border = BORDER;
    if (rowNumber >= firstDataRow) { cell.alignment = { vertical: 'top', wrapText: true }; cell.font = { name: 'Calibri', size: 10 }; }
  }));
  headerRows.forEach((rowNumber) => { const row = worksheet.getRow(rowNumber); row.height = 28; row.font = { name: 'Calibri', size: 10, bold: true, color: { argb: 'FF1F1F1F' } }; row.alignment = { vertical: 'middle', horizontal: 'center', wrapText: true }; });
}

function makeSummarySheet(workbook, quarter, year) {
  const worksheet = workbook.addWorksheet('Mẫu 1 - Tổng hợp', { views: [{ state: 'frozen', ySplit: 4 }], pageSetup: { orientation: 'landscape', fitToPage: true, fitToWidth: 1, fitToHeight: 1 } });
  worksheet.columns = [{ width: 28 }, { width: 22 }, { width: 15 }, { width: 15 }, { width: 15 }, { width: 16 }, { width: 22 }];
  styleTitle(worksheet, 7, `BÁO CÁO KHEN THƯỞNG QUÝ ${quarter} NĂM ${year}`, 'Mẫu 1 · Tổng hợp theo đơn vị; kế hoạch sử dụng mục tiêu năm');
  worksheet.addRow([]); worksheet.addRow(['Đơn vị / nhóm', 'Kế hoạch năm\n(LĐTT / YTV)', 'YTV trong quý', 'Đơn vị tự xét', 'Công ty xét', 'Điểm Công ty', 'Hiệu quả thực tế (VND)']);
  (report.summary || []).forEach((row) => worksheet.addRow([row.unit_name, annualPlan(row.annual_headcount, row.annual_target), Number(row.idea_count || 0), Number(row.unit_review_count || 0), Number(row.company_review_count || 0), row.company_scored_count ? Number(row.company_score || 0) : null, row.benefit_count ? Number(row.benefit_value || 0) : null]));
  const rows = report.summary || []; const sum = (key) => rows.reduce((total, row) => total + Number(row[key] || 0), 0); const planned = rows.filter(row => row.annual_target != null);
  const totalRow = worksheet.addRow(['TỔNG CỘNG', planned.length ? annualPlan(planned.every(row => row.annual_headcount != null) ? sum('annual_headcount') : null, sum('annual_target')) : null, sum('idea_count'), sum('unit_review_count'), sum('company_review_count'), rows.some(row => row.company_scored_count) ? sum('company_score') : null, rows.some(row => row.benefit_count) ? sum('benefit_value') : null]);
  worksheet.getRow(4).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFD9EAF7' } }; totalRow.font = { bold: true, color: { argb: 'FF1F4E78' } }; totalRow.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFEAF3F8' } };
  styleTable(worksheet, [4], 5); [3, 4, 5, 6, 7].forEach((column) => { worksheet.getColumn(column).numFmt = '#,##0'; });
  worksheet.autoFilter = { from: { row: 4, column: 1 }, to: { row: 4, column: 7 } }; worksheet.pageSetup.margins = { left: 0.25, right: 0.25, top: 0.5, bottom: 0.5, header: 0.2, footer: 0.2 }; worksheet.pageSetup.printTitlesRow = '1:4';
}

function makeDetailSheet(workbook, quarter, year) {
  const metadataHeaders = ['Ngày gửi', 'Mã ý tưởng', 'Mã sản phẩm', 'Tên ý tưởng', 'Người đề xuất', 'Mã nhân viên', 'Đơn vị', 'Phân loại'];
  const trailingHeaders = ['Điểm BCT', 'Điểm Công ty', 'Hiệu quả (VND)', 'Quý', 'Năm', 'Lý do chuyển kỳ'];
  const headers = [...metadataHeaders, ...CRITERIA_CODES, ...trailingHeaders];
  const worksheet = workbook.addWorksheet('Mẫu 2 - Chi tiết điểm', { views: [{ state: 'frozen', xSplit: 8, ySplit: 5 }], pageSetup: { orientation: 'landscape', fitToPage: true, fitToWidth: 1, fitToHeight: 0 } });
  worksheet.columns = headers.map((header) => ({ width: header === 'Tên ý tưởng' ? 38 : header === 'Người đề xuất' || header === 'Lý do chuyển kỳ' ? 24 : header === 'Đơn vị' || header === 'Phân loại' ? 18 : /^[ABC]\d+$/.test(header) ? 6 : 13 }));
  styleTitle(worksheet, headers.length, `BẢNG CHI TIẾT ĐIỂM KHEN THƯỞNG QUÝ ${quarter} NĂM ${year}`, 'Mẫu 2 · Điểm thành phần K1, K2, K3 theo từng ý tưởng'); worksheet.addRow([]);
  const groupRow = worksheet.addRow([]); const headerRow = worksheet.addRow(headers); let start = 1;
  const groups = [[metadataHeaders.length, 'THÔNG TIN Ý TƯỞNG', 'FFD9EAF7'], [K1_CODES.length, 'K1 · TÍNH SÁNG TẠO', 'FFBDD7EE'], [K2_CODES.length, 'K2 · KHẢ NĂNG ÁP DỤNG', 'FFB7DEE8'], [K3_CODES.length, 'K3 · HIỆU QUẢ, GIÁ TRỊ LÀM LỢI', 'FFF8CBAD'], [trailingHeaders.length, 'KẾT QUẢ XÉT DUYỆT', 'FFD6DCE4']];
  groups.forEach(([length, label, color]) => { worksheet.mergeCells(4, start, 4, start + length - 1); const cell = groupRow.getCell(start); cell.value = label; cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: color } }; start += length; });
  (report.items || []).forEach((item) => { const scores = item.criteria_scores || {}; worksheet.addRow([dateLabel(item.submitted_at), item.idea_id, item.product_code || null, item.title, item.full_name, item.employee_code || null, item.unit_name, classificationLabel(item.classification), ...CRITERIA_CODES.map((code) => Object.prototype.hasOwnProperty.call(scores, code) ? Number(scores[code]) : null), item.ie_score == null ? null : Number(item.ie_score), item.council_score == null ? null : Number(item.council_score), item.benefit_value == null ? null : Number(item.benefit_value), item.report_quarter, item.report_year, item.period_note || null]); });
  const fills = [...metadataHeaders.map(() => 'FFD9EAF7'), ...K1_CODES.map(() => 'FFDCEBFA'), ...K2_CODES.map(() => 'FFD9F2F0'), ...K3_CODES.map(() => 'FFFFE8C2'), ...trailingHeaders.map(() => 'FFE2E8F0')];
  headerRow.eachCell((cell, column) => { cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: fills[column - 1] } }; }); styleTable(worksheet, [4, 5], 6);
  for (let column = metadataHeaders.length + 1; column <= headers.length - 3; column += 1) { worksheet.getColumn(column).numFmt = '#,##0'; worksheet.getColumn(column).alignment = { horizontal: 'center', vertical: 'top', wrapText: true }; }
  worksheet.autoFilter = { from: { row: 5, column: 1 }, to: { row: 5, column: headers.length } }; worksheet.pageSetup.margins = { left: 0.2, right: 0.2, top: 0.4, bottom: 0.4, header: 0.15, footer: 0.15 }; worksheet.pageSetup.printTitlesRow = '1:5';
}

async function exportExcel(kind) {
  if (typeof ExcelJS === 'undefined') return notify('Chưa tải được thư viện Excel. Hãy thử tải lại trang.', true);
  const button = byId(kind === 'summary' ? 'exportSummary' : 'exportDetail'); const original = button.textContent; button.disabled = true; button.textContent = 'Đang tạo file...';
  try {
    const quarter = Number(byId('quarter').value); const year = Number(byId('year').value); const workbook = new ExcelJS.Workbook(); workbook.creator = 'Golden Idea'; workbook.created = new Date();
    if (kind === 'summary') makeSummarySheet(workbook, quarter, year); else makeDetailSheet(workbook, quarter, year);
    const buffer = await workbook.xlsx.writeBuffer(); downloadBlob(`${kind === 'summary' ? 'tong-hop-khen-thuong' : 'chi-tiet-diem'}-Q${quarter}-${year}.xlsx`, new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }));
  } catch (error) { console.error(error); notify(error.message || 'Không tạo được file Excel.', true); }
  finally { button.disabled = false; button.textContent = original; }
}

async function init() {
  const employeeCode = (localStorage.getItem('employee_code') || '').trim().toUpperCase();
  if (localStorage.getItem('is_logged_in') !== 'true' || !employeeCode) return window.location.assign('/pages/login');
  try {
    currentUser = await api.getUserByCode(employeeCode);
    const roles = new Set([currentUser.role, ...(Array.isArray(currentUser.roles) ? currentUser.roles : [])].filter(Boolean));
    if (![...roles].some((role) => REPORT_ROLES.has(role))) return window.location.assign('/pages/menu');
    byId('whoami').textContent = `${currentUser.employee_code} · ${currentUser.full_name || ''}`; const now = new Date();
    const month = Number(new Intl.DateTimeFormat('en-US', { timeZone: 'Asia/Bangkok', month: 'numeric' }).format(now)); const year = Number(new Intl.DateTimeFormat('en-US', { timeZone: 'Asia/Bangkok', year: 'numeric' }).format(now));
    byId('quarter').innerHTML = [1, 2, 3, 4].map(q => `<option value="${q}">Quý ${q}</option>`).join(''); byId('quarter').value = Math.floor((month - 1) / 3) + 1; byId('year').value = year; renderCriteriaHeaders();
    byId('refresh').addEventListener('click', loadReport); byId('search').addEventListener('input', renderDetail); byId('exportSummary').addEventListener('click', () => exportExcel('summary')); byId('exportDetail').addEventListener('click', () => exportExcel('detail')); await loadReport();
  } catch (error) { notify(error.message || 'Không mở được báo cáo.', true); }
}
init();
