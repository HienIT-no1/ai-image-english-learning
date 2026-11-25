const quizTypes = {
  IMAGE_TO_WORD: 'Nhìn hình chọn từ',
  WORD_TO_IMAGE: 'Nhìn từ chọn hình',
  LISTENING: 'Nghe chọn từ',
  FILL_BLANK: 'Điền từ',
  MIXED: 'Tổng hợp',
};
const statuses = {IN_PROGRESS: 'Đang làm', COMPLETED: 'Hoàn thành', ABORTED: 'Đã bỏ dở'};
const number = new Intl.NumberFormat('vi-VN');
const percent = new Intl.NumberFormat('vi-VN', {style:'percent', maximumFractionDigits:1});
const date = new Intl.DateTimeFormat('vi-VN', {dateStyle:'short', timeStyle:'short', timeZone:'Asia/Ho_Chi_Minh'});
const fmt = value => number.format(value);
const when = value => value ? date.format(new Date(value)) : '—';
const rate = (correct, total) => total ? percent.format(correct / total) : '—';
const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({
  '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;',
})[char]);

function label(options, key) {
  return escape(Object.hasOwn(options, key) ? options[key] : key);
}

function selectOptions(options) {
  return Object.entries(options).map(([value, text]) => `<option value="${value}">${text}</option>`).join('');
}

function statusBadge(status) {
  const variant = status === 'COMPLETED' ? 'user' : status === 'ABORTED' ? 'neutral' : 'admin';
  return `<span class="badge ${variant}">${label(statuses, status)}</span>`;
}

