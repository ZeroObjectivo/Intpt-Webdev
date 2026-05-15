// Image Modal Logic (Facebook Theater Style)

// CSRF token helper — reads from meta tag set in base.html
function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

function showModerationPopup(message) {
    const text = message || 'Your content violates community policy.';
    if (window.createToast) {
        window.createToast(`⚠ ${text}`, 'error');
        return;
    }
    alert(`⚠ ${text}`);
}

let currentPost = null;
let currentIdx = 0;
let isDragging = false;
let hasMoved = false;
let startX, startY;
let translateX = 0, translateY = 0;
let currentScale = 1;
let currentReplyTo = null;
let modalCommentRefreshTimer = null;
let modalCommentPollTimer = null;
let currentCommentsSignature = '';

function resetZoomState() {
    const wrapper = document.querySelector('.modal-image-wrapper');
    const img = document.getElementById('modalImage');
    const btn = document.getElementById('zoomToggleBtn');
    if (wrapper) {
        wrapper.classList.remove('zoomed');
        wrapper.classList.remove('dragging');
    }
    currentScale = 1;
    if (img) img.style.transform = 'scale(1) translate(0px, 0px)';
    if (btn) btn.classList.remove('active');
    translateX = 0;
    translateY = 0;
    hasMoved = false;
}

function openImageModal(post, index, updateHash = true) {
    // Sync with latest state from dashboard if available
    const dashCard = document.querySelector(`.post-card[data-post-id="${post.id}"]`);
    if (dashCard) {
        const dashLikeBtn = dashCard.querySelector('.like-btn');
        const dashCommentCount = dashCard.querySelector('.comments-count');
        const dashLikesCount = dashCard.querySelector('.likes-count');

        if (dashLikeBtn) post.user_has_liked = dashLikeBtn.classList.contains('text-red-500');
        if (dashCommentCount) post.comments_count = parseInt(dashCommentCount.innerText || '0');
        if (dashLikesCount) post.likes_count = parseInt(dashLikesCount.innerText || '0');
    }

    currentPost = post;
    currentIdx = index;

    resetZoomState();
    updateModalContent();
    updateModalActions(post);

    const modal = document.getElementById('imageModal');
    const container = modal.querySelector('.modal-container');
    const mainView = modal.querySelector('.modal-main-view');

    modal.style.display = 'flex';
    modal.classList.remove('no-image');
    mainView.style.display = 'flex';
    container.classList.remove('no-image');
    document.body.style.overflow = 'hidden';

    // Trigger fade-in/scale animation
    requestAnimationFrame(() => modal.classList.add('modal-visible'));

    // Update URL hash for persistence (e.g., #view-post-uuid-0)
    if (updateHash) {
        window.location.hash = `view-post-${post.id}-${index}`;
    }

    currentCommentsSignature = '';
    fetchComments(post.id);
    startModalCommentPolling(post.id);
}

function openCommentModal(post) {
    // Sync with latest state from dashboard if available
    const dashCard = document.querySelector(`.post-card[data-post-id="${post.id}"]`);
    if (dashCard) {
        const dashLikeBtn = dashCard.querySelector('.like-btn');
        const dashCommentCount = dashCard.querySelector('.comments-count');
        const dashLikesCount = dashCard.querySelector('.likes-count');

        if (dashLikeBtn) post.user_has_liked = dashLikeBtn.classList.contains('text-red-500');
        if (dashCommentCount) post.comments_count = parseInt(dashCommentCount.innerText || '0');
        if (dashLikesCount) post.likes_count = parseInt(dashLikesCount.innerText || '0');
    }

    currentPost = post;
    currentIdx = 0;

    resetZoomState();
    updateModalContent();
    updateModalActions(post);

    const modal = document.getElementById('imageModal');
    const container = modal.querySelector('.modal-container');
    const mainView = modal.querySelector('.modal-main-view');

    modal.style.display = 'flex';

    const hasImages = (post.image_urls && post.image_urls.length > 0) || post.image_url;

    if (!hasImages) {
        mainView.style.display = 'none';
        modal.classList.add('no-image');
        container.classList.add('no-image');
    } else {
        mainView.style.display = 'flex';
        modal.classList.remove('no-image');
        container.classList.remove('no-image');
    }

    document.body.style.overflow = 'hidden';

    // Trigger fade-in/scale animation
    requestAnimationFrame(() => modal.classList.add('modal-visible'));

    currentCommentsSignature = '';
    fetchComments(post.id);
    startModalCommentPolling(post.id);
}

