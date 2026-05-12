-- 1. Ensure dynamic fields and image_url exist in posts table
ALTER TABLE "public"."posts" 
ADD COLUMN IF NOT EXISTS "price" NUMERIC,
ADD COLUMN IF NOT EXISTS "location" TEXT,
ADD COLUMN IF NOT EXISTS "status" TEXT,
ADD COLUMN IF NOT EXISTS "event_date" TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS "image_url" TEXT;

-- 2. Storage Setup (Bucket and Policies)
-- Note: This requires the storage extension to be enabled (default in Supabase)
INSERT INTO storage.buckets (id, name, public)
VALUES ('post-images', 'post-images', true)
ON CONFLICT (id) DO NOTHING;

-- Policy to allow public to view images
CREATE POLICY "Public Access" ON storage.objects
FOR SELECT USING (bucket_id = 'post-images');

-- Policy to allow authenticated users to upload images
CREATE POLICY "Authenticated users can upload" ON storage.objects
FOR INSERT WITH CHECK (
  bucket_id = 'post-images' 
  AND auth.role() = 'authenticated'
);

-- 3. Likes (Helpful) Table
CREATE TABLE IF NOT EXISTS "public"."likes" (
    "id" "uuid" DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    "post_id" "uuid" REFERENCES "public"."posts"("id") ON DELETE CASCADE,
    "user_id" "uuid" REFERENCES "public"."profiles"("id") ON DELETE CASCADE,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE("post_id", "user_id")
);

-- 4. Comments Table
CREATE TABLE IF NOT EXISTS "public"."comments" (
    "id" "uuid" DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    "post_id" "uuid" REFERENCES "public"."posts"("id") ON DELETE CASCADE,
    "user_id" "uuid" REFERENCES "public"."profiles"("id") ON DELETE CASCADE,
    "content" TEXT NOT NULL,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- RLS Policies for Likes
ALTER TABLE "public"."likes" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Likes are viewable by everyone" ON "public"."likes" FOR SELECT USING (true);
CREATE POLICY "Users can toggle their own likes" ON "public"."likes" FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can remove their own likes" ON "public"."likes" FOR DELETE USING (auth.uid() = user_id);

-- RLS Policies for Comments
ALTER TABLE "public"."comments" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Comments are viewable by everyone" ON "public"."comments" FOR SELECT USING (true);
CREATE POLICY "Users can post comments" ON "public"."comments" FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update their own comments" ON "public"."comments" FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete their own comments" ON "public"."comments" FOR DELETE USING (auth.uid() = user_id);

-- Grant permissions
GRANT ALL ON TABLE "public"."likes" TO "authenticated";
GRANT ALL ON TABLE "public"."comments" TO "authenticated";
GRANT SELECT ON TABLE "public"."likes" TO "anon";
GRANT SELECT ON TABLE "public"."comments" TO "anon";
