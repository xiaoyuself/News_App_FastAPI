/**
 * 新闻列表视图：顶部新闻分类 + 分类下的新闻列表（分页加载）
 * 路由： #/news
 */
window.NewsView = {
  state: {
    categories: [],
    activeCategoryId: null,
    page: 1,
    hasMore: false,
    loading: false,
  },

  async render() {
    setHeader({ title: '新闻', showBack: false, right: '' });
    showTabBar(true);
    setTabActive('news');

    const main = document.getElementById('app-main');
    main.innerHTML = '<div class="loading">加载中...</div>';

    try {
      // 加载分类
      const categories = await API.getCategories();
      this.state.categories = categories;

      // 默认选中第一个分类；若上次选中的分类仍存在则沿用
      if (!this.state.activeCategoryId ||
          !categories.some(c => c.id === this.state.activeCategoryId)) {
        this.state.activeCategoryId = categories.length ? categories[0].id : null;
      }

      this.state.page = 1;
      this.state.hasMore = false;
      this.renderShell();

      if (this.state.activeCategoryId != null) {
        await this.loadMore(true);
      } else {
        document.getElementById('news-list').innerHTML = '<div class="empty">暂无新闻分类</div>';
      }
    } catch (e) {
      main.innerHTML = '<div class="error">' + escapeHtml(e.message) + '</div>';
    }
  },

  /** 渲染分类栏 + 列表骨架 */
  renderShell() {
    const main = document.getElementById('app-main');
    const chips = this.state.categories.map(c =>
      `<div class="chip ${c.id === this.state.activeCategoryId ? 'active' : ''}" data-cid="${c.id}">${escapeHtml(c.name)}</div>`
    ).join('');

    main.innerHTML = `
      <div class="category-bar">${chips}</div>
      <div class="news-list" id="news-list"></div>
      <button class="load-more hidden" id="load-more-btn">加载更多</button>
    `;

    // 分类点击
    main.querySelectorAll('.chip').forEach(el => {
      el.addEventListener('click', () => this.switchCategory(Number(el.dataset.cid)));
    });
    // 加载更多
    document.getElementById('load-more-btn').addEventListener('click', () => this.loadMore());

    // 新闻卡片点击（事件委托，避免重复绑定）
    document.getElementById('news-list').addEventListener('click', (e) => {
      const card = e.target.closest('.news-card[data-id]');
      if (card) Router.navigate('news/' + card.dataset.id);
    });
  },

  /** 切换分类：重置分页并重新加载 */
  async switchCategory(categoryId) {
    if (categoryId === this.state.activeCategoryId) return;
    this.state.activeCategoryId = categoryId;
    this.state.page = 1;
    this.state.hasMore = false;

    // 更新分类高亮
    document.querySelectorAll('.chip').forEach(el => {
      el.classList.toggle('active', Number(el.dataset.cid) === categoryId);
    });
    document.getElementById('news-list').innerHTML = '<div class="loading">加载中...</div>';

    await this.loadMore(true);
  },

  /** 分页加载新闻列表 */
  async loadMore(reset = false) {
    if (this.state.loading) return;
    this.state.loading = true;

    const listEl = document.getElementById('news-list');
    const btn = document.getElementById('load-more-btn');
    if (!listEl) { this.state.loading = false; return; }

    if (reset) listEl.innerHTML = '<div class="loading">加载中...</div>';

    try {
      const { list, hasMore } = await API.getNewsList(this.state.activeCategoryId, this.state.page);
      if (reset) listEl.innerHTML = '';

      if (list.length === 0 && reset) {
        listEl.innerHTML = '<div class="empty">该分类暂无新闻</div>';
        if (btn) btn.classList.add('hidden');
      } else {
        listEl.insertAdjacentHTML('beforeend', list.map(item => this.cardHtml(item)).join(''));
        this.state.hasMore = hasMore;
        if (btn) btn.classList.toggle('hidden', !hasMore);
      }
      this.state.page += 1;
    } catch (e) {
      listEl.innerHTML = '<div class="error">' + escapeHtml(e.message) + '</div>';
    } finally {
      this.state.loading = false;
    }
  },

  cardHtml(item) {
    const cover = item.image
      ? `<img class="news-cover" src="${escapeHtml(item.image)}" alt="" onerror="this.onerror=null;this.src=window.placeholderImage('📰')">`
      : `<div class="news-cover" style="display:flex;align-items:center;justify-content:center;font-size:30px;">📰</div>`;
    return `
      <div class="news-card" data-id="${item.id}">
        ${cover}
        <div class="news-body">
          <div class="news-title">${escapeHtml(item.title)}</div>
          <div class="news-desc">${escapeHtml(item.description)}</div>
          <div class="news-meta">
            <span>${escapeHtml(item.author || '佚名')}</span>
            <span>${escapeHtml(formatTime(item.publishTime))}</span>
            <span class="views">👁 ${formatViews(item.views)}</span>
          </div>
        </div>
      </div>`;
  },
};