function closeImageModal(event) {
    const modal = document.getElementById('imageModal');
    // If called without event, it's a forced close
    if (!event || event.target === modal || event.target.closest('.modal-close')) {
        if (document.fullscreenElement) {
            document.exitFullscreen();
        }

        // Animate out then hide
        modal.classList.remove('modal-visible');
        setTimeout(() => {
            modal.style.display = 'none';
        }, 200);

        document.body.style.overflow = 'auto';

        // Clear hash on close
        if (window.location.hash.startsWith('#view-post-')) {
            history.pushState("", document.title, window.location.pathname + window.location.search);
        }
        stopModalCommentPolling();
        currentCommentsSignature = '';
        const embedIframe = document.getElementById('modalEmbedIframe');
        if (embedIframe) {
            embedIframe.src = '';
        }
    }
}

function changeModalImage(step, event) {
    if (event) event.stopPropagation();
    resetZoomState();
    
    const urls = currentPost.image_urls;
    currentIdx = (currentIdx + step + urls.length) % urls.length;
    updateModalContent();
    
    // Update hash when switching images
    window.location.hash = `view-post-${currentPost.id}-${currentIdx}`;
}

function checkHashAndOpenModal() {
    const hash = window.location.hash;
    if (hash.startsWith('#view-post-')) {
        // Regex to handle UUIDs and index: #view-post-{id}-{index}
        const match = hash.match(/#view-post-(.+)-(\d+)$/);
        if (match) {
            const postId = match[1];
            const imgIdx = parseInt(match[2]);
            
            if (window.allPosts) {
                const post = window.allPosts.find(p => p.id == postId);
                if (post) {
                    // Don't re-open if it's already the current post/index
                    if (currentPost && currentPost.id == postId && currentIdx == imgIdx) return;
                    openImageModal(post, imgIdx, false); // false to avoid redundant hash update
                }
            }
        }
    } else if (document.getElementById('imageModal') && document.getElementById('imageModal').style.display === 'flex') {
        closeImageModal();
    }
}

function toggleZoom(event) {
    if (event) event.stopPropagation();
    if (isDragging || hasMoved) return;
    
    const wrapper = document.querySelector('.modal-image-wrapper');
    const img = document.getElementById('modalImage');
    const btn = document.getElementById('zoomToggleBtn');
    
    if (wrapper.classList.contains('zoomed')) {
        resetZoomState();
    } else {
        currentScale = 2.5;
        wrapper.classList.add('zoomed');
        img.style.transform = `scale(${currentScale}) translate(0px, 0px)`;
        btn.classList.add('active');
    }
}

function handleImageClick(event) {
    const wrapper = document.querySelector('.modal-image-wrapper');
    if (wrapper && wrapper.classList.contains('zoomed')) {
        toggleZoom(event);
    }
}

function toggleFullScreen(event) {
    if (event) event.stopPropagation();
    const view = document.querySelector('.modal-main-view');
    if (!document.fullscreenElement) {
        view.requestFullscreen().catch(err => {
            console.error(`Error enabling full-screen: ${err.message}`);
        });
    } else {
        document.exitFullscreen();
    }
}

function updateModalContent() {
    const modalImg = document.getElementById('modalImage');
    const prevBtn = document.getElementById('modalPrev');
    const nextBtn = document.getElementById('modalNext');
    
    if (!currentPost) return;
    
    if (currentPost.image_urls && currentPost.image_urls.length > 0) {
        modalImg.src = currentPost.image_urls[currentIdx];
        
        if (currentPost.image_urls.length <= 1) {
            prevBtn.style.display = 'none';
            nextBtn.style.display = 'none';
        } else {
            prevBtn.style.display = 'flex';
            nextBtn.style.display = 'flex';
        }
    } else if (currentPost.image_url) {
        modalImg.src = currentPost.image_url;
        prevBtn.style.display = 'none';
        nextBtn.style.display = 'none';
    }

    const avatar = document.getElementById('modalUserAvatar');
    const embedContainer = document.getElementById('modalEmbedContainer');
    const embedIframe = document.getElementById('modalEmbedIframe');
    const profile = currentPost.profiles || {};
    avatar.src = profile.avatar_url || "/static/images/Logo.png";
    document.getElementById('modalUserName').innerText = profile.full_name || 'Heron';
    document.getElementById('modalPostTime').innerText = formatPostTime(currentPost.created_at);
    document.getElementById('modalPostText').innerText = currentPost.content;

    const badge = document.getElementById('modalCategoryBadge');
    badge.innerText = currentPost.category;
    badge.className = "inline-block px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-widest mb-3 ";
    
    const cat = currentPost.category;
    if (cat === 'General') badge.classList.add('badge-general');
    else if (cat === 'Lost & Found') badge.classList.add('badge-lost-found');
    else if (cat === 'Buy & Sell' || cat === 'Heron Business') badge.classList.add('badge-heron-business');
    else if (cat === 'Question') badge.classList.add('badge-question');
    else if (cat === 'Events') badge.classList.add('badge-events');

    const dynamic = document.getElementById('modalDynamicDetails');
    dynamic.innerHTML = '';
    
    if (currentPost.event_title) {
        document.getElementById('modalPostText').innerHTML = `<strong class="block text-slate-900 mb-1">${currentPost.event_title}</strong>` + currentPost.content;
    }

    if (embedContainer && embedIframe) {
        const embedUrl = currentPost.embed && currentPost.embed.embed_url ? currentPost.embed.embed_url : '';
        if (embedUrl) {
            embedIframe.src = embedUrl;
            embedContainer.classList.remove('hidden');
        } else {
            embedIframe.src = '';
            embedContainer.classList.add('hidden');
        }
    }

    if (currentPost.price) {
        dynamic.innerHTML += `<div class="flex items-center gap-2 text-xs font-bold text-emerald-600">
            <span class="bg-emerald-50 px-2 py-1 rounded">₱${parseFloat(currentPost.price).toLocaleString()}</span>
        </div>`;
    }
    if (currentPost.location) {
        dynamic.innerHTML += `<div class="flex items-center gap-2 text-xs font-bold text-slate-500">
            <span class="bg-slate-100 px-2 py-1 rounded">${currentPost.location}</span>
        </div>`;
    }
    if (currentPost.event_date) {
        const eventDt = new Date(currentPost.event_date);
        const dateStr = eventDt.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
        const timeStr = eventDt.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
        dynamic.innerHTML += `<div class="flex items-center gap-2 text-xs font-bold text-purple-600">
            <span class="bg-purple-50 px-2 py-1 rounded">${dateStr} at ${timeStr}</span>
        </div>`;
    }
}

function formatPostTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) + ' at ' + 
           date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
}

