// Image Modal Logic (Refined Minimalist Theater View)

// CSRF token helper — reads from meta tag set in base.html
function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

function escapeHtmlForLinkify(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function linkifyText(text) {
    var safe = escapeHtmlForLinkify(text || '');
    return safe.replace(/(https?:\/\/[^\s<>"']+)/gi, function(url) {
        var clean = url.replace(/[.,!?;:)]+$/, '');
        return '<a href="' + clean + '" target="_blank" rel="noopener noreferrer" class="text-blue-500 hover:underline break-all">' + clean + '</a>';
    });
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
const isAdminContext = window.location.pathname.startsWith('/admin/');

function resizeCommentComposerTextarea(textarea) {
    if (!textarea) return;
    const maxHeight = 132;
    textarea.style.height = 'auto';
    const nextHeight = Math.min(textarea.scrollHeight, maxHeight);
    textarea.style.height = `${nextHeight}px`;
    textarea.style.overflowY = textarea.scrollHeight > maxHeight ? 'auto' : 'hidden';
}

function initCommentComposerInteractions() {
    const form = document.getElementById('modalCommentForm');
    const textarea = document.getElementById('commentTextarea');
    if (!form || !textarea || textarea.dataset.boundComposer === '1') return;

    textarea.dataset.boundComposer = '1';
    resizeCommentComposerTextarea(textarea);

    textarea.addEventListener('input', () => {
        resizeCommentComposerTextarea(textarea);
    });

    textarea.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter') return;
        if (event.shiftKey) return;

        event.preventDefault();
        if (!textarea.value.trim()) return;

        if (typeof form.requestSubmit === 'function') {
            form.requestSubmit();
            return;
        }
        form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    });
}

