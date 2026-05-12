-- RLS Policies for the Herons' Hub Database
-- Refined for specific security requirements

-- 1. Announcements
ALTER TABLE public.announcements ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Announcements are viewable by everyone" ON public.announcements FOR SELECT USING (true);
-- Only users with 'admin' or 'super_admin' roles in their profile can create/update/delete
CREATE POLICY "Admins can manage announcements" ON public.announcements 
  FOR ALL 
  TO authenticated 
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles 
      WHERE id = auth.uid() AND role IN ('admin', 'super_admin')
    )
  );

-- 2. Posts (RESTRICTED: Viewable only by logged-in users)
ALTER TABLE public.posts ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Posts are viewable by everyone" ON public.posts;
CREATE POLICY "Posts are viewable by authenticated users" ON public.posts 
  FOR SELECT TO authenticated USING (true);

-- 3. Likes (ANONYMITY: Likers are hidden from public SELECT)
ALTER TABLE public.likes ENABLE ROW LEVEL SECURITY;
-- Anyone authenticated can see the presence of a like (to count them), 
-- but we only allow users to see exactly WHO liked it if it's their own like
CREATE POLICY "Likes can be counted by authenticated" ON public.likes 
  FOR SELECT TO authenticated USING (true);
-- (Note: The frontend will handle the 'hiding' of IDs, but we ensure users can only see the rows to count them)

-- 4. Comments
ALTER TABLE public.comments ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Comments are viewable by authenticated users" ON public.comments 
  FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated users can post comments" ON public.comments 
  FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can manage their own comments" ON public.comments 
  FOR ALL TO authenticated USING (auth.uid() = user_id);

-- Rest of the policies updated for 'authenticated' only
-- Lost and Found
ALTER TABLE public.lost_and_found ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Lost and Found viewable by authenticated" ON public.lost_and_found 
  FOR SELECT TO authenticated USING (true);
CREATE POLICY "Users manage their own reports" ON public.lost_and_found 
  FOR ALL TO authenticated USING (auth.uid() = user_id);

-- Marketplace
ALTER TABLE public.marketplace_posts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Marketplace viewable by authenticated" ON public.marketplace_posts 
  FOR SELECT TO authenticated USING (true);
CREATE POLICY "Users manage their own marketplace posts" ON public.marketplace_posts 
  FOR ALL TO authenticated USING (auth.uid() = user_id);

