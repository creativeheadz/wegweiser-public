# Filepath: app/models/__init__.py
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
bcrypt = Bcrypt()

# Import all models here
from .accounts import Accounts
from .messages import Messages
from .profiles import Profiles
from .roles import Roles, AccountsXRoles
from .tags import Tags, TagsXDevices, TagsXAccounts, TagsXOrgs, TagsXGroups, TagsXTenants
from .tenants import Tenants
from .organisations import Organisations
from .groups import Groups
from .devices import DeviceBattery, DeviceDrives, DeviceMemory, DeviceNetworks, Devices, \
	DeviceStatus, DevicePartitions, DeviceUsers, DeviceCpu, DeviceGpu, DeviceBios, DeviceCollector, \
	DevicePrinters, DevicePciDevices, DeviceDrivers, DeviceUsbDevices, DeviceRealtimeData, DeviceRealtimeHistory, \
	DeviceConnectivity
from .device_audit_json_test import DeviceAuditJsonTest
from .user_log import UserLog
from .servercore import ServerCore
from .mfa import MFA
from .devicemetadata import DeviceMetadata
from .ai_memory import AIMemory
from .context import Context
from .conversations import Conversations
from .snippets import Snippets, SnippetsSchedule, SnippetsHistory
from .userxorganisation import UserXOrganisation
from .health_score_update_log import HealthScoreUpdateLog
from .faq import FAQ
from .wegcoin_transaction import WegcoinTransaction
from .health_score_history import HealthScoreHistory
from .rss_feeds import RSSFeed
from .messagestream import MessageStream
from .tenantmetadata import TenantMetadata
from .invite_codes import InviteCodes
from .two_factor import UserTwoFactor
from .device_osquery import DeviceOSQuery
from .orgmetadata import OrganizationMetadata
from .groupmetadata import GroupMetadata
from .guided_tours import GuidedTour, TourProgress
from .email_verification import EmailVerification
from .agent_update import AgentUpdateHistory
from .analysis_config import TenantAnalysisPrompt, AnalysisExclusion, EntityType
