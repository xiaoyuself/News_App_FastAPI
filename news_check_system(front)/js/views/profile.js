/**
 * 个人中心视图
 * - 未登录：注册（首次进入需要注册）/ 登录
 * - 已登录：头像 / 用户名 / 个性签名 + 详细信息 / 收藏列表 / 浏览记录 / 修改密码 四个功能
 * 路由： #/profile  #/profile/edit  #/profile/favorites  #/profile/history  #/profile/password
 */
window.ProfileView = {
  /* ---------------- 入口 ---------------- */
  render(sub) {
    if (!sub) return this.renderMain();
    switch (sub) {
      case 'edit': return this.renderEdit();
      case 'favorites': return this.renderFavorites();
      case 'history': return this.renderHistory();
      case 'password': return this.renderPassword();
      default: return this.renderMain();
    }
  },

  /* ---------------- 主页面 ---------------- */
  renderMain() {
    setHeader({ title: '个人中心', showBack: false, right: '' });
    showTabBar(true);
    setTabActive('profile');
    const main = document.getElementById('app-main');

    if (!isLoggedIn()) {
      return this.renderAuth(main);
    }
    const u = getUserInfo() || {};
    const avatar = u.avatar
      ? `<img src="${escapeHtml(u.avatar)}" alt="" onerror="this.onerror=null;this.style.display='none'">`
      : escapeHtml(avatarPlaceholder(u.nickname || u.username));

    main.innerHTML = `
      <div class="profile-header">
        <div class="profile-avatar">${avatar}</div>
        <div class="profile-info">
          <div class="profile-nick">${escapeHtml(u.nickname || u.username || '用户')}</div>
          <div class="profile-username">@${escapeHtml(u.username || '')}</div>
          <div class="profile-bio">${escapeHtml(u.bio || '这个人很懒，什么都没留下')}</div>
        </div>
      </div>
      <div class="profile-menu">
        <div class="menu-item" data-page="edit"><span class="mi-icon">📋</span>详细信息<span class="mi-arrow">›</span></div>
        <div class="menu-item" data-page="favorites"><span class="mi-icon">⭐</span>收藏列表<span class="mi-arrow">›</span></div>
        <div class="menu-item" data-page="history"><span class="mi-icon">🕘</span>浏览记录<span class="mi-arrow">›</span></div>
        <div class="menu-item" data-page="password"><span class="mi-icon">🔒</span>修改密码<span class="mi-arrow">›</span></div>
      </div>
      <button class="btn btn-outline logout-btn" id="logout-btn">退出登录</button>
    `;

    main.querySelectorAll('.menu-item').forEach(el => {
      el.addEventListener('click', () => Router.navigate('profile/' + el.dataset.page));
    });
    document.getElementById('logout-btn').addEventListener('click', () => {
      clearAuth();
      toast('已退出登录');
      this.renderMain();
    });
  },

  /* ---------------- 注册 / 登录 ---------------- */
  renderAuth(main) {
    main.innerHTML = `
      <div class="auth-page">
        <div class="auth-logo">📰</div>
        <div class="auth-title">新闻软件</div>
        <div class="auth-sub">首次使用请先注册，注册成功后自动登录</div>
        <div class="auth-tabs">
          <div class="at active" data-mode="register">注册</div>
          <div class="at" data-mode="login">登录</div>
        </div>
        <form id="auth-form" autocomplete="off" novalidate>
          <div class="form-group">
            <label>用户名</label>
            <input class="input" id="auth-username" type="text" maxlength="50" placeholder="请输入用户名（唯一）" required>
          </div>
          <div class="form-group">
            <label>密码</label>
            <input class="input" id="auth-password" type="password" maxlength="50" placeholder="请输入密码" required>
          </div>
          <div class="form-group" id="confirm-group">
            <label>确认密码</label>
            <input class="input" id="auth-confirm" type="password" maxlength="50" placeholder="请再次输入密码" required>
          </div>
          <button class="btn" type="submit" id="auth-submit">注 册</button>
        </form>
      </div>`;

    let mode = 'register';
    const switchMode = (m) => {
      mode = m;
      document.querySelectorAll('.auth-tabs .at').forEach(el => el.classList.toggle('active', el.dataset.mode === m));
      document.getElementById('confirm-group').classList.toggle('hidden', m !== 'register');
      document.getElementById('auth-submit').textContent = m === 'register' ? '注 册' : '登 录';
    };
    document.querySelectorAll('.auth-tabs .at').forEach(el => {
      el.addEventListener('click', () => switchMode(el.dataset.mode));
    });

    document.getElementById('auth-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const username = document.getElementById('auth-username').value.trim();
      const password = document.getElementById('auth-password').value;
      const confirm = document.getElementById('auth-confirm').value;
      if (!username) return toast('请输入用户名');
      if (!password) return toast('请输入密码');
      if (mode === 'register') {
        if (password !== confirm) return toast('两次输入的密码不一致');
        if (password.length < 6) return toast('密码长度不能少于 6 位');
      }

      const btn = document.getElementById('auth-submit');
      const originalText = btn.textContent;
      btn.disabled = true;
      btn.textContent = mode === 'register' ? '注册中…' : '登录中…';
      try {
        const data = mode === 'register'
          ? await API.register(username, password)
          : await API.login(username, password);
        setAuth(data.token, data.userInfo);
        toast(mode === 'register' ? '注册成功，已自动登录' : '登录成功');
        this.renderMain();
      } catch (err) {
        // 任何错误都明确提示，避免"点击没反应"
        toast(err && err.message ? err.message : '操作失败，请重试');
      } finally {
        btn.disabled = false;
        btn.textContent = originalText;
      }
    });
  },

  /* ---------------- 详细信息（编辑资料） ---------------- */
  async renderEdit() {
    setHeader({ title: '详细信息', showBack: true, onBack: () => Router.navigate('profile') });
    showTabBar(false);
    const main = document.getElementById('app-main');
    main.innerHTML = '<div class="loading">加载中...</div>';

    let u;
    try {
      u = await API.getUserInfoRemote();
      setAuth(getToken(), u); // 同步最新用户信息
    } catch (e) {
      main.innerHTML = '<div class="error">' + escapeHtml(e.message) + '</div>';
      return;
    }

    const genderMap = { male: '男', female: '女', unknown: '保密' }; // 备用：性别中文映射
    main.innerHTML = `
      <div class="edit-page">
        <div class="form-card">
          <div class="form-group">
            <label>用户ID</label>
            <input class="input" value="${u.id}" disabled>
          </div>
          <div class="form-group">
            <label>用户名（唯一，不可修改）</label>
            <input class="input" value="${escapeHtml(u.username || '')}" disabled>
          </div>
          <div class="form-group">
            <label>昵称</label>
            <input class="input" id="p-nick" maxlength="50" value="${escapeHtml(u.nickname || '')}" placeholder="请输入昵称">
          </div>
          <div class="form-group">
            <label>头像 URL</label>
            <input class="input" id="p-avatar" maxlength="255" value="${escapeHtml(u.avatar || '')}" placeholder="请输入头像图片地址">
          </div>
          <div class="form-group">
            <label>性别</label>
            <select class="input" id="p-gender">
              <option value="unknown" ${(u.gender || 'unknown') === 'unknown' ? 'selected' : ''}>保密</option>
              <option value="male" ${u.gender === 'male' ? 'selected' : ''}>男</option>
              <option value="female" ${u.gender === 'female' ? 'selected' : ''}>女</option>
            </select>
          </div>
          <div class="form-group">
            <label>个性签名</label>
            <input class="input" id="p-bio" maxlength="500" value="${escapeHtml(u.bio || '')}" placeholder="一句话介绍自己">
          </div>
          <div class="form-group">
            <label>手机号</label>
            <input class="input" id="p-phone" maxlength="20" value="${escapeHtml(u.phone || '')}" placeholder="请输入手机号">
          </div>
        </div>
        <button class="btn" id="save-btn">保存修改</button>
      </div>`;

    document.getElementById('save-btn').addEventListener('click', async () => {
      const payload = {
        nickname: document.getElementById('p-nick').value.trim() || null,
        avatar: document.getElementById('p-avatar').value.trim() || null,
        gender: document.getElementById('p-gender').value,
        bio: document.getElementById('p-bio').value.trim() || null,
        phone: document.getElementById('p-phone').value.trim() || null,
      };
      const btn = document.getElementById('save-btn');
      btn.disabled = true;
      try {
        const updated = await API.updateUser(payload);
        setAuth(getToken(), updated);
        toast('保存成功');
        Router.navigate('profile');
      } catch (e) {
        toast(e.message);
      } finally {
        btn.disabled = false;
      }
    });
  },

  /* ---------------- 收藏列表 ---------------- */
  async renderFavorites() {
    setHeader({ title: '收藏列表', showBack: true, onBack: () => Router.navigate('profile') });
    showTabBar(false);
    const main = document.getElementById('app-main');
    main.innerHTML = '<div class="loading">加载中...</div>';

    const st = { page: 1, hasMore: false, list: [] };
    const loadMore = async (reset) => {
      if (reset) { st.page = 1; st.list = []; }
      try {
        const res = await API.getFavoriteList(st.page);
        st.list = reset ? res.list : st.list.concat(res.list);
        st.hasMore = res.hasMore;
        st.page += 1;
        this.renderNewsListPage(main, st, loadMore, 'fav', res.total);
      } catch (e) {
        main.innerHTML = '<div class="error">' + escapeHtml(e.message) + '</div>';
      }
    };
    await loadMore(true);
  },

  /* ---------------- 浏览记录 ---------------- */
  async renderHistory() {
    setHeader({ title: '浏览记录', showBack: true, onBack: () => Router.navigate('profile') });
    showTabBar(false);
    const main = document.getElementById('app-main');
    main.innerHTML = '<div class="loading">加载中...</div>';

    const st = { page: 1, hasMore: false, list: [] };
    const loadMore = async (reset) => {
      if (reset) { st.page = 1; st.list = []; }
      try {
        const res = await API.getHistoryList(st.page);
        st.list = reset ? res.list : st.list.concat(res.list);
        st.hasMore = res.hasMore;
        st.page += 1;
        this.renderNewsListPage(main, st, loadMore, 'hist', res.total);
      } catch (e) {
        main.innerHTML = '<div class="error">' + escapeHtml(e.message) + '</div>';
      }
    };
    await loadMore(true);
  },

  /**
   * 收藏/历史的通用列表渲染
   * @param main 容器
   * @param st   分页状态 { page, hasMore, list }
   * @param loadMoreFn 加载更多函数（reset 时重置分页）
   * @param kind 'fav' | 'hist' 决定操作按钮
   */
  renderNewsListPage(main, st, loadMoreFn, kind, total) {
    const label = kind === 'fav' ? '收藏' : '历史';
    const clearText = kind === 'fav' ? '清空收藏' : '清空记录';
    main.innerHTML = `
      <div class="list-header-ops">
        <button class="list-op-btn" id="clear-btn">${clearText}</button>
      </div>
      <div class="news-list" id="sub-news-list">
        ${st.list.length ? '' : '<div class="empty">暂无' + label + '记录</div>'}
      </div>
      <button class="load-more ${st.hasMore ? '' : 'hidden'}" id="sub-load-more">加载更多</button>`;

    const listEl = document.getElementById('sub-news-list');
    st.list.forEach(item => {
      const el = document.createElement('div');
      el.className = 'news-card';
      el.style.alignItems = 'center';
      const cover = item.image
        ? `<img class="news-cover" src="${escapeHtml(item.image)}" alt="" onerror="this.onerror=null;this.src=window.placeholderImage('📰')">`
        : `<div class="news-cover" style="display:flex;align-items:center;justify-content:center;font-size:30px;">📰</div>`;
      const extraTime = kind === 'fav' ? formatTime(item.favoriteTime) : formatTime(item.viewTime);
      el.innerHTML = `
        ${cover}
        <div class="news-body">
          <div class="news-title">${escapeHtml(item.title)}</div>
          <div class="news-meta">
            <span>${escapeHtml(formatTime(item.publishTime))}</span>
            <span>👁 ${formatViews(item.views)}</span>
            ${extraTime ? `<span>${escapeHtml(extraTime)}</span>` : ''}
          </div>
        </div>
        <button class="list-op-btn op-btn">${kind === 'fav' ? '取消收藏' : '删除'}</button>`;
      el.addEventListener('click', () => Router.navigate('news/' + item.id));
      el.querySelector('.op-btn').addEventListener('click', async (ev) => {
        ev.stopPropagation();
        try {
          if (kind === 'fav') await API.removeFavorite(item.id);
          else await API.deleteHistory(item.id);
          toast(kind === 'fav' ? '已取消收藏' : '已删除');
          const idx = st.list.indexOf(item);
          if (idx > -1) st.list.splice(idx, 1);
          el.remove();
          if (st.list.length === 0) {
            document.getElementById('sub-news-list').innerHTML = `<div class="empty">暂无${label}记录</div>`;
          }
        } catch (e) {
          toast(e.message);
        }
      });
      listEl.appendChild(el);
    });

    document.getElementById('sub-load-more').addEventListener('click', () => loadMoreFn(false));
    document.getElementById('clear-btn').addEventListener('click', async () => {
      if (!confirm(`确定要${clearText}吗？`)) return;
      try {
        if (kind === 'fav') await API.clearFavorites();
        else await API.clearHistory();
        toast(clearText + '成功');
        loadMoreFn(true);
      } catch (e) {
        toast(e.message);
      }
    });
  },

  /* ---------------- 修改密码 ---------------- */
  renderPassword() {
    setHeader({ title: '修改密码', showBack: true, onBack: () => Router.navigate('profile') });
    showTabBar(false);
    const main = document.getElementById('app-main');
    main.innerHTML = `
      <div class="form-page">
        <div class="form-card">
          <div class="form-group">
            <label>原密码</label>
            <input class="input" id="old-pwd" type="password" placeholder="请输入原密码" required>
          </div>
          <div class="form-group">
            <label>新密码</label>
            <input class="input" id="new-pwd" type="password" placeholder="请输入新密码（不少于 6 位）" required>
          </div>
          <div class="form-group">
            <label>确认新密码</label>
            <input class="input" id="confirm-pwd" type="password" placeholder="请再次输入新密码" required>
          </div>
        </div>
        <button class="btn" id="pwd-submit">确认修改</button>
        <div class="pwd-tip">新密码需不少于 6 位，且两次输入需一致</div>
      </div>`;

    document.getElementById('pwd-submit').addEventListener('click', async () => {
      const oldPwd = document.getElementById('old-pwd').value;
      const newPwd = document.getElementById('new-pwd').value;
      const confirmPwd = document.getElementById('confirm-pwd').value;
      if (!oldPwd) return toast('请输入原密码');
      if (newPwd.length < 6) return toast('新密码长度不能少于 6 位');
      if (newPwd !== confirmPwd) return toast('两次输入的新密码不一致');

      const btn = document.getElementById('pwd-submit');
      btn.disabled = true;
      try {
        await API.changePassword(oldPwd, newPwd);
        toast('密码修改成功');
        setTimeout(() => Router.navigate('profile'), 700);
      } catch (e) {
        toast(e.message);
      } finally {
        btn.disabled = false;
      }
    });
  },
};
