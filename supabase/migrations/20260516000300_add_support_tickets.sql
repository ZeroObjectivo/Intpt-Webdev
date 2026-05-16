-- Create support_tickets table
CREATE TABLE IF NOT EXISTS public.support_tickets (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id uuid REFERENCES public.profiles(id) ON DELETE CASCADE,
    subject text NOT NULL,
    message text NOT NULL,
    status text DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'resolved', 'closed')),
    admin_notes text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Enable RLS
ALTER TABLE public.support_tickets ENABLE ROW LEVEL SECURITY;

-- Users can view their own tickets
CREATE POLICY "Users can view their own support tickets"
    ON public.support_tickets FOR SELECT
    USING (auth.uid() = user_id);

-- Users can insert their own tickets
CREATE POLICY "Users can create support tickets"
    ON public.support_tickets FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Admins can do everything
CREATE POLICY "Admins can manage all support tickets"
    ON public.support_tickets FOR ALL
    USING (EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid() AND role IN ('admin', 'super_admin', 'account_manager', 'content_moderator')
    ));

-- Log the schema update
INSERT INTO public.admin_logs (action_type, details) 
VALUES ('schema_update', 'Created support_tickets table for Heron Support feature.');
