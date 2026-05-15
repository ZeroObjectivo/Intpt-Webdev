-- Add missing indexes on high-frequency lookup columns
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON public.notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_warnings_user_id ON public.warnings(user_id);

-- Fix missing ON DELETE CASCADE on events and announcements foreign keys.
-- Drop existing constraints (names inferred from PostgreSQL defaults) and re-add with CASCADE.

-- events.created_by
ALTER TABLE public.events DROP CONSTRAINT IF EXISTS events_created_by_fkey;
ALTER TABLE public.events
    ADD CONSTRAINT events_created_by_fkey
    FOREIGN KEY (created_by) REFERENCES public.profiles(id) ON DELETE SET NULL;

-- events.group_id
ALTER TABLE public.events DROP CONSTRAINT IF EXISTS events_group_id_fkey;
ALTER TABLE public.events
    ADD CONSTRAINT events_group_id_fkey
    FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE SET NULL;

-- announcements.created_by
ALTER TABLE public.announcements DROP CONSTRAINT IF EXISTS announcements_created_by_fkey;
ALTER TABLE public.announcements
    ADD CONSTRAINT announcements_created_by_fkey
    FOREIGN KEY (created_by) REFERENCES public.profiles(id) ON DELETE SET NULL;

-- announcements.group_id
ALTER TABLE public.announcements DROP CONSTRAINT IF EXISTS announcements_group_id_fkey;
ALTER TABLE public.announcements
    ADD CONSTRAINT announcements_group_id_fkey
    FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE SET NULL;