function table(headers, rows, empty) {
  if (!rows.length) return `<div class="empty">${empty}</div>`;
  const headings = headers.map(text => `<th scope="col">${text}</th>`).join('');
  return `<div class="table-wrap"><table><thead><tr>${headings}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
}

function summaryMarkup(stats) {
  const metrics = [['Tổng lượt', stats.total], ['Hoàn thành', stats.completed], ['Đang làm', stats.in_progress], ['Đã bỏ dở', stats.aborted]];
  const kinds = stats.by_quiz_type.map(item => `<tr><td>${label(quizTypes,item.quiz_type)}</td><td>${fmt(item.total)}</td><td>${fmt(item.completed)}</td><td>${fmt(item.in_progress)}</td><td>${fmt(item.aborted)}</td></tr>`);
  const questions = stats.by_question_type.map(item => `<tr><td>${label(quizTypes,item.question_type)}</td><td>${fmt(item.answered)}</td><td>${fmt(item.correct)}</td><td>${rate(item.correct,item.answered)}</td></tr>`);
  const words = stats.common_misses.map(item => `<tr><td>${escape(item.word)}</td><td>${fmt(item.missed)} / ${fmt(item.answered)}</td><td>${rate(item.missed,item.answered)}</td></tr>`);
  return `<div class="stats" aria-label="Tổng quan quiz">${metrics.map(([name,value]) => `<article class="stat"><div class="stat-top">${name}</div><div class="stat-number">${fmt(value)}</div></article>`).join('')}</div>
    <details class="panel">
      <summary class="panel-head">Thống kê toàn bộ lịch sử quiz</summary>
      <div class="panel-head"><h3>Lượt làm theo dạng bài</h3></div>
      ${table(['Dạng bài','Tổng lượt','Hoàn thành','Đang làm','Đã bỏ dở'],kinds,'Chưa có lượt làm quiz.')}
      <div class="panel-head"><h3>Kết quả theo dạng câu hỏi</h3><p>Tính trên các câu đã trả lời, kể cả bài chưa hoàn thành.</p></div>
      ${table(['Dạng câu hỏi','Đã trả lời','Đúng','Tỷ lệ đúng'],questions,'Chưa có câu trả lời.')}
      <div class="panel-head"><h3>Từ thường trả lời sai</h3></div>
      ${table(['Từ vựng','Sai / Đã trả lời','Tỷ lệ sai'],words,'Chưa ghi nhận câu trả lời sai.')}
    </details>`;
}

function attemptsMarkup(page) {
  const rows = page.items.map(item => `<tr>
    <td>#${fmt(item.attempt_id)}</td>
    <td><strong>${escape(item.full_name || item.username)}</strong>${item.full_name ? `<br><small class="muted">@${escape(item.username)}</small>` : ''}</td>
    <td>${label(quizTypes,item.quiz_type)}</td><td>${statusBadge(item.status)}</td>
    <td>${fmt(item.answered_count)} / ${fmt(item.total_questions)}</td><td>${fmt(item.correct_answers)}</td>
    <td>${when(item.started_at)}</td>
    <td><button class="icon-btn" type="button" data-quiz-details="${Number(item.attempt_id)}" aria-label="Xem lượt quiz ${fmt(item.attempt_id)}">Chi tiết</button></td>
  </tr>`);
  const pageNumber = Math.floor(page.offset / page.limit) + 1;
  const lastPage = Math.max(1, Math.ceil(page.total / page.limit));
  const shown = page.items.length ? `${fmt(page.offset + 1)}–${fmt(page.offset + page.items.length)}` : '0';
  return `${table(['Mã lượt','Người học','Dạng bài','Trạng thái','Đã trả lời','Số câu đúng','Bắt đầu','Thao tác'],rows,'Không tìm thấy lượt quiz phù hợp.')}
    <div class="table-foot"><span>${shown} / ${fmt(page.total)} lượt</span>
      <div class="pager"><button type="button" data-quiz-page="previous" ${pageNumber > 1 ? '' : 'disabled'}>Trước</button>
      <span>Trang ${fmt(pageNumber)} / ${fmt(lastPage)}</span>
      <button type="button" data-quiz-page="next" ${pageNumber < lastPage ? '' : 'disabled'}>Sau</button></div>
    </div>`;
}

function detailMarkup(attempt) {
  const rows = attempt.questions.map(item => {
    const result = item.is_correct === null ? 'Chưa trả lời' : item.is_correct ? 'Đúng' : 'Sai';
    const options = item.options.length ? `<br><small class="muted">Lựa chọn: ${item.options.map(option => escape(item.question_type === 'WORD_TO_IMAGE' ? option.meaning_vi || option.word : option.word)).join(' · ')}</small>` : '';
    return `<tr><td>${fmt(item.position)}</td><td>${label(quizTypes,item.question_type)}</td>
      <td>${escape(item.word)}${item.meaning_vi ? `<br><small class="muted">${escape(item.meaning_vi)}</small>` : ''}${options}</td>
      <td>${escape(item.user_answer ?? '—')}</td><td>${escape(item.correct_answer ?? '—')}</td><td>${result}</td><td>${when(item.answered_at)}</td></tr>`;
  });
  const finished = attempt.completed_at ? `Hoàn thành ${when(attempt.completed_at)}` : attempt.aborted_at ? `Bỏ dở ${when(attempt.aborted_at)}` : '';
  return `<div class="detail-item"><small>NGƯỜI HỌC</small><div>${escape(attempt.full_name || attempt.username)}${attempt.full_name ? ` · @${escape(attempt.username)}` : ''}</div></div>
    <div class="detail-item"><small>KẾT QUẢ</small><div>${label(quizTypes,attempt.quiz_type)} · ${statusBadge(attempt.status)}<br>
    Đã trả lời ${fmt(attempt.answered_count)} / ${fmt(attempt.total_questions)} · Đúng ${fmt(attempt.correct_answers)} câu<br>Bắt đầu ${when(attempt.started_at)}${finished ? ` · ${finished}` : ''}</div></div>
    <div class="detail-item"><small>CÂU HỎI VÀ ĐÁP ÁN</small>${table(['Câu','Dạng câu','Từ','Câu trả lời','Đáp án đúng','Kết quả','Thời gian'],rows,'Lượt quiz này chưa có câu hỏi hoặc câu trả lời được lưu.')}</div>`;
}

export async function quizAdminPage(container, api) {
  container.innerHTML = `<section id="quiz-stats" aria-label="Thống kê quiz"></section>
    <section class="panel" aria-labelledby="quiz-attempts-title">
      <div class="panel-head"><h2 id="quiz-attempts-title">Lịch sử làm quiz</h2></div>
      <form class="toolbar" id="quiz-filters">
        <div class="search"><input type="search" id="quiz-search" name="q" maxlength="100" aria-label="Tìm lượt quiz" placeholder="Tên người học, tên đăng nhập hoặc mã lượt"></div>
        <select id="quiz-kind" name="quiz_type" aria-label="Dạng bài"><option value="">Tất cả dạng bài</option>${selectOptions(quizTypes)}</select>
        <select id="quiz-status" name="status" aria-label="Trạng thái"><option value="">Tất cả trạng thái</option>${selectOptions(statuses)}</select>
        <button class="btn" type="submit">Tìm</button>
      </form>
      <div id="quiz-attempts"></div>
    </section>
    <dialog id="quiz-dialog" aria-labelledby="quiz-dialog-title">
      <div class="dialog-head"><h2 id="quiz-dialog-title"></h2></div>
      <div class="dialog-body" id="quiz-dialog-body"></div>
      <form method="dialog" class="dialog-foot"><button class="btn" type="submit">Đóng</button></form>
    </dialog>`;

  const stats = container.querySelector('#quiz-stats');
  const list = container.querySelector('#quiz-attempts');
  const filter = container.querySelector('#quiz-filters');
  const dialog = container.querySelector('#quiz-dialog');
  const dialogBody = container.querySelector('#quiz-dialog-body');
  const pageSize = 20;
  let offset = 0;
  let listVersion = 0;
  let detailVersion = 0;
  let appliedSearch = '';
  const loading = '<div class="loading" role="status">Đang tải dữ liệu…</div>';
  const errorMarkup = error => `<div class="error" role="alert">${escape(error.message)}</div>`;

  async function fetchSummary() {
    stats.innerHTML = loading;
    try {
      const data = await api('/admin/quizzes/summary');
      if (container.isConnected) stats.innerHTML = summaryMarkup(data);
    } catch (error) {
      if (container.isConnected) stats.innerHTML = errorMarkup(error);
    }
  }

  async function showDetails(id) {
    const version = ++detailVersion;
    container.querySelector('#quiz-dialog-title').textContent = `Lượt quiz #${fmt(id)}`;
    dialogBody.innerHTML = loading;
    if (!dialog.open) dialog.showModal();
    try {
      const item = await api(`/admin/quizzes/${id}`);
      if (container.isConnected && dialog.open && version === detailVersion) dialogBody.innerHTML = detailMarkup(item);
    } catch (error) {
      if (container.isConnected && dialog.open && version === detailVersion) dialogBody.innerHTML = errorMarkup(error);
    }
  }

  async function fetchAttempts(repairOffset = true) {
    const version = ++listVersion;
    list.innerHTML = loading;
    const params = new URLSearchParams({limit:pageSize,offset});
    if (appliedSearch) params.set('q', appliedSearch);
    for (const key of ['quiz_type','status']) {
      const value = filter.elements.namedItem(key).value;
      if (value) params.set(key, value);
    }
    try {
      const data = await api(`/admin/quizzes?${params}`);
      if (!container.isConnected || version !== listVersion) return;
      if (repairOffset && offset && !data.items.length) {
        offset = Math.min(offset - pageSize, Math.max(0, (Math.ceil(data.total / pageSize) - 1) * pageSize));
        return fetchAttempts(false);
      }
      list.innerHTML = attemptsMarkup(data);
    } catch (error) {
      if (container.isConnected && version === listVersion) list.innerHTML = errorMarkup(error);
    }
  }

  function applyFilters() {
    appliedSearch = filter.elements.namedItem('q').value.trim();
    offset = 0;
    fetchAttempts();
  }

  filter.addEventListener('submit', event => {
    event.preventDefault();
    applyFilters();
  });
  filter.querySelectorAll('select').forEach(select => select.addEventListener('change', applyFilters));
  list.addEventListener('click', event => {
    const detail = event.target.closest('[data-quiz-details]');
    if (detail) showDetails(Number(detail.dataset.quizDetails));
    const page = event.target.closest('[data-quiz-page]');
    if (page && !page.disabled) {
      offset = Math.max(0, offset + (page.dataset.quizPage === 'next' ? pageSize : -pageSize));
      fetchAttempts();
    }
  });
  await Promise.all([fetchSummary(), fetchAttempts()]);
}
