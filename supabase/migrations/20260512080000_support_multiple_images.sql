-- Update posts table to support multiple images
ALTER TABLE "public"."posts" 
DROP COLUMN IF EXISTS "image_url",
ADD COLUMN IF NOT EXISTS "image_urls" TEXT[] DEFAULT '{}';

-- Re-verify Storage Bucket and Policies
INSERT INTO storage.buckets (id, name, public)
VALUES ('post-images', 'post-images', true)
ON CONFLICT (id) DO NOTHING;

-- Policies for public viewing
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'objects' AND policyname = 'Public Access'
    ) THEN
        CREATE POLICY "Public Access" ON storage.objects FOR SELECT USING (bucket_id = 'post-images');
    END IF;
END $$;

-- Policies for authenticated uploads
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'objects' AND policyname = 'Authenticated users can upload'
    ) THEN
        CREATE POLICY "Authenticated users can upload" ON storage.objects FOR INSERT WITH CHECK (
            bucket_id = 'post-images' AND auth.role() = 'authenticated'
        );
    END IF;
END $$;