function buildCommentsSignature(comments) {
    return (comments || []).map((comment) => {
        const stamp = comment.updated_at || comment.created_at || '';
        return `${comment.id}:${stamp}:${comment.content || ''}`;
    }).join('|');
}

function renderCommentsList(list, comments) {
    if (comments.length > 0) {
        list.innerHTML = '';

        // Organize comments by parent_id
        const topLevel = comments.filter((c) => !c.parent_id);
        const replies = comments.filter((c) => c.parent_id);

        topLevel.forEach((comment) => {
            const commentEl = renderComment(comment);
            list.appendChild(commentEl);

            // Find and render replies for this comment
            const commentReplies = replies.filter((r) => r.parent_id === comment.id);
            if (commentReplies.length > 0) {
                const repliesContainer = commentEl.querySelector('.comment-replies');
                repliesContainer.style.display = 'none'; // Hide by default

                const toggleBtn = document.createElement('button');
                toggleBtn.className = 'view-replies-btn';
                toggleBtn.onclick = () => toggleReplies(comment.id, toggleBtn);
                toggleBtn.innerHTML = `
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                    <span>View ${commentReplies.length} ${commentReplies.length === 1 ? 'reply' : 'replies'}</span>
                `;

                // Insert button after the main comment body
                commentEl.insertBefore(toggleBtn, repliesContainer);

                commentReplies.forEach((reply) => {
                    repliesContainer.appendChild(renderComment(reply, true));
                });
            }
        });
    } else {
        list.innerHTML = '<div class="text-center py-8"><p class="text-xs text-slate-400 italic">No comments yet. Be the first to reply!</p></div>';
    }
}

