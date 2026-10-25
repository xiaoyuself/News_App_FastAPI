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

    // 首次进入添加欢迎语
    if (this._messages.length === 0) {
      this._messages.push({
        role: 'assistant',
        text: '您好！我是新闻软件智能客服助手 🤖\n您可以问我关于注册登录、新闻浏览、收藏、浏览记录、修改密码等问题。',
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
    const chips = ['如何注册账号？', '如何收藏新闻？', '浏览记录在哪里查看？', '如何修改密码？'];
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
      const answer = await API.chat(text);
      thinking.querySelector('.bubble').textContent = answer;
      this._messages.push({ role: 'assistant', text: answer });
    } catch (e) {
      // AI 服务不可用时的降级提示（大模型接口已预留，服务就绪后即可联通）
      const fallback = '抱歉，智能客服暂时无法回答：' + e.message + '\n\n' +
        '可能原因：\n' +
        '1. AI 服务未启动：运行 RAG_NEW/ai_server.py（依赖 .env 中的 API Key）\n' +
        '2. Milvus 知识库服务未启动：请先启动 Milvus（默认 http://localhost:19530），' +
        '否则除问候语外的提问无法检索知识库\n\n' +
        '您也可以先通过「个人中心」体验注册登录、收藏、浏览记录、修改密码等功能。';
      thinking.querySelector('.bubble').textContent = fallback;
      this._messages.push({ role: 'assistant', text: fallback });
    }
    box.scrollTop = box.scrollHeight;
  },
};
