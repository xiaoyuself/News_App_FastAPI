/**
 * 通用工具函数
 */

/** 轻提示（2.4 秒自动消失） */
function toast(message, duration = 2400) {
  const el = document.getElementById('toast');
  if (!el) return;
  el.textContent = message;
  el.classList.remove('hidden');
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => el.classList.add('hidden'), duration);
}

/** HTML 转义，防止 XSS */
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/** 日期格式化：'2024-01-01T12:00:00' / '2024-01-01 12:00:00' -> '2024-01-01 12:00' */
function formatTime(value) {
  if (!value) return '';
  const s = String(value).replace('T', ' ');
  const m = s.match(/^(\d{4}-\d{2}-\d{2})[ ](\d{2}:\d{2})/);
  return m ? `${m[1]} ${m[2]}` : s.slice(0, 16);
}

/** 浏览量格式化：12345 -> 1.2万 */
function formatViews(n) {
  const num = Number(n) || 0;
  if (num >= 10000) return (num / 10000).toFixed(1) + '万';
  return String(num);
}

/** localStorage 封装 */
const Store = {
  get(key) {
    try { return JSON.parse(localStorage.getItem(key)); } catch (e) { return null; }
  },
  set(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* ignore */ }
  },
  remove(key) {
    localStorage.removeItem(key);
  },
};

/** 空图片兜底：返回一个渐变色块 dataURL（用于无封面图的新闻/头像） */
function placeholderImage(text) {
  // 纯前端生成简单的 SVG 占位图
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="200" height="150">` +
    `<rect width="200" height="150" fill="#e8edf2"/>` +
    `<text x="100" y="80" font-size="40" text-anchor="middle" fill="#b0bcc9">${escapeHtml(text)}</text></svg>`;
  return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
}

/** 头像兜底（首字母圆形） */
function avatarPlaceholder(name) {
  return (name || '客').slice(0, 1).toUpperCase();
}
