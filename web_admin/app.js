import { request } from './api.js';
const app = document.querySelector('#app'), dialog = document.querySelector('#editor');
const paths = {
  book: '<path d="M12 7c-3-2-6-2-9-1v14c3-1 6-1 9 1 3-2 6-2 9-1V6c-3-1-6-1-9 1Z"/><path d="M12 7v14M6 10h3M15 10h3M6 13h3M15 13h3"/>',
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  folder: '<path d="M3 7a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>',
  users: '<circle cx="9" cy="8" r="3"/><path d="M3 21v-2a6 6 0 0 1 12 0v2M16 5a3 3 0 0 1 0 6M21 21v-2a6 6 0 0 0-4-5"/>',
  check: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="m8 12 3 3 5-6"/>',
  arrow: '<path d="M5 12h14m-5-5 5 5-5 5"/>', plus: '<path d="M12 5v14M5 12h14"/>',
  refresh: '<path d="M20 7v5h-5M4 17v-5h5M6 7a7 7 0 0 1 12-1l2 3M4 15l2 3a7 7 0 0 0 12-1"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  edit: '<path d="m15 5 4 4M4 20l4-1L21 6a2 2 0 0 0-3-3L5 16Z"/>',
  delete: '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>', logout: '<path d="M9 4H4v16h5M10 12h11m-4-4 4 4-4 4"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  eye: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
};
const icon = name => `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${paths[name] || paths.book}</svg>`;
const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' })[c]);
const num = value => new Intl.NumberFormat('vi-VN').format(value ?? 0);
const logo = `<div class="logo"><span class="logo-mark">${icon('book')}</span><span>LENLEARN<small>ADMIN WORKSPACE</small></span></div>`;
const titles = { dashboard: 'Tổng quan', vocabulary: 'Từ vựng', topics: 'Chủ đề', users: 'Người dùng' };
const state = { token: sessionStorage.getItem('admin_token') || '', profile: null, page: 'dashboard', data: null, query: '', filter: '', pagination: 1, userOffset: 0, userHasNext: false, busy: false, loadId: 0 };
let toastTimer, pendingEditor = '';

function toast(message) {
  const el = document.querySelector('#toast');
  el.textContent = message;
  el.classList.add('visible');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('visible'), 4000);
}

async function api(path, options = {}) {
  const token = state.token;
  try { return await request(path, { token, ...options }); }
  catch (error) { if (state.token === token && (error.status === 401 || error.status === 403)) { logout(); toast(error.message); } throw error; }
}

function logout() {
  state.token = ''; state.profile = null; state.data = null; state.loadId++; pendingEditor = '';
  sessionStorage.removeItem('admin_token'); if (dialog.open) dialog.close(); login();
}