function startModalCommentPolling(postId) {
    stopModalCommentPolling();
    if (!postId) return;

    modalCommentPollTimer = setInterval(() => {
        const modal = document.getElementById('imageModal');
        if (!currentPost || String(currentPost.id) !== String(postId)) return;
        if (!modal || modal.style.display !== 'flex' || document.hidden) return;
        fetchComments(postId, { silent: true });
    }, 4500);
}

function stopModalCommentPolling() {
    if (modalCommentPollTimer) {
        clearInterval(modalCommentPollTimer);
        modalCommentPollTimer = null;
    }
}

async function fetchComments(postId, options = {}) {
    const { silent = false, force = false } = options;
    const list = document.getElementById('modalCommentsList');
    if (!list) return;
    if (!silent) {
        list.innerHTML = '<div class="text-center py-8"><p class="text-xs text-slate-400">Loading comments...</p></div>';
    }
    
    try {
        const response = await fetch(`/posts/${postId}/comments`);
        if (!response.ok) throw new Error(`Comments request failed (${response.status})`);
        const data = await response.json();

        const comments = Array.isArray(data.comments) ? data.comments : [];
        const nextSignature = buildCommentsSignature(comments);
        if (!force && currentCommentsSignature && nextSignature === currentCommentsSignature) {
            return;
        }

        currentCommentsSignature = nextSignature;
        renderCommentsList(list, comments);
    } catch (error) {
        console.error('Error fetching comments:', error);
        if (!silent) {
            list.innerHTML = '<div class="text-center py-8"><p class="text-xs text-red-400">Failed to load comments.</p></div>';
        }
    }
}

function toggleReplies(commentId, btn) {
    const parentEl = document.getElementById(`comment-${commentId}`);
    const repliesContainer = parentEl.querySelector('.comment-replies');
    const isHidden = repliesContainer.style.display === 'none';
    
    if (isHidden) {
        repliesContainer.style.display = 'flex';
        btn.classList.add('active');
        btn.querySelector('span').innerText = 'Hide replies';
    } else {
        repliesContainer.style.display = 'none';
        btn.classList.remove('active');
        // Count replies to restore text
        const count = repliesContainer.children.length;
        btn.querySelector('span').innerText = `View ${count} ${count === 1 ? 'reply' : 'replies'}`;
    }
}

function renderComment(comment, isReply = false) {
    const avatar = comment.profiles.avatar_url || "/static/images/Logo.png";
    const isOwner = window.currentUser && window.currentUser.id === comment.user_id;
    const isAdmin = window.currentUser && (window.currentUser.role === 'admin' || window.currentUser.role === 'super_admin');
    
    const div = document.createElement('div');
    div.className = 'flex flex-col gap-2 group';
    div.id = `comment-${comment.id}`;
    
    div.innerHTML = `
        <div class="flex gap-3">
            <img src="${avatar}" alt="" class="w-8 h-8 rounded-full object-cover">
            <div class="flex-1">
                <div class="bg-slate-50 rounded-2xl px-3 py-2 relative group/comment">
                    <h5>${comment.profiles.full_name}</h5>
                    <p id="comment-text-${comment.id}">${comment.content}</p>
                    
                    <div class="absolute right-2 top-2 hidden group-hover/comment:flex items-center gap-1">
                        ${isOwner ? `
                            <button onclick="startEditComment('${comment.id}')" class="p-1 hover:bg-slate-200 rounded text-slate-400 hover:text-slate-600 transition-all">
                                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path></svg>
                            </button>
                            <button onclick="deleteComment('${comment.id}')" class="p-1 hover:bg-red-100 rounded text-slate-400 hover:text-red-500 transition-all">
                                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                            </button>
                        ` : ''}
                        ${isAdmin ? `
                            <button onclick="if(window.flagComment) flagComment('${comment.id}')" class="flag-btn p-1 hover:bg-orange-100 rounded text-slate-400 hover:text-orange-500 transition-all" title="Flag Comment">
                                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9"></path></svg>
                            </button>
                        ` : ''}
                    </div>
                </div>
                <div id="comment-edit-area-${comment.id}" class="hidden mt-2">
                    <textarea id="comment-edit-input-${comment.id}" class="w-full p-2 text-xs bg-white border border-slate-200 rounded-lg outline-none focus:ring-1 focus:ring-umak-blue/30">${comment.content}</textarea>
                    <div class="flex justify-end gap-2 mt-1">
                        <button onclick="cancelEditComment('${comment.id}')" class="text-[9px] font-bold text-slate-400 hover:text-slate-600">Cancel</button>
                        <button onclick="saveEditComment('${comment.id}')" class="text-[9px] font-bold text-umak-blue hover:text-blue-700">Save</button>
                    </div>
                </div>
                <div class="flex items-center gap-3 mt-1 ml-2">
                    <span class="text-[10px] font-bold text-slate-400">${formatPostTime(comment.created_at)}</span>
                    <button onclick="setReply('${comment.id}', '${comment.profiles.full_name}')" class="text-[10px] font-bold text-slate-400 hover:text-umak-blue">Reply</button>
                </div>
            </div>
        </div>
        ${!isReply ? '<div class="comment-replies"></div>' : ''}
    `;
    return div;
}

