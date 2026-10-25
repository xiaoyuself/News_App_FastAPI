/**
 * API 请求层
 *
 * ⚠️ 重要说明（后端 Token 认证的坑）：
 * 后端 utils/auth.py 中提取 token 的代码是 authorization.replace("Beared", "")，
 * 并没有真正去掉 "Bearer " 前缀，所以前端不能发送标准的 "Bearer xxx"，
 * 而应直接发送原始 token（不带任何前缀），后端才能正确匹配。
 * 因此下面 authHeaders() 返回 { Authorization: token }（只有 token 本身）。
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

/** 构造认证请求头：直接带原始 token（不带 Bearer 前缀，见文件头注释） */
function authHeaders() {
  const token = getToken();
  return token ? { Authorization: token } : {};
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
    const msg = (json && (json.message || json.detail)) || `请求失败（HTTP ${res.status}）`;
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
    throw new Error(json.message || '请求失败');
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

/** 取消收藏 */
async function removeFavorite(newsId) {
  return await request('/api/favorite/remove', { params: { newsId } });
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

/** 删除一条浏览记录
 *  ⚠️ 注意：后端路由参数虽名为 history_id，但 crud 实际按 news_id 删除，
 *  所以这里传入新闻 id 即可正确删除对应记录 */
async function deleteHistory(newsId) {
  return await request('/api/history/delete/' + newsId, { method: 'DELETE' });
}

/** 清空浏览记录 */
async function clearHistory() {
  return await request('/api/history/clear', { method: 'DELETE' });
}

/* ============================ AI 智能客服接口 ============================ */

/** AI 请求超时（毫秒）：覆盖首次知识库构建（最长 120s）+ 问答（90s）的余量 */
const AI_CHAT_TIMEOUT = 130000;

/**
 * 向智能客服发送问题（预留的大模型调用接口）
 * 后端由 RAG_NEW/ai_server.py 提供（LangChain + Milvus RAG），默认端口 8001。
 * 带超时保护：AI 服务挂起时最多等待 AI_CHAT_TIMEOUT，超时抛错，不会一直"正在思考"。
 */
async function chat(question) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), AI_CHAT_TIMEOUT);
  let res;
  try {
    res = await fetch(CONFIG.AI_BASE_URL + '/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
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