function login(error = '') {
  app.innerHTML = `
    <main class="login">
      <section class="login-story">
        <div class="login-story-top">
          ${logo}
          <div class="login-badge">PORTAL QUẢN TRỊ</div>
        </div>
        <div class="login-story-center">
          <div class="login-sparkle">✨ HỌC TIẾNG ANH QUA HÌNH ẢNH</div>
          <h1>Mỗi từ mới.<br><span class="hero-highlight">Một thế giới mới.</span></h1>
          <p>Không gian quản trị nội dung học tập. Cùng xây dựng hành trình học tiếng Anh trực quan và đầy cảm hứng.</p>
          <div class="welcome-graphic" aria-hidden="true">
            <div class="book-art">${icon('book')}</div>
          </div>
          <div class="login-features">
            <div class="feature-tag"><span>📚</span> Quản lý kho từ vựng &amp; chủ đề linh hoạt</div>
            <div class="feature-tag"><span>👥</span> Tra cứu &amp; giám sát tài khoản người dùng</div>
            <div class="feature-tag"><span>⚡</span> Đồng bộ dữ liệu học tập tức thì tới ứng dụng</div>
          </div>
        </div>
        <small class="login-story-foot">LENLEARN &nbsp; · &nbsp; HỆ THỐNG QUẢN TRỊ NỘI DUNG</small>
      </section>
      <section class="login-form-wrap">
        <div class="login-card">
          <form class="login-form" id="login-form">
            <div class="login-label">CHÀO MỪNG TRỞ LẠI</div>
            <h2>Đăng nhập quản trị</h2>
            <p>Quản lý kho từ vựng, phân loại chủ đề và theo dõi hoạt động người dùng.</p>
            <label class="field">
              <span class="field-title">Tên đăng nhập</span>
              <input name="username" autocomplete="username" required minlength="3" maxlength="50" placeholder="Nhập tên đăng nhập của bạn">
            </label>
            <label class="field">
              <span class="field-title">Mật khẩu</span>
              <div class="password-field">
                <input name="password" type="password" autocomplete="current-password" required minlength="8" maxlength="128" placeholder="Nhập mật khẩu tài khoản">
                <button type="button" id="toggle-password" aria-label="Hiện mật khẩu">Hiện</button>
              </div>
            </label>
            <div id="login-error" role="alert">${error ? `<p class="error">${escape(error)}</p>` : ''}</div>
            <button class="btn primary btn-submit" type="submit">Đăng nhập ngay ${icon('arrow')}</button>
            <div class="login-note">
              Dành riêng cho tài khoản có quyền <b>ADMIN</b>.<br>
              <small>Liên hệ quản trị hệ thống nếu bạn cần được cấp tài khoản.</small>
            </div>
          </form>
        </div>
      </section>
    </main>`;

  document.querySelector('#toggle-password').onclick = e => {
    const input = app.querySelector('[name=password]');
    const hidden = input.type === 'password';
    input.type = hidden ? 'text' : 'password';
    e.currentTarget.textContent = hidden ? 'Ẩn' : 'Hiện';
    e.currentTarget.setAttribute('aria-label', hidden ? 'Ẩn mật khẩu' : 'Hiện mật khẩu');
  };

  document.querySelector('#login-form').onsubmit = async event => {
    event.preventDefault();
    const form = event.currentTarget, button = form.querySelector('[type=submit]');
    button.disabled = true; button.textContent = 'Đang đăng nhập…'; document.querySelector('#login-error').textContent = '';
    const values = new FormData(form);
    try {
      const response = await request('/auth/login', { method: 'POST', body: { username: values.get('username').trim(), password: values.get('password') } });
      if (!response?.access_token) throw new Error('Backend không trả về mã đăng nhập hợp lệ.');
      const profile = await request('/users/me', { token: response.access_token });
      if (profile.role !== 'ADMIN') throw new Error('Tài khoản này không có quyền quản trị.');
      state.token = response.access_token; state.profile = profile; state.query = ''; state.filter = ''; state.pagination = 1; state.userOffset = 0;
      sessionStorage.setItem('admin_token', state.token); form.reset(); shell(); await load();
    } catch (error) {
      state.token = ''; sessionStorage.removeItem('admin_token');
      const target = document.querySelector('#login-error'); if (target) target.innerHTML = `<p class="error">${escape(error.message)}</p>`;
    } finally { button.disabled = false; button.innerHTML = `Đăng nhập ngay ${icon('arrow')}`; }
  };
}

function getPage() { return Object.hasOwn(titles, location.hash.slice(1)) ? location.hash.slice(1) : 'dashboard'; }