function startEditComment(commentId) {
    document.getElementById(`comment-text-${commentId}`).classList.add('hidden');
    document.getElementById(`comment-edit-area-${commentId}`).classList.remove('hidden');
    const input = document.getElementById(`comment-edit-input-${commentId}`);
    input.focus();
    input.setSelectionRange(input.value.length, input.value.length);
}

function cancelEditComment(commentId) {
    document.getElementById(`comment-text-${commentId}`).classList.remove('hidden');
    document.getElementById(`comment-edit-area-${commentId}`).classList.add('hidden');
}

async function saveEditComment(commentId) {
    const input = document.getElementById(`comment-edit-input-${commentId}`);
    const content = input.value.trim();
    if (!content) return;

    try {
        const response = await fetch(`/comments/${commentId}/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
            body: JSON.stringify({ content })
        });
        const data = await response.json();
        if (!response.ok || data.status === 'blocked') {
            showModerationPopup(data.error || 'Comment update blocked by policy.');
            return;
        }
        if (data.comment) {
            document.getElementById(`comment-text-${commentId}`).innerText = data.comment.content;
            cancelEditComment(commentId);
        }
    } catch (error) {
        console.error('Error saving comment:', error);
    }
}

async function deleteComment(commentId) {
    showConfirmModal(
        'Delete Comment?',
        'Are you sure you want to delete this comment?',
        async () => {
            try {
                const response = await fetch(`/comments/${commentId}/delete`, { method: 'POST', headers: { 'X-CSRFToken': getCSRFToken() } });
                const data = await response.json();
                if (data.status === 'deleted') {
                    document.getElementById(`comment-${commentId}`).remove();
                    if (currentPost) {
                        updateDashboardCount(currentPost.id, 'comments', -1);
                        if (window.requestInteractionSync) window.requestInteractionSync(currentPost.id);
                    }
                }
            } catch (error) {
                console.error('Error deleting comment:', error);
            }
        }
    );
}

// Custom Confirmation Modal Helpers
function showConfirmModal(title, message, onConfirm) {
    const modal = document.getElementById('confirmModal');
    const titleEl = document.getElementById('confirmTitle');
    const messageEl = document.getElementById('confirmMessage');
    const confirmBtn = document.getElementById('confirmActionBtn');
    
    titleEl.innerText = title;
    messageEl.innerText = message;
    
    // Use a new button reference to clear old listeners
    const newConfirmBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
    
    newConfirmBtn.onclick = async () => {
        await onConfirm();
        closeConfirmModal();
    };
    
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeConfirmModal(event) {
    const modal = document.getElementById('confirmModal');
    // Allow closing if no event (manual call), clicking the overlay, or clicking any button
    if (!event || event.target === modal || event.target.closest('button')) {
        modal.classList.remove('active');
        // Only restore body overflow if the main image modal is also closed
        const imageModal = document.getElementById('imageModal');
        if (!imageModal || imageModal.style.display !== 'flex') {
            document.body.style.overflow = 'auto';
        }
    }
}

async function submitComment(event) {
    event.preventDefault();
    const textarea = document.getElementById('commentTextarea');
    const content = textarea.value.trim();
    
    if (!content || !currentPost) return;
    
    const submitBtn = event.target.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    
    const body = { content };
    if (currentReplyTo) {
        body.parent_id = currentReplyTo.id;
    }
    
    try {
        const response = await fetch(`/posts/${currentPost.id}/comments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
            body: JSON.stringify(body)
        });
        
        const data = await response.json();
        if (!response.ok || data.status === 'blocked') {
            showModerationPopup(data.error || 'Comment blocked by policy.');
            return;
        }
        
        if (data.comment) {
            const list = document.getElementById('modalCommentsList');
            if (list.querySelector('.italic')) list.innerHTML = ''; // Remove "No comments" text
            
            const newCommentEl = renderComment(data.comment, !!data.comment.parent_id);
            
            if (data.comment.parent_id) {
                const parentEl = document.getElementById(`comment-${data.comment.parent_id}`);
                // If the parent is itself a reply, we append to the same container
                const repliesContainer = parentEl.querySelector('.comment-replies') || parentEl.closest('.comment-replies');
                if (repliesContainer) {
                    repliesContainer.appendChild(newCommentEl);
                } else {
                    // Fallback to end of list if container not found
                    list.appendChild(newCommentEl);
                }
            } else {
                list.appendChild(newCommentEl);
            }
            
            textarea.value = '';
            textarea.style.height = 'auto';
            newCommentEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            
            // Clear reply state
            cancelReply();
            
            // Update comments count on dashboard
            updateDashboardCount(currentPost.id, 'comments', 1);
            if (window.requestInteractionSync) window.requestInteractionSync(currentPost.id);
        }
    } catch (error) {
        console.error('Error submitting comment:', error);
    } finally {
        submitBtn.disabled = false;
    }
}

