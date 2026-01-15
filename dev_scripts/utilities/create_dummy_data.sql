




select * from tenants;
select * from roles;
select * from accounts;
select * from organisations;
select * from groups;
select * from devices;


insert into tenants (
    tenantuuid, 
    tenantname, 
    created_at)
values(
    gen_random_uuid (), 
    'bigcats', 
    cast(extract(epoch from now()) as int)
    );

insert into accounts (
    useruuid, 
    firstname, 
    lastname, 
    companyname, 
    companyemail, 
    password, 
    tenantuuid, 
    role, 
    created_at)
values(
	gen_random_uuid (),
	'john', 
	'nuttall', 
	'bigcats', 
	'john@bigcats.uk', 
	'myPassword123', 
	(select tenantuuid from tenants where tenantname = 'bigcats'), 
	(select roleuuid from roles where rolename = 'master'), 
	cast(extract(epoch from now()) as int));

insert into organisations (
    orguuid, 
    orgname, 
    tenantuuid, 
    created_at
    )
values(
    gen_random_uuid (), 
    'longmead', 
    (select tenantuuid from tenants where tenantname = 'bigcats'), 
    cast(extract(epoch from now()) as int)
    );

insert into groups (
    groupuuid, 
    groupname, 
    orguuid, 
    tenantuuid, 
    created_at, 

    )
values(
    gen_random_uuid (), 
    'linux_devices', 
    (select orguuid from organisations where orgname = 'longmead'), 
    (select tenantuuid from tenants where tenantname = 'bigcats'), 
    cast(extract(epoch from now()) as int), 
    (select useruuid from accounts where companyemail = 'john@bigcats.uk')
    );

insert into groups (
    groupuuid, 
    groupname, 
    orguuid, 
    tenantuuid, 
    created_at, 
    )
values(
    gen_random_uuid (), 
    'windows_devices', 
    (select orguuid from organisations where orgname = 'longmead'), 
    (select tenantuuid from tenants where tenantname = 'bigcats'), 
    cast(extract(epoch from now()) as int), 
    (select useruuid from accounts where companyemail = 'john@bigcats.uk')
    );	

insert into devices (
    deviceuuid, 
    devicename, 
    hardwareinfo, 
    groupuuid,
    orguuid,
    tenantuuid, 
    created_at
    )
values(
    gen_random_uuid (), 
    'dev_name', 
    'hardware',
    (select groupuuid from groups where groupname = 'linux_devices'), 
    (select orguuid from organisations where orgname = 'longmead'), 
    (select tenantuuid from tenants where tenantname = 'bigcats'), 
    cast(extract(epoch from now()) as int)
    );	    