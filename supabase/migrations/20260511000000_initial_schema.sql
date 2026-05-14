-- =============================================================
-- Herons' Hub - Complete Initial Schema
-- =============================================================
-- Extracted from the live Supabase project on 2026-05-14.
-- Run this on a fresh Supabase project. All later migrations
-- in this folder use IF NOT EXISTS / IF EXISTS and are safe
-- to run after this, but are effectively no-ops.
-- =============================================================


-- =============================================
--  FUNCTIONS (must exist before triggers)
-- =============================================

-- Auto-set updated_at on row update
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

-- Sanitize posts/comments against forbidden words
CREATE OR REPLACE FUNCTION public.sanitize_etiquette()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
    bad_regex text;
BEGIN
    SELECT string_agg('\y' || word || '\y', '|')
      INTO bad_regex
      FROM public.forbidden_words;

    IF bad_regex IS NOT NULL THEN
        NEW.content := regexp_replace(NEW.content, bad_regex, '****', 'gi');
    END IF;

    RETURN NEW;
END;
$$;

-- Trigger-based likes_count sync
CREATE OR REPLACE FUNCTION public.update_post_likes_count()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        UPDATE public.posts SET likes_count = likes_count + 1 WHERE id = NEW.post_id;
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        UPDATE public.posts SET likes_count = likes_count - 1 WHERE id = OLD.post_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;

-- Trigger-based likes sync (newer version with COALESCE/GREATEST)
CREATE OR REPLACE FUNCTION public.handle_like_sync()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        UPDATE public.posts SET likes_count = COALESCE(likes_count, 0) + 1 WHERE id = NEW.post_id;
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        UPDATE public.posts SET likes_count = GREATEST(COALESCE(likes_count, 0) - 1, 0) WHERE id = OLD.post_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;

-- Trigger-based comments_count sync (only top-level comments)
CREATE OR REPLACE FUNCTION public.handle_comment_sync()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        IF (NEW.parent_id IS NULL) THEN
            UPDATE public.posts SET comments_count = COALESCE(comments_count, 0) + 1 WHERE id = NEW.post_id;
        END IF;
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        IF (OLD.parent_id IS NULL) THEN
            UPDATE public.posts SET comments_count = GREATEST(COALESCE(comments_count, 0) - 1, 0) WHERE id = OLD.post_id;
        END IF;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;

-- Bulk sync all post counts (utility)
CREATE OR REPLACE FUNCTION public.sync_all_post_counts()
RETURNS void LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    UPDATE public.posts p SET likes_count = (SELECT count(*) FROM public.likes l WHERE l.post_id = p.id);
    UPDATE public.posts p SET comments_count = (SELECT count(*) FROM public.comments c WHERE c.post_id = p.id AND c.parent_id IS NULL);
END;
$$;

