-- Migration to allow anonymous inserts into verification_disputes
-- This allows the backend to record restricted login attempts even if the user is not authenticated

CREATE POLICY "Allow anonymous inserts into disputes" ON public.verification_disputes
    FOR INSERT WITH CHECK (true);
