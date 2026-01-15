------------
create view v_schedule_timeout as
select 
	ss.scheduleuuid
from 
	snippetsschedule ss 
join 
	snippets s on ss.snippetuuid = s.snippetuuid
join
	devicestatus ds on ss.deviceuuid = ds.deviceuuid
where 
	(ss.inprogress = True)
and 
	cast(EXTRACT(EPOCH FROM CURRENT_TIMESTAMP) - ss.nextexecution as int) > s.max_exec_secs
and 
	ds.last_update > (EXTRACT(EPOCH FROM CURRENT_TIMESTAMP) - 61)
-------------

-------------
create or replace view v_device_summary as
select
	d.deviceuuid
	,d.devicename
	,t.tenantname || '/' || o.orgname || '/' || g.groupname || '/' || d.devicename as devicePath
	,g.groupuuid
	,o.orguuid
	,t.tenantuuid
	,to_timestamp(ds.last_update) as last_seen
	,case
		when ds.last_update > (EXTRACT(EPOCH FROM CURRENT_TIMESTAMP) - 180) THEN true
		else false 
	end as Online
from 
	devices d
left join
	groups g on d.groupuuid = g.groupuuid
left join
	organisations o on d.orguuid = o.orguuid
left join
	tenants t on d.tenantuuid = t.tenantuuid
left join 
	devicestatus ds on d.deviceuuid = ds.deviceuuid
-------------



-------------
create view v_snippet_schedule as
select 
    d.deviceuuid
    ,d.devicename
    ,ss.snippetuuid
    ,ss.scheduleuuid
    ,s.snippetname
    ,to_timestamp(ss.nextexecution) as nextexecution_ts
    ,to_timestamp(ss.lastexecution) as lastexecution_ts
    ,ss.lastexecstatus
    ,ss.inprogress
    ,ss.enabled


FROM
    snippetsschedule ss  
LEFT JOIN
    snippets s on ss.snippetuuid = s.snippetuuid
LEFT JOIN
    devices d on ss.deviceuuid = d.deviceuuid
-------------
