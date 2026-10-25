/**
 * 极简 hash 路由
 * 路由表：
 *   #/news               新闻列表（一级 Tab）
 *   #/news/:id           新闻详情（二级页，隐藏 Tab）
 *   #/ai                 AI 对话（一级 Tab）
 *   #/profile            个人中心（一级 Tab，未登录显示注册/登录）
 *   #/profile/edit       详细信息（二级页）
 *   #/profile/favorites  收藏列表（二级页）
 *   #/profile/history    浏览记录（二级页）
 *   #/profile/password   修改密码（二级页）
 */
const Router = {
  parse() {
    const hash = location.hash.replace(/^#\/?/, '');
    const parts = hash.split('/').filter(Boolean);
    return { path: parts[0] || 'news', id: parts[1] || null };
  },

  navigate(path) {
    location.hash = '#/' + path;
  },

  init() {
    window.addEventListener('hashchange', () => this.render());
    if (!location.hash || location.hash === '#/') {
      location.hash = '#/news';
      return; // hashchange 会触发 render
    }
    this.render();
  },

  render() {
    const { path, id } = this.parse();
    window.scrollTo(0, 0);
    switch (path) {
      case 'news':
        id ? DetailView.render(Number(id)) : NewsView.render();
        break;
      case 'ai':
        ChatView.render();
        break;
      case 'profile':
        ProfileView.render(id);
        break;
      default:
        location.hash = '#/news';
    }
  },
};
