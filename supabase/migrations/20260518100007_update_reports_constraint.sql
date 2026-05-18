-- Drop the old strict constraint that prevents comment reporting
ALTER TABLE public.reports DROP CONSTRAINT IF EXISTS reports_target_check;

-- Add a new flexible constraint that allows exactly one primary target or a specific combination
-- Standard: Exactly one of post_id, reported_user_id, OR comment_id must be provided
-- Refinement: Allow comment_id to co-exist with post_id for better context, or just keep it simple.
-- Let's stick to the principle of identifying the PRIMARY target.
ALTER TABLE public.reports
    ADD CONSTRAINT reports_target_check
    CHECK (
        (post_id IS NOT NULL AND reported_user_id IS NULL AND comment_id IS NULL) OR -- Post Report
        (post_id IS NULL AND reported_user_id IS NOT NULL AND comment_id IS NULL) OR -- User Report
        (comment_id IS NOT NULL) -- Comment Report (Allowing co-existence with post/user for context)
    );
