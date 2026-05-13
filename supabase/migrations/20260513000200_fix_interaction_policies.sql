-- RLS Policies for Likes
ALTER TABLE public.likes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow public read access" ON public.likes;
CREATE POLICY "Allow public read access" ON public.likes
    FOR SELECT USING (true);

DROP POLICY IF EXISTS "Allow authenticated insert" ON public.likes;
CREATE POLICY "Allow authenticated insert" ON public.likes
    FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Allow individual delete" ON public.likes;
CREATE POLICY "Allow individual delete" ON public.likes
    FOR DELETE USING (auth.uid() = user_id);

-- RLS Policies for Comments
ALTER TABLE public.comments ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow public read access" ON public.comments;
CREATE POLICY "Allow public read access" ON public.comments
    FOR SELECT USING (true);

DROP POLICY IF EXISTS "Allow authenticated insert" ON public.comments;
CREATE POLICY "Allow authenticated insert" ON public.comments
    FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Allow individual update" ON public.comments;
CREATE POLICY "Allow individual update" ON public.comments
    FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Allow individual delete" ON public.comments;
CREATE POLICY "Allow individual delete" ON public.comments
    FOR DELETE USING (auth.uid() = user_id);
