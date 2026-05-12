-- Add dynamic fields to posts table
ALTER TABLE "public"."posts" 
ADD COLUMN IF NOT EXISTS "price" NUMERIC,
ADD COLUMN IF NOT EXISTS "location" TEXT,
ADD COLUMN IF NOT EXISTS "status" TEXT,
ADD COLUMN IF NOT EXISTS "event_date" TIMESTAMP WITH TIME ZONE;

-- Add comments for documentation
COMMENT ON COLUMN "public"."posts"."price" IS 'Price for Buy & Sell posts';
COMMENT ON COLUMN "public"."posts"."location" IS 'Location for Lost & Found or Events';
COMMENT ON COLUMN "public"."posts"."status" IS 'Status (e.g., Available/Sold for Buy & Sell, Lost/Found for Lost & Found)';
COMMENT ON COLUMN "public"."posts"."event_date" IS 'Date and time for Events';
