-- 1. Ensure the bucket exists and is public
INSERT INTO storage.buckets (id, name, public)
VALUES ('post-images', 'post-images', true)
ON CONFLICT (id) DO UPDATE SET public = true;

-- 2. Drop existing policies to avoid conflicts
DROP POLICY IF EXISTS "Public Access" ON storage.objects;
DROP POLICY IF EXISTS "Authenticated users can upload" ON storage.objects;
DROP POLICY IF EXISTS "Allow public access" ON storage.objects;
DROP POLICY IF EXISTS "Allow authenticated uploads" ON storage.objects;
DROP POLICY IF EXISTS "Users can update their own images" ON storage.objects;
DROP POLICY IF EXISTS "Users can delete their own images" ON storage.objects;

-- 3. Create robust policies for storage

-- Allow anyone to view images (since bucket is public)
CREATE POLICY "Allow public access" ON storage.objects
FOR SELECT USING (bucket_id = 'post-images');

-- Allow authenticated users to upload to post-images
-- We also allow anon role as a fallback if the backend is using the anon key
CREATE POLICY "Allow authenticated uploads" ON storage.objects
FOR INSERT WITH CHECK (
    bucket_id = 'post-images' 
    AND (auth.role() = 'authenticated' OR auth.role() = 'anon')
);

-- Allow users to update their own images
CREATE POLICY "Users can update their own images" ON storage.objects
FOR UPDATE WITH CHECK (
    bucket_id = 'post-images' 
    AND (storage.foldername(name))[1] = auth.uid()::text
);

-- Allow users to delete their own images
CREATE POLICY "Users can delete their own images" ON storage.objects
FOR DELETE USING (
    bucket_id = 'post-images' 
    AND (storage.foldername(name))[1] = auth.uid()::text
);
