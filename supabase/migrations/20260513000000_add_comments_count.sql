-- Migration to add comments_count to posts table
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS comments_count integer DEFAULT 0;

-- Optional: Update existing comments_count based on current comments
UPDATE public.posts p
SET comments_count = (
    SELECT count(*)
    FROM public.comments c
    WHERE c.post_id = p.id
);