function setReply(commentId, userName) {
    currentReplyTo = { id: commentId, name: userName };
    const textarea = document.getElementById('commentTextarea');
    textarea.value = `@${userName} `;
    textarea.focus();
    
    // Show reply indicator
    let indicator = document.getElementById('replyIndicator');
    if (!indicator) {
        indicator = document.createElement('div');
        indicator.id = 'replyIndicator';
        indicator.className = 'flex items-center justify-between bg-slate-100 px-3 py-1 rounded-t-lg text-[10px] font-bold text-slate-500 border-b border-white';
        document.getElementById('modalCommentForm').parentElement.prepend(indicator);
    }
    indicator.innerHTML = `
        <span>Replying to ${userName}</span>
        <button onclick="cancelReply()" class="text-slate-400 hover:text-red-500">
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
        </button>
    `;
}

function cancelReply() {
    currentReplyTo = null;
    const indicator = document.getElementById('replyIndicator');
    if (indicator) indicator.remove();
    
    const textarea = document.getElementById('commentTextarea');
    if (textarea.value.startsWith('@')) {
        textarea.value = '';
    }
}

// Global state to prevent spam clicking
let isLiking = false;

async function toggleLike(postId, btn) {
    if (isLiking || btn.disabled) return;
    isLiking = true;
    
    const icon = btn.querySelector('svg');
    const countSpan = btn.querySelector('.likes-count');
    let count = parseInt(countSpan ? countSpan.innerText : '0');
    
    const isLiked = btn.classList.contains('text-red-500');
    
    // Disable button during request
    btn.disabled = true;
    btn.style.opacity = '0.7';

    // Optimistic update
    if (isLiked) {
        btn.classList.remove('text-red-500');
        btn.classList.add('text-slate-400');
        icon.classList.remove('fill-current');
        if (countSpan) countSpan.innerText = Math.max(0, count - 1);
    } else {
        btn.classList.add('text-red-500');
        btn.classList.remove('text-slate-400');
        icon.classList.add('fill-current');
        if (countSpan) countSpan.innerText = count + 1;
    }
    
    try {
        const response = await fetch(`/posts/${postId}/like`, { method: 'POST', headers: { 'X-CSRFToken': getCSRFToken() } });
        const data = await response.json();
        
        // Update currentPost state if in modal
        if (currentPost && currentPost.id === postId) {
            currentPost.user_has_liked = (data.status === 'liked');
            currentPost.likes_count = (data.status === 'liked') ? count + 1 : Math.max(0, count - 1);
        }

        // Final sync based on server response
        if (data.status === 'liked') {
            btn.classList.add('text-red-500');
            btn.classList.remove('text-slate-400');
            icon.classList.add('fill-current');
        } else if (data.status === 'unliked') {
            btn.classList.remove('text-red-500');
            btn.classList.add('text-slate-400');
            icon.classList.remove('fill-current');
        }
        if (window.requestInteractionSync) window.requestInteractionSync(postId);
    } catch (error) {
        console.error('Error toggling like:', error);
        // Revert on error
        if (countSpan) countSpan.innerText = count;
        if (isLiked) {
            btn.classList.add('text-red-500');
            btn.classList.remove('text-slate-400');
            icon.classList.add('fill-current');
        } else {
            btn.classList.remove('text-red-500');
            btn.classList.add('text-slate-400');
            icon.classList.remove('fill-current');
        }
    } finally {
        isLiking = false;
        btn.disabled = false;
        btn.style.opacity = '';
    }
}

