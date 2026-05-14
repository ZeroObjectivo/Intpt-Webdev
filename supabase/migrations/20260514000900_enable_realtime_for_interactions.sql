-- Enable Realtime publication for interaction tables used by live UI sync
DO $$
BEGIN
    BEGIN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.likes;
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END;

    BEGIN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.comments;
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END;
END $$;
