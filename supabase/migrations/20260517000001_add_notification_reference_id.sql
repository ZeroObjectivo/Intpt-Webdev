-- Migration to ensure reference_id exists in notifications table
ALTER TABLE public.notifications ADD COLUMN IF NOT EXISTS reference_id uuid;

-- Add a comment for documentation
COMMENT ON COLUMN public.notifications.reference_id IS 'ID of the related entity (e.g., post_id for like/comment notifications)';
