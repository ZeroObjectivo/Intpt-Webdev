-- =============================================
--  FIX: Missing ON DELETE actions on all FKs
--  FIX: Missing UNIQUE constraints
--  FIX: Missing indexes
--  FIX: notifications title/message NOT NULL
--
--  Safe to run multiple times (all IF EXISTS / IF NOT EXISTS).
-- =============================================


-- =============================================
--  1. PROFILES — FK to auth.users
-- =============================================
ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_id_fkey;
ALTER TABLE public.profiles
    ADD CONSTRAINT profiles_id_fkey
    FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE;


-- =============================================
--  2. POSTS — user_id FK
-- =============================================
ALTER TABLE public.posts DROP CONSTRAINT IF EXISTS posts_user_id_fkey;
ALTER TABLE public.posts
    ADD CONSTRAINT posts_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES public.profiles(id) ON DELETE CASCADE;


-- =============================================
--  3. LIKES — FKs + UNIQUE
-- =============================================
ALTER TABLE public.likes DROP CONSTRAINT IF EXISTS likes_user_id_fkey;
ALTER TABLE public.likes
    ADD CONSTRAINT likes_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES public.profiles(id) ON DELETE CASCADE;

ALTER TABLE public.likes DROP CONSTRAINT IF EXISTS likes_post_id_fkey;
ALTER TABLE public.likes
    ADD CONSTRAINT likes_post_id_fkey
    FOREIGN KEY (post_id) REFERENCES public.posts(id) ON DELETE CASCADE;

-- Prevent duplicate likes
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'likes_user_id_post_id_key'
    ) THEN
        ALTER TABLE public.likes ADD CONSTRAINT likes_user_id_post_id_key UNIQUE (user_id, post_id);
    END IF;
END $$;


-- =============================================
--  4. COMMENTS — FKs
-- =============================================
ALTER TABLE public.comments DROP CONSTRAINT IF EXISTS comments_post_id_fkey;
ALTER TABLE public.comments
    ADD CONSTRAINT comments_post_id_fkey
    FOREIGN KEY (post_id) REFERENCES public.posts(id) ON DELETE CASCADE;

ALTER TABLE public.comments DROP CONSTRAINT IF EXISTS comments_user_id_fkey;
ALTER TABLE public.comments
    ADD CONSTRAINT comments_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES public.profiles(id) ON DELETE CASCADE;

ALTER TABLE public.comments DROP CONSTRAINT IF EXISTS comments_parent_id_fkey;
ALTER TABLE public.comments
    ADD CONSTRAINT comments_parent_id_fkey
    FOREIGN KEY (parent_id) REFERENCES public.comments(id) ON DELETE CASCADE;


-- =============================================
--  5. GROUP_MEMBERS — FKs + UNIQUE
-- =============================================
ALTER TABLE public.group_members DROP CONSTRAINT IF EXISTS group_members_group_id_fkey;
ALTER TABLE public.group_members
    ADD CONSTRAINT group_members_group_id_fkey
    FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;

ALTER TABLE public.group_members DROP CONSTRAINT IF EXISTS group_members_user_id_fkey;
ALTER TABLE public.group_members
    ADD CONSTRAINT group_members_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES public.profiles(id) ON DELETE CASCADE;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'group_members_group_id_user_id_key'
    ) THEN
        ALTER TABLE public.group_members ADD CONSTRAINT group_members_group_id_user_id_key UNIQUE (group_id, user_id);
    END IF;
END $$;


-- =============================================
--  6. EVENTS — FKs (SET NULL, not CASCADE)
-- =============================================
ALTER TABLE public.events DROP CONSTRAINT IF EXISTS events_created_by_fkey;
ALTER TABLE public.events
    ADD CONSTRAINT events_created_by_fkey
    FOREIGN KEY (created_by) REFERENCES public.profiles(id) ON DELETE SET NULL;

ALTER TABLE public.events DROP CONSTRAINT IF EXISTS events_group_id_fkey;
ALTER TABLE public.events
    ADD CONSTRAINT events_group_id_fkey
    FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE SET NULL;


-- =============================================
--  7. EVENT_RSVPS — FKs + UNIQUE
-- =============================================
ALTER TABLE public.event_rsvps DROP CONSTRAINT IF EXISTS event_rsvps_event_id_fkey;
ALTER TABLE public.event_rsvps
    ADD CONSTRAINT event_rsvps_event_id_fkey
    FOREIGN KEY (event_id) REFERENCES public.events(id) ON DELETE CASCADE;

