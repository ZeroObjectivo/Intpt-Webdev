// Main JavaScript for Herons' Hub

/**
 * Shared Post Management Functions
 */

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

// Global click listener to close menus when clicking outside
document.addEventListener('click', (e) => {
    const isMenuButton = e.target.closest('button[onclick^="togglePostMenu"]');
    const isInsideMenu = e.target.closest('.post-menu-dropdown');
    
    if (!isMenuButton && !isInsideMenu) {
        document.querySelectorAll('.post-menu-dropdown').forEach(m => m.classList.add('hidden'));
    }
});

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
        if (!confirm('Are you sure you want to delete this post?')) return;
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
    const reason = window.prompt(
        'Why are you reporting this post? (e.g., Harassment, Spam, Misinformation)',
        'Inappropriate content'
    );

    if (reason === null) return;
    const trimmedReason = reason.trim();
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
    if (!confirm('Flag this post for further review?')) return;
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
    if (!confirm('Flag this comment for further review?')) return;
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