function shell() {
  state.page = getPage(); const name = state.profile.full_name || state.profile.username;
  app.innerHTML = `
    <div class="shell">
      <aside class="sidebar" id="sidebar">
        <button class="mobile-close" id="close-menu" aria-label="Đóng menu">${icon('close')}</button>
        ${logo}
        <p class="nav-caption">KHÔNG GIAN QUẢN TRỊ</p>
        <nav class="nav" aria-label="Điều hướng chính">
          ${Object.entries(titles).map(([key, label], i) => `
            <a href="#${key}" ${key === state.page ? 'class="active" aria-current="page"' : ''}>
              ${icon(['grid','book','folder','users'][i])}
              <span>${label}</span>
            </a>
          `).join('')}
        </nav>
        <div class="sidebar-foot">
          <div class="workspace-card">
            <b>${icon('book')} &nbsp; Nội dung tạo cảm hứng</b>
            <p>Mỗi từ vựng bạn thêm là một bước tiến của người học.</p>
          </div>
          <p class="sidebar-version">LENLEARN &nbsp; · &nbsp; ADMIN v1.0</p>
        </div>
      </aside>
      <div class="content">
        <header class="topbar">
          <button class="mobile-menu" id="open-menu" aria-label="Mở menu" aria-expanded="false" aria-controls="sidebar">${icon('menu')}</button>
          <div class="breadcrumb">
            <span>Không gian quản trị</span>
            <span class="bc-sep">/</span>
            <b>${titles[state.page]}</b>
          </div>
          <div class="account">
            <span class="avatar">${escape(name.slice(0, 2).toUpperCase())}</span>
            <div class="account-info">
              <div class="account-name">${escape(name)}</div>
              <small class="account-role">Quản trị viên</small>
            </div>
            <button class="logout" id="logout" aria-label="Đăng xuất" title="Đăng xuất">
              ${icon('logout')}
              <span>Đăng xuất</span>
            </button>
          </div>
        </header>
        <main class="main" id="main"></main>
      </div>
    </div>`;

  document.querySelector('#logout').onclick = logout;
  const setMenu = open => {
    document.querySelector('#sidebar').classList.toggle('open', open);
    document.querySelector('#open-menu').setAttribute('aria-expanded', String(open));
  };
  document.querySelector('#open-menu').onclick = () => setMenu(true);
  document.querySelector('#close-menu').onclick = () => setMenu(false);
}

function head() {
  const descriptions = {
    dashboard: 'Nội dung học tập và hoạt động ứng dụng, trong một góc nhìn tổng thể.',
    vocabulary: 'Xây dựng và chăm chút kho từ vựng tiếng Anh sinh động cho người học.',
    topics: 'Sắp xếp nội dung theo từng chủ đề học tập trực quan và gần gũi.',
    users: 'Tra cứu danh sách tài khoản, vai trò và trạng thái người dùng trong hệ thống.'
  };
  return `
    <div class="page-head">
      <div>
        <div class="eyebrow">YOUR LEARNING WORKSPACE</div>
        <h1>${titles[state.page]}</h1>
        <p>${descriptions[state.page]}</p>
      </div>
      <div class="actions">
        <button class="btn" id="refresh">${icon('refresh')} <span>Tải lại</span></button>
        ${['vocabulary','topics'].includes(state.page) ? `<button class="btn primary" id="create">${icon('plus')} <span>Thêm ${state.page === 'topics' ? 'chủ đề' : 'từ vựng'}</span></button>` : ''}
      </div>
    </div>`;
}

function bindHead() {
  document.querySelector('#refresh').onclick = () => load();
  const create = document.querySelector('#create');
  if (create) create.onclick = () => editor(state.page === 'topics' ? 'topic' : 'word');
}

async function load() {
  if (!state.token) return;
  const id = ++state.loadId, main = document.querySelector('#main');
  main.innerHTML = `${head()}<div class="panel"><div class="loading" role="status"><span class="spinner"></span>Đang tải dữ liệu…</div></div>`;
  document.querySelector('#refresh').disabled = true;
  const create = document.querySelector('#create');
  if (create) create.disabled = true;

  try {
    let data;
    if (state.page === 'dashboard') {
      const [summary, topics] = await Promise.all([api('/admin/summary'), api('/admin/topics')]);
      data = { summary, topics };
    } else if (state.page === 'vocabulary') {
      const [words, topics] = await Promise.all([api('/admin/vocabularies'), api('/admin/topics')]);
      data = { words, topics };
    } else if (state.page === 'topics') {
      data = { topics: await api('/admin/topics') };
    } else {
      const users = await api(`/admin/users?offset=${state.userOffset}&limit=100`);
      data = { users: users.slice(0, 99) };
      if (id === state.loadId) state.userHasNext = users.length === 100;
    }
    if (id !== state.loadId) return;
    state.data = data;
    render();
    return true;
  } catch (error) {
    if (id !== state.loadId || !state.token) return;
    state.data = null;
    main.innerHTML = `${head()}<div class="error" role="alert">${escape(error.message)}</div>`;
    bindHead();
    const create = document.querySelector('#create');
    if (create) create.disabled = true;
  }
}

