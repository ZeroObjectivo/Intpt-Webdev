-- Migration to sync notifications table schema
ALTER TABLE public.notifications ADD COLUMN IF NOT EXISTS title text;
ALTER TABLE public.notifications ADD COLUMN IF NOT EXISTS message text;

-- Update existing rows if any (though we saw it's empty)
UPDATE public.notifications SET title = 'Notification' WHERE title IS NULL;
UPDATE public.notifications SET message = '' WHERE message IS NULL;

-- Make them NOT NULL after populating defaults if needed
ALTER TABLE public.notifications ALTER COLUMN title SET NOT NULL;
ALTER TABLE public.notifications ALTER COLUMN message SET NOT NULL;