function updateDashboardCount(postId, type, delta, excludeElement = null) {
    // Find all instances of the post on the dashboard (main feed, profile, or trending)
    const cards = document.querySelectorAll(`.post-card[data-post-id="${postId}"]`);

    cards.forEach(card => {
        if (card === excludeElement || card.contains(excludeElement)) return;

        if (type === 'comments') {
            const span = card.querySelector('.comments-count');
            if (span) {
                const currentCount = parseInt(span.innerText || '0');
                span.innerText = Math.max(0, currentCount + delta);
            }
        } else if (type === 'likes') {
            const span = card.querySelector('.likes-count');
            const likeBtn = card.querySelector('.like-btn');
            const icon = likeBtn ? likeBtn.querySelector('svg') : null;

            if (span) {
                const currentCount = parseInt(span.innerText || '0');
                span.innerText = Math.max(0, currentCount + delta);
            }

            if (likeBtn && icon) {
                if (delta > 0) {
                    likeBtn.classList.add('text-red-500');
                    likeBtn.classList.remove('text-slate-400');
                    icon.classList.add('fill-current');
                } else {
                    likeBtn.classList.remove('text-red-500');
                    likeBtn.classList.add('text-slate-400');
                    icon.classList.remove('fill-current');
                }
            }
        }
    });
    // Handle trending list items (they have a different structure)
    if (type === 'likes') {
        const trendingItems = document.querySelectorAll('.trending-item');
        trendingItems.forEach(item => {
            // This is a bit tricky as trending items don't always have the ID in a data attribute
            // But we can check if the onclick contains the ID
            const onclickAttr = item.getAttribute('onclick') || '';
            if (onclickAttr.includes(postId)) {
                const likesSpan = item.querySelector('.likes');
                if (likesSpan) {
                    const match = likesSpan.innerText.match(/(\d+)/);
                    if (match) {
                        const newCount = Math.max(0, parseInt(match[1]) + delta);
                        likesSpan.innerText = `${newCount} Likes`;
                    }
                }
            }
        });
    }
}

function updateModalActions(post) {
    const sidePanel = document.querySelector('.modal-side-panel');
    const likeBtn = sidePanel.querySelector('.modal-action-btn:first-child');
    const commentBtn = sidePanel.querySelector('.modal-action-btn:last-child');

    // Set initial state
    if (post.user_has_liked) {
        likeBtn.classList.add('text-red-500');
        likeBtn.querySelector('svg').classList.add('fill-current');
    } else {
        likeBtn.classList.remove('text-red-500');
        likeBtn.querySelector('svg').classList.remove('fill-current');
    }

    likeBtn.onclick = async () => {
        if (isLiking || likeBtn.disabled) return;
        
        const isCurrentlyLiked = likeBtn.classList.contains('text-red-500');
        
        // Sync with dashboard
        updateDashboardCount(post.id, 'likes', isCurrentlyLiked ? -1 : 1);

        // Use the global toggleLike which handles the modal button's UI and API call
        await toggleLike(post.id, likeBtn);
    };

    commentBtn.onclick = () => {
        document.getElementById('commentTextarea').focus();
    };
}

