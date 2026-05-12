// Image Modal Logic (Facebook Theater Style)
let currentPost = null;
let currentIdx = 0;
let isDragging = false;
let hasMoved = false;
let startX, startY;
let translateX = 0, translateY = 0;
let currentScale = 1;

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

function openImageModal(post, index) {
    currentPost = post;
    currentIdx = index;
    
    resetZoomState();
    updateModalContent();
    
    document.getElementById('imageModal').style.display = 'flex';
    document.body.style.overflow = 'hidden';
    
    // Update URL hash for persistence (e.g., #view-post-123-0)
    window.location.hash = `view-post-${post.id}-${index}`;
}

function closeImageModal(event) {
    const modal = document.getElementById('imageModal');
    if (!event || event.target === modal || event.target.closest('.modal-close')) {
        if (document.fullscreenElement) {
            document.exitFullscreen();
        }
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
        
        // Clear hash on close
        history.pushState("", document.title, window.location.pathname + window.location.search);
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
    if (wrapper.classList.contains('zoomed')) {
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
    
    modalImg.src = currentPost.image_urls[currentIdx];
    
    if (currentPost.image_urls.length <= 1) {
        prevBtn.style.display = 'none';
        nextBtn.style.display = 'none';
    } else {
        prevBtn.style.display = 'flex';
        nextBtn.style.display = 'flex';
    }

    document.getElementById('modalUserAvatar').src = currentPost.profiles.avatar_url || "/static/images/Logo.png";
    document.getElementById('modalUserName').innerText = currentPost.profiles.full_name;
    document.getElementById('modalPostTime').innerText = formatPostTime(currentPost.created_at);
    document.getElementById('modalPostText').innerText = currentPost.content;

    const badge = document.getElementById('modalCategoryBadge');
    badge.innerText = currentPost.category;
    badge.className = "inline-block px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-widest mb-3 ";
    
    const cat = currentPost.category;
    if (cat === 'General') badge.classList.add('badge-general');
    else if (cat === 'Lost & Found') badge.classList.add('badge-lost-found');
    else if (cat === 'Buy & Sell') badge.classList.add('badge-buy-sell');
    else if (cat === 'Question') badge.classList.add('badge-question');
    else if (cat === 'Events') badge.classList.add('badge-events');

    const dynamic = document.getElementById('modalDynamicDetails');
    dynamic.innerHTML = '';
    
    if (currentPost.price) {
        dynamic.innerHTML += `<div class="flex items-center gap-2 text-xs font-bold text-emerald-600">
            <span class="bg-emerald-50 px-2 py-1 rounded">₱${parseFloat(currentPost.price).toLocaleString()}</span>
        </div>`;
    }
    if (currentPost.location) {
        dynamic.innerHTML += `<div class="flex items-center gap-2 text-xs font-bold text-slate-500">
            <span class="bg-slate-100 px-2 py-1 rounded">📍 ${currentPost.location}</span>
        </div>`;
    }
}

function formatPostTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) + ' at ' + 
           date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
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

    // Handle Persistence on Refresh
    if (window.location.hash.startsWith('#view-post-')) {
        const parts = window.location.hash.split('-');
        const postId = parts[2];
        const imgIdx = parseInt(parts[3] || 0);
        
        // We need the 'allPosts' data from the dashboard
        if (window.allPosts) {
            const post = window.allPosts.find(p => p.id == postId);
            if (post) openImageModal(post, imgIdx);
        }
    }
});
