-- Migration to support merged notifications and actor avatars
ALTER TABLE public.notifications ADD COLUMN IF NOT EXISTS actor_id uuid REFERENCES public.profiles(id);

-- Comment for documentation
COMMENT ON COLUMN public.notifications.actor_id IS 'The user who triggered the notification (used for displaying their photo)';
