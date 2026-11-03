/**
 * 新闻列表视图：顶部新闻分类 + 分类下的新闻列表（分页加载）
 * 路由： #/news
 *
 * 体验说明：
 *  - 从详情页返回时直接复用上次的列表和滚动位置，不会又跳回第一页（原来每次返回都会重新拉第 1 页）
 *  - 加载失败时给出"重试"按钮，而不是只有一行报错
 */
window.NewsView = {
  state: {
    categories: [],
    activeCategoryId: null,
    page: 1,
    hasMore: false,
    loading: false,
    cards: [],      // 已经加载到的新闻（用于返回时还原）
    total: 0,
    scrollY: 0,     // 点击进入详情前的滚动位置
  },

  async render() {
    setHeader({ title: '新闻', showBack: false, right: '' });
    showTabBar(true);
    setTabActive('news');

    const main = document.getElementById('app-main');

    // 已经有列表内容（比如从详情页返回）→ 立刻按原样画出来，再静默刷新分类
    if (this.state.cards.length && this.state.activeCategoryId != null) {
      this.renderShell();
      this.paintCards();
      window.scrollTo(0, this.state.scrollY || 0);
      this.refreshCategoriesInBackground();
      return;
    }

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
      this.state.cards = [];
      this.renderShell();

      if (this.state.activeCategoryId != null) {
        await this.loadMore(true);
      } else {
        document.getElementById('news-list').innerHTML = '<div class="empty">暂无新闻分类</div>';
      }
    } catch (e) {
      main.innerHTML = this.errorHtml(e.message);
      this.bindRetry();
    }
  },

  /** 分类变化（后台静默刷新）：只为让新加的分类能出现，不打断当前列表 */
  async refreshCategoriesInBackground() {
    try {
      const categories = await API.getCategories();
      if (!categories.length) return;
      const changed = categories.length !== this.state.categories.length ||
        categories.some((c, i) => !this.state.categories[i] || this.state.categories[i].id !== c.id ||
          this.state.categories[i].name !== c.name);
      if (!changed) return;
      this.state.categories = categories;
      if (!categories.some(c => c.id === this.state.activeCategoryId)) {
        this.state.activeCategoryId = categories[0].id;
        this.state.cards = [];
        this.state.page = 1;
      }
      this.renderShell();
      this.paintCards();
    } catch (e) { /* 后台刷新失败不打扰用户 */ }
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
      if (card) {
        // 记住当前位置，从详情返回时能回到原处
        this.state.scrollY = window.scrollY;
        Router.navigate('news/' + card.dataset.id);
      }
    });
  },

  /** 把已加载的卡片一次性画出来 */
  paintCards() {
    const listEl = document.getElementById('news-list');
    const btn = document.getElementById('load-more-btn');
    if (!listEl) return;
    if (!this.state.cards.length) {
      listEl.innerHTML = '<div class="empty">该分类暂无新闻</div>';
      if (btn) btn.classList.add('hidden');
      return;
    }
    listEl.innerHTML = this.state.cards.map(item => this.cardHtml(item)).join('');
    if (btn) btn.classList.toggle('hidden', !this.state.hasMore);
  },

  /** 切换分类：重置分页并重新加载 */
  async switchCategory(categoryId) {
    if (categoryId === this.state.activeCategoryId) return;
    this.state.activeCategoryId = categoryId;
    this.state.page = 1;
    this.state.hasMore = false;
    this.state.cards = [];

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

    if (reset) {
      listEl.innerHTML = '<div class="loading">加载中...</div>';
      this.state.cards = [];
    }
    if (btn && !reset) {
      btn.disabled = true;
      btn.textContent = '加载中...';
    }

    try {
      const { list, hasMore, total } = await API.getNewsList(this.state.activeCategoryId, this.state.page);
      if (reset) listEl.innerHTML = '';

      this.state.cards = this.state.cards.concat(list);
      this.state.hasMore = hasMore;
      this.state.total = total;
      this.state.page += 1;

      if (!this.state.cards.length) {
        listEl.innerHTML = '<div class="empty">该分类暂无新闻</div>';
      } else if (reset) {
        this.paintCards();
      } else {
        // 追加：只插入新增的那几条，避免整块重绘导致图片闪一下
        listEl.insertAdjacentHTML('beforeend', list.map(item => this.cardHtml(item)).join(''));
        if (btn) btn.classList.toggle('hidden', !hasMore);
      }
    } catch (e) {
      listEl.innerHTML = this.errorHtml(e.message);
      this.bindRetry();
    } finally {
      this.state.loading = false;
      if (btn) {
        btn.disabled = false;
        btn.textContent = '加载更多';
      }
    }
  },

  /** 统一的错误块（带重试按钮） */
  errorHtml(message) {
    return `<div class="error">${escapeHtml(message)}
      <div><button class="btn-retry" id="retry-btn">点我重试</button></div>
    </div>`;
  },

  bindRetry() {
    const btn = document.getElementById('retry-btn');
    if (btn) {
      btn.addEventListener('click', () => {
        if (this.state.cards.length) { this.loadMore(false); }
        else { this.state.page = 1; this.loadMore(true); }
      });
    }
  },

  cardHtml(item) {
    const cover = item.image
      ? `<img class="news-cover" src="${escapeHtml(item.image)}" alt="" loading="lazy" onerror="this.onerror=null;this.src=window.placeholderImage('📰')">`
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
