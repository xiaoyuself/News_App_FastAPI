/**
 * 应用入口：头部 / 底部 Tab 公共控制 + 路由启动
 */

/** 设置顶部导航栏 */
function setHeader({ title = '', showBack = false, onBack = null, right = '' } = {}) {
  document.getElementById('header-title').textContent = title;
  const back = document.getElementById('header-back');
  back.classList.toggle('hidden', !showBack);
  back.onclick = onBack || (() => history.back());
  document.getElementById('header-right').innerHTML = right;
}

/** 显示 / 隐藏底部三 Tab（二级页面隐藏） */
function showTabBar(show) {
  document.getElementById('tab-bar').classList.toggle('hidden', !show);
  document.getElementById('app-main').style.paddingBottom = show ? '64px' : '24px';
}

/** 高亮当前 Tab */
function setTabActive(tab) {
  document.querySelectorAll('.tab-item').forEach(el => {
    el.classList.toggle('active', el.dataset.tab === tab);
  });
}

document.addEventListener('DOMContentLoaded', () => {
  // 底部 Tab 点击切换
  document.querySelectorAll('.tab-item').forEach(el => {
    el.addEventListener('click', () => {
      Router.navigate(el.dataset.tab);
    });
  });
  // 启动路由
  Router.init();
});
