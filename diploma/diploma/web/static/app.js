const DEFAULT_TOPIC =
	'Применение методов машинного обучения для автоматизированной диагностики мочекаменной болезни по данным компьютерной томографии';

const $ = (id) => document.getElementById(id);
const form = $('form');
const progressCard = $('progressCard');
const resultCard = $('resultCard');
let pollTimer = null;

$('topic').value = localStorage.getItem('topic') || DEFAULT_TOPIC;

form.addEventListener('submit', async (e) => {
	e.preventDefault();
	localStorage.setItem('topic', $('topic').value);
	startJob();
});

async function startJob() {
	progressCard.hidden = false;
	resultCard.hidden = true;
	$('steps').innerHTML = '';
	$('files').innerHTML = '';
	$('stats').innerHTML = '';
	$('warnings').hidden = true;
	setProgress(0, 'Отправка задания…');

	const payload = {
		topic: $('topic').value.trim(),
		work_type: $('work_type').value,
		bib_style: $('bib_style').value,
		author: $('author').value,
		group: $('group').value,
		chair: $('chair').value,
		supervisor: $('supervisor').value,
		institution: $('institution').value,
		city: $('city').value,
		year: $('year').value,
		max_sources: Number($('max_sources').value || 20),
		offline: $('offline').checked,
		export_quarto: $('export_quarto').checked,
		make_zip: $('make_zip').checked
	};

	const res = await fetch('/api/generate', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(payload)
	});
	const data = await res.json();
	if (!res.ok) {
		setProgress(0, 'Ошибка: ' + (data.error || res.status));
		return;
	}
	poll(data.id);
}

function setProgress(percent, text) {
	$('bar').style.width = Math.max(2, Math.min(100, percent)) + '%';
	$('progressText').textContent = text;
}

function addStep(text, ok = true) {
	const li = document.createElement('li');
	li.textContent = (ok ? '✓ ' : '• ') + text;
	$('steps').appendChild(li);
}

async function poll(id) {
	clearTimeout(pollTimer);
	try {
		const res = await fetch('/api/jobs/' + id);
		const job = await res.json();
		const pct = (job.step / (job.total || 9)) * 100;
		setProgress(pct, `${job.step}/${job.total} · ${job.message}`);
		if (job.message && job.message !== lastMessage) {
			addStep(job.message, job.status !== 'error');
			lastMessage = job.message;
		}
		if (job.status === 'running' || job.status === 'queued') {
			pollTimer = setTimeout(() => poll(id), 700);
		} else if (job.status === 'done') {
			setProgress(100, 'Готово');
			showResult(id, job);
		} else if (job.status === 'error') {
			setProgress(100, 'Ошибка: ' + job.message);
			$('warnings').hidden = false;
			$('warnings').innerHTML =
				'<b>Ошибка конвейера</b><pre>' + escapeHtml((job.warnings || []).join('\n')) + '</pre>';
		}
	} catch (err) {
		pollTimer = setTimeout(() => poll(id), 1200);
	}
}

let lastMessage = '';

function showResult(id, job) {
	resultCard.hidden = false;
	const s = job.stats || {};
	$('stats').innerHTML = [
		stat('Источников', `${s.verified || 0} / ${s.sources || 0} проверено`),
		stat('Разделов', s.sections || 0),
		stat('Рисунков', s.figures || 0),
		stat('Таблиц', s.tables || 0)
	].join('');

	const files = job.files || {};
	const order = [
		'DOCX',
		'PDF',
		'HTML',
		'Markdown',
		'BibTeX',
		'ZIP',
		'Quarto',
		'План',
		'Протокол проверки',
		'Данные (JSON)'
	];
	const keys = [
		...order.filter((k) => files[k]),
		...Object.keys(files).filter((k) => !order.includes(k))
	];
	$('files').innerHTML = keys
		.map((label) => {
			const p = files[label];
			const name = p.split('/').pop();
			return `<a class="file" href="/api/jobs/${id}/download/${encodeURIComponent(label)}">
				<span class="ficon">${icon(label)}</span>
				<span class="fname"><b>${label}</b><small>${escapeHtml(name)}</small></span>
				<span class="fgo">скачать ↓</span>
			</a>`;
		})
		.join('');

	if ((job.warnings || []).length) {
		$('warnings').hidden = false;
		$('warnings').innerHTML =
			'<b>Предупреждения</b><ul>' +
			job.warnings.map((w) => `<li>${escapeHtml(w)}</li>`).join('') +
			'</ul>';
	}
}

function stat(label, value) {
	return `<div class="stat"><b>${value}</b><span>${label}</span></div>`;
}
function icon(label) {
	return (
		{ DOCX: '📄', PDF: '📕', HTML: '🌐', ZIP: '🗜️', BibTeX: '📚', Quarto: '⚙️' }[label] || '📎'
	);
}
function escapeHtml(s) {
	return String(s).replace(
		/[&<>"]/g,
		(c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]
	);
}
