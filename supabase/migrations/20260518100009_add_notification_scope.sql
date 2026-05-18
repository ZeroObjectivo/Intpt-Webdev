-- Add scope column to notifications table to separate user-side and admin-side notifications
-- Scope 'user' is for personal notifications (likes, comments, etc.)
-- Scope 'admin' is for administrative alerts (reports, approvals, etc.)

ALTER TABLE public.notifications ADD COLUMN IF NOT EXISTS scope text DEFAULT 'user' CHECK (scope IN ('user', 'admin'));

-- Migration: Set existing 'admin' type notifications to 'admin' scope
UPDATE public.notifications SET scope = 'admin' WHERE type = 'admin';

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_notifications_user_id_scope ON public.notifications(user_id, scope);
CREATE INDEX IF NOT EXISTS idx_notifications_scope ON public.notifications(scope);