function resetZoomState() {
    const wrapper = document.querySelector('.modal-image-wrapper');
    const img = document.getElementById('modalImg');
    const btn = document.getElementById('zoomToggleBtn');
    if (wrapper) {
        wrapper.classList.remove('zoomed', 'dragging');
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
    if (!event || event.target === modal || event.target.closest('.modal-close')) {
        if (document.fullscreenElement) {
            document.exitFullscreen();
        }

        modal.classList.remove('modal-visible');
        setTimeout(() => {
            modal.style.display = 'none';
        }, 200);

        document.body.style.overflow = 'auto';

        if (window.location.hash.startsWith('#view-post-')) {
            history.pushState("", document.title, window.location.pathname + window.location.search);
        }
        stopModalCommentPolling();
        currentCommentsSignature = '';
        const embedIframe = document.getElementById('modalEmbedIframe');
        if (embedIframe) {
            embedIframe.src = '';
        }
        const embedSourceLink = document.getElementById('modalEmbedSourceLink');
        if (embedSourceLink) embedSourceLink.classList.add('hidden');
    }
}

function navigateModal(step, event) {
    if (event) event.stopPropagation();
    resetZoomState();
    
    const urls = currentPost.image_urls || [];
    if (!urls.length) return;
    
    currentIdx = (currentIdx + step + urls.length) % urls.length;
    updateModalContent();
    
    window.location.hash = `view-post-${currentPost.id}-${currentIdx}`;
}

function zoomImage(delta) {
    currentScale = Math.min(Math.max(1, currentScale + delta), 5);
    const img = document.getElementById('modalImg');
    const wrapper = document.getElementById('modalImageWrapper');
    const btn = document.getElementById('resetZoomBtn');
    
    if (currentScale > 1) {
        wrapper.classList.add('zoomed');
    } else {
        wrapper.classList.remove('zoomed');
        translateX = 0;
        translateY = 0;
    }
    
    img.style.transform = `scale(${currentScale}) translate(${translateX}px, ${translateY}px)`;
}

function checkHashAndOpenModal() {
    const hash = window.location.hash;
    if (hash.startsWith('#view-post-')) {
        const match = hash.match(/#view-post-(.+)-(\d+)$/);
        if (match) {
            const postId = match[1];
            const imgIdx = parseInt(match[2]);
            
            if (window.allPosts) {
                const post = window.allPosts.find(p => p.id == postId);
                if (post) {
                    if (currentPost && currentPost.id == postId && currentIdx == imgIdx) return;
                    openImageModal(post, imgIdx, false);
                }
            }
        }
    } else if (document.getElementById('imageModal') && document.getElementById('imageModal').style.display === 'flex') {
        closeImageModal();
    }
}

function toTitleCase(str) {
    if (!str) return '';
    return str.toLowerCase().split(' ').map(word => {
        return word.charAt(0).toUpperCase() + word.slice(1);
    }).join(' ');
}

function updateModalContent() {
    const modalImg = document.getElementById('modalImg');
    const prevBtn = document.getElementById('modalPrevBtn');
    const nextBtn = document.getElementById('modalNextBtn');
    
    if (!currentPost) return;
    
    if (currentPost.image_urls && currentPost.image_urls.length > 0) {
        modalImg.src = currentPost.image_urls[currentIdx];
        const showNav = currentPost.image_urls.length > 1;
        prevBtn.style.display = showNav ? 'flex' : 'none';
        nextBtn.style.display = showNav ? 'flex' : 'none';
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
    document.getElementById('modalUserName').innerText = toTitleCase(profile.full_name || currentPost.full_name) || 'Heron';

    // College Pill
    const collegeEl = document.getElementById('modalUserCollege');
    const collegeContainer = document.getElementById('modalUserCollegeContainer');
    if (collegeEl && collegeContainer) {
        if (profile.college) {
            collegeContainer.style.display = 'flex';
            collegeEl.innerText = profile.college.split(' ')[0];
            const collCode = profile.college.split(' ')[0].toLowerCase();
            collegeEl.className = `badge college-${collCode} shrink-0`;
        } else {
            collegeContainer.style.display = 'none';
        }
    }

    const profileEmbed = document.getElementById('modalUserProfileEmbed');
    const profileProgram = document.getElementById('modalUserProgram');
    const profileLink = document.getElementById('modalUserProfileLink');

    if (profileEmbed && profileProgram && profileLink) {
        const profileBits = [profile.course, profile.college, profile.level].filter((v) => !!(v && String(v).trim()));
        profileProgram.innerText = profileBits.length ? profileBits.join(' • ') : 'UMak community member';
        const ownerId = currentPost.user_id || '';
        if (ownerId) {
            // Admin Hub Redirect logic
            const isAdminHub = window.location.pathname.startsWith('/admin/');
            profileLink.href = isAdminHub ? `/admin/users/${ownerId}/manage` : `/profile/${encodeURIComponent(ownerId)}`;
            profileLink.classList.remove('pointer-events-none', 'opacity-50');
        } else {
            profileLink.href = '#';
            profileLink.classList.add('pointer-events-none', 'opacity-50');
        }
    }

    // Timestamp & Category
    const timeEl = document.getElementById('modalPostTime');
    if (timeEl) {
        timeEl.innerText = formatPostTime(currentPost.created_at);
        const date = new Date(currentPost.created_at);
        timeEl.title = date.toLocaleString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }
    
    const catBadge = document.getElementById('modalCategoryBadge');
    if (catBadge) {
        const cat = currentPost.category || 'General';
        catBadge.innerText = cat;
        catBadge.className = 'badge transition-all';
        
        if (cat === 'General') catBadge.classList.add('badge-general');
        else if (cat === 'Lost & Found') catBadge.classList.add('badge-lost-found');
        else if (cat === 'Buy & Sell' || cat === 'Heron Business') catBadge.classList.add('badge-heron-business');
        else if (cat === 'Question') catBadge.classList.add('badge-question');
        else if (cat === 'Events') catBadge.classList.add('badge-events');
    }

    document.getElementById('modalPostText').innerHTML = linkifyText(currentPost.content);

    const dynamic = document.getElementById('modalDynamicDetails');
    dynamic.innerHTML = '';

    if (currentPost.event_title) {
        document.getElementById('modalPostText').innerHTML = `<strong class="block text-slate-900 mb-1">${escapeHtmlForLinkify(currentPost.event_title)}</strong>` + linkifyText(currentPost.content);
    }

    if (embedContainer && embedIframe) {
        const embedUrl = currentPost.embed && currentPost.embed.embed_url ? currentPost.embed.embed_url : '';
        const sourceLink = document.getElementById('modalEmbedSourceLink');
        const sourceText = document.getElementById('modalEmbedSourceText');
        if (embedUrl) {
            embedIframe.src = embedUrl;
            embedContainer.classList.remove('hidden');
            if (sourceLink && currentPost.embed.source_url) {
                sourceLink.href = currentPost.embed.source_url;
                sourceLink.classList.remove('hidden');
                if (sourceText) {
                    const provider = (currentPost.embed.provider || 'source');
                    sourceText.textContent = 'Open on ' + provider.charAt(0).toUpperCase() + provider.slice(1);
                }
            }
        } else {
            embedIframe.src = '';
            embedContainer.classList.add('hidden');
            if (sourceLink) sourceLink.classList.add('hidden');
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
    const now = new Date();
    const diff = (now - date) / 1000;
    
    if (diff < 86400) {
        if (diff < 60) return "Just now";
        if (diff < 3600) return `${Math.floor(diff/60)} mins ago`;
        return `${Math.floor(diff/3600)} hrs ago`;
    }

    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) + ' at ' + 
           date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
}

function renderComment(comment, isReply = false) {
    const avatar = comment.profiles.avatar_url || "/static/images/Logo.png";
    const isOwner = window.currentUser && window.currentUser.id === comment.user_id;
    const isAdmin = window.currentUser && (window.currentUser.role === 'admin' || window.currentUser.role === 'super_admin');
    const allowOwnEdit = isOwner && !isAdminContext;
    
    const div = document.createElement('div');
    div.className = `flex flex-col ${isReply ? 'mt-3' : 'mt-6'} group`;
    div.id = `comment-${comment.id}`;
    
    div.innerHTML = `
        <div class="flex gap-3">
            <img src="${avatar}" alt="" class="w-9 h-9 rounded-xl object-cover shadow-sm">
            <div class="flex-1 min-w-0">
                <div class="bg-slate-50 rounded-2xl px-4 py-3 relative group/comment transition-all hover:bg-slate-100/50">
                    <div class="flex justify-between items-start mb-1">
                        <h5 class="text-[13px] font-bold text-slate-900">${toTitleCase(comment.profiles.full_name)}</h5>
                        <div class="flex items-center gap-1 opacity-0 group-hover/comment:opacity-100 transition-opacity">
                            ${allowOwnEdit ? `
                                <button onclick="startEditComment('${comment.id}')" class="p-1.5 hover:bg-white rounded-lg text-slate-400 hover:text-slate-600 transition-all" title="Edit">
                                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path></svg>
                                </button>
                                <button onclick="deleteComment('${comment.id}')" class="p-1.5 hover:bg-white rounded-lg text-slate-400 hover:text-red-500 transition-all" title="Delete">
                                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                                </button>
                            ` : ''}
                        </div>
                    </div>
                    <p id="comment-text-${comment.id}" class="text-[13px] text-slate-600 leading-relaxed font-medium">${comment.content}</p>
                </div>
                
                <div id="comment-edit-area-${comment.id}" class="hidden mt-2 bg-white rounded-2xl p-3 border border-slate-100 shadow-sm">
                    <textarea id="comment-edit-input-${comment.id}" class="w-full p-2 text-xs bg-slate-50 border-none rounded-xl outline-none focus:ring-0 resize-none min-h-[60px] font-medium text-slate-700">${comment.content}</textarea>
                    <div class="flex justify-end gap-3 mt-2">
                        <button onclick="cancelEditComment('${comment.id}')" class="px-3 py-1.5 text-[10px] font-bold text-slate-400 hover:text-slate-600 transition-colors">Cancel</button>
                        <button onclick="saveEditComment('${comment.id}')" class="px-4 py-1.5 text-[10px] font-bold bg-slate-900 text-white rounded-lg hover:bg-black transition-all shadow-sm">Save</button>
                    </div>
                </div>
                
                <div class="flex items-center gap-4 mt-1.5 ml-2">
                    <span class="text-[10px] font-medium text-slate-400 uppercase tracking-widest">${formatPostTime(comment.created_at)}</span>
                    <button onclick="setReply('${comment.id}', '${toTitleCase(comment.profiles.full_name)}')" class="text-[10px] font-bold text-slate-400 hover:text-slate-900 transition-colors uppercase tracking-widest">Reply</button>
                </div>
            </div>
        </div>
        ${!isReply ? '<div class="comment-replies border-l-2 border-slate-50 ml-[18px] pl-6 mt-2"></div>' : ''}
    `;
    return div;
}

function renderCommentsList(list, comments) {
    if (comments.length > 0) {
        list.innerHTML = '';
        const topLevel = comments.filter((c) => !c.parent_id);
        const replies = comments.filter((c) => c.parent_id);

        topLevel.forEach((comment) => {
            const commentEl = renderComment(comment);
            list.appendChild(commentEl);

            const commentReplies = replies.filter((r) => r.parent_id === comment.id);
            if (commentReplies.length > 0) {
                const repliesContainer = commentEl.querySelector('.comment-replies');
                repliesContainer.style.display = 'none';

                const toggleBtn = document.createElement('button');
                toggleBtn.className = 'view-replies-btn text-[11px] font-bold text-slate-400 hover:text-slate-600 flex items-center gap-2 mt-2 ml-12 transition-colors';
                toggleBtn.onclick = () => toggleReplies(comment.id, toggleBtn);
                toggleBtn.innerHTML = `
                    <svg class="w-3 h-3 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 9l-7 7-7-7"></path></svg>
                    <span>Show ${commentReplies.length} ${commentReplies.length === 1 ? 'reply' : 'replies'}</span>
                `;

                commentEl.insertBefore(toggleBtn, repliesContainer);
                commentReplies.forEach((reply) => {
                    repliesContainer.appendChild(renderComment(reply, true));
                });
            }
        });
    } else {
        list.innerHTML = '<div class="text-center py-12"><p class="text-xs text-slate-300 italic">No entries yet.</p></div>';
    }
}

async function fetchComments(postId, options = {}) {
    const { silent = false, force = false } = options;
    const list = document.getElementById('modalCommentsList');
    if (!list) return;
    if (!silent) {
        list.innerHTML = '<div class="text-center py-12"><p class="text-xs text-slate-400 animate-pulse">Synchronizing conversation...</p></div>';
    }
    
    try {
        const commentsUrl = isAdminContext ? `/admin/posts/${postId}/comments` : `/posts/${postId}/comments`;
        const response = await fetch(commentsUrl, { headers: { 'Accept': 'application/json' } });
        const data = await response.json();

        const nextSignature = (data.comments || []).map(c => `${c.id}:${c.updated_at}`).join('|');
        if (!force && currentCommentsSignature && nextSignature === currentCommentsSignature) return;

        currentCommentsSignature = nextSignature;
        renderCommentsList(list, data.comments || []);
    } catch (error) {
        console.error('Error fetching comments:', error);
    }
}

function toggleReplies(commentId, btn) {
    const parentEl = document.getElementById(`comment-${commentId}`);
    const repliesContainer = parentEl.querySelector('.comment-replies');
    const isHidden = repliesContainer.style.display === 'none';
    
    if (isHidden) {
        repliesContainer.style.display = 'flex';
        btn.querySelector('svg').style.transform = 'rotate(180deg)';
        btn.querySelector('span').innerText = 'Hide replies';
    } else {
        repliesContainer.style.display = 'none';
        btn.querySelector('svg').style.transform = 'rotate(0deg)';
        const count = repliesContainer.children.length;
        btn.querySelector('span').innerText = `Show ${count} ${count === 1 ? 'reply' : 'replies'}`;
    }
}

function startModalCommentPolling(postId) {
    stopModalCommentPolling();
    modalCommentPollTimer = setInterval(() => {
        if (!currentPost || String(currentPost.id) !== String(postId)) return;
        if (document.hidden) return;
        fetchComments(postId, { silent: true });
    }, 5000);
}

function stopModalCommentPolling() {
    if (modalCommentPollTimer) clearInterval(modalCommentPollTimer);
}

function updateModalActions(post) {
    const likeBtn = document.getElementById('modalLikeBtn');
    if (post.user_has_liked) {
        likeBtn.classList.add('text-red-500');
        likeBtn.querySelector('svg').classList.add('fill-current');
    } else {
        likeBtn.classList.remove('text-red-500');
        likeBtn.querySelector('svg').classList.remove('fill-current');
    }

    if (isAdminContext) {
        likeBtn.onclick = () => showModerationPopup('Liking is disabled in admin moderation view.');
    }
}

async function toggleLike(postId, btn) {
    if (isAdminContext) return;
    try {
        const response = await fetch(`/posts/${postId}/like`, { method: 'POST', headers: { 'X-CSRFToken': getCSRFToken() } });
        const data = await response.json();
        var liked = data.status === 'liked';
        if (liked) {
            btn.classList.add('text-red-500');
            btn.querySelector('svg').classList.add('fill-current');
        } else {
            btn.classList.remove('text-red-500');
            btn.querySelector('svg').classList.remove('fill-current');
        }
        // Optimistically update like count on the card
        var card = document.querySelector('.post-card[data-post-id="' + postId + '"]');
        if (card) {
            var countEl = card.querySelector('.likes-count');
            if (countEl) {
                var cur = parseInt(countEl.textContent, 10) || 0;
                countEl.textContent = String(Math.max(0, cur + (liked ? 1 : -1)));
            }
        }
        if (window.requestInteractionSync) window.requestInteractionSync(postId);
    } catch (error) {
        console.error('Like error:', error);
    }
}

async function submitComment(event) {
    event.preventDefault();
    if (isAdminContext) return;
    const textarea = document.getElementById('commentTextarea');
    const content = textarea.value.trim();
    if (!content || !currentPost) return;

    try {
        const body = { content };
        if (currentReplyTo) body.parent_id = currentReplyTo.id;
        
        const response = await fetch(`/posts/${currentPost.id}/comments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
            body: JSON.stringify(body)
        });
        const data = await response.json();
        if (!response.ok || data.status === 'blocked') {
            var msg = data.error || data.message || 'Your comment violates content policy.';
            if (typeof showModerationPopup === 'function') {
                showModerationPopup(msg);
            } else if (window.createToast) {
                window.createToast(msg, 'error');
            }
            return;
        }
        if (data.comment) {
            textarea.value = '';
            resizeCommentComposerTextarea(textarea);
            cancelReply();
            fetchComments(currentPost.id, { force: true, silent: true });
            // Optimistically update comment count on the card
            var card = document.querySelector('.post-card[data-post-id="' + currentPost.id + '"]');
            if (card) {
                var countEl = card.querySelector('.comments-count');
                if (countEl) countEl.textContent = String((parseInt(countEl.textContent, 10) || 0) + 1);
            }
            if (window.requestInteractionSync) window.requestInteractionSync(currentPost.id);
        }
    } catch (error) {
        console.error('Comment error:', error);
    }
}

function setReply(commentId, userName) {
    currentReplyTo = { id: commentId, name: userName };
    const textarea = document.getElementById('commentTextarea');
    textarea.value = `@${userName} `;
    resizeCommentComposerTextarea(textarea);
    textarea.focus();
}

function cancelReply() {
    currentReplyTo = null;
}

function startEditComment(commentId) {
    const area = document.getElementById(`comment-edit-area-${commentId}`);
    const input = document.getElementById(`comment-edit-input-${commentId}`);
    if (!area || !input) return;
    area.classList.remove('hidden');
    input.focus();
    input.setSelectionRange(input.value.length, input.value.length);
}

function cancelEditComment(commentId) {
    const area = document.getElementById(`comment-edit-area-${commentId}`);
    if (area) area.classList.add('hidden');
}

async function saveEditComment(commentId) {
    const input = document.getElementById(`comment-edit-input-${commentId}`);
    const text = document.getElementById(`comment-text-${commentId}`);
    if (!input || !text) return;
    const content = input.value.trim();
    if (!content) return;

    try {
        const response = await fetch(`/comments/${commentId}/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
            body: JSON.stringify({ content })
        });
        const data = await response.json();
        if (!response.ok || (data && data.error)) {
            showModerationPopup((data && data.error) || 'Failed to update comment.');
            return;
        }
        text.innerText = content;
        cancelEditComment(commentId);
        if (window.requestInteractionSync && currentPost) window.requestInteractionSync(currentPost.id);
    } catch (error) {
        console.error('Update comment error:', error);
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
                if (!response.ok || (data && data.error)) {
                    showModerationPopup((data && data.error) || 'Failed to delete comment.');
                    return;
                }
                const node = document.getElementById(`comment-${commentId}`);
                if (node) node.remove();
                if (currentPost) fetchComments(currentPost.id, { force: true, silent: true });
                if (window.requestInteractionSync && currentPost) window.requestInteractionSync(currentPost.id);
            } catch (error) {
                console.error('Delete comment error:', error);
            }
        }
    );
}

function closeConfirmModal() {
    const modal = document.getElementById('confirmModal');
    if (!modal) return;
    modal.classList.remove('active', 'modal-visible');
    setTimeout(() => {
        modal.style.display = 'none';
    }, 150);

    const confirmBtn = document.getElementById('confirmActionBtn');
    if (confirmBtn) confirmBtn.onclick = null;

    const reasonContainer = document.getElementById('confirmReasonContainer');
    const reasonSelect = document.getElementById('confirmReasonSelect');
    const reasonNote = document.getElementById('confirmReasonNote');
    if (reasonContainer) reasonContainer.classList.add('hidden');
    if (reasonSelect) reasonSelect.innerHTML = '<option value="">Select a reason</option>';
    if (reasonNote) reasonNote.value = '';
}

function showConfirmModal(title, message, onConfirm, options = {}) {
    const modal = document.getElementById('confirmModal');
    const titleEl = document.getElementById('confirmTitle');
    const msgEl = document.getElementById('confirmMessage');
    const confirmBtn = document.getElementById('confirmActionBtn');
    const reasonContainer = document.getElementById('confirmReasonContainer');
    const reasonSelect = document.getElementById('confirmReasonSelect');
    const reasonNote = document.getElementById('confirmReasonNote');
    if (!modal || !titleEl || !msgEl || !confirmBtn) return false;

    titleEl.textContent = title || 'Confirm Action';
    msgEl.textContent = message || 'Are you sure you want to proceed with this action?';

    const reasons = Array.isArray(options.reasons) ? options.reasons : [];
    const requireReason = Boolean(options.requireReason);
    if (reasonContainer && reasonSelect && reasons.length > 0) {
        reasonContainer.classList.remove('hidden');
        reasonSelect.innerHTML = '<option value="">Select a reason</option>';
        reasons.forEach((reason) => {
            const option = document.createElement('option');
            option.value = reason;
            option.textContent = reason;
            reasonSelect.appendChild(option);
        });
    } else if (reasonContainer) {
        reasonContainer.classList.add('hidden');
        if (reasonSelect) reasonSelect.innerHTML = '<option value="">Select a reason</option>';
        if (reasonNote) reasonNote.value = '';
    }

    confirmBtn.onclick = async () => {
        const payload = {
            reason: reasonSelect ? reasonSelect.value : '',
            note: reasonNote ? reasonNote.value.trim() : ''
        };
        if (requireReason && !payload.reason) {
            showModerationPopup('Please select a reason before continuing.');
            return;
        }
        closeConfirmModal();
        if (typeof onConfirm === 'function') await onConfirm(payload);
    };

    modal.style.display = 'flex';
    requestAnimationFrame(() => modal.classList.add('active'));
    return true;
}

document.addEventListener('DOMContentLoaded', () => {
    initCommentComposerInteractions();
    checkHashAndOpenModal();
    window.addEventListener('hashchange', checkHashAndOpenModal);
});
