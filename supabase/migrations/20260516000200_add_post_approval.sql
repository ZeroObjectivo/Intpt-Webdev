-- Add approval tracking to posts
ALTER TABLE public.posts 
    ADD COLUMN IF NOT EXISTS status text DEFAULT 'approved' CHECK (status IN ('approved', 'pending', 'rejected'));

-- Update existing posts with images to be pending if they haven't been reviewed
-- (In a real migration we might leave old ones approved, but for this rule:)
-- For new posts with images, we'll set them to pending via the application logic,
-- but let's ensure the default is 'approved' for text-only posts and handled in code.

-- Create an index for the moderation queue
CREATE INDEX IF NOT EXISTS idx_posts_status ON public.posts(status);

-- Update RLS: Users can see their own pending posts, but public can only see approved ones
DROP POLICY IF EXISTS "Public can view approved posts" ON public.posts;
CREATE POLICY "Public can view approved posts" ON public.posts
    FOR SELECT
    USING (status = 'approved' OR auth.uid() = user_id);

-- Log schema update
INSERT INTO public.admin_logs (action_type, details) 
VALUES ('schema_update', 'Added post approval status (approved/pending/rejected) and updated RLS for media moderation.');
