-- Migration to fix comment count logic: only count top-level comments
-- 1. Update the sync function
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

  -- Recalculate comments_count (Only top-level comments)
  UPDATE public.posts p
  SET comments_count = (
    SELECT count(*)
    FROM public.comments c
    WHERE c.post_id = p.id AND c.parent_id IS NULL
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 2. Update the comment sync trigger function
CREATE OR REPLACE FUNCTION handle_comment_sync()
RETURNS TRIGGER AS $$
BEGIN
  IF (TG_OP = 'INSERT') THEN
    -- Only increment if it's a top-level comment
    IF (NEW.parent_id IS NULL) THEN
      UPDATE public.posts
      SET comments_count = COALESCE(comments_count, 0) + 1
      WHERE id = NEW.post_id;
    END IF;
    RETURN NEW;
  ELSIF (TG_OP = 'DELETE') THEN
    -- Only decrement if it's a top-level comment
    IF (OLD.parent_id IS NULL) THEN
      UPDATE public.posts
      SET comments_count = GREATEST(COALESCE(comments_count, 0) - 1, 0)
      WHERE id = OLD.post_id;
    END IF;
    RETURN OLD;
  END IF;
  RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 3. Run a one-time sync to fix existing counts
SELECT sync_all_post_counts();