ALTER TABLE public.event_rsvps DROP CONSTRAINT IF EXISTS event_rsvps_user_id_fkey;
ALTER TABLE public.event_rsvps
    ADD CONSTRAINT event_rsvps_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES public.profiles(id) ON DELETE CASCADE;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'event_rsvps_event_id_user_id_key'
    ) THEN
        ALTER TABLE public.event_rsvps ADD CONSTRAINT event_rsvps_event_id_user_id_key UNIQUE (event_id, user_id);
    END IF;
END $$;


-- =============================================
--  8. ANNOUNCEMENTS — FKs
-- =============================================
ALTER TABLE public.announcements DROP CONSTRAINT IF EXISTS announcements_created_by_fkey;
ALTER TABLE public.announcements
    ADD CONSTRAINT announcements_created_by_fkey
    FOREIGN KEY (created_by) REFERENCES public.profiles(id) ON DELETE SET NULL;

ALTER TABLE public.announcements DROP CONSTRAINT IF EXISTS announcements_group_id_fkey;
ALTER TABLE public.announcements
    ADD CONSTRAINT announcements_group_id_fkey
    FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE SET NULL;


-- =============================================
--  9. NOTIFICATIONS — FK + NOT NULL
-- =============================================
ALTER TABLE public.notifications DROP CONSTRAINT IF EXISTS notifications_user_id_fkey;
ALTER TABLE public.notifications
    ADD CONSTRAINT notifications_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES public.profiles(id) ON DELETE CASCADE;

-- Backfill any NULLs before adding NOT NULL
UPDATE public.notifications SET title = 'Notification' WHERE title IS NULL;
UPDATE public.notifications SET message = '' WHERE message IS NULL;
ALTER TABLE public.notifications ALTER COLUMN title SET NOT NULL;
ALTER TABLE public.notifications ALTER COLUMN message SET NOT NULL;


-- =============================================
--  10. REPORTS — FKs
-- =============================================
ALTER TABLE public.reports DROP CONSTRAINT IF EXISTS reports_post_id_fkey;
ALTER TABLE public.reports
    ADD CONSTRAINT reports_post_id_fkey
    FOREIGN KEY (post_id) REFERENCES public.posts(id) ON DELETE CASCADE;

ALTER TABLE public.reports DROP CONSTRAINT IF EXISTS reports_reporter_id_fkey;
ALTER TABLE public.reports
    ADD CONSTRAINT reports_reporter_id_fkey
    FOREIGN KEY (reporter_id) REFERENCES public.profiles(id) ON DELETE CASCADE;


-- =============================================
--  11. WARNINGS — FKs
-- =============================================
ALTER TABLE public.warnings DROP CONSTRAINT IF EXISTS warnings_user_id_fkey;
ALTER TABLE public.warnings
    ADD CONSTRAINT warnings_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES public.profiles(id) ON DELETE CASCADE;

ALTER TABLE public.warnings DROP CONSTRAINT IF EXISTS warnings_admin_id_fkey;
ALTER TABLE public.warnings
    ADD CONSTRAINT warnings_admin_id_fkey
    FOREIGN KEY (admin_id) REFERENCES public.profiles(id) ON DELETE SET NULL;

ALTER TABLE public.warnings DROP CONSTRAINT IF EXISTS warnings_post_id_fkey;
ALTER TABLE public.warnings
    ADD CONSTRAINT warnings_post_id_fkey
    FOREIGN KEY (post_id) REFERENCES public.posts(id) ON DELETE SET NULL;


-- =============================================
--  12. ADMIN_LOGS — FK
-- =============================================
ALTER TABLE public.admin_logs DROP CONSTRAINT IF EXISTS admin_logs_admin_id_fkey;
ALTER TABLE public.admin_logs
    ADD CONSTRAINT admin_logs_admin_id_fkey
    FOREIGN KEY (admin_id) REFERENCES public.profiles(id) ON DELETE SET NULL;


-- =============================================
--  13. ALL MISSING INDEXES
-- =============================================
CREATE INDEX IF NOT EXISTS idx_posts_user_id        ON public.posts(user_id);
CREATE INDEX IF NOT EXISTS idx_posts_category       ON public.posts(category);
CREATE INDEX IF NOT EXISTS idx_posts_created_at     ON public.posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_likes_post_id        ON public.likes(post_id);
CREATE INDEX IF NOT EXISTS idx_likes_user_id        ON public.likes(user_id);
CREATE INDEX IF NOT EXISTS idx_comments_post_id     ON public.comments(post_id);
CREATE INDEX IF NOT EXISTS idx_comments_user_id     ON public.comments(user_id);
CREATE INDEX IF NOT EXISTS idx_comments_parent_id   ON public.comments(parent_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON public.notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_warnings_user_id     ON public.warnings(user_id);
