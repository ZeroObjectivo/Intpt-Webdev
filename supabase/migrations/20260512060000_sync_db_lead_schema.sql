-- Migration to sync local schema with remote Supabase state
-- Created based on Database Lead's schema definitions

-- Announcements
CREATE TABLE IF NOT EXISTS public.announcements (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  title text NOT NULL,
  content text NOT NULL,
  created_by uuid,
  group_id uuid,
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT announcements_pkey PRIMARY KEY (id)
);

-- Groups
CREATE TABLE IF NOT EXISTS public.groups (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  name text NOT NULL,
  type text,
  description text,
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT groups_pkey PRIMARY KEY (id)
);

-- Comments
CREATE TABLE IF NOT EXISTS public.comments (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  post_id uuid,
  user_id uuid,
  content text NOT NULL,
  created_at timestamp without time zone DEFAULT now(),
  updated_at timestamp without time zone DEFAULT now(),
  CONSTRAINT comments_pkey PRIMARY KEY (id)
);

-- Likes
CREATE TABLE IF NOT EXISTS public.likes (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid,
  post_id uuid,
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT likes_pkey PRIMARY KEY (id)
);

-- Events
CREATE TABLE IF NOT EXISTS public.events (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  title text NOT NULL,
  description text,
  location text,
  event_date timestamp without time zone,
  created_by uuid,
  group_id uuid,
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT events_pkey PRIMARY KEY (id)
);

-- Event RSVPs
CREATE TABLE IF NOT EXISTS public.event_rsvps (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  event_id uuid,
  user_id uuid,
  status text DEFAULT 'going'::text,
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT event_rsvps_pkey PRIMARY KEY (id)
);

-- Group Members
CREATE TABLE IF NOT EXISTS public.group_members (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  group_id uuid,
  user_id uuid,
  role text DEFAULT 'member'::text,
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT group_members_pkey PRIMARY KEY (id)
);

-- Lost and Found
CREATE TABLE IF NOT EXISTS public.lost_and_found (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid,
  type text NOT NULL,
  title text NOT NULL,
  description text,
  image_url text,
  location text,
  status text DEFAULT 'open'::text,
  claimed_by uuid,
  created_at timestamp without time zone DEFAULT now(),
  updated_at timestamp without time zone DEFAULT now(),
  CONSTRAINT lost_and_found_pkey PRIMARY KEY (id)
);

-- Marketplace Posts
CREATE TABLE IF NOT EXISTS public.marketplace_posts (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid,
  title text NOT NULL,
  description text,
  price numeric,
  image_url text,
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT marketplace_posts_pkey PRIMARY KEY (id)
);

-- Notifications
CREATE TABLE IF NOT EXISTS public.notifications (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid,
  type text,
  reference_id uuid,
  is_read boolean DEFAULT false,
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT notifications_pkey PRIMARY KEY (id)
);

-- Foreign Key Constraints (Added separately to ensure tables exist first)
ALTER TABLE public.announcements ADD CONSTRAINT announcements_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.profiles(id);
ALTER TABLE public.announcements ADD CONSTRAINT announcements_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id);
ALTER TABLE public.comments ADD CONSTRAINT comments_post_id_fkey FOREIGN KEY (post_id) REFERENCES public.posts(id);
ALTER TABLE public.comments ADD CONSTRAINT comments_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.profiles(id);
ALTER TABLE public.event_rsvps ADD CONSTRAINT event_rsvps_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.events(id);
ALTER TABLE public.event_rsvps ADD CONSTRAINT event_rsvps_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.profiles(id);
ALTER TABLE public.events ADD CONSTRAINT events_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.profiles(id);
ALTER TABLE public.events ADD CONSTRAINT events_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id);
ALTER TABLE public.group_members ADD CONSTRAINT group_members_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id);
ALTER TABLE public.group_members ADD CONSTRAINT group_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.profiles(id);
ALTER TABLE public.likes ADD CONSTRAINT likes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.profiles(id);
ALTER TABLE public.likes ADD CONSTRAINT likes_post_id_fkey FOREIGN KEY (post_id) REFERENCES public.posts(id);
ALTER TABLE public.lost_and_found ADD CONSTRAINT lost_and_found_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.profiles(id);
ALTER TABLE public.lost_and_found ADD CONSTRAINT lost_and_found_claimed_by_fkey FOREIGN KEY (claimed_by) REFERENCES public.profiles(id);
ALTER TABLE public.marketplace_posts ADD CONSTRAINT marketplace_posts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.profiles(id);
ALTER TABLE public.notifications ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.profiles(id);

-- Update Posts table with new columns if they don't exist
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='posts' AND column_name='price') THEN
        ALTER TABLE public.posts ADD COLUMN price numeric;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='posts' AND column_name='location') THEN
        ALTER TABLE public.posts ADD COLUMN location text;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='posts' AND column_name='status') THEN
        ALTER TABLE public.posts ADD COLUMN status text;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='posts' AND column_name='event_date') THEN
        ALTER TABLE public.posts ADD COLUMN event_date timestamp with time zone;
    END IF;
END $$;
