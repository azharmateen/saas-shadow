/* saas-shadow client-side logic */

// === Theme Toggle ===
function initTheme() {
    const saved = localStorage.getItem('theme') || document.body.dataset.defaultTheme || 'dark';
    document.documentElement.setAttribute('data-theme', saved);
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
}

// === Modal ===
function showModal(id) {
    document.getElementById(id).classList.add('visible');
}

function hideModal(id) {
    document.getElementById(id).classList.remove('visible');
}

// === API Helper ===
async function api(method, url, data = null) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (data) opts.body = JSON.stringify(data);
    const resp = await fetch(url, opts);
    return resp.json();
}

// === Kanban Drag & Drop ===
let draggedCard = null;

function initKanban() {
    document.querySelectorAll('.kanban-card').forEach(card => {
        card.addEventListener('dragstart', (e) => {
            draggedCard = card;
            card.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', card.dataset.cardId);
        });
        card.addEventListener('dragend', () => {
            card.classList.remove('dragging');
            draggedCard = null;
            document.querySelectorAll('.kanban-drop-zone').forEach(z => z.classList.remove('drag-over'));
        });
    });

    document.querySelectorAll('.kanban-drop-zone').forEach(zone => {
        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            zone.classList.add('drag-over');
        });
        zone.addEventListener('dragleave', () => {
            zone.classList.remove('drag-over');
        });
        zone.addEventListener('drop', async (e) => {
            e.preventDefault();
            zone.classList.remove('drag-over');
            const cardId = e.dataTransfer.getData('text/plain');
            const targetColumn = zone.dataset.column;
            if (cardId && targetColumn) {
                await api('POST', `/api/cards/${cardId}/move`, { column: targetColumn, position: 0 });
                location.reload();
            }
        });
    });
}

// === Kanban Card CRUD ===
async function createCard() {
    const title = document.getElementById('card-title').value.trim();
    if (!title) return;
    const column = document.getElementById('card-column').value;
    const description = document.getElementById('card-description').value;
    await api('POST', '/api/cards', { title, column, description });
    hideModal('card-modal');
    location.reload();
}

async function deleteCard(id) {
    if (!confirm('Delete this card?')) return;
    await api('DELETE', `/api/cards/${id}`);
    location.reload();
}

// === Task CRUD ===
async function createTask() {
    const title = document.getElementById('task-title').value.trim();
    if (!title) return;
    const data = {
        title,
        description: document.getElementById('task-description').value,
        assignee: document.getElementById('task-assignee').value,
        due_date: document.getElementById('task-due-date').value,
        priority: document.getElementById('task-priority').value,
    };
    await api('POST', '/api/tasks', data);
    hideModal('task-modal');
    location.reload();
}

async function updateTaskStatus(id, status) {
    await api('PUT', `/api/tasks/${id}`, { status });
    location.reload();
}

async function deleteTask(id) {
    if (!confirm('Delete this task?')) return;
    await api('DELETE', `/api/tasks/${id}`);
    location.reload();
}

// === Wiki CRUD ===
async function createWikiPage() {
    const title = document.getElementById('wiki-title').value.trim();
    if (!title) return;
    const result = await api('POST', '/api/wiki', { title, content: '# ' + title + '\n\nStart writing...' });
    hideModal('wiki-modal');
    window.location.href = `/wiki/${result.slug}/edit`;
}

async function saveWikiPage(slug) {
    const content = document.getElementById('wiki-editor').value;
    const title = document.getElementById('wiki-page-title')?.value;
    await api('PUT', `/api/wiki/${slug}`, { content, title });
    window.location.href = `/wiki/${slug}`;
}

async function deleteWikiPage(slug) {
    if (!confirm('Delete this page?')) return;
    await api('DELETE', `/api/wiki/${slug}`);
    window.location.href = '/wiki';
}

// === Wiki Live Preview ===
function initWikiPreview() {
    const editor = document.getElementById('wiki-editor');
    const preview = document.getElementById('wiki-preview');
    if (!editor || !preview) return;

    editor.addEventListener('input', () => {
        // Simple markdown preview (basic)
        let html = editor.value
            .replace(/^### (.+)$/gm, '<h3>$1</h3>')
            .replace(/^## (.+)$/gm, '<h2>$1</h2>')
            .replace(/^# (.+)$/gm, '<h1>$1</h1>')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<em>$1</em>')
            .replace(/`(.+?)`/g, '<code>$1</code>')
            .replace(/^- (.+)$/gm, '<li>$1</li>')
            .replace(/\n\n/g, '<br><br>')
            .replace(/\n/g, '<br>');
        preview.innerHTML = html;
    });
}

// === AI Breakdown ===
async function aiBreakdown() {
    const desc = document.getElementById('ai-description').value.trim();
    if (!desc) return;
    const btn = document.getElementById('ai-btn');
    btn.textContent = 'Thinking...';
    btn.disabled = true;

    try {
        const result = await api('POST', '/api/ai/breakdown', { description: desc });
        const tasks = result.tasks || [];
        const container = document.getElementById('ai-results');
        container.innerHTML = '';

        if (tasks.length === 0) {
            container.innerHTML = '<p>No tasks generated.</p>';
            return;
        }

        tasks.forEach(t => {
            const div = document.createElement('div');
            div.className = 'card';
            div.innerHTML = `
                <h3>${t.title}</h3>
                <p style="color:var(--text-muted);font-size:13px">${t.description || ''}</p>
                <div style="margin-top:8px;display:flex;gap:8px;font-size:12px">
                    <span class="priority-badge priority-${t.priority}">${t.priority}</span>
                    <span>${t.estimated_hours}h estimated</span>
                    ${t.assignee ? `<span>${t.assignee}</span>` : ''}
                </div>
                <button class="btn btn-sm btn-primary" style="margin-top:8px" onclick="importTask(this, '${t.title.replace(/'/g, "\\'")}', '${(t.description || '').replace(/'/g, "\\'")}', '${t.priority}')">Import as Task</button>
            `;
            container.appendChild(div);
        });

        const source = result.source === 'ai' ? 'AI' : 'Heuristic';
        container.insertAdjacentHTML('afterbegin', `<p style="color:var(--text-muted);font-size:12px;margin-bottom:12px">Generated ${tasks.length} tasks via ${source}</p>`);
    } catch (e) {
        console.error(e);
    } finally {
        btn.textContent = 'Break Down';
        btn.disabled = false;
    }
}

async function importTask(btn, title, description, priority) {
    await api('POST', '/api/tasks', { title, description, priority });
    btn.textContent = 'Imported';
    btn.disabled = true;
    btn.classList.remove('btn-primary');
}

// === Init ===
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    if (document.querySelector('.kanban-board')) initKanban();
    if (document.getElementById('wiki-editor')) initWikiPreview();
});
