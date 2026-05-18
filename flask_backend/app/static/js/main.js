// Main JavaScript for Herons' Hub

/**
 * Shared Post Management Functions
 */

function ensureInlineDialog() {
    let modal = document.getElementById('inlineActionDialog');
    if (modal) return modal;

    modal = document.createElement('div');
    modal.id = 'inlineActionDialog';
    modal.style.cssText = [
        'display:none',
        'position:fixed',
        'inset:0',
        'z-index:4000',
        'align-items:center',
        'justify-content:center',
        'padding:16px',
        'background:rgba(2,6,23,0.45)',
        'backdrop-filter:blur(3px)'
    ].join(';');
    modal.innerHTML = `
        <div style="width:100%;max-width:28rem;border-radius:18px;background:#fff;border:1px solid #e2e8f0;box-shadow:0 20px 40px rgba(2,6,23,0.25);overflow:hidden;">
            <div style="padding:16px 20px;border-bottom:1px solid #f1f5f9;">
                <h3 id="inlineActionDialogTitle" style="margin:0;font-size:16px;line-height:1.2;font-weight:800;color:#0f172a;">Confirm Action</h3>
                <p id="inlineActionDialogMessage" style="margin:8px 0 0;font-size:14px;line-height:1.45;font-weight:600;color:#475569;"></p>
            </div>
            <div id="inlineActionDialogInputWrap" style="display:none;padding:14px 20px 8px;">
                <label id="inlineActionDialogInputLabel" for="inlineActionDialogInput" style="display:block;margin-bottom:8px;font-size:11px;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;color:#94a3b8;">Reason</label>
                <input id="inlineActionDialogInput" type="text" style="width:100%;border:1px solid #dbe3ef;border-radius:12px;background:#f8fafc;padding:10px 12px;font-size:14px;font-weight:600;color:#334155;outline:none;" />
            </div>
            <div style="padding:12px 20px 18px;display:flex;align-items:center;justify-content:flex-end;gap:10px;">
                <button id="inlineActionDialogCancel" type="button" style="padding:9px 14px;border:none;border-radius:12px;background:#f1f5f9;color:#475569;font-size:13px;font-weight:700;cursor:pointer;">Cancel</button>
                <button id="inlineActionDialogConfirm" type="button" style="padding:9px 16px;border:none;border-radius:12px;background:#111942;color:#fff;font-size:13px;font-weight:800;cursor:pointer;">Confirm</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    return modal;
}

function showInlineDialog(options = {}) {
    const {
        title = 'Confirm Action',
        message = 'Are you sure you want to continue?',
        confirmText = 'Confirm',
        cancelText = 'Cancel',
        requireInput = false,
        inputLabel = 'Reason',
        inputPlaceholder = 'Type here...',
        defaultValue = '',
    } = options;

    const modal = ensureInlineDialog();
    const titleEl = document.getElementById('inlineActionDialogTitle');
    const messageEl = document.getElementById('inlineActionDialogMessage');
    const inputWrap = document.getElementById('inlineActionDialogInputWrap');
    const inputLabelEl = document.getElementById('inlineActionDialogInputLabel');
    const inputEl = document.getElementById('inlineActionDialogInput');
    const cancelBtn = document.getElementById('inlineActionDialogCancel');
    const confirmBtn = document.getElementById('inlineActionDialogConfirm');

    titleEl.textContent = title;
    messageEl.textContent = message;
    cancelBtn.textContent = cancelText;
    confirmBtn.textContent = confirmText;

    if (requireInput) {
        inputWrap.style.display = 'block';
        inputLabelEl.textContent = inputLabel;
        inputEl.value = defaultValue;
        inputEl.placeholder = inputPlaceholder;
    } else {
        inputWrap.style.display = 'none';
        inputEl.value = '';
    }

    modal.style.display = 'flex';

    if (requireInput) {
        setTimeout(() => inputEl.focus(), 0);
    } else {
        setTimeout(() => confirmBtn.focus(), 0);
    }

    return new Promise((resolve) => {
        let settled = false;
        const finish = (confirmed) => {
            if (settled) return;
            settled = true;
            modal.style.display = 'none';
            document.removeEventListener('keydown', escHandler);
            resolve({
                confirmed,
                value: requireInput ? (inputEl.value || '') : ''
            });
        };

        const escHandler = (event) => {
            if (event.key === 'Escape') finish(false);
        };

        document.addEventListener('keydown', escHandler);
        modal.onclick = (event) => {
            if (event.target === modal) finish(false);
        };
        cancelBtn.onclick = () => finish(false);
        confirmBtn.onclick = () => finish(true);
    });
}

function togglePostMenu(postId, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const menu = document.getElementById(`post-menu-${postId}`);
    const allMenus = document.querySelectorAll('.post-menu-dropdown');

    // Close others
    allMenus.forEach(m => {
        if (m.id !== `post-menu-${postId}`) m.classList.add('hidden');
    });

    if (menu) {
        menu.classList.toggle('hidden');
    }
}

function toggleSaveMenu(postId, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const menu = document.getElementById(`save-menu-${postId}`);
    const allMenus = document.querySelectorAll('[id^="save-menu-"]');

    // Close others
    allMenus.forEach(m => {
        if (m.id !== `save-menu-${postId}`) m.classList.add('hidden');
    });

    if (menu) {
        menu.classList.toggle('hidden');
    }
}

// Global click listener to close menus when clicking outside
document.addEventListener('click', (e) => {
    const isMenuButton = e.target.closest('button[onclick^="togglePostMenu"]') || e.target.closest('button[onclick^="toggleSaveMenu"]');
    const isInsideMenu = e.target.closest('.post-menu-dropdown') || e.target.closest('[id^="save-menu-"]');
    
    if (!isMenuButton && !isInsideMenu) {
        document.querySelectorAll('.post-menu-dropdown').forEach(m => m.classList.add('hidden'));
        document.querySelectorAll('[id^="save-menu-"]').forEach(m => m.classList.add('hidden'));
    }
});

function saveToGoogle(title, startStr, endStr, location, details) {
    const formatDate = (dateStr) => {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        return d.toISOString().replace(/-|:|\.\d\d\d/g, "");
    };

    const start = formatDate(startStr);
    const end = endStr ? formatDate(endStr) : formatDate(new Date(new Date(startStr).getTime() + 3600000)); // Default +1 hour

    const url = new URL('https://calendar.google.com/calendar/render');
    url.searchParams.append('action', 'TEMPLATE');
    url.searchParams.append('text', title);
    url.searchParams.append('dates', `${start}/${end}`);
    url.searchParams.append('details', details);
    url.searchParams.append('location', location);
    url.searchParams.append('sf', 'true');
    url.searchParams.append('output', 'xml');

    window.open(url.toString(), '_blank');
}

function downloadICS(title, startStr, endStr, location, details) {
    const formatDate = (dateStr) => {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        return d.toISOString().replace(/-|:|\.\d\d\d/g, "").split('Z')[0] + 'Z';
    };

    const start = formatDate(startStr);
    const end = endStr ? formatDate(endStr) : formatDate(new Date(new Date(startStr).getTime() + 3600000));

    const icsContent = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//Herons Hub//Event Calendar//EN',
        'BEGIN:VEVENT',
        `UID:${Date.now()}@heronshub.social`,
        `DTSTAMP:${formatDate(new Date())}`,
        `DTSTART:${start}`,
        `DTEND:${end}`,
        `SUMMARY:${title}`,
        `DESCRIPTION:${details.replace(/\n/g, '\\n')}`,
        `LOCATION:${location}`,
        'END:VEVENT',
        'END:VCALENDAR'
    ].join('\r\n');

    const blob = new Blob([icsContent], { type: 'text/calendar;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `${title.replace(/\s+/g, '_')}.ics`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function showEditForm(postId) {
    const content = document.getElementById(`post-content-${postId}`);
    const form = document.getElementById(`edit-form-${postId}`);
    if (content) content.classList.add('hidden');
    if (form) form.classList.remove('hidden');
}

function hideEditForm(postId) {
    const content = document.getElementById(`post-content-${postId}`);
    const form = document.getElementById(`edit-form-${postId}`);
    if (content) content.classList.remove('hidden');
    if (form) form.classList.add('hidden');
}

async function confirmDeletePost(postId) {
    if (typeof showConfirmModal !== 'function') {
        const decision = await showInlineDialog({
            title: 'Delete Post?',
            message: 'Are you sure you want to delete this post? This action cannot be undone.',
            confirmText: 'Delete',
            cancelText: 'Cancel'
        });
        if (!decision.confirmed) return;
        executeDelete(postId);
        return;
    }
    showConfirmModal(
        'Delete Post?',
        'Are you sure you want to delete this post? This action cannot be undone.',
        async () => executeDelete(postId)
    );
}

async function executeDelete(postId) {
    try {
        const response = await fetch(`/posts/${postId}/delete`, { 
            method: 'POST', 
            headers: { 'X-CSRFToken': getCSRFToken() } 
        });
        const data = await response.json();
        if (data.status === 'deleted') {
            if (window.createToast) window.createToast('Post deleted successfully.', 'success');
            const card = document.querySelector(`.post-card[data-post-id="${postId}"]`);
            if (card) {
                card.style.opacity = '0';
                card.style.transform = 'scale(0.95)';
                setTimeout(() => card.remove(), 300);
            } else {
                window.location.reload();
            }
        } else {
            if (window.createToast) window.createToast(data.error || 'Failed to delete post', 'error');
        }
    } catch (error) {
        console.error('Error deleting post:', error);
        if (window.createToast) window.createToast('An unexpected error occurred.', 'error');
    }
}

async function reportPost(postId) {
    const decision = await showInlineDialog({
        title: 'Report Post',
        message: 'Why are you reporting this post? (e.g., Harassment, Spam, Misinformation)',
        confirmText: 'Submit',
        cancelText: 'Cancel',
        requireInput: true,
        inputLabel: 'Report Reason',
        inputPlaceholder: 'Describe the reason for your report',
        defaultValue: 'Inappropriate content'
    });
    if (!decision.confirmed) return;

    const trimmedReason = (decision.value || '').trim();
    if (!trimmedReason) {
        if (window.createToast) window.createToast('Report reason is required.', 'error');
        return;
    }

    try {
        const response = await fetch(`/posts/${postId}/report`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({ reason: trimmedReason })
        });
        const data = await response.json();

        if (data.status === 'reported') {
            if (window.createToast) window.createToast('Report submitted. Thank you.', 'success');
            return;
        }
        if (data.status === 'already_reported') {
            if (window.createToast) window.createToast('You already reported this post.', 'info');
            return;
        }

        if (window.createToast) window.createToast(data.error || 'Failed to report post.', 'error');
    } catch (error) {
        console.error('Error reporting post:', error);
        if (window.createToast) window.createToast('Failed to report post.', 'error');
    }
}

/**
 * Admin Shared Functions
 */

async function flagPost(postId) {
    if (typeof showConfirmModal === 'function') {
        showConfirmModal('Flag Post?', 'Flag this post for further review?', async () => executeFlagPost(postId));
        return;
    }
    const decision = await showInlineDialog({
        title: 'Flag Post?',
        message: 'Flag this post for further review?',
        confirmText: 'Flag',
        cancelText: 'Cancel'
    });
    if (!decision.confirmed) return;
    await executeFlagPost(postId);
}

async function executeFlagPost(postId) {
    try {
        const res = await fetch(`/admin/posts/${postId}/flag`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() }
        });
        const data = await res.json();
        if (data.status === 'success') {
            if (window.createToast) window.createToast('Post flagged', 'success');
        }
    } catch (e) { 
        if (window.createToast) window.createToast('Action failed', 'error'); 
    }
}

async function flagComment(commentId) {
    if (typeof showConfirmModal === 'function') {
        showConfirmModal('Flag Comment?', 'Flag this comment for further review?', async () => executeFlagComment(commentId));
        return;
    }
    const decision = await showInlineDialog({
        title: 'Flag Comment?',
        message: 'Flag this comment for further review?',
        confirmText: 'Flag',
        cancelText: 'Cancel'
    });
    if (!decision.confirmed) return;
    await executeFlagComment(commentId);
}

async function executeFlagComment(commentId) {
    try {
        const res = await fetch(`/admin/comments/${commentId}/flag`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() }
        });
        const data = await res.json();
        if (data.status === 'success') {
            if (window.createToast) window.createToast('Comment flagged', 'success');
        }
    } catch (e) { 
        if (window.createToast) window.createToast('Action failed', 'error'); 
    }
}

// CSRF Token Helper
function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}