function render() {
  const main = document.querySelector('#main');
  if (!main) return;
  main.innerHTML = head() + (state.page === 'dashboard' ? dashboard() : state.page === 'users' ? '<div class="notice">Danh sách người dùng chỉ hỗ trợ tra cứu. Quyền quản trị được cấp từ công cụ phía máy chủ.</div>' + listShell() : listShell()) + `<footer class="footer"><span>LENLEARN · Không gian quản trị nội dung</span><span>Dữ liệu từ backend · ${escape(new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }))}</span></footer>`;
  bindHead();

  if (state.page === 'dashboard') {
    main.querySelectorAll('[data-quick]').forEach(button => button.onclick = () => {
      const type = button.dataset.quick;
      pendingEditor = type === 'users' ? '' : type;
      location.hash = type === 'word' ? 'vocabulary' : type === 'topic' ? 'topics' : 'users';
    });
    main.querySelectorAll('[data-width]').forEach(el => el.style.width = `${Number(el.dataset.width)}%`);
  } else {
    document.querySelector('#search').oninput = event => {
      state.query = event.target.value;
      state.pagination = 1;
      renderRows();
    };
    const filter = document.querySelector('#filter');
    if (filter) filter.onchange = event => {
      state.filter = event.target.value;
      state.pagination = 1;
      renderRows();
    };
    renderRows();
  }
}

function dashboard() {
  const { summary: s, topics } = state.data;
  const stats = [
    ['Người dùng', s.users, 'users', `${num(s.admins)} tài khoản quản trị`],
    ['Từ vựng', s.vocabularies, 'book', 'Trong thư viện học tập'],
    ['Chủ đề', s.topics, 'folder', 'Nhóm nội dung học tập'],
    ['Bài kiểm tra', s.completed_quizzes, 'check', 'Lượt đã hoàn thành']
  ];
  const sorted = [...topics].sort((a,b) => b.vocabulary_count - a.vocabulary_count).slice(0, 5);
  const max = Math.max(1, ...sorted.map(t => t.vocabulary_count));

  return `
    <section class="welcome">
      <div class="welcome-text">
        <div class="welcome-tag"><span class="dot"></span> LET'S GROW TOGETHER</div>
        <h2>Chăm chút nội dung. Nuôi lớn tri thức.</h2>
        <p>Theo dõi thư viện học tập, tổ chức chủ đề và đồng hành cùng cộng đồng người học của bạn.</p>
      </div>
      <div class="welcome-graphic" aria-hidden="true">
        <div class="book-art">${icon('book')}</div>
      </div>
    </section>
    <section class="stats" aria-label="Thống kê ứng dụng">
      ${stats.map(([label, value, i, note]) => `
        <article class="stat">
          <div class="stat-top">
            <span class="stat-label">${label}</span>
            <span class="stat-icon">${icon(i)}</span>
          </div>
          <strong class="stat-number">${num(value)}</strong>
          <small class="stat-note">${note}</small>
        </article>
      `).join('')}
    </section>
    <div class="dashboard-grid">
      <section class="panel">
        <div class="panel-head">
          <div>
            <h2>Thư viện theo chủ đề</h2>
            <p>5 chủ đề có nhiều từ vựng nhất</p>
          </div>
          <a class="text-link" href="#topics">Tất cả chủ đề ↗</a>
        </div>
        ${sorted.length ? `<div class="topic-bars">${sorted.map(t => `
          <div class="bar-row">
            <div class="bar-label">
              <span><span class="bar-symbol">${escape(t.symbol)}</span> &nbsp; <b>${escape(t.name)}</b></span>
              <small>${num(t.vocabulary_count)} từ vựng</small>
            </div>
            <div class="bar-track">
              <div class="bar-fill" data-width="${Math.round(t.vocabulary_count/max*100)}"></div>
            </div>
          </div>
        `).join('')}</div>` : empty('Chưa có chủ đề. Thêm chủ đề đầu tiên để bắt đầu.')}
      </section>
      <section class="panel">
        <div class="panel-head">
          <div>
            <h2>Thao tác nhanh</h2>
            <p>Tiếp tục xây dựng trải nghiệm học tập</p>
          </div>
        </div>
        <div class="quick">
          ${[
            ['word', 'book', 'Thêm từ vựng', 'Mở rộng thư viện học tập với hình ảnh'],
            ['topic', 'folder', 'Tạo chủ đề', 'Kết nối từ vựng theo nội dung bài học'],
            ['users', 'users', 'Xem người dùng', 'Tra cứu tài khoản trong hệ thống']
          ].map(([type, i, title, desc]) => `
            <button class="quick-item" data-quick="${type}">
              <span class="quick-icon">${icon(i)}</span>
              <span>
                <strong>${title}</strong>
                <small>${desc}</small>
              </span>
              <span class="quick-arrow">${icon('arrow')}</span>
            </button>
          `).join('')}
        </div>
        <div class="info">
          <span class="info-icon">💡</span>
          <span>Nội dung được lưu trực tiếp vào backend và dùng chung với ứng dụng học tiếng Anh.</span>
        </div>
      </section>
    </div>`;
}