-- RPC: increment likes_count
CREATE OR REPLACE FUNCTION public.increment_likes_count(row_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    UPDATE public.posts SET likes_count = COALESCE(likes_count, 0) + 1 WHERE id = row_id;
END;
$$;

-- RPC: decrement likes_count
CREATE OR REPLACE FUNCTION public.decrement_likes_count(row_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    UPDATE public.posts SET likes_count = GREATEST(COALESCE(likes_count, 0) - 1, 0) WHERE id = row_id;
END;
$$;

-- RPC: increment comments_count
CREATE OR REPLACE FUNCTION public.increment_comments_count(row_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    UPDATE public.posts SET comments_count = COALESCE(comments_count, 0) + 1 WHERE id = row_id;
END;
$$;

-- RPC: decrement comments_count
CREATE OR REPLACE FUNCTION public.decrement_comments_count(row_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    UPDATE public.posts SET comments_count = GREATEST(COALESCE(comments_count, 0) - 1, 0) WHERE id = row_id;
END;
$$;

-- RPC: create post (array variant)
CREATE OR REPLACE FUNCTION public.create_post_rpc(
    user_id uuid, content text, category text,
    price numeric, location text, status text,
    event_date timestamptz, image_urls text[]
) RETURNS void LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    INSERT INTO public.posts (user_id, content, category, price, location, status, event_date, image_urls)
    VALUES (user_id, content, category, price, location, status, event_date, image_urls);
END;
$$;

-- RPC: create post (single-image variant)
CREATE OR REPLACE FUNCTION public.create_post_rpc(
    p_user_id uuid, p_content text, p_category text,
    p_price numeric, p_location text, p_status text,
    p_event_date timestamptz, p_image_urls text
) RETURNS void LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    INSERT INTO public.posts (user_id, content, category, price, location, status, event_date, image_url)
    VALUES (p_user_id, p_content, p_category, p_price, p_location, p_status, p_event_date, p_image_urls);
END;
$$;


-- =============================================
--  TABLES
-- =============================================

-- 1. PROFILES
CREATE TABLE IF NOT EXISTS public.profiles (
    id                uuid        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email             text        UNIQUE NOT NULL,
    full_name         text,
    avatar_url        text,
    role              text        DEFAULT 'student',
    created_at        timestamptz NOT NULL DEFAULT timezone('utc', now()),
    updated_at        timestamptz NOT NULL DEFAULT timezone('utc', now()),
    contact_number    text,
    contact_privacy   text        DEFAULT 'public',
    college           text,
    course            text,
    level             text,
    bio               text,
    status            text        DEFAULT 'active',
    ban_reason        text
);

-- 2. POSTS
CREATE TABLE IF NOT EXISTS public.posts (
    id                uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           uuid        NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    content           text        NOT NULL,
    category          text        DEFAULT 'General',
    image_url         text,
    created_at        timestamptz NOT NULL DEFAULT timezone('utc', now()),
    updated_at        timestamptz NOT NULL DEFAULT timezone('utc', now()),
    price             numeric,
    location          text,
    status            text,
    event_date        timestamptz,
    likes_count       integer     DEFAULT 0,
    image_urls        text[]      DEFAULT '{}',
    comments_count    integer     DEFAULT 0,
    event_end_date    timestamptz
);

CREATE INDEX IF NOT EXISTS idx_posts_user_id     ON public.posts(user_id);
CREATE INDEX IF NOT EXISTS idx_posts_category    ON public.posts(category);
CREATE INDEX IF NOT EXISTS idx_posts_created_at  ON public.posts(created_at DESC);

-- 3. LIKES
CREATE TABLE IF NOT EXISTS public.likes (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid        REFERENCES public.profiles(id) ON DELETE CASCADE,
    post_id     uuid        REFERENCES public.posts(id) ON DELETE CASCADE,
    created_at  timestamp   DEFAULT now(),
    UNIQUE(user_id, post_id)
);

CREATE INDEX IF NOT EXISTS idx_likes_post_id ON public.likes(post_id);
CREATE INDEX IF NOT EXISTS idx_likes_user_id ON public.likes(user_id);

-- 4. COMMENTS
CREATE TABLE IF NOT EXISTS public.comments (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id     uuid        REFERENCES public.posts(id) ON DELETE CASCADE,
    user_id     uuid        REFERENCES public.profiles(id) ON DELETE CASCADE,
    content     text        NOT NULL,
    created_at  timestamp   DEFAULT now(),
    updated_at  timestamp   DEFAULT now(),
    parent_id   uuid        REFERENCES public.comments(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_comments_post_id    ON public.comments(post_id);
CREATE INDEX IF NOT EXISTS idx_comments_user_id    ON public.comments(user_id);
CREATE INDEX IF NOT EXISTS idx_comments_parent_id  ON public.comments(parent_id);

-- 5. GROUPS
CREATE TABLE IF NOT EXISTS public.groups (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    name        text        NOT NULL,
    type        text,
    description text,
    created_at  timestamp   DEFAULT now()
);

-- 6. GROUP MEMBERS
CREATE TABLE IF NOT EXISTS public.group_members (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id    uuid        REFERENCES public.groups(id) ON DELETE CASCADE,
    user_id     uuid        REFERENCES public.profiles(id) ON DELETE CASCADE,
    role        text        DEFAULT 'member',
    created_at  timestamp   DEFAULT now(),
    UNIQUE(group_id, user_id)
);

-- 7. EVENTS
CREATE TABLE IF NOT EXISTS public.events (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    title       text        NOT NULL,
    description text,
    location    text,
    event_date  timestamp,
    created_by  uuid        REFERENCES public.profiles(id),
    group_id    uuid        REFERENCES public.groups(id),
    created_at  timestamp   DEFAULT now()
);

-- 8. EVENT RSVPs
CREATE TABLE IF NOT EXISTS public.event_rsvps (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id    uuid        REFERENCES public.events(id) ON DELETE CASCADE,
    user_id     uuid        REFERENCES public.profiles(id) ON DELETE CASCADE,
    status      text        DEFAULT 'going',
    created_at  timestamp   DEFAULT now(),
    UNIQUE(event_id, user_id)
);

-- 9. ANNOUNCEMENTS
CREATE TABLE IF NOT EXISTS public.announcements (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    title       text        NOT NULL,
    content     text        NOT NULL,
    created_by  uuid        REFERENCES public.profiles(id),
    group_id    uuid        REFERENCES public.groups(id),
    created_at  timestamp   DEFAULT now()
);

-- 10. NOTIFICATIONS
CREATE TABLE IF NOT EXISTS public.notifications (
    id           uuid       PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      uuid       REFERENCES public.profiles(id) ON DELETE CASCADE,
    type         text,
    reference_id uuid,
    is_read      boolean    DEFAULT false,
    created_at   timestamp  DEFAULT now()
);

-- 11. REPORTS
CREATE TABLE IF NOT EXISTS public.reports (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id     uuid        NOT NULL REFERENCES public.posts(id) ON DELETE CASCADE,
    reporter_id uuid        NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    reason      text        NOT NULL,
    status      text        DEFAULT 'pending',
    created_at  timestamptz DEFAULT timezone('utc', now())
);

-- 12. WARNINGS
CREATE TABLE IF NOT EXISTS public.warnings (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid        REFERENCES public.profiles(id) ON DELETE CASCADE,
    admin_id    uuid        REFERENCES public.profiles(id) ON DELETE SET NULL,
    reason      text        NOT NULL,
    post_id     uuid        REFERENCES public.posts(id) ON DELETE SET NULL,
    created_at  timestamptz DEFAULT now()
);

-- 13. ADMIN LOGS
CREATE TABLE IF NOT EXISTS public.admin_logs (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id    uuid        REFERENCES public.profiles(id) ON DELETE SET NULL,
    action_type text        NOT NULL,
    target_id   uuid,
    details     text,
    created_at  timestamptz DEFAULT now()
);

-- 14. FORBIDDEN WORDS
CREATE TABLE IF NOT EXISTS public.forbidden_words (
    word        text        PRIMARY KEY,
    created_at  timestamptz DEFAULT timezone('utc', now())
);

-- 15. VERIFICATION DISPUTES
CREATE TABLE IF NOT EXISTS public.verification_disputes (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    email       text        NOT NULL,
    full_name   text,
    reason      text,
    status      text        DEFAULT 'pending',
    created_at  timestamptz DEFAULT now()
);


-- =============================================
--  TRIGGERS
-- =============================================

-- Auto updated_at on profiles
CREATE OR REPLACE TRIGGER set_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- Auto updated_at on posts
CREATE OR REPLACE TRIGGER set_updated_at_posts
    BEFORE UPDATE ON public.posts
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- Sanitize posts content
CREATE OR REPLACE TRIGGER trigger_sanitize_posts
    BEFORE INSERT OR UPDATE ON public.posts
    FOR EACH ROW EXECUTE FUNCTION public.sanitize_etiquette();

-- Sanitize comments content
CREATE OR REPLACE TRIGGER trigger_sanitize_comments
    BEFORE INSERT OR UPDATE ON public.comments
    FOR EACH ROW EXECUTE FUNCTION public.sanitize_etiquette();

-- Likes count sync trigger
DROP TRIGGER IF EXISTS trigger_update_post_likes_count ON public.likes;
DROP TRIGGER IF EXISTS on_like_change ON public.likes;
CREATE TRIGGER on_like_change
    AFTER INSERT OR DELETE ON public.likes
    FOR EACH ROW EXECUTE FUNCTION public.handle_like_sync();

-- Comments count sync trigger (top-level only)
DROP TRIGGER IF EXISTS on_comment_change ON public.comments;
CREATE TRIGGER on_comment_change
    AFTER INSERT OR DELETE ON public.comments
    FOR EACH ROW EXECUTE FUNCTION public.handle_comment_sync();


-- =============================================
--  ROW LEVEL SECURITY
-- =============================================

ALTER TABLE public.profiles              ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.posts                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.likes                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.comments              ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.groups                ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.group_members         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.events                ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.event_rsvps           ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.announcements         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reports               ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.warnings              ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.admin_logs            ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.forbidden_words       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.verification_disputes ENABLE ROW LEVEL SECURITY;


-- =============================================
--  RLS POLICIES
-- =============================================

-- ---- profiles ----
CREATE POLICY "Profiles are viewable by everyone"  ON public.profiles FOR SELECT USING (true);
CREATE POLICY "Users can insert their own profile"  ON public.profiles FOR INSERT WITH CHECK (auth.uid() = id);
CREATE POLICY "Users can update their own profile"  ON public.profiles FOR UPDATE USING (auth.uid() = id);
CREATE POLICY "Admins can update all profiles"      ON public.profiles FOR UPDATE USING (
    EXISTS (SELECT 1 FROM profiles WHERE profiles.id = auth.uid() AND profiles.role IN ('admin','super_admin'))
);

-- ---- posts ----
CREATE POLICY "Posts are viewable by everyone"   ON public.posts FOR SELECT USING (true);
CREATE POLICY "Users can insert their own posts" ON public.posts FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update their own posts" ON public.posts FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete their own posts" ON public.posts FOR DELETE USING (auth.uid() = user_id);

-- ---- likes ----
CREATE POLICY "Allow public read access"    ON public.likes FOR SELECT USING (true);
CREATE POLICY "Allow authenticated insert"  ON public.likes FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Allow individual delete"     ON public.likes FOR DELETE USING (auth.uid() = user_id);

-- ---- comments ----
CREATE POLICY "Allow public read access"    ON public.comments FOR SELECT USING (true);
CREATE POLICY "Allow authenticated insert"  ON public.comments FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Allow individual update"     ON public.comments FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Allow individual delete"     ON public.comments FOR DELETE USING (auth.uid() = user_id);

-- ---- reports ----
CREATE POLICY "Users can report posts"  ON public.reports FOR INSERT WITH CHECK (auth.uid() = reporter_id);
CREATE POLICY "Admins can view reports" ON public.reports FOR SELECT USING (
    EXISTS (SELECT 1 FROM profiles WHERE profiles.id = auth.uid() AND profiles.role IN ('admin','super_admin','content_moderator'))
);

-- ---- warnings ----
CREATE POLICY "Users can view their own warnings" ON public.warnings FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Admins can view all warnings"      ON public.warnings FOR SELECT USING (
    EXISTS (SELECT 1 FROM profiles WHERE profiles.id = auth.uid() AND profiles.role IN ('admin','super_admin'))
);

-- ---- admin_logs ----
CREATE POLICY "Admins can view admin logs" ON public.admin_logs FOR SELECT USING (
    EXISTS (SELECT 1 FROM profiles WHERE profiles.id = auth.uid() AND profiles.role IN ('admin','super_admin'))
);
CREATE POLICY "Admins can insert logs"     ON public.admin_logs FOR INSERT WITH CHECK (
    EXISTS (SELECT 1 FROM profiles WHERE profiles.id = auth.uid() AND profiles.role IN ('admin','super_admin'))
);

-- ---- forbidden_words ----
CREATE POLICY "Admins can view forbidden words"   ON public.forbidden_words FOR SELECT USING (
    EXISTS (SELECT 1 FROM profiles WHERE profiles.id = auth.uid() AND profiles.role IN ('admin','super_admin','content_moderator'))
);
CREATE POLICY "Admins can manage forbidden words" ON public.forbidden_words FOR ALL USING (
    EXISTS (SELECT 1 FROM profiles WHERE profiles.id = auth.uid() AND profiles.role IN ('admin','super_admin'))
);

-- ---- verification_disputes ----
CREATE POLICY "Allow anonymous inserts into disputes" ON public.verification_disputes FOR INSERT WITH CHECK (true);
CREATE POLICY "Admins can view disputes"              ON public.verification_disputes FOR SELECT USING (
    EXISTS (SELECT 1 FROM profiles WHERE profiles.id = auth.uid() AND profiles.role IN ('admin','super_admin'))
);

-- ---- groups ----
CREATE POLICY "Groups are viewable by everyone"       ON public.groups FOR SELECT USING (true);
CREATE POLICY "Authenticated users can create groups"  ON public.groups FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

-- ---- group_members ----
CREATE POLICY "Group members are viewable by everyone" ON public.group_members FOR SELECT USING (true);
CREATE POLICY "Users can join groups"                  ON public.group_members FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can leave groups"                 ON public.group_members FOR DELETE USING (auth.uid() = user_id);

-- ---- events ----
CREATE POLICY "Events are viewable by everyone"       ON public.events FOR SELECT USING (true);
CREATE POLICY "Authenticated users can create events"  ON public.events FOR INSERT WITH CHECK (auth.uid() = created_by);

-- ---- event_rsvps ----
CREATE POLICY "RSVPs are viewable by everyone"  ON public.event_rsvps FOR SELECT USING (true);
CREATE POLICY "Users can RSVP"                  ON public.event_rsvps FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update their RSVP"     ON public.event_rsvps FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can cancel RSVP"           ON public.event_rsvps FOR DELETE USING (auth.uid() = user_id);

-- ---- announcements ----
CREATE POLICY "Announcements are viewable by everyone"       ON public.announcements FOR SELECT USING (true);
CREATE POLICY "Authenticated users can create announcements"  ON public.announcements FOR INSERT WITH CHECK (auth.uid() = created_by);

-- ---- notifications ----
CREATE POLICY "Users can view their notifications"   ON public.notifications FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "System can insert notifications"      ON public.notifications FOR INSERT WITH CHECK (true);
CREATE POLICY "Users can update their notifications" ON public.notifications FOR UPDATE USING (auth.uid() = user_id);


-- =============================================
--  STORAGE
-- =============================================

INSERT INTO storage.buckets (id, name, public)
VALUES ('post-images', 'post-images', true)
ON CONFLICT (id) DO UPDATE SET public = true;

CREATE POLICY "Allow public access"               ON storage.objects FOR SELECT USING (bucket_id = 'post-images');
CREATE POLICY "Allow authenticated uploads"        ON storage.objects FOR INSERT WITH CHECK (
    bucket_id = 'post-images' AND auth.role() = 'authenticated'
);
CREATE POLICY "Users can update their own images"  ON storage.objects FOR UPDATE WITH CHECK (
    bucket_id = 'post-images' AND (storage.foldername(name))[1] = auth.uid()::text
);
CREATE POLICY "Users can delete their own images"  ON storage.objects FOR DELETE USING (
    bucket_id = 'post-images' AND (storage.foldername(name))[1] = auth.uid()::text
);
