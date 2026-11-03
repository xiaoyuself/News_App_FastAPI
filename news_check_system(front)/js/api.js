/**
 * API 请求层
 *
 * 鉴权说明：后端 utils/auth.py 现在既认标准 `Authorization: Bearer <token>`，
 * 也兼容历史遗留的"裸 token"（早期由于后端把 Bearer 拼成了 Beared，前端只能发裸 token）。
 * 这里统一发标准写法 Bearer，语义更正确，也方便以后换 JWT / 网关鉴权。
 */

const STORAGE_KEYS = { token: 'news_token', user: 'news_user' };

function getToken() { return Store.get(STORAGE_KEYS.token); }
function getUserInfo() { return Store.get(STORAGE_KEYS.user) || null; }
function isLoggedIn() { return !!getToken(); }

/** 登录/注册成功后保存 token 和用户信息 */
function setAuth(token, userInfo) {
  Store.set(STORAGE_KEYS.token, token);
  Store.set(STORAGE_KEYS.user, userInfo);
}

/** 退出登录 / token 失效时清除本地登录态 */
function clearAuth() {
  Store.remove(STORAGE_KEYS.token);
  Store.remove(STORAGE_KEYS.user);
}

/** 构造认证请求头：标准 Bearer 写法 */
function authHeaders() {
  const token = getToken();
  return token ? { Authorization: 'Bearer ' + token } : {};
}

/**
 * 从错误响应里取出"人能看懂"的提示。
 * 后端业务错误是 { code, message, data }；
 * 参数校验失败(422) 是 { code, message, data }（后端已统一），
 * 但为兼容 FastAPI 原生格式，也支持 detail 为字符串或数组的情况。
 */
function errorMessage(json, status) {
  if (!json) return `请求失败（HTTP ${status}）`;
  if (typeof json.message === 'string' && json.message) return json.message;
  if (typeof json.detail === 'string' && json.detail) return json.detail;
  if (Array.isArray(json.detail)) {
    const parts = json.detail.map(d => {
      const loc = Array.isArray(d.loc)
        ? d.loc.filter(x => x !== 'body' && x !== 'query' && x !== 'path').join('.')
        : '';
      return loc ? `${loc}：${d.msg}` : d.msg;
    }).filter(Boolean);
    if (parts.length) return parts.join('；');
  }
  return `请求失败（HTTP ${status}）`;
}

/**
 * 统一请求
 * @param {string} path 如 '/api/news/list'
 * @param {object} options { method, params(查询参数), body(JSON 对象), auth(是否需要token) }
 */
