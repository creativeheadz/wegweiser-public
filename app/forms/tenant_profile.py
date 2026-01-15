# Filepath: app/forms/tenant_profile.py
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, FileField, SubmitField, SelectMultipleField, IntegerField
from wtforms.validators import DataRequired, Email, Length, NumberRange
from flask_wtf.file import FileAllowed
from wtforms.widgets import ListWidget, CheckboxInput

# Filepath: app/forms/tenant_profile_form.py

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, FileField, SubmitField, SelectMultipleField
from wtforms.validators import DataRequired, Email
from flask_wtf.file import FileAllowed

class TenantProfileForm(FlaskForm):
    tenantname = StringField('Tenant Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone')
    address = TextAreaField('Address')
    logo = FileField('Logo', validators=[FileAllowed(['jpg', 'png'], 'Images only!')])
    
    company_size = SelectField('Company Size', choices=[
        ('1-10', '1-10 employees'),
        ('11-50', '11-50 employees'),
        ('51-200', '51-200 employees'),
        ('201+', '201+ employees')
    ])
    primary_focus = StringField('Primary Focus')

    # Restored original rmm_type as SelectField. Note: Consider if this is redundant with software_bundles.
    rmm_type = SelectField('Primary RMM Type (Legacy)', choices=[
        ('none', 'None'),
        ('atera', 'Atera'),
        ('barracuda_msp', 'Barracuda MSP'),
        ('comodo_one', 'Comodo One MSP'),
        ('connectwise', 'ConnectWise Suite'),
        ('datto', 'Datto Suite'),
        ('kaseya', 'Kaseya Suite'),
        ('manageengine', 'ManageEngine MSP'),
        ('n_able', 'N-able (formerly SolarWinds MSP)'),
        ('ninja_rmm', 'NinjaRMM'),
        ('pulseway', 'Pulseway MSP'),
        ('syncro', 'Syncro')
    ])

    service_areas = SelectMultipleField('Service Areas', choices=[
        ('networking', 'Networking'),
        ('security', 'Security'),
        ('cloud', 'Cloud Services'),
        ('managed_services', 'Managed Services'),
        ('voip', 'VoIP'),
        ('hardware', 'Hardware Support')
    ])
    specializations = SelectMultipleField('Specializations', choices=[
        ('smb', 'Small and Medium Business'),
        ('enterprise', 'Enterprise'),
        ('healthcare', 'Healthcare'),
        ('finance', 'Finance'),
        ('education', 'Education'),
        ('government', 'Government')
    ])
    customer_industries = SelectMultipleField('Customer Industries', choices=[
        ('technology', 'Technology'),
        ('healthcare', 'Healthcare'),
        ('finance', 'Finance'),
        ('education', 'Education'),
        ('manufacturing', 'Manufacturing'),
        ('retail', 'Retail')
    ])
    monitoring_preferences = SelectMultipleField('Monitoring Preferences', choices=[
        ('24x7', '24/7 Monitoring'),
        ('business_hours', 'Business Hours Monitoring'),
        ('proactive', 'Proactive Monitoring'),
        ('reactive', 'Reactive Monitoring')
    ])

    # --- Stack Categories (SelectMultipleField) ---

    # Software Bundles and Suites, RMM & PSA
    software_bundles = SelectMultipleField('Software Bundles and Suites, RMM & PSA', choices=[
        ('atera', 'Atera'),
        ('barracuda_msp', 'Barracuda MSP'),
        ('comodo_one', 'Comodo One MSP'),
        ('connectwise', 'ConnectWise Suite'),
        ('datto', 'Datto Suite'),
        ('kaseya', 'Kaseya Suite'),
        ('manageengine', 'ManageEngine MSP'),
        ('n_able', 'N-able (formerly SolarWinds MSP)'),
        ('ninja_rmm', 'NinjaRMM'),
        ('pulseway', 'Pulseway MSP'),
        ('syncro', 'Syncro')
    ])

    # Remote Support, RMM & Device Monitoring
    remote_support = SelectMultipleField('Remote Support, RMM & Device Monitoring', choices=[
        ('anydesk', 'AnyDesk'),
        ('beyondtrust', 'BeyondTrust Remote Support'),
        ('screenconnect', 'ConnectWise ScreenConnect'),
        ('level', 'Level'),
        ('logmein_rescue', 'LogMeIn Rescue'),
        ('remote_utilities', 'Remote Utilities'),
        ('splashtop', 'Splashtop'),
        ('teamviewer', 'TeamViewer')
    ])

    # PSA, Service Desk & CX
    psa_service_desk = SelectMultipleField('PSA, Service Desk & CX', choices=[
        ('autotask', 'Autotask PSA'),
        ('connectwise_psa', 'ConnectWise PSA'),
        ('deskdirector', 'DeskDirector'),
        ('freshdesk', 'Freshdesk'),
        ('halopsa', 'HaloPSA'),
        ('invarosoft', 'Invarosoft'),
        ('kaseya_bms', 'Kaseya BMS'),
        ('manageengine_service_desk', 'ManageEngine ServiceDesk Plus'),
        ('thread', 'Thread'),
        ('tigerpaw', 'Tigerpaw'),
        ('zendesk', 'Zendesk'),
        ('zestmsp', 'ZestMSP')
    ])

    # BDR
    bdr = SelectMultipleField('BDR', choices=[
        ('acronis', 'Acronis'),
        ('altaro_vm_backup', 'Altaro VM Backup'),
        ('barracuda_backup', 'Barracuda Backup'),
        ('carbonite', 'Carbonite Server Backup'),
        ('commvault', 'Commvault Complete Backup & Recovery'),
        ('datto_siris', 'Datto SIRIS'),
        ('infrascale', 'Infrascale Disaster Recovery'),
        ('nakivo', 'Nakivo Backup & Replication'),
        ('rubrik', 'Rubrik Cloud Data Management'),
        ('storagecraft', 'StorageCraft'),
        ('unitrends', 'Unitrends Backup & Recovery'),
        ('veeam', 'Veeam')
    ])

    # DNS Filtering and Web Security
    dns_filtering = SelectMultipleField('DNS Filtering and Web Security', choices=[
        ('censornet', 'Censornet Web Security'),
        ('cisco_umbrella', 'Cisco Umbrella'),
        ('dnsfilter', 'DNSFilter'),
        ('forcepoint', 'Forcepoint Web Security'),
        ('mcafee_web_gateway', 'McAfee Web Gateway'),
        ('safedns', 'SafeDNS'),
        ('titanhq_webtitan', 'TitanHQ WebTitan'),
        ('watchguard_dnswatch', 'WatchGuard DNSWatch')
    ])

    # Email Security
    email_security = SelectMultipleField('Email Security', choices=[
        ('avanan', 'Avanan'),
        ('barracuda_email', 'Barracuda Email Protection'),
        ('cisco_email', 'Cisco Email Security'),
        ('fortinet', 'Fortinet FortiMail'),
        ('mesh', 'Mesh'),
        ('mimecast', 'Mimecast'),
        ('n_able_mail_assure', 'N-able Mail Assure'),
        ('proofpoint', 'Proofpoint'),
        ('sophos_email', 'Sophos Email Security'),
        ('spamtitan', 'SpamTitan'),
        ('trellix_email', 'Trellix Email Security'),
        ('trend_micro_email', 'Trend Micro Email Security'),
        ('zix', 'Zix Email Threat Protection')
    ])

    # Endpoint Protection and EDR
    endpoint_protection = SelectMultipleField('Endpoint Protection and EDR', choices=[
        ('bitdefender_edr', 'Bitdefender EDR'),
        ('comodo', 'Comodo'),
        ('crowdstrike', 'CrowdStrike Falcon'),
        ('deep_instinct', 'Deep Instinct'),
        ('mcafee', 'McAfee Endpoint Security'),
        ('sentinelone', 'SentinelOne'),
        ('sophos', 'Sophos Intercept X'),
        ('trend_micro_apex', 'Trend Micro Apex One'),
        ('vmware_carbon_black', 'VMware Carbon Black'),
        ('webroot', 'Webroot')
    ])

    # Security Suites, Platforms and MDRs
    security_suites = SelectMultipleField('Security Suites, Platforms and MDRs', choices=[
        ('arctic_wolf', 'Arctic Wolf Managed Risk'),
        ('bitdefender', 'Bitdefender'),
        ('blackpoint_cyber', 'Blackpoint Cyber'),
        ('check_point_harmony', 'Check Point Harmony'),
        ('crowdstrike_falcon_complete', 'CrowdStrike Falcon Complete'),
        ('cynet', 'Cynet'),
        ('guardz', 'Guardz'),
        ('huntress', 'Huntress'),
        ('sentinelone_singularity', 'SentinelOne Singularity'),
        ('sophos', 'Sophos'),
        ('trend_micro', 'Trend Micro Worry-Free')
    ])

    # IT Documentation
    it_documentation = SelectMultipleField('IT Documentation', choices=[
        ('hudu', 'Hudu'),
        ('it_glue', 'IT Glue'),
        ('passportal', 'Passportal')
    ])

    # Network Monitoring
    network_monitoring = SelectMultipleField('Network Monitoring', choices=[
        ('auvik', 'Auvik'),
        ('prtg', 'PRTG Network Monitor'),
        ('zabbix', 'Zabbix')
    ])

    # Communication and Collaboration
    communication_collaboration = SelectMultipleField('Communication and Collaboration', choices=[
        ('microsoft_teams', 'Microsoft Teams'),
        ('slack', 'Slack'),
        ('zoom', 'Zoom')
    ])

    # Training and Certification
    training_certification = SelectMultipleField('Training and Certification', choices=[
        ('cisco_academy', 'Cisco Networking Academy'),
        ('comptia', 'CompTIA'),
        ('microsoft_learn', 'Microsoft Learn'),
        ('msp_alliance', 'MSP Alliance') # Note: Also listed under Business Resources
    ])

    # Asset Management
    asset_management = SelectMultipleField('Asset Management', choices=[
        ('asset_panda', 'Asset Panda'),
        ('lansweeper', 'Lansweeper'),
        ('snipe_it', 'Snipe-IT')
    ])

    # Password Management
    password_management = SelectMultipleField('Password Management', choices=[
        ('1password', '1Password'),
        ('bitwarden', 'Bitwarden'),
        ('enpass', 'Enpass'),
        ('keeper', 'Keeper'),
        ('lastpass', 'LastPass'),
        ('n_able_passportal', 'N-able Passportal'),
        ('nordpass', 'NordPass'),
        ('roboform', 'RoboForm'),
        ('sticky_password', 'Sticky Password'),
        ('true_key', 'True Key'),
        ('zoho_vault', 'Zoho Vault')
    ])

    # VoIP and Telephony
    voip_telephony = SelectMultipleField('VoIP and Telephony', choices=[
        ('3cx', '3CX'),
        ('8x8', '8x8'),
        ('dialpad', 'Dialpad'),
        ('grasshopper', 'Grasshopper'),
        ('intermedia', 'Intermedia'),
        ('jive_communications', 'Jive Communications'),
        ('mitel', 'Mitel'),
        ('nextiva', 'Nextiva'),
        ('oit', 'OIT'),
        ('ooma', 'Ooma'),
        ('ringcentral', 'RingCentral'),
        ('vonage', 'Vonage')
    ])

    # Patch Management
    patch_management = SelectMultipleField('Patch Management', choices=[
        ('automox', 'Automox'),
        ('batchpatch', 'BatchPatch'),
        ('gfi_languard', 'GFI LanGuard'),
        ('ivanti_patch', 'Ivanti Patch for SCCM'),
        ('manageengine_patch_manager', 'ManageEngine Patch Manager Plus'),
        ('n_able_patch', 'N-able N-central'), # Note: N-able N-central is a broader RMM
        ('pdq_deploy', 'PDQ Deploy'),
        ('scappman', 'Scappman'),
        ('solarwinds_patch_manager', 'SolarWinds Patch Manager'),
        ('syxsense_manage', 'Syxsense Manage')
    ])

    # Identity and Access Management (IAM)
    iam = SelectMultipleField('Identity and Access Management (IAM)', choices=[
        ('cyberark', 'CyberArk Identity'),
        ('duo', 'Duo'),
        ('forgerock', 'ForgeRock'),
        ('ibm_security', 'IBM Security Identity and Access Management'),
        ('jumpcloud', 'JumpCloud'),
        ('microsoft_azure_ad', 'Microsoft Azure Active Directory'),
        ('okta', 'Okta'),
        ('onelogin', 'OneLogin'),
        ('oracle_identity', 'Oracle Identity Management'),
        ('ping_identity', 'Ping Identity'),
        ('rsa_securid', 'RSA SecurID Suite')
    ])

    # Managed Print Services
    managed_print_services = SelectMultipleField('Managed Print Services', choices=[
        ('eci_fmaudit', 'ECiFMAudit'),
        ('papercut', 'PaperCut'),
        ('printerlogic', 'PrinterLogic'),
        ('printix', 'Printix')
    ])

    # Virtual Desktop Infrastructure (VDI)
    vdi = SelectMultipleField('Virtual Desktop Infrastructure (VDI)', choices=[
        ('citrix_virtual_apps', 'Citrix Virtual Apps and Desktops'),
        ('microsoft_windows_virtual_desktop', 'Microsoft Windows Virtual Desktop'),
        ('vmware_horizon', 'VMware Horizon')
    ])

    # Business Resources
    business_resources = SelectMultipleField('Business Resources', choices=[
        ('msp_alliance', 'MSPAlliance'), # Note: Also listed under Training
        ('mspcfo', 'MSPCFO'),
        ('mspgh', 'MSPGH'),
        ('mspmentor', 'MSPmentor'),
        ('msp_insights', 'MSP Insights')
    ])

    # --- Newly Added Stack Categories ---

    # Cloud Management
    cloud_management = SelectMultipleField('Cloud Management', choices=[
        ('cloudcheckr', 'CloudCheckr'),
        ('cloudhealth', 'CloudHealth'),
        ('nerdio', 'Nerdio')
    ])

    # Mobile Device Management (MDM)
    mdm = SelectMultipleField('Mobile Device Management (MDM)', choices=[
        ('jamf_pro', 'Jamf Pro'),
        ('kandji', 'Kandji'),
        ('microsoft_intune', 'Microsoft Intune'),
        ('mobileiron', 'MobileIron'),
        ('vmware_workspace_one', 'VMware Workspace ONE')
    ])

    # Communities & Forums
    communities_forums = SelectMultipleField('Communities & Forums', choices=[
        ('everything_msp_fb', 'Everything MSP Facebook Group'),
        ('it_msp_owners_fb', 'IT & MSP Business Owners Facebook Group'),
        ('it_nation', 'IT Nation'),
        ('msp_subreddit', 'MSP subreddit (r/msp)'),
        ('mspgeek', 'MSPGeek'),
        ('tech_tribe', 'The Tech Tribe')
    ])

    # --- Other Fields ---
    
    sla_response_time = IntegerField('SLA Response Time (in minutes)')
    sla_uptime_guarantee = StringField('SLA Uptime Guarantee (in %)')
    
    preferred_communication_style = SelectField('Preferred Communication Style', choices=[
        ('formal', 'Formal'),
        ('casual', 'Casual')
    ])
    submit = SubmitField('Update Profile')
