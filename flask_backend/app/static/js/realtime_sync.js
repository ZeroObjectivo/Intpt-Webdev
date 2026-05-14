(function () {
    const dashboardPage = document.querySelector('.dashboard-page');
    if (!dashboardPage || !window.currentUser || !window.currentUser.id) {
        return;
    }

    const syncConfig = window.dashboardSyncConfig || {};
    const realtimeConfig = window.realtimeConfig || {};
    const activeCategory = syncConfig.activeCategory || '';
    const pollIntervalMs = 7000;
    const notificationSyncIntervalMs = 15000;
    let baselineStateVersion = null;
    let latestAdminVersion = null;
    let pollInProgress = false;
    let reloadScheduled = false;
    let lastNotificationSyncAt = 0;
    let pendingInteractionPostIds = new Set();
    let interactionFlushTimer = null;
    let realtimeClient = null;
    let interactionsChannel = null;

    function getVisiblePostIds() {
        return Array.from(document.querySelectorAll('.post-card[data-post-id]'))
            .map((el) => el.dataset.postId)
            .filter(Boolean);
    }

    function updateLikeButtonVisual(likeBtn, isLiked) {
        if (!likeBtn) return;
        const icon = likeBtn.querySelector('svg');
        if (isLiked) {
            likeBtn.classList.add('text-red-500');
            likeBtn.classList.remove('text-slate-400');
            if (icon) icon.classList.add('fill-current');
        } else {
            likeBtn.classList.remove('text-red-500');
            likeBtn.classList.add('text-slate-400');
            if (icon) icon.classList.remove('fill-current');
        }
    }

    function syncPostCards(postRows) {
        const postMap = new Map((postRows || []).map((row) => [row.id, row]));

        document.querySelectorAll('.post-card[data-post-id]').forEach((card) => {
            const postId = card.dataset.postId;
            const row = postMap.get(postId);
            if (!row) return;

            const likeCount = card.querySelector('.likes-count');
            const commentCount = card.querySelector('.comments-count');
            const likeBtn = card.querySelector('.like-btn');

            if (likeCount) likeCount.textContent = String(row.likes_count || 0);
            if (commentCount) commentCount.textContent = String(row.comments_count || 0);
            updateLikeButtonVisual(likeBtn, !!row.user_has_liked);
        });

        if (Array.isArray(window.allPosts)) {
            const byId = new Map(window.allPosts.map((post) => [post.id, post]));
            (postRows || []).forEach((row) => {
                const post = byId.get(row.id);
                if (!post) return;
                post.likes_count = row.likes_count || 0;
                post.comments_count = row.comments_count || 0;
                post.user_has_liked = !!row.user_has_liked;
            });
        }

        // Let modal/comment views react instantly to count/like changes.
        window.dispatchEvent(new CustomEvent('dashboard-interactions-sync', {
            detail: { posts: postRows || [] }
        }));
    }

    function syncTrendingLikes(postRows) {
        const postMap = new Map((postRows || []).map((row) => [row.id, row]));

        document.querySelectorAll('.trending-item[data-post-id]').forEach((item) => {
            const postId = item.dataset.postId;
            const row = postMap.get(postId);
            if (!row) return;

            const likesLabel = item.querySelector('.likes');
            if (likesLabel) {
                likesLabel.textContent = formatTrendingLikes(row.likes_count || 0);
            }
        });
    }

    function formatTrendingLikes(value) {
        const n = Number(value || 0);
        if (n >= 1000000) return `${(n / 1000000).toFixed(1).replace(/\\.0$/, '')}m likes`;
        if (n >= 1000) return `${(n / 1000).toFixed(1).replace(/\\.0$/, '')}k likes`;
        return `${n} likes`;
    }

    function syncNotifications(notificationsPayload) {
        if (!notificationsPayload || typeof window.renderNotificationMenu !== 'function') {
            return;
        }
        const items = Array.isArray(notificationsPayload.items) ? notificationsPayload.items : [];
        const unreadCount = Number(notificationsPayload.unread_count || 0);
        window.renderNotificationMenu(items, unreadCount);
    }

    function scheduleReload(message) {
        if (reloadScheduled) return;
        reloadScheduled = true;

        if (typeof window.createToast === 'function') {
            window.createToast(message, 'info');
        }

        setTimeout(() => {
            window.location.reload();
        }, 1200);
    }

    function maybeRefreshForNewContent(state) {
        if (!state || !state.version) return;

        if (!baselineStateVersion) {
            baselineStateVersion = state.version;
            return;
        }

        if (baselineStateVersion !== state.version) {
            baselineStateVersion = state.version;
            scheduleReload('New posts, events, or trending updates detected. Refreshing.');
        }
    }

    function buildSyncUrl(path, includePostIds, overridePostIds) {
        const params = new URLSearchParams();
        if (activeCategory) {
            params.set('category', activeCategory);
        }
        if (includePostIds) {
            const postIds = Array.isArray(overridePostIds) && overridePostIds.length
                ? overridePostIds
                : getVisiblePostIds();
            if (postIds.length) {
                params.set('post_ids', postIds.join(','));
            }
        }
        const qs = params.toString();
        return qs ? `${path}?${qs}` : path;
    }

    function queueInteractionRefresh(postId) {
        if (!postId) return;
        pendingInteractionPostIds.add(postId);
        if (interactionFlushTimer) return;
        interactionFlushTimer = window.setTimeout(flushInteractionRefresh, 240);
    }

    async function flushInteractionRefresh() {
        interactionFlushTimer = null;
        const postIds = Array.from(pendingInteractionPostIds);
        pendingInteractionPostIds.clear();
        if (!postIds.length) return;

        try {
            const data = await fetchJson(buildSyncUrl('/sync/realtime', true, postIds));
            if (!data) return;
            const rows = data.interactions ? data.interactions.posts : [];
            syncPostCards(rows || []);
            syncTrendingLikes(rows || []);
        } catch (error) {
            console.error('Realtime interaction refresh failed:', error);
        }
    }

    async function fetchJson(url) {
        const response = await fetch(url, {
            headers: { 'Accept': 'application/json' }
        });
        if (response.status === 401) {
            window.location.href = '/login';
            return null;
        }
        if (!response.ok) {
            throw new Error(`Sync request failed (${response.status})`);
        }
        return response.json();
    }

    async function runLoadSync() {
        try {
            const data = await fetchJson(buildSyncUrl('/sync/dashboard/load', false));
            if (data && data.state && data.state.version) {
                baselineStateVersion = data.state.version;
            }
        } catch (error) {
            console.error('Dashboard load sync failed:', error);
        }
    }

    async function runLiveSync() {
        if (pollInProgress || document.hidden) return;
        pollInProgress = true;

        try {
            const data = await fetchJson(buildSyncUrl('/sync/realtime', true));
            if (!data) return;
            const now = Date.now();
            if (now - lastNotificationSyncAt >= notificationSyncIntervalMs) {
                syncNotifications(data.notifications);
                lastNotificationSyncAt = now;
            }
            syncPostCards(data.interactions ? data.interactions.posts : []);
            syncTrendingLikes(data.interactions ? data.interactions.posts : []);
            maybeRefreshForNewContent(data.state);

            if (data.admin && data.admin.version) {
                if (latestAdminVersion && latestAdminVersion !== data.admin.version && typeof window.createToast === 'function') {
                    window.createToast('Admin interaction update detected.', 'info');
                }
                latestAdminVersion = data.admin.version;
            }
        } catch (error) {
            console.error('Realtime sync failed:', error);
        } finally {
            pollInProgress = false;
        }
    }

    function initRealtimeInteractionSync() {
        if (!window.supabase || !window.supabase.createClient) return;
        if (!realtimeConfig.supabaseUrl || !realtimeConfig.supabaseAnonKey) return;

        try {
            const { createClient } = window.supabase;
            realtimeClient = createClient(realtimeConfig.supabaseUrl, realtimeConfig.supabaseAnonKey);

            interactionsChannel = realtimeClient
                .channel(`dashboard-interactions-${window.currentUser.id}`)
                .on('postgres_changes', { event: '*', schema: 'public', table: 'likes' }, (payload) => {
                    const row = (payload && payload.new && payload.new.post_id) ? payload.new : (payload ? payload.old : null);
                    if (row && row.post_id) queueInteractionRefresh(row.post_id);
                })
                .on('postgres_changes', { event: '*', schema: 'public', table: 'comments' }, (payload) => {
                    const row = (payload && payload.new && payload.new.post_id) ? payload.new : (payload ? payload.old : null);
                    if (row && row.post_id) {
                        queueInteractionRefresh(row.post_id);
                        window.dispatchEvent(new CustomEvent('dashboard-comment-mutation', {
                            detail: {
                                postId: row.post_id,
                                eventType: payload ? payload.eventType : null
                            }
                        }));
                    }
                })
                .subscribe((status) => {
                    if (status === 'CHANNEL_ERROR') {
                        console.error('Realtime interactions channel failed.');
                    }
                });

            window.requestInteractionSync = function (postId) {
                queueInteractionRefresh(postId);
            };
        } catch (error) {
            console.error('Failed to initialize realtime interaction sync:', error);
        }
    }

    document.addEventListener('visibilitychange', function () {
        if (!document.hidden) {
            runLiveSync();
        }
    });

    window.addEventListener('focus', function () {
        runLiveSync();
    });

    document.addEventListener('DOMContentLoaded', function () {
        runLoadSync().finally(function () {
            initRealtimeInteractionSync();
            runLiveSync();
            window.setInterval(runLiveSync, pollIntervalMs);
        });
    });

    window.addEventListener('beforeunload', function () {
        try {
            if (realtimeClient && interactionsChannel) {
                realtimeClient.removeChannel(interactionsChannel);
            }
        } catch (_e) {}
    });
})();
