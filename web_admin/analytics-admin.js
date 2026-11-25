const number = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 1 });
const format = value => value == null ? '—' : number.format(value);
const percent = value => value == null ? '—' : `${format(value)}%`;
const text = value => String(value ?? '').replace(/[&<>"']/g, char => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[char]));
const shortDate = value => {
  const [, month, day] = value.split('-');
  return `${day}/${month}`;
};
const learningMetrics = [
  ['active_learners', 'Người học hoạt động'],
  ['study_events', 'Lượt học'],
  ['accuracy_rate', 'Tỷ lệ đúng', true],
  ['next_day_return_rate', 'Tỷ lệ quay lại ngày kế tiếp', true],
];
const gameMetrics = [
  ['game_runs', 'Lượt chơi bắt đầu'],
  ['average_score', 'Điểm trung bình'],
  ['passed_rounds', 'Màn vượt qua'],
];

export function analyticsPage(container, api, mode, settings) {
  const learning = mode === 'learning';
  const metrics = learning ? learningMetrics : gameMetrics;
  container.innerHTML = `
    <form class="panel analytics-controls" aria-label="Bộ lọc thống kê">
      <label>Khoảng thời gian
        <select name="days">
          <option value="7">7 ngày</option><option value="30">30 ngày</option><option value="90">90 ngày</option>
        </select>
      </label>
      ${learning ? '' : `<label>Trò chơi
        <select name="game_type"><option value="">Tất cả</option>
          <option value="WORD_SHOOTER">Bắn chữ</option><option value="WORD_DEFENSE">Phòng tuyến từ vựng</option>
        </select></label>`}
    </form>
    <div class="analytics-results" aria-live="polite"></div>`;
  const form = container.querySelector('form');
  const results = container.querySelector('.analytics-results');
  form.elements.days.value = settings.days;
  if (!learning) form.elements.game_type.value = settings.gameType;

  let requestId = 0;
  async function fetchReport() {
    const current = ++requestId;
    const params = new URLSearchParams({ days: settings.days });
    if (!learning && settings.gameType) params.set('game_type', settings.gameType);
    results.innerHTML = '<div class="panel loading"><span class="spinner"></span>Đang tải thống kê…</div>';
    try {
      const report = await api(`/admin/analytics/${mode}?${params}`);
      if (current !== requestId || !container.isConnected) return;
      renderReport(results, report, learning, metrics, settings);
    } catch (error) {
      if (current !== requestId || !container.isConnected) return;
      results.innerHTML = '<div class="error" role="alert"></div>';
      results.firstElementChild.textContent = error.message;
    }
  }
  form.addEventListener('submit', event => event.preventDefault());
  form.addEventListener('change', () => {
    settings.days = form.elements.days.value;
    if (!learning) settings.gameType = form.elements.game_type.value;
    void fetchReport();
  });
  return fetchReport();
}

function renderReport(container, report, learning, metrics, settings) {
  const cards = learning ? [
    ['Người học hoạt động', format(report.active_learners), 'Số người học khác nhau trong kỳ'],
    ['Lượt học', format(report.study_events), 'Flashcard, quiz và trò chơi đã ghi nhận'],
    ['Tỷ lệ đúng', percent(report.accuracy_rate), `${format(report.correct_events)} / ${format(report.study_events)} lượt đúng`],
    ['Quay lại ngày kế tiếp', percent(report.next_day_return_rate), `${format(report.returned_learner_days)} / ${format(report.eligible_learner_days)} lượt người học theo ngày`],
  ] : [
    ['Lượt chơi bắt đầu', format(report.game_runs), 'Số lượt chơi được tạo trong kỳ'],
    ['Điểm trung bình', format(report.average_score), `Trên ${format(report.scored_runs)} lượt có màn đã chấm`],
    ['Màn vượt qua', format(report.passed_rounds), 'Số màn được ghi nhận vượt qua trong kỳ'],
  ];
  const dateRange = [report.start_date, report.end_date]
    .map(date => `${shortDate(date)}/${date.slice(0, 4)}`).join(' – ');
  container.innerHTML = `
    <p class="analytics-period muted">${text(dateRange)} · Giờ Việt Nam (UTC+7)</p>
    <div class="analytics-cards">${cards.map(([label, value, note]) => `
      <section class="panel analytics-card"><h2>${label}</h2><strong>${value}</strong><p>${note}</p></section>`).join('')}
    </div>
    <section class="panel analytics-panel" aria-labelledby="daily-report-heading">
      <div class="analytics-heading">
        <div><h2 id="daily-report-heading">Diễn biến theo ngày</h2><p>Chọn cột hoặc dùng phím mũi tên để xem từng ngày.</p></div>
        <label>Chỉ số <select id="daily-metric">${metrics.map(([key, label]) => `<option value="${key}">${label}</option>`).join('')}</select></label>
      </div>
      <div id="daily-chart"></div>
      <details class="analytics-daily-table">
        <summary>Xem bảng số liệu theo ngày</summary>
        ${reportTable(['Ngày', ...metrics.map(([, label]) => label)], report.daily.map(day =>
          [day.date, ...metrics.map(([key, , rate]) => rate ? percent(day[key]) : format(day[key]))]))}
      </details>
      ${learning ? '<p class="analytics-note">Tỷ lệ quay lại đo số người có hoạt động cả ngày gốc và ngày ngay sau đó, chia cho số người hoạt động ngày gốc. Chỉ tính các ngày đã quan sát trọn ngày kế tiếp. Dấu — là chưa đủ dữ liệu.</p>' : '<p class="analytics-note">Điểm trung bình lấy tổng điểm các màn được chấm trong kỳ chia cho số lượt có màn được chấm. Ngày ghi lượt chơi và ngày vượt màn có thể khác nhau.</p>'}
    </section>
    ${learning ? hardestWords(report.hardest_words) : missedWords(report.most_missed_words)}`;
  const select = container.querySelector('#daily-metric');
  select.value = metrics.some(([key]) => key === settings.metric) ? settings.metric : metrics[0][0];
  const chart = container.querySelector('#daily-chart');
  const updateChart = () => {
    settings.metric = select.value;
    renderChart(chart, report.daily, metrics.find(([key]) => key === select.value));
  };
  select.addEventListener('change', updateChart);
  updateChart();
}

function renderChart(container, days, [key, label, rate]) {
  const scale = rate ? 100 : Math.max(1, ...days.map(day => day[key] ?? 0));
  const stride = Math.ceil(days.length / 7);
  container.innerHTML = `
    <div class="analytics-scale" aria-hidden="true"><span>${rate ? percent(scale) : format(scale)}</span><span>0</span></div>
    <div class="analytics-chart-scroll"><div class="analytics-chart" role="group" aria-label="${text(label)} theo ngày">
      ${days.map((day, index) => {
        const value = day[key];
        const description = `${day.date} · ${label}: ${value == null ? 'Chưa đủ dữ liệu' : rate ? percent(value) : format(value)}`;
        const showDate = index === 0 || index === days.length - 1 || (index % stride === 0 && days.length - 1 - index >= stride / 2);
        return `<button type="button" class="analytics-point" tabindex="-1" title="${text(description)}" aria-label="${text(description)}">
          <span class="analytics-column"><span class="analytics-bar${value == null ? ' missing' : ''}" data-height="${(value ?? 0) / scale * 100}"></span></span>
          <span class="analytics-date" aria-hidden="true">${showDate ? shortDate(day.date) : ''}</span>
        </button>`;
      }).join('')}
    </div></div>
    <p class="analytics-chart-value" aria-live="polite"></p>`;
  const detail = container.querySelector('.analytics-chart-value');
  const points = Array.from(container.querySelectorAll('.analytics-point'));
  points.forEach((point, index) => {
    const bar = point.querySelector('.analytics-bar');
    bar.style.height = `${bar.dataset.height}%`;
    point.addEventListener('click', () => choose(point));
    point.addEventListener('focus', () => choose(point));
    point.addEventListener('keydown', event => {
      const destinations = {
        ArrowLeft: Math.max(0, index - 1), ArrowRight: Math.min(points.length - 1, index + 1),
        Home: 0, End: points.length - 1,
      };
      if (!Object.hasOwn(destinations, event.key)) return;
      event.preventDefault();
      const next = points[destinations[event.key]];
      choose(next);
      next.focus();
    });
  });
  if (points.length) {
    choose(points.at(-1));
    const scroll = container.querySelector('.analytics-chart-scroll');
    scroll.scrollLeft = scroll.scrollWidth;
  }
  function choose(point) {
    const previous = container.querySelector('.analytics-point.selected');
    if (previous) {
      previous.classList.remove('selected');
      previous.tabIndex = -1;
    }
    point.classList.add('selected');
    point.tabIndex = 0;
    detail.textContent = point.getAttribute('aria-label');
  }
}

function reportTable(headers, rows) {
  return `<div class="table-wrap"><table><thead><tr>${headers.map(header => `<th scope="col">${text(header)}</th>`).join('')}</tr></thead>
    <tbody>${rows.map(row => `<tr>${row.map(value => `<td>${text(value)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}

function hardestWords(words) {
  return `<section class="panel analytics-panel" aria-labelledby="hardest-heading"><div class="analytics-heading">
    <div><h2 id="hardest-heading">Từ khó</h2><p>Xếp theo tỷ lệ sai trong các lượt học đã ghi nhận.</p></div></div>
    ${words.length ? reportTable(['Từ vựng', 'Lượt học', 'Lượt sai', 'Tỷ lệ sai'], words.map(word =>
      [word.word, format(word.attempts), format(word.incorrect), percent(word.incorrect_rate)])) : '<p class="analytics-note">Chưa có từ trả lời sai trong kỳ.</p>'}
    </section>`;
}

function missedWords(words) {
  return `<section class="panel analytics-panel" aria-labelledby="missed-heading"><div class="analytics-heading">
    <div><h2 id="missed-heading">Từ thường bị bỏ lỡ</h2><p>Dựa trên kết quả từng từ trong các màn đã chấm.</p></div></div>
    ${words.length ? reportTable(['Từ vựng', 'Số lần bỏ lỡ'], words.map(word =>
      [word.word, format(word.misses)])) : '<p class="analytics-note">Chưa ghi nhận từ bị bỏ lỡ trong kỳ.</p>'}
    </section>`;
}
