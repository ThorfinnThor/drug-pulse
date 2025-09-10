-- Fix function search path security issues
CREATE OR REPLACE FUNCTION public.refresh_search_mv()
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY public.search_mv;
END;
$$;

CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

-- Fix materialized view API access - revoke public access
REVOKE SELECT ON public.search_mv FROM anon;
REVOKE SELECT ON public.search_mv FROM authenticated;