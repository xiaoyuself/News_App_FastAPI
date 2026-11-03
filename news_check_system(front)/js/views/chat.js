/**
 * AI 对话视图：内置智能客服助手
 *
 * 对接说明：
 * 前端通过 API.chat()（见 js/api.js）调用 AI 服务：
 *   POST {AI_BASE_URL}/api/ai/chat   body: { "question": "..." }
 *   返回: { "code": 200, "message": "success", "data": { "answer": "..." } }
 *
 * AI 服务由「RAG_NEW/ai_server.py」提供（LangChain + Milvus RAG，
 * 知识库来自 RAG_NEW/data/ 下的产品手册与 FAQ），独立运行在 8001 端口。
 * 若该服务未启动，这里会给出友好的降级提示（大模型接口已预留）。
 * 路由： #/ai
 */
window.ChatView = {
  // 会话消息缓存（切换页面后保留，刷新页面清空）
  _messages: [],
  // 是否正在等上一次回答：等回答期间不允许再发，避免连点发出一堆并发请求
  _busy: false,

  render() {
    setHeader({ title: 'AI对话', showBack: false, right: '' });
    showTabBar(true);
    setTabActive('ai');

    const main = document.getElementById('app-main');
    main.innerHTML = `
      <div class="chat-page">
        <div class="chat-messages" id="chat-messages"></div>
        <div class="chat-input-bar">
          <input class="input" id="chat-input" type="text" placeholder="请输入您的问题…" maxlength="200">
          <button class="btn chat-send" id="chat-send">发送</button>
        </div>
      </div>`;

    // 首次进入添加欢迎语（标 welcome，多轮时不会把它当历史发给服务端）
    if (this._messages.length === 0) {
      this._messages.push({
        role: 'assistant',
        welcome: true,
        text: '您好！我是新闻软件智能客服助手 🤖\n您可以问我关于注册登录、密码修改与找回、新闻浏览、收藏、浏览记录等问题。',
      });
    }
    this._messages.forEach(m => this.appendMsg(m.role, m.text, false));

    // 常用问题快捷入口
    this.appendQuickChips();

    const input = document.getElementById('chat-input');
    const send = document.getElementById('chat-send');

    const doSend = () => {
      const text = input.value.trim();
      if (!text) return;
      input.value = '';
      this.send(text);
    };
    send.addEventListener('click', doSend);
    input.addEventListener('keydown', e => { if (e.key === 'Enter') doSend(); });

    // 若切换页面回来时上一次回答还没结束，保持"回答中"状态
    this.setInputEnabled(!this._busy);
  },

  /** 回答过程中禁用输入框和按钮，避免连点发出一堆并发请求 */
  setInputEnabled(enabled) {
    const btn = document.getElementById('chat-send');
    const input = document.getElementById('chat-input');
    if (btn) {
      btn.disabled = !enabled;
      btn.textContent = enabled ? '发送' : '回答中';
    }
    if (input) input.disabled = !enabled;
  },

  /** 追加一条消息到界面（keepScroll=false 时自动滚动到底部） */
  appendMsg(role, text, keepScroll = false) {
    const box = document.getElementById('chat-messages');
    if (!box) return;
    const isUser = role === 'user';
    const avatar = isUser
      ? (getUserInfo() && getUserInfo().avatar
          ? `<img src="${escapeHtml(getUserInfo().avatar)}" alt="">`
          : escapeHtml(avatarPlaceholder(getUserInfo() && getUserInfo().nickname)))
      : '🤖';
    const div = document.createElement('div');
    div.className = 'msg ' + (isUser ? 'user' : 'assistant');
    div.innerHTML = `<div class="avatar">${avatar}</div><div class="bubble">${escapeHtml(text)}</div>`;
    box.appendChild(div);
    if (!keepScroll) box.scrollTop = box.scrollHeight;
  },

  /** 追加常用问题快捷 chips */
  appendQuickChips() {
    const box = document.getElementById('chat-messages');
    if (!box) return;
    const chips = ['如何注册账号？', '如何收藏新闻？', '浏览记录在哪里查看？', '忘记密码怎么找回？'];
    const wrap = document.createElement('div');
    wrap.className = 'chat-quick';
    wrap.innerHTML = chips.map(c => `<div class="chip" data-q="${escapeHtml(c)}">${escapeHtml(c)}</div>`).join('');
    wrap.querySelectorAll('.chip').forEach(el => {
      el.addEventListener('click', () => this.send(el.dataset.q));
    });
    box.appendChild(wrap);
    box.scrollTop = box.scrollHeight;
  },

  /** 发送一条消息并请求 AI 回复 */
  async send(text) {
    if (this._busy) {
      toast('上一条还在回答中，请稍候');
      return;
    }

    // 先取历史，再把自己这句加进去（历史里不含本轮问题和欢迎语）
    const history = this._messages
      .filter(m => !m.welcome)
      .slice(-6)                                  // 最近 3 轮（一问一答 = 2 条）
      .map(m => ({ role: m.role, content: m.text }));

    this._busy = true;
    this.setInputEnabled(false);

    this._messages.push({ role: 'user', text });
    this.appendMsg('user', text);

    // 追加"正在思考…"占位
    const box = document.getElementById('chat-messages');
    const thinking = document.createElement('div');
    thinking.className = 'msg assistant';
    thinking.innerHTML = `<div class="avatar">🤖</div><div class="bubble">正在思考…</div>`;
    box.appendChild(thinking);
    box.scrollTop = box.scrollHeight;

    try {
      const answer = await API.chat(text, history);
      thinking.querySelector('.bubble').textContent = answer;
      this._messages.push({ role: 'assistant', text: answer });
    } catch (e) {
      // AI 服务不可用时的降级提示
      const fallback = '抱歉，智能客服暂时无法回答：' + e.message + '\n\n' +
        '可能原因：\n' +
        '1. 智能客服服务未启动（news_check_system(AI)，端口 8001）\n' +
        '2. 向量库连不上（Docker 里向量库随 ai 容器启动，本地运行需自行启动 Milvus）\n\n' +
        '您可以先通过「个人中心」体验注册登录、收藏、浏览记录、修改密码等功能。';
      thinking.querySelector('.bubble').textContent = fallback;
      this._messages.push({ role: 'assistant', text: fallback });
    } finally {
      this._busy = false;
      this.setInputEnabled(true);
    }
    box.scrollTop = box.scrollHeight;
  },
};
