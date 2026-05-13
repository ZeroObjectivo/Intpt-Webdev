-- RPC for incrementing likes_count
CREATE OR REPLACE FUNCTION increment_likes_count(row_id uuid)
RETURNS void AS $$
BEGIN
  UPDATE public.posts
  SET likes_count = COALESCE(likes_count, 0) + 1
  WHERE id = row_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- RPC for decrementing likes_count
CREATE OR REPLACE FUNCTION decrement_likes_count(row_id uuid)
RETURNS void AS $$
BEGIN
  UPDATE public.posts
  SET likes_count = GREATEST(COALESCE(likes_count, 0) - 1, 0)
  WHERE id = row_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- RPC for incrementing comments_count
CREATE OR REPLACE FUNCTION increment_comments_count(row_id uuid)
RETURNS void AS $$
BEGIN
  UPDATE public.posts
  SET comments_count = COALESCE(comments_count, 0) + 1
  WHERE id = row_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- RPC for decrementing comments_count
CREATE OR REPLACE FUNCTION decrement_comments_count(row_id uuid)
RETURNS void AS $$
BEGIN
  UPDATE public.posts
  SET comments_count = GREATEST(COALESCE(comments_count, 0) - 1, 0)
  WHERE id = row_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
