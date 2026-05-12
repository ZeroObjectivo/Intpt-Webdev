-- 1. Add likes_count column to posts table
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS likes_count int DEFAULT 0;

-- 2. Create the trigger function
CREATE OR REPLACE FUNCTION public.update_post_likes_count()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        UPDATE public.posts
        SET likes_count = likes_count + 1
        WHERE id = NEW.post_id;
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        UPDATE public.posts
        SET likes_count = likes_count - 1
        WHERE id = OLD.post_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 3. Create the trigger on the likes table
DROP TRIGGER IF EXISTS trigger_update_post_likes_count ON public.likes;
CREATE TRIGGER trigger_update_post_likes_count
AFTER INSERT OR DELETE ON public.likes
FOR EACH ROW EXECUTE FUNCTION public.update_post_likes_count();

-- 4. SYNC: Update existing counts (in case there are already likes in the DB)
UPDATE public.posts p
SET likes_count = (
    SELECT count(*)
    FROM public.likes l
    WHERE l.post_id = p.id
);
