-- Create user roles system for admin authentication
CREATE TYPE public.app_role AS ENUM ('owner', 'admin', 'user');

-- Create user_roles table
CREATE TABLE public.user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    role app_role NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE (user_id, role)
);

-- Enable RLS on user_roles
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;

-- Create security definer function to check roles (prevents RLS recursion)
CREATE OR REPLACE FUNCTION public.has_role(_user_id UUID, _role app_role)
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.user_roles
    WHERE user_id = _user_id
      AND role = _role
  )
$$;

-- RLS policies for user_roles table
CREATE POLICY "Users can view their own roles"
ON public.user_roles
FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

CREATE POLICY "Only owners can manage roles"
ON public.user_roles
FOR ALL
TO authenticated
USING (public.has_role(auth.uid(), 'owner'));

-- Create profiles table for user information
CREATE TABLE public.profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL UNIQUE,
    email TEXT,
    display_name TEXT,
    avatar_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Enable RLS on profiles
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Profiles policies  
CREATE POLICY "Users can view all profiles"
ON public.profiles
FOR SELECT
TO authenticated
USING (true);

CREATE POLICY "Users can update their own profile"
ON public.profiles
FOR UPDATE
TO authenticated
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own profile"
ON public.profiles
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);

-- Trigger for updating profiles updated_at
CREATE TRIGGER update_profiles_updated_at
BEFORE UPDATE ON public.profiles
FOR EACH ROW
EXECUTE FUNCTION public.update_updated_at_column();

-- Create ETL execution log table
CREATE TABLE public.etl_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    etl_type TEXT NOT NULL, -- 'ctgov', 'fda', 'edgar'
    status TEXT NOT NULL, -- 'running', 'success', 'failed'
    started_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    completed_at TIMESTAMP WITH TIME ZONE,
    executed_by UUID REFERENCES auth.users(id),
    error_message TEXT,
    records_processed INTEGER
);

-- Enable RLS on etl_executions
ALTER TABLE public.etl_executions ENABLE ROW LEVEL SECURITY;

-- ETL executions policies
CREATE POLICY "Owners and admins can view ETL executions"
ON public.etl_executions
FOR SELECT
TO authenticated
USING (
    public.has_role(auth.uid(), 'owner') OR 
    public.has_role(auth.uid(), 'admin')
);

CREATE POLICY "Owners and admins can insert ETL executions"
ON public.etl_executions
FOR INSERT
TO authenticated
WITH CHECK (
    public.has_role(auth.uid(), 'owner') OR 
    public.has_role(auth.uid(), 'admin')
);