function listShell() {
  const filter = state.page === 'vocabulary'
    ? `<select id="filter" aria-label="Lọc theo chủ đề"><option value="">Tất cả chủ đề</option><option value="none" ${state.filter === 'none' ? 'selected' : ''}>Chưa phân chủ đề</option>${state.data.topics.map(t => `<option value="${t.topic_id}" ${state.filter === String(t.topic_id) ? 'selected' : ''}>${escape(t.name)}</option>`).join('')}</select>`
    : state.page === 'users'
    ? `<select id="filter" aria-label="Lọc theo vai trò"><option value="">Tất cả vai trò</option><option value="ADMIN" ${state.filter === 'ADMIN' ? 'selected' : ''}>Quản trị viên</option><option value="USER" ${state.filter === 'USER' ? 'selected' : ''}>Người học</option></select>`
    : '';
  const placeholder = state.page === 'vocabulary' ? 'Tìm từ vựng, nghĩa tiếng Việt…' : state.page === 'topics' ? 'Tìm tên chủ đề, slug…' : 'Tìm trong nhóm tài khoản đang tải…';
  return `<section class="panel"><div class="toolbar"><div class="search">${icon('search')}<input type="search" id="search" aria-label="${placeholder}" placeholder="${placeholder}" value="${escape(state.query)}"></div>${filter}</div><div id="rows"></div></section>`;
}

