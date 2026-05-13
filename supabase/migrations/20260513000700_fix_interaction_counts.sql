-- Migration to fix dangling likes and comments counts
-- 1. Create a function to recalculate all post counts
CREATE OR REPLACE FUNCTION sync_all_post_counts()
RETURNS void AS $$
BEGIN
  -- Recalculate likes_count
  UPDATE public.posts p
  SET likes_count = (
    SELECT count(*)
    FROM public.likes l
    WHERE l.post_id = p.id
  );

  -- Recalculate comments_count
  UPDATE public.posts p
  SET comments_count = (
    SELECT count(*)
    FROM public.comments c
    WHERE c.post_id = p.id
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- For Likes
CREATE OR REPLACE FUNCTION handle_like_sync()
RETURNS TRIGGER AS $$
BEGIN
  IF (TG_OP = 'INSERT') THEN
    UPDATE public.posts
    SET likes_count = COALESCE(likes_count, 0) + 1
    WHERE id = NEW.post_id;
    RETURN NEW;
  ELSIF (TG_OP = 'DELETE') THEN
    UPDATE public.posts
    SET likes_count = GREATEST(COALESCE(likes_count, 0) - 1, 0)
    WHERE id = OLD.post_id;
    RETURN OLD;
  END IF;
  RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_like_change ON public.likes;
CREATE TRIGGER on_like_change
  AFTER INSERT OR DELETE ON public.likes
  FOR EACH ROW
  EXECUTE FUNCTION handle_like_sync();

-- For Comments
CREATE OR REPLACE FUNCTION handle_comment_sync()
RETURNS TRIGGER AS $$
BEGIN
  IF (TG_OP = 'INSERT') THEN
    UPDATE public.posts
    SET comments_count = COALESCE(comments_count, 0) + 1
    WHERE id = NEW.post_id;
    RETURN NEW;
  ELSIF (TG_OP = 'DELETE') THEN
    UPDATE public.posts
    SET comments_count = GREATEST(COALESCE(comments_count, 0) - 1, 0)
    WHERE id = OLD.post_id;
    RETURN OLD;
  END IF;
  RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_comment_change ON public.comments;
CREATE TRIGGER on_comment_change
  AFTER INSERT OR DELETE ON public.comments
  FOR EACH ROW
  EXECUTE FUNCTION handle_comment_sync();

-- 3. Run a one-time sync to fix existing discrepancies
SELECT sync_all_post_counts();
