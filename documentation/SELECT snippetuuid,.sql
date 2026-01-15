SELECT snippetuuid,
       tenantuuid,
       snippetname,
       created_at,
       max_exec_secs
FROM public.snippets
LIMIT 1000;

delete from public.snippets
where snippetname in ('Test Logging Patch - Find Agent','debug_test_old_key.py','debug_test_current_key.py','Replace Agent Logging - Fix ANSI Codes','Check Formatter Code - Verify agent.py','Test Logging Patch - Find Agent','Diagnostic Logging - Check Setup','Apply Logging Formatter - Direct Injection','Patch Agent Logging Formatter','updateLoggingConfig.py')


select * from tenants
where tenantuuid = 'c2237c2b-7a04-4c06-8fd0-1f7467093fff'