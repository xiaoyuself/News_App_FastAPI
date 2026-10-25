/**
 * 全局配置
 *
 * 两种场景自动切换，不用改代码：
 *   1) 本地开发：双击 index.html，或用 localhost / 127.0.0.1 打开 → 直连两个后端端口
 *   2) 服务器部署：通过公网 IP / 域名访问 → 接口走"同源"，由 nginx 转发给后端容器
 */
const IS_LOCAL_DEV =
  location.protocol === 'file:' ||
  location.hostname === 'localhost' ||
  location.hostname === '127.0.0.1';

const CONFIG = {
  // 主后端（FastAPI）：新闻列表、详情、用户、收藏、历史等接口
  API_BASE_URL: IS_LOCAL_DEV ? 'http://localhost:8000' : location.origin,

  // AI 智能客服服务地址（独立运行在 8001 端口）
  AI_BASE_URL: IS_LOCAL_DEV ? 'http://localhost:8001' : location.origin,

  // 每页新闻条数
  PAGE_SIZE: 10,
};
