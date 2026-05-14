-- Drop the existing restrictive policy
DROP POLICY IF EXISTS "Admins can insert notifications" ON public.notifications;

-- Create a new, more inclusive policy for inserting notifications
CREATE POLICY "Admins can insert notifications" ON public.notifications
FOR INSERT
WITH CHECK (
  EXISTS (
    SELECT 1
    FROM public.profiles
    WHERE
      id = auth.uid() AND
      role IN ('admin', 'super_admin', 'superadmin', 'super admin')
  )
)
