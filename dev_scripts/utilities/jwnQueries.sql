select * from snippets;
select * from devices;

delete from snippets
where snippets.snippetname = 'updateAgent.py';

select * from snippetsschedule;

delete from snippetsschedule
where snippetuuid = '38e26a31-6bc4-4de0-9f0a-fc49b7872bc9'

select to_timestamp(created_at), * from devices
where devicename ilike '%desktop%';

----- DELETE DEIVCES ----
delete from messages
where messages.entityuuid in  (
	select devices.deviceuuid from devices
	where devicename = 'DESKTOP-7EID0IS'
);

delete from messages
where messages.entityuuid in  (
	select devices.deviceuuid from devices
	where devicename ilike '%HERMES%'
);

delete from devices
where devicename ilike '%hermes%';

delete from devices
where devicename ilike '%DESKTOP-7EID0IS%';

select * from devices
where devicename = 'DESKTOP-7EID0IS';

select * from devices
where devicename ilike '%hermes%';
-------

----- DELETE HERMES ----
delete from messages
where messages.entityuuid in  (
	select devices.deviceuuid from devices
	where devicename ilike '%HERMES%'
);

delete from devices
where devicename ilike '%HERMES%';

select * from devices
where devicename ilike '%HERMES%'
-------


select * from devices;
select * from messages;

delete from snippetsschedule
where scheduleuuid = '0578e229-8d81-403e-bdc1-aad78c506710'

select 
	d.devicename, 
	s.snippetname,
	to_timestamp(lastexecution) as lastExec,
	to_timestamp(nextexecution) as nextExec, 
	ss.scheduleuuid,  
	*
from 
	snippetsschedule ss  
JOIN
	devices d on ss.deviceuuid = d.deviceuuid
JOIN
	snippets s on ss.snippetuuid = s.snippetuuid
ORDER BY
	devicename, snippetname asc


-------------------
INSERT INTO snippetsschedule (
	scheduleuuid,
	snippetuuid,
	deviceuuid,
	recurrence,
	interval,
	nextexecution
)
select 
	uuid_generate_v4(),
	'38e26a31-6bc4-4de0-9f0a-fc49b7872bc9',
	deviceuuid,
	60,
	2,
	1727700681
from
	devices
where
devicename in ('DESKTOP-7EID0IS','hermes.longmead.local');

------------
update snippetsschedule
set interval = 3
where scheduleuuid = 'ccce3a2c-baa3-4d1b-a959-e0f7611e324e'

----------------
select * from devices
order by devicename asc;
----------------

----------------
select d.devicename, * from devicegpu x 
join devices d on x.deviceuuid = d.deviceuuid
order by d.devicename asc
----------------


delete from analysis_cycles
where deviceuuid in (
	select deviceuuid from devices
	where devicename in ('thyme.longmead.local', 'ginger.longmead.local', 'basil.longmead.local')
    and agent_public_key is not null
);
delete from messages
where entityuuid in (
	select deviceuuid from devices
	where devicename in ('thyme.longmead.local', 'ginger.longmead.local', 'basil.longmead.local')
    and agent_public_key is not null
);
delete from devices
where devicename in ('thyme.longmead.local', 'ginger.longmead.local', 'basil.longmead.local')
    and agent_public_key is not null




select s.snippetname, d.devicename, * from snippetsschedule ss  
join snippets s on ss.snippetuuid = s.snippetuuid
join devices d on ss.deviceuuid = d.deviceuuid
order by devicename, snippetname asc

--delete from snippets
--where snippets.snippetname = 'fullAudit.py'

select * from devices;
select * from snippets;
select * from snippetsschedule;
select * from snippetshistory
order by exectime DESC
limit 100;

--delete from snippetsschedule 
--where scheduleuuid = 'bafe171b-f538-4880-b057-f22de0683268'

select * from servercore

update servercore
SET
agent_version = '202410011000',
agent_hash_py = 'a6c01363f220a70a43931dfd0f5f4d15d54446ee408d78b6e5946a941670023f',
agent_hash_win = '7f7c707e21121d4eccc95d86fcb99e6b36d5641344c76db0a9100a0151069098'

select * from 
select * from snippets




SELECT EXTRACT(EPOCH FROM CURRENT_TIMESTAMP);




select * from snippets
delete from snippets
where snippets.snippetname = 'fullAudit.py'

select * from servercore

select * from devices
where devicename ilike '%desktop%'

select s.snippetname, d.devicename, * from snippetsschedule ss 
join devices d on ss.deviceuuid = d.deviceuuid
join snippets s on ss.snippetuuid = s.snippetuuid



update snippetsschedule
set 
    interval = 1, 
    recurrence = 86400,
    nextexecution = 1727913600
where snippetuuid = 'd99ead32-4247-4d0d-88af-7d81a225a663'