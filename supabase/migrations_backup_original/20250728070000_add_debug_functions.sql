-- Debug functions for investigating user creation issues
CREATE OR REPLACE FUNCTION get_auth_user_by_email(user_email TEXT)
RETURNS TABLE(
    id UUID,
    email TEXT,
    email_confirmed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT au.id, au.email, au.email_confirmed_at, au.created_at, au.updated_at
    FROM auth.users au
    WHERE au.email = user_email;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION get_all_auth_users()
RETURNS TABLE(
    id UUID,
    email TEXT,
    email_confirmed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT au.id, au.email, au.email_confirmed_at, au.created_at
    FROM auth.users au
    ORDER BY au.created_at DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER; 