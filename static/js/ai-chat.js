function formatSafeMarkdown(text) {
    if (!text) return '';
    return text
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/\*\*(.*?)\*\*/g, '<strong class="text-warning">$1</strong>')
        .replace(/\n/g, '<br>');
}

function toggleAIDrawer() {
    document.getElementById('ai-drawer')?.classList.toggle('open');
}

function sendQuickPrompt(text, targetInputId = 'ai-chat-input', targetListId = 'ai-messages-list') {
    const input = document.getElementById(targetInputId);
    if (input) {
        input.value = text;
        sendAIMessage(new Event('submit'), targetInputId, targetListId);
    }
}

async function sendAIMessage(e, inputId = 'ai-chat-input', listId = 'ai-messages-list') {
    if (e && e.preventDefault) e.preventDefault();
    const input = document.getElementById(inputId);
    const list = document.getElementById(listId);
    const text = (input?.value || '').trim();
    if (!text || !list) return;
    input.value = '';

    list.innerHTML += `<div class="msg-bubble msg-user">${formatSafeMarkdown(text)}</div>`;
    const tempId = 'ai-load-' + Date.now();
    list.innerHTML += `<div id="${tempId}" class="msg-bubble msg-assistant text-warning"><span class="spinner-grow spinner-grow-sm me-2"></span>Analyzing vehicle telemetry & live grid...</div>`;
    list.scrollTop = list.scrollHeight;

    try {
        const res = await fetch('/api/ai/chat/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
            body: JSON.stringify({ message: text })
        });
        const data = await res.json();
        document.getElementById(tempId)?.remove();

        let btns = '<div class="mt-2 d-flex flex-wrap gap-1">';
        (data.actions || []).forEach(a => {
            if (a.url) {
                btns += `<a href="${a.url}" class="btn btn-sm btn-gridx py-1 px-2" style="font-size:0.74rem;">${a.label}</a>`;
            } else if (a.category_slug) {
                btns += `<a href="/dashboard/?cat=${a.category_slug}#booking-section" class="btn btn-sm btn-gridx-outline py-1 px-2" style="font-size:0.74rem;">${a.label}</a>`;
            }
        });
        btns += '</div>';

        list.innerHTML += `<div class="msg-bubble msg-assistant">${formatSafeMarkdown(data.reply)}${btns}</div>`;
        list.scrollTop = list.scrollHeight;
    } catch (err) {
        document.getElementById(tempId)?.remove();
        list.innerHTML += `<div class="msg-bubble msg-assistant text-danger">Connection interrupted. Turn on hazard lights if stranded.</div>`;
    }
}