function syncModalFromInteractionRows(rows) {
    if (!currentPost || !Array.isArray(rows)) return;
    const row = rows.find((item) => item.id === currentPost.id);
    if (!row) return;

    const previousCommentCount = Number(currentPost.comments_count || 0);
    currentPost.likes_count = Number(row.likes_count || 0);
    currentPost.comments_count = Number(row.comments_count || 0);
    currentPost.user_has_liked = !!row.user_has_liked;

    updateModalActions(currentPost);

    // If other users added/removed comments while modal is open, refresh list.
    if (currentPost.comments_count !== previousCommentCount) {
        fetchComments(currentPost.id, { silent: true, force: true });
    }
}

function scheduleModalCommentRefresh(postId) {
    if (!postId || !currentPost || String(currentPost.id) !== String(postId)) return;
    const modal = document.getElementById('imageModal');
    if (!modal || modal.style.display !== 'flex') return;

    if (modalCommentRefreshTimer) {
        clearTimeout(modalCommentRefreshTimer);
    }

    modalCommentRefreshTimer = setTimeout(() => {
        fetchComments(postId, { silent: true, force: true });
        modalCommentRefreshTimer = null;
    }, 280);
}

// Global Event Listeners
document.addEventListener('keydown', (e) => {
    const modal = document.getElementById('imageModal');
    if (modal && modal.style.display === 'flex') {
        if (e.key === 'ArrowLeft') changeModalImage(-1);
        if (e.key === 'ArrowRight') changeModalImage(1);
        if (e.key === 'Escape') closeImageModal();
    }
});

document.addEventListener('DOMContentLoaded', () => {
    const wrapper = document.querySelector('.modal-image-wrapper');
    const img = document.getElementById('modalImage');
    const commentTextarea = document.getElementById('commentTextarea');
    const commentForm = document.getElementById('modalCommentForm');

    if (commentTextarea) {
        // Submit on Enter, New line on Shift + Enter
        commentTextarea.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                const content = commentTextarea.value.trim();
                if (content) {
                    // Trigger the form submission
                    const event = new Event('submit', { cancelable: true });
                    commentForm.dispatchEvent(event);
                }
            }
        });

        // Auto-resize textarea as user types
        commentTextarea.addEventListener('input', () => {
            commentTextarea.style.height = 'auto';
            commentTextarea.style.height = (commentTextarea.scrollHeight) + 'px';
        });
    }

    if (!wrapper || !img) return;

    wrapper.addEventListener('mousedown', (e) => {
        if (!wrapper.classList.contains('zoomed')) return;
        isDragging = true;
        wrapper.classList.add('dragging');
        startX = e.clientX - (translateX * currentScale);
        startY = e.clientY - (translateY * currentScale);
        e.preventDefault();
    });

    window.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        hasMoved = true;
        translateX = (e.clientX - startX) / currentScale;
        translateY = (e.clientY - startY) / currentScale;
        img.style.transform = `scale(${currentScale}) translate(${translateX}px, ${translateY}px)`;
    });

    window.addEventListener('mouseup', () => {
        if (isDragging) {
            isDragging = false;
            wrapper.classList.remove('dragging');
            setTimeout(() => { hasMoved = false; }, 100);
        }
    });

    wrapper.addEventListener('wheel', (e) => {
        e.preventDefault();
        const delta = e.deltaY > 0 ? -0.2 : 0.2;
        currentScale = Math.min(Math.max(1, currentScale + delta), 5);
        
        const btn = document.getElementById('zoomToggleBtn');
        if (currentScale > 1) {
            wrapper.classList.add('zoomed');
            btn.classList.add('active');
        } else {
            resetZoomState();
        }
        img.style.transform = `scale(${currentScale}) translate(${translateX}px, ${translateY}px)`;
    }, { passive: false });

    // Handle initial hash on load with a small delay to ensure allPosts is populated
    setTimeout(checkHashAndOpenModal, 100);
});

// Handle browser back/forward and direct hash entry
window.addEventListener('hashchange', checkHashAndOpenModal);
window.addEventListener('dashboard-interactions-sync', (event) => {
    const rows = event && event.detail ? event.detail.posts : [];
    syncModalFromInteractionRows(rows);
});
window.addEventListener('dashboard-comment-mutation', (event) => {
    const postId = event && event.detail ? event.detail.postId : null;
    scheduleModalCommentRefresh(postId);
});
