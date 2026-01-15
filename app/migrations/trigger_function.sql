-- migrations/trigger_function.sql
CREATE OR REPLACE FUNCTION track_tenant_profile_changes()
RETURNS TRIGGER AS $$
BEGIN
    -- If profile_data has changed
    IF (TG_OP = 'UPDATE' AND OLD.profile_data IS DISTINCT FROM NEW.profile_data) THEN
        -- Delete existing recommendations from tenantmetadata
        DELETE FROM tenantmetadata 
        WHERE tenantuuid = NEW.tenantuuid 
        AND metalogos_type IN ('ai_recommendations', 'ai_suggestions');
        
        -- Update last_ai_interaction to trigger refresh
        NEW.last_ai_interaction = NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create the trigger
CREATE TRIGGER tenant_profile_changes
    BEFORE UPDATE ON tenants
    FOR EACH ROW
    EXECUTE FUNCTION track_tenant_profile_changes();