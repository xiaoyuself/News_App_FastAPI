/**
 * 新闻详情视图：
 * - 右上角收藏按钮（需登录）
 * - 登录用户进入详情时自动记录浏览历史
 * - 底部展示同分类下浏览量最高的 5 条推荐新闻
 * 路由： #/news/:id
 */
window.DetailView = {
  newsId: null,
  isFav: false,

  async render(id) {
    this.newsId = id;
    setHeader({
      title: '新闻详情',
      showBack: true,
      onBack: () => Router.navigate('news'),
      right: `<button class="header-action fav-star" id="fav-btn" title="收藏">☆</button>`,
    });
    showTabBar(false);

    const main = document.getElementById('app-main');
    main.innerHTML = '<div class="loading">加载中...</div>';

    // 收藏按钮点击：登录后可切换收藏状态
    const favBtn = document.getElementById('fav-btn');
    if (favBtn) favBtn.addEventListener('click', () => this.toggleFavorite());

    try {
      const detail = await API.getNewsDetail(id);
      // 已登录用户浏览新闻 → 记录浏览历史（失败静默忽略）
      if (isLoggedIn()) {
        API.addHistory(id).catch(() => { /* 记录失败不影响浏览 */ });
      }
      // 已登录用户 → 查询当前新闻收藏状态
      if (isLoggedIn()) {
        this.isFav = await API.checkFavorite(id);
        this.updateFavIcon();
      }
      main.innerHTML = this.pageHtml(detail);
      this.bindRelated(detail.relatedNews);
    } catch (e) {
      main.innerHTML = '<div class="error">' + escapeHtml(e.message) + '</div>';
    }
  },

  pageHtml(detail) {
    const cover = detail.image
      ? `<img class="detail-cover" src="${escapeHtml(detail.image)}" alt="" onerror="this.onerror=null;this.src=window.placeholderImage('📰')">`
      : '';
    const related = detail.relatedNews.length
      ? detail.relatedNews.map((n, i) => `
          <div class="related-item" data-id="${n.id}">
            <div class="rank">${i + 1}</div>
            <div class="rt">${escapeHtml(n.title)}</div>
            <div class="rv">👁 ${formatViews(n.views)}</div>
          </div>`).join('')
      : '<div class="empty">暂无推荐</div>';

    return `
      <div class="detail-page">
        <h2 class="detail-title">${escapeHtml(detail.title)}</h2>
        <div class="detail-meta">
          <span>✍ ${escapeHtml(detail.author || '佚名')}</span>
          <span>🕒 ${escapeHtml(formatTime(detail.publishTime))}</span>
          <span class="views">👁 ${formatViews(detail.views)} 次浏览</span>
        </div>
        ${cover}
        <div class="detail-content">${escapeHtml(detail.content)}</div>

        <div class="related-section">
          <div class="related-title">同类推荐（同分类浏览量最高）</div>
          ${related}
        </div>
      </div>`;
  },

  bindRelated(list) {
    document.querySelectorAll('.related-item[data-id]').forEach(el => {
      el.addEventListener('click', () => {
        Router.navigate('news/' + el.dataset.id);
      });
    });
  },

  /** 收藏状态图标 */
  updateFavIcon() {
    const favBtn = document.getElementById('fav-btn');
    if (favBtn) favBtn.textContent = this.isFav ? '★' : '☆';
  },

  /** 点击收藏按钮：未登录提示登录；已登录切换收藏 */
  async toggleFavorite() {
    if (!isLoggedIn()) {
      toast('请先登录后再收藏');
      setTimeout(() => Router.navigate('profile'), 700);
      return;
    }
    const favBtn = document.getElementById('fav-btn');
    if (favBtn) favBtn.disabled = true;
    try {
      if (this.isFav) {
        await API.removeFavorite(this.newsId);
        this.isFav = false;
        toast('已取消收藏');
      } else {
        await API.addFavorite(this.newsId);
        this.isFav = true;
        toast('收藏成功');
      }
      this.updateFavIcon();
    } catch (e) {
      toast(e.message);
    } finally {
      if (favBtn) favBtn.disabled = false;
    }
  },
};
