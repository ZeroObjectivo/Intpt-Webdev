-- Migration to support Admin Dashboard features
-- 1. Add status and ban tracking to profiles
ALTER TABLE public.profiles 
ADD COLUMN IF NOT EXISTS status text DEFAULT 'active',
ADD COLUMN IF NOT EXISTS ban_reason text;

-- 2. Create Admin Logs table for "Recent Activities"
CREATE TABLE IF NOT EXISTS public.admin_logs (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    admin_id uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    action_type text NOT NULL, -- 'ban', 'suspend', 'warn', 'remove_post', 'update_config'
    target_id uuid, -- ID of the user or post acted upon
    details text,
    created_at timestamp with time zone DEFAULT now()
);

-- 3. Create Verification Disputes table
CREATE TABLE IF NOT EXISTS public.verification_disputes (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    email text NOT NULL,
    full_name text,
    reason text,
    status text DEFAULT 'pending', -- 'pending', 'resolved', 'rejected'
    created_at timestamp with time zone DEFAULT now()
);

-- 4. Create User Warnings table
CREATE TABLE IF NOT EXISTS public.warnings (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id uuid REFERENCES public.profiles(id) ON DELETE CASCADE,
    admin_id uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    reason text NOT NULL,
    post_id uuid REFERENCES public.posts(id) ON DELETE SET NULL,
    created_at timestamp with time zone DEFAULT now()
);

-- Enable RLS
ALTER TABLE public.admin_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.verification_disputes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.warnings ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Admins can view admin logs" ON public.admin_logs
    FOR SELECT USING (EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin', 'super_admin')));

CREATE POLICY "Admins can view disputes" ON public.verification_disputes
    FOR SELECT USING (EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin', 'super_admin')));

CREATE POLICY "Admins can view warnings" ON public.warnings
    FOR SELECT USING (EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin', 'super_admin')));

CREATE POLICY "Users can view their own warnings" ON public.warnings
    FOR SELECT USING (auth.uid() = user_id);
