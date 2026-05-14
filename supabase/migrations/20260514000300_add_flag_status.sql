-- Add flagged status to posts and comments
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS is_flagged boolean DEFAULT false;
ALTER TABLE public.comments ADD COLUMN IF NOT EXISTS is_flagged boolean DEFAULT false;