function normalize(value) { return String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').replace(/Đ/g,'D').toLowerCase(); }
function empty(message) { return `<div class="empty">${icon('search')}${escape(message)}</div>`; }

function renderRows() {
  const type = state.page, q = normalize(state.query.trim());
  let rows = (type === 'vocabulary' ? state.data.words : type === 'topics' ? state.data.topics : state.data.users).filter(item => {
    const text = type === 'vocabulary' ? [item.word,...item.meanings.map(m => m.meaning_vi)].join(' ') : type === 'topics' ? `${item.name} ${item.slug}` : `${item.username} ${item.full_name || ''} ${item.email}`;
    if (!normalize(text).includes(q)) return false;
    if (type === 'vocabulary' && state.filter) return state.filter === 'none' ? !item.topics.length : item.topics.some(t => String(t.topic_id) === state.filter);
    if (type === 'users' && state.filter) return item.role === state.filter;
    return true;
  });
  const count = rows.length, size = type === 'topics' ? 9 : 10, pages = Math.max(1,Math.ceil(count/size));
  state.pagination = Math.min(state.pagination,pages);
  const offset = (state.pagination-1)*size; rows = rows.slice(offset,offset+size);
  let content;
  if (!rows.length) {
    content = empty(q || state.filter ? 'Không có kết quả phù hợp với bộ lọc.' : 'Chưa có dữ liệu.');
  } else if (type === 'topics') {
    content = `<div class="topic-grid">${rows.map(t => `
      <article class="topic-card">
        <div class="topic-card-header">
          <div class="topic-symbol">${escape(t.symbol)}</div>
          <span class="topic-id-badge">ID ${t.topic_id}</span>
        </div>
        <h3>${escape(t.name)}</h3>
        <p class="topic-slug">/${escape(t.slug)}</p>
        <div class="topic-bottom">
          <span class="topic-count-badge">${icon('book')} ${num(t.vocabulary_count)} từ vựng</span>
          <div class="row-actions">
            <button class="icon-btn" data-edit="${t.topic_id}" aria-label="Sửa ${escape(t.name)}">${icon('edit')} <span>Sửa</span></button>
            <button class="icon-btn delete" data-delete="${t.topic_id}" aria-label="Xóa ${escape(t.name)}" ${t.vocabulary_count ? 'disabled title="Chủ đề đang chứa từ vựng"' : ''}>${icon('delete')} <span>Xóa</span></button>
          </div>
        </div>
      </article>`).join('')}</div>`;
  } else if (type === 'vocabulary') {
    content = `<div class="table-wrap"><table><thead><tr><th>Từ vựng</th><th>Nghĩa tiếng Việt</th><th>Chủ đề</th><th>Trình độ</th><th>Thao tác</th></tr></thead><tbody>${rows.map(w => `
      <tr>
        <td class="word">
          <div>${escape(w.word)}</div>
          <small class="word-ipa">${escape(w.ipa || 'Chưa có phiên âm')}</small>
        </td>
        <td class="meaning">${escape(primary(w.meanings,'meaning_id')?.meaning_vi || '—')}</td>
        <td>${w.topics.length ? w.topics.map(t => `<span class="badge topic-badge">${escape(t.symbol)} ${escape(t.name)}</span>`).join(' ') : '<span class="badge neutral">Chưa phân chủ đề</span>'}</td>
        <td><span class="badge level-${w.level?.toLowerCase() || 'neutral'}">${escape(({BEGINNER:'Cơ bản',INTERMEDIATE:'Trung cấp',ADVANCED:'Nâng cao'})[w.level] || w.level || '—')}</span></td>
        <td>
          <div class="row-actions">
            <button class="icon-btn" data-detail="${w.vocabulary_id}" aria-label="Chi tiết ${escape(w.word)}">${icon('eye')} <span>Xem</span></button>
            <button class="icon-btn" data-edit="${w.vocabulary_id}">${icon('edit')} <span>Sửa</span></button>
          </div>
        </td>
      </tr>`).join('')}</tbody></table></div>`;
  } else {
    content = `<div class="table-wrap"><table><thead><tr><th>ID</th><th>Người dùng</th><th>Email</th><th>Vai trò</th></tr></thead><tbody>${rows.map(u => `
      <tr>
        <td class="muted">#${u.user_id}</td>
        <td class="word">
          <div>${escape(u.full_name || u.username)}</div>
          <small>@${escape(u.username)}</small>
        </td>
        <td>${escape(u.email)}</td>
        <td><span class="badge ${u.role === 'ADMIN' ? 'admin' : 'user'}">${u.role === 'ADMIN' ? '👑 Quản trị viên' : '🎓 Người học'}</span></td>
      </tr>`).join('')}</tbody></table></div>`;
  }

  document.querySelector('#rows').innerHTML = content + `<div class="table-foot"><span>${count ? `${offset+1}–${Math.min(offset+size,count)}` : '0'} / ${num(count)} ${type === 'users' ? 'kết quả trong nhóm đang tải' : 'kết quả'}</span><div class="pager"><button id="prev" ${state.pagination === 1 ? 'disabled' : ''} aria-label="Trang trước">←</button><span>${state.pagination} / ${pages}</span><button id="next" ${state.pagination === pages ? 'disabled' : ''} aria-label="Trang sau">→</button></div></div>${type === 'users' ? `<div class="table-foot"><span>Nhóm tài khoản từ vị trí ${state.userOffset+1}. Tìm kiếm và lọc áp dụng trong nhóm này.</span><div class="pager"><button id="prev-users" ${!state.userOffset ? 'disabled' : ''}>Nhóm trước</button><button id="next-users" ${!state.userHasNext ? 'disabled' : ''}>Nhóm tiếp</button></div></div>` : ''}`;
  document.querySelector('#prev').onclick = () => { state.pagination--; renderRows(); };
  document.querySelector('#next').onclick = () => { state.pagination++; renderRows(); };
  app.querySelectorAll('[data-edit]').forEach(b => b.onclick = () => editor(type === 'topics' ? 'topic' : 'word',Number(b.dataset.edit)));
  app.querySelectorAll('[data-delete]').forEach(b => b.onclick = () => deleteTopic(Number(b.dataset.delete)));
  app.querySelectorAll('[data-detail]').forEach(b => b.onclick = () => details(Number(b.dataset.detail)));
  if (type === 'users') {
    document.querySelector('#prev-users').onclick = () => { state.userOffset = Math.max(0,state.userOffset-99); state.pagination = 1; load(); };
    document.querySelector('#next-users').onclick = () => { state.userOffset += 99; state.pagination = 1; load(); };
  }
}

function primary(items,key) { return [...items].sort((a,b) => a[key]-b[key])[0]; }

function showDialog(title,body,footer = '<button class="btn" type="button" data-close>Đóng</button>') {
  dialog.innerHTML = `<div class="dialog-head"><h2 id="dialog-title">${escape(title)}</h2><button class="icon-btn" type="button" data-close aria-label="Đóng hộp thoại">${icon('close')}</button></div>${body}<div class="dialog-foot">${footer}</div>`;
  dialog.querySelectorAll('[data-close]').forEach(b => b.onclick = () => { if (!state.busy) dialog.close(); });
  if (!dialog.open) dialog.showModal();
}

dialog.addEventListener('cancel',event => { if (state.busy) event.preventDefault(); });

function field(label,name,value,attrs = '',full = false,textarea = false) {
  return `<label class="field ${full ? 'full' : ''}"><span class="field-title">${label}</span>${textarea ? `<textarea name="${name}" ${attrs}>${escape(value)}</textarea>` : `<input name="${name}" value="${escape(value)}" ${attrs}>`}</label>`;
}

function editor(type,id) {
  const topic = type === 'topic';
  const item = id ? (topic ? state.data.topics.find(t => t.topic_id === id) : state.data.words.find(w => w.vocabulary_id === id)) : {};
  if (!item) return;
  const meaning = topic ? {} : primary(item.meanings || [],'meaning_id'), example = topic ? {} : primary(item.examples || [],'example_id');
  const fields = topic ? field('Tên chủ đề *','name',item.name || '','required maxlength="100"') + field('Biểu tượng *','symbol',item.symbol || '📚','required maxlength="20"') + field('Slug *','slug',item.slug || '','required maxlength="50" pattern="[a-z0-9]+(-[a-z0-9]+)*" placeholder="vi-du: everyday-life"',true) + '<p class="muted full">Slug dùng chữ thường không dấu, số và dấu gạch ngang.</p>' : field('Từ tiếng Anh *','word',item.word || '','required maxlength="100"') + field('Phiên âm IPA','ipa',item.ipa || '','maxlength="100" placeholder="/ˈæp.əl/"') + field('Nghĩa tiếng Việt *','meaning_vi',meaning?.meaning_vi || '','required maxlength="2000"',true,true) + field('Câu ví dụ tiếng Anh','sentence_en',example?.sentence_en || '',`maxlength="2000" ${example ? 'required' : ''}`,true,true) + field('Dịch câu ví dụ','sentence_vi',example?.sentence_vi || '','maxlength="2000"',true,true) + `<div class="field full"><span class="field-title">Chủ đề</span><div class="topic-checks">${state.data.topics.length ? state.data.topics.map(t => `<label><input type="checkbox" name="topic_ids" value="${t.topic_id}" ${item.topics?.some(x => x.topic_id === t.topic_id) ? 'checked' : ''}>${escape(t.symbol)} ${escape(t.name)}</label>`).join('') : '<span class="muted">Chưa có chủ đề. Bạn có thể bổ sung sau.</span>'}</div><small>Tối đa 50 chủ đề. Biểu mẫu sửa nghĩa và ví dụ đầu tiên, giữ nguyên các nội dung bổ sung.</small></div>`;

  showDialog(`${id ? 'Chỉnh sửa' : 'Thêm'} ${topic ? 'chủ đề' : 'từ vựng'}`,`<form id="edit-form" class="dialog-body"><div class="form-grid">${fields}</div><div id="form-error" role="alert"></div></form>`,'<button class="btn" type="button" data-close>Hủy</button><button class="btn primary" type="submit" form="edit-form" id="save">Lưu thay đổi</button>');
  const form = dialog.querySelector('#edit-form');
  form.onsubmit = async event => {
    event.preventDefault(); if (state.busy) return;
    const values = new FormData(form), payload = {};
    for (const [key,value] of values) if (key !== 'topic_ids') payload[key] = value.trim();
    if (!topic) payload.topic_ids = values.getAll('topic_ids').map(Number);
    if (!topic && payload.topic_ids.length > 50) { dialog.querySelector('#form-error').innerHTML = '<div class="error">Chỉ được chọn tối đa 50 chủ đề.</div>'; return; }
    await mutate(() => api(`/admin/${topic ? 'topics' : 'vocabularies'}${id ? `/${id}` : ''}`,{ method: id ? 'PUT' : 'POST',body: payload }),'Đã lưu thay đổi.');
  };
}

async function mutate(action,success) {
  state.busy = true; dialog.querySelectorAll('button').forEach(b => b.disabled = true);
  const errorTarget = dialog.querySelector('#form-error'); errorTarget.textContent = '';
  try { await action(); dialog.close(); toast(success); await load(); }
  catch (error) { if (dialog.open) errorTarget.innerHTML = `<div class="error">${escape(error.message)}</div>`; }
  finally { state.busy = false; dialog.querySelectorAll('button').forEach(b => b.disabled = false); }
}

function deleteTopic(id) {
  const topic = state.data.topics.find(t => t.topic_id === id); if (!topic || topic.vocabulary_count) return;
  showDialog('Xóa chủ đề?',`<div class="dialog-body"><p>Bạn sắp xóa chủ đề <strong>${escape(topic.name)}</strong>. Thao tác này không thể hoàn tác.</p><div id="form-error" role="alert"></div></div>`,'<button class="btn" data-close>Hủy</button><button class="btn danger" id="confirm-delete">Xóa chủ đề</button>');
  dialog.querySelector('#confirm-delete').onclick = () => mutate(() => api(`/admin/topics/${id}`,{method:'DELETE'}),'Đã xóa chủ đề.');
}

function details(id) {
  const word = state.data.words.find(w => w.vocabulary_id === id); if (!word) return;
  const detail = (label,value) => `<div class="detail-item"><small>${label}</small><div>${value}</div></div>`;
  showDialog(word.word,`<div class="dialog-body">${detail('PHIÊN ÂM',escape(word.ipa || 'Chưa có'))}${detail('NGHĨA TIẾNG VIỆT',word.meanings.map(m => `<p>${escape(m.meaning_vi)}</p>${m.definition_en ? `<p class="muted">${escape(m.definition_en)}</p>` : ''}`).join('') || 'Chưa có')}${detail('VÍ DỤ',word.examples.map(e => `<p>${escape(e.sentence_en)}</p><p class="muted">${escape(e.sentence_vi)}</p>`).join('') || 'Chưa có')}${detail('CHỦ ĐỀ',word.topics.map(t => `<span class="badge topic-badge">${escape(t.symbol)} ${escape(t.name)}</span>`).join(' ') || 'Chưa phân chủ đề')}${detail('TỪ LIÊN QUAN',word.relations.map(r => `<p>${escape(r.relation_type)}: ${escape(r.related_text || `#${r.related_vocabulary_id}`)}</p>`).join('') || 'Chưa có')}</div>`);
}

window.addEventListener('hashchange',async () => {
  if (!state.profile) return;
  const destination = getPage();
  if (state.busy) { location.replace(`#${state.page}`); return; }
  if (destination === state.page) return;
  if (dialog.open) dialog.close();
  state.query = ''; state.filter = ''; state.pagination = 1; state.userOffset = 0;
  shell(); const loaded = await load();
  if (pendingEditor) { const type = pendingEditor; pendingEditor = ''; if (loaded && ((type === 'word' && state.page === 'vocabulary') || (type === 'topic' && state.page === 'topics'))) editor(type); }
});

async function boot() {
  if (!state.token) { login(); return; }
  app.innerHTML = '<div class="loading" role="status"><span class="spinner"></span>Đang kiểm tra phiên đăng nhập…</div>';
  try {
    state.profile = await request('/users/me',{token:state.token});
    if (state.profile.role !== 'ADMIN') throw new Error('Tài khoản này không có quyền quản trị.');
    shell(); await load();
  } catch (error) { logout(); login(error.message); }
}

boot();