async function request(path, options = {}) {
  const { method = 'GET', params, body, auth = true } = options;
  const url = new URL(CONFIG.API_BASE_URL + path);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, v);
    });
  }

  const headers = { 'Content-Type': 'application/json' };
  if (auth) Object.assign(headers, authHeaders());

  let res;
  try {
    res = await fetch(url.toString(), {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (e) {
    throw new Error('无法连接服务器，请确认后端已启动（' + CONFIG.API_BASE_URL + '）');
  }

  let json = null;
  try { json = await res.json(); } catch (e) { /* 非 JSON 响应 */ }

  // HTTP 层错误
  // 注意：本后端注册了自定义异常处理器（utils/exception.py），错误响应格式为
  //   { code, message, data }（不是标准 FastAPI 的 { detail }），因此优先取 message，其次 detail。
  if (!res.ok) {
    const msg = errorMessage(json, res.status);
    // 仅当"带着 token 访问受保护接口"（auth=true）返回 401 时，才视为会话过期；
    // 登录/注册接口（auth=false）返回 401 属于"用户名或密码错误"，直接展示后端提示即可，
    // 否则会出现"点击登录没反应/被当成登录过期"的误导。
    if (res.status === 401 && auth) {
      clearAuth();
      toast('登录已过期，请重新登录');
      setTimeout(() => { location.hash = '#/profile'; }, 600);
    }
    throw new Error(msg);
  }

  // 业务层错误
  if (json && json.code !== 200) {
    throw new Error(errorMessage(json, res.status));
  }

  return json ? json.data : null;
}

/* ============================ 数据归一化 ============================ */

/** 新闻列表项：新闻列表接口返回 snake_case（publish_time/category_id），
 *  收藏/历史列表接口返回 camelCase（publishedTime/categoryId），统一转成同一结构。
 *  注意：通过展开保留收藏/历史列表特有的字段（favoriteTime / viewTime / historyId 等）。 */
function normalizeNewsItem(item) {
  return {
    ...item,
    id: item.id,
    title: item.title || '',
    description: item.description || '',
    image: item.image || '',
    author: item.author || '',
    categoryId: item.category_id ?? item.categoryId ?? null,
    views: item.views ?? 0,
    publishTime: item.publish_time ?? item.publishTime ?? item.publishedTime ?? null,
  };
}

/* ============================ 新闻接口 ============================ */

/** 获取新闻分类列表 */
async function getCategories() {
  const data = await request('/api/news/categories', { auth: false });
  return (data || []).map(c => ({ id: c.id, name: c.name }));
}

/** 获取某分类下的新闻列表（分页） */
async function getNewsList(categoryId, page, pageSize = CONFIG.PAGE_SIZE) {
  const data = await request('/api/news/list', {
    auth: false,
    params: { categoryId, page, pageSize },
  });
  return {
    list: (data.list || []).map(normalizeNewsItem),
    total: data.total || 0,
    hasMore: !!data.hasMore,
  };
}

/** 获取新闻详情（后端会同时返回同分类浏览量最高的 5 条推荐） */
async function getNewsDetail(id) {
  const d = await request('/api/news/detail', { auth: false, params: { id } });
  return {
    id: d.id,
    title: d.title || '',
    content: d.content || '',
    image: d.image || '',
    author: d.author || '',
    publishTime: d.publishTime || null,
    categoryId: d.categoryId ?? null,
    views: d.views ?? 0,
    relatedNews: (d.relatedNews || []).map(normalizeNewsItem),
  };
}

/* ============================ 用户接口 ============================ */

/** 注册（用户名唯一，注册成功返回 token） */
async function register(username, password) {
  const data = await request('/api/user/register', { auth: false, method: 'POST', body: { username, password } });
  return data; // { token, userInfo }
}

/** 登录 */
async function login(username, password) {
  const data = await request('/api/user/login', { auth: false, method: 'POST', body: { username, password } });
  return data; // { token, userInfo }
}

/** 获取当前登录用户信息 */
async function getUserInfoRemote() {
  return await request('/api/user/info');
}

/** 更新用户资料（昵称/头像/性别/个性签名/手机号） */
async function updateUser(payload) {
  return await request('/api/user/update', { method: 'PUT', body: payload });
}

/** 修改密码（原密码 + 新密码） */
async function changePassword(oldPassword, newPassword) {
  return await request('/api/user/password', {
    method: 'PUT',
    body: { oldPassword, newPassword },
  });
}

/* ============================ 收藏接口 ============================ */

/** 检查某条新闻是否已收藏 */
async function checkFavorite(newsId) {
  const data = await request('/api/favorite/check', { params: { newId: newsId } });
  return !!data.isFavorite;
}

/** 添加收藏 */
async function addFavorite(newsId) {
  return await request('/api/favorite/add', { method: 'POST', body: { newsId } });
}

/** 取消收藏（后端是 DELETE 方法，这里必须显式指定，否则会发成 GET -> 405 Method Not Allowed） */
async function removeFavorite(newsId) {
  return await request('/api/favorite/remove', { method: 'DELETE', params: { newsId } });
}

/** 收藏列表（分页） */
async function getFavoriteList(page, pageSize = CONFIG.PAGE_SIZE) {
  const data = await request('/api/favorite/list', { params: { page, pageSize } });
  return {
    list: (data.list || []).map(normalizeNewsItem),
    total: data.total || 0,
    hasMore: !!data.hasMore,
  };
}

/** 清空收藏 */
async function clearFavorites() {
  return await request('/api/favorite/clear', { method: 'DELETE' });
}

/* ============================ 浏览历史接口 ============================ */

/** 添加浏览记录（登录状态下进入详情页时调用） */
async function addHistory(newsId) {
  return await request('/api/history/add', { method: 'POST', body: { newsId } });
}

/** 浏览历史列表（分页） */
async function getHistoryList(page, pageSize = CONFIG.PAGE_SIZE) {
  const data = await request('/api/history/list', { params: { page, pageSize } });
  return {
    list: (data.list || []).map(normalizeNewsItem),
    total: data.total || 0,
    hasMore: !!data.hasMore,
  };
}

/** 删除一条浏览记录（按历史记录自己的 id 删除，见后端 /api/history/delete/{history_id}） */
async function deleteHistory(historyId) {
  return await request('/api/history/delete/' + historyId, { method: 'DELETE' });
}

/** 清空浏览记录 */
async function clearHistory() {
  return await request('/api/history/clear', { method: 'DELETE' });
}

/* ============================ AI 智能客服接口 ============================ */

/** AI 请求超时（毫秒）：覆盖首次知识库构建（最长 120s）+ 问答（90s）的余量 */
const AI_CHAT_TIMEOUT = 130000;

/**
 * 向智能客服发送问题（支持多轮）
 * @param {string} question 本轮问题
 * @param {Array} history 最近几轮对话 [{role:'user'|'assistant', content:'...'}]
 *                        只放问答内容，不要放检索片段（片段由服务端每轮重新检索）
 */
async function chat(question, history) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), AI_CHAT_TIMEOUT);
  let res;
  try {
    res = await fetch(CONFIG.AI_BASE_URL + '/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, history: history || [] }),
      signal: controller.signal,
    });
  } catch (e) {
    throw new Error(e && e.name === 'AbortError' ? '请求超时，请稍后重试' : 'AI 服务未连接');
  } finally {
    clearTimeout(timer);
  }
  let json = null;
  try { json = await res.json(); } catch (e) { /* ignore */ }
  if (!res.ok || !json || json.code !== 200) {
    throw new Error((json && json.message) || 'AI 服务响应异常');
  }
  return json.data ? json.data.answer : '';
}

/* 统一导出 */
const API = {
  getCategories,
  getNewsList,
  getNewsDetail,
  register,
  login,
  getUserInfoRemote,
  updateUser,
  changePassword,
  checkFavorite,
  addFavorite,
  removeFavorite,
  getFavoriteList,
  clearFavorites,
  addHistory,
  getHistoryList,
  deleteHistory,
  clearHistory,
  chat,
};
