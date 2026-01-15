# Filepath: app/models/devices.py
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.schema import DDL
from sqlalchemy.orm import relationship
from sqlalchemy import event, PrimaryKeyConstraint
from . import db
from typing import Dict, Any, List
import uuid
import time
import logging
from .groups import Groups
from datetime import datetime

class Devices(db.Model):
    __tablename__ = 'devices'
    deviceuuid = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    devicename = db.Column(db.String(255), nullable=False)
    hardwareinfo = db.Column(db.Text, nullable=True)
    groupuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('groups.groupuuid', ondelete="CASCADE"), nullable=False)
    orguuid = db.Column(UUID(as_uuid=True), db.ForeignKey('organisations.orguuid', ondelete="CASCADE"), nullable=False)
    tenantuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('tenants.tenantuuid', ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()))
    health_score = db.Column(db.Float, nullable=True)
    agent_public_key = db.Column(db.Text, nullable=True)

    # Fields for analysis cycle management
    force_analysis = db.Column(db.Boolean, default=False)



    # Columns to indicate if a device was manually created
    is_manual_profile = db.Column(db.Boolean, default=False)
    manual_profile_created_at = db.Column(db.BigInteger, nullable=True)

    # Relationships
    messages = relationship("Messages",
        primaryjoin="and_(Devices.deviceuuid == foreign(Messages.entityuuid), Messages.entity_type == 'device')",
        backref="messages_from_device")  # Changed backref to avoid conflicts

    conversations = relationship('Conversations', back_populates='device', cascade="all, delete-orphan")
    organisation = relationship('Organisations', backref='devices', lazy=True)
    tenant = relationship('Tenants', back_populates='devices')
    is_online = db.Column(db.Boolean, nullable=True, default=False)
    last_online_change = db.Column(db.BigInteger, nullable=True)
    last_seen_online = db.Column(db.BigInteger, nullable=True)
    last_heartbeat = db.Column(db.BigInteger, nullable=True)

    # Additional helper methods
    def get_online_status(self):
        if not self.is_online:
            return "Offline"

        # Check if heartbeat is recent (within 2 minutes)
        if self.last_heartbeat and (time.time() - self.last_heartbeat) < 120:
            return "Online"
        else:
            return "Stale"

    def get_last_seen_formatted(self):
        if not self.last_seen_online:
            return "Never"

        # Format timestamp for display
        from datetime import datetime
        return datetime.fromtimestamp(self.last_seen_online).strftime('%Y-%m-%d %H:%M:%S')



    def _gather_critical_issues(self) -> List[Dict[str, Any]]:
        """Gather critical issues based on device status and metadata"""
        critical_issues = []

        # Example criteria for critical issues
        if self.health_score and self.health_score < 70:
            critical_issues.append({
                'area': 'Health Score',
                'score': self.health_score,
                'summary': 'Health score is below the critical threshold.'
            })

        # Add more criteria as needed
        # ...

        return critical_issues



    def _determine_role(self) -> str:
        """Determine device's role based on its characteristics"""
        status = DeviceStatus.query.filter_by(deviceuuid=self.deviceuuid).first()
        if not status:
            return "Unknown role"

        if 'server' in status.system_name.lower():
            return "Server"
        elif status.system_manufacturer and 'laptop' in status.system_model.lower():
            return "Laptop"
        elif status.system_manufacturer:
            return "Workstation"
        return "General purpose device"

    


    def get_last_conversation(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent conversation history"""
        try:
            # Import here to avoid circular imports
            from .messages import Messages

            # Use sequence_id for guaranteed chronological order
            all_messages = Messages.query.filter_by(
                entityuuid=self.deviceuuid,
                entity_type='device'
            ).order_by(Messages.sequence_id.asc()).all()

            # Take the most recent messages
            messages = all_messages[-limit:] if len(all_messages) > limit else all_messages

            return [{
                'content': msg.content,
                'is_ai': msg.useruuid is None,
                'timestamp': msg.created_at
            } for msg in messages]  # Already in chronological order

        except Exception as e:
            logging.error(f"Error getting conversation history: {str(e)}")
            return []



    def get_uuid(self):
        return self.deviceuuid

    def get_messages(self):
        # Import here to avoid circular imports
        from .messages import Messages
        return Messages.query.filter_by(entityuuid=self.deviceuuid, entity_type='device').all()

    def to_dict(self):
        """Convert device object to dictionary with safe value handling."""
        try:
            return {
                'deviceuuid': str(self.deviceuuid),
                'devicename': self.devicename,
                'hardwareinfo': self.hardwareinfo,
                'groupuuid': str(self.groupuuid) if self.groupuuid else None,
                'orguuid': str(self.orguuid) if self.orguuid else None,
                'tenantuuid': str(self.tenantuuid) if self.tenantuuid else None,
                'created_at': self.created_at,
                'health_score': self.health_score,
                'group': {
                    'groupuuid': str(self.group.groupuuid),
                    'groupname': self.group.groupname
                } if self.group else None,
                'organisation': {
                    'orguuid': str(self.organisation.orguuid),
                    'orgname': self.organisation.orgname
                } if self.organisation else None
            }
        except Exception as e:
            logging.error(f"Error in to_dict() for device {self.deviceuuid}: {e}")
            return {
                'deviceuuid': str(self.deviceuuid),
                'devicename': self.devicename,
                'error': 'Failed to convert all device data'
            }





# Add custom deletion logic to prevent group deletion if it contains devices
def before_group_delete(mapper, connection, target):
    # mapper and connection are required by SQLAlchemy event signature but not used
    session = db.session.object_session(target)
    if session.query(Devices).filter(Devices.groupuuid == target.groupuuid).count() > 0:
        raise Exception("Cannot delete group because it contains devices")

event.listen(Groups, 'before_delete', before_group_delete)








class DeviceBattery(db.Model):
    __tablename__ = 'devicebattery'
    deviceuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('devices.deviceuuid', ondelete="CASCADE"), primary_key=True, default=uuid.uuid4)
    last_update = db.Column(db.Integer, nullable=False)
    last_json = db.Column(db.Integer, nullable=False)
    battery_installed = db.Column(db.Boolean, nullable=False)
    percent_charged = db.Column(db.Integer, nullable=False)
    secs_remaining = db.Column(db.Integer, nullable=False)
    on_mains_power = db.Column(db.Boolean, nullable=False)

#   device = relationship('Devices', back_populates='battery')

    @property
    def info(self):
        return {
            'last_update': self.last_update,
            'last_json': self.last_json,
            'battery_installed': self.battery_installed,
            'percent_charged': self.percent_charged,
            'secs_remaining': self.secs_remaining,
            'on_mains_power': self.on_mains_power
        }

class DeviceDrives(db.Model):
    __tablename__ = 'devicedrives'
    deviceuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('devices.deviceuuid', ondelete="CASCADE"), primary_key=True)
    last_update = db.Column(db.Integer, nullable=False)
    last_json = db.Column(db.Integer, nullable=False)
    drive_name = db.Column(db.String(255), nullable=False, primary_key=True)
    drive_total = db.Column(db.BigInteger, nullable=False)
    drive_used = db.Column(db.BigInteger, nullable=False)
    drive_free = db.Column(db.BigInteger, nullable=False)
    drive_used_percentage = db.Column(db.Float, nullable=False)
    drive_free_percentage = db.Column(db.Float, nullable=False)

#    device = relationship('Devices', back_populates='drives')

    __table_args__ = (
        PrimaryKeyConstraint('deviceuuid', 'drive_name', name='deviceuuid_drive_name_pk'),
    )

    @property
    def info(self):
        return {
            'last_update': self.last_update,
            'last_json': self.last_json,
            'drive_name': self.drive_name,
            'drive_total': self.drive_total,
            'drive_used': self.drive_used,
            'drive_free': self.drive_free,
            'drive_used_percentage': self.drive_used_percentage,
            'drive_free_percentage': self.drive_free_percentage
        }

class DeviceMemory(db.Model):
    __tablename__ = 'devicememory'
    deviceuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('devices.deviceuuid', ondelete="CASCADE"), primary_key=True)
    last_update = db.Column(db.Integer, nullable=False)
    last_json = db.Column(db.Integer, nullable=False)
    total_memory = db.Column(db.BigInteger, nullable=False)
    available_memory = db.Column(db.BigInteger, nullable=False)
    used_memory = db.Column(db.BigInteger, nullable=False)
    free_memory = db.Column(db.BigInteger, nullable=False)
    cache_memory = db.Column(db.BigInteger, nullable=False)
    mem_used_percent = db.Column(db.Float, nullable=False)
    mem_free_percent = db.Column(db.Float, nullable=False)
    memory_metrics_json = db.Column(JSONB, nullable=True)

#    device = relationship('Devices', back_populates='memory')

    @property
    def info(self):
        return {
            'last_update': self.last_update,
            'last_json': self.last_json,
            'total_memory': self.total_memory,
            'available_memory': self.available_memory,
            'used_memory': self.used_memory,
            'free_memory': self.free_memory,
            'cache_memory': self.cache_memory,
            'mem_used_percent': self.mem_used_percent,
            'mem_free_percent': self.mem_free_percent,
            'memory_metrics_json': self.memory_metrics_json
        }

class DeviceNetworks(db.Model):
    __tablename__ = 'devicenetworks'
    deviceuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('devices.deviceuuid', ondelete="CASCADE"), primary_key=True)
    last_update = db.Column(db.Integer, nullable=False)
    last_json = db.Column(db.Integer, nullable=False)
    network_name  = db.Column(db.String(255), primary_key=True)
    if_is_up = db.Column(db.Boolean, nullable=False)
    if_speed = db.Column(db.BigInteger, nullable=False)
    if_mtu = db.Column(db.Integer, nullable=False)
    bytes_sent = db.Column(db.BigInteger, nullable=False)
    bytes_rec = db.Column(db.BigInteger, nullable=False)
    err_in = db.Column(db.BigInteger, nullable=False)
    err_out = db.Column(db.BigInteger, nullable=False)
    address_4 = db.Column(db.String(255), nullable=False)
    netmask_4 = db.Column(db.String(255), nullable=False)
    broadcast_4 = db.Column(db.String(255), nullable=False)
    address_6 = db.Column(db.String(255), nullable=False)
    netmask_6 = db.Column(db.String(255), nullable=False)
    broadcast_6 = db.Column(db.String(255), nullable=False)

#    device = relationship('Devices', back_populates='networks')

    __table_args__ = (
        PrimaryKeyConstraint('deviceuuid', 'network_name', name='deviceuuid_network_name_pk'),
    )

    @property
    def info(self):
        return {
            'last_update': self.last_update,
            'last_json': self.last_json,
            'network_name': self.network_name,
            'if_is_up': self.if_is_up,
            'if_speed': self.if_speed,
            'if_mtu': self.if_mtu,
            'bytes_sent': self.bytes_sent,
            'bytes_rec': self.bytes_rec,
            'err_in': self.err_in,
            'err_out': self.err_out,
            'address_4': self.address_4,
            'netmask_4': self.netmask_4,
            'broadcast_4': self.broadcast_4,
            'address_6': self.address_6,
            'netmask_6': self.netmask_6,
            'broadcast_6': self.broadcast_6
        }

class DeviceStatus(db.Model):
    __tablename__ = 'devicestatus'
    deviceuuid 			= db.Column(UUID(as_uuid=True), db.ForeignKey('devices.deviceuuid', ondelete="CASCADE"), primary_key=True, default=uuid.uuid4)
    last_update 		= db.Column(db.Integer, 	nullable=False)
    last_json 			= db.Column(db.Integer, 	nullable=False)
    agent_platform 		= db.Column(db.String(255), nullable=False)
    system_name 		= db.Column(db.String(255), nullable=False)
    logged_on_user 		= db.Column(db.String(255), nullable=False)
    cpu_usage 			= db.Column(db.Integer, 	nullable=False, default=lambda: int(time.time()))
    cpu_count 			= db.Column(db.Integer, 	nullable=False)
    boot_time 			= db.Column(db.Integer, 	nullable=False)
    publicIp 			= db.Column(db.String(255), nullable=True)
    country 			= db.Column(db.String(255), nullable=True)
    system_model 		= db.Column(db.String(255), nullable=True)
    system_manufacturer = db.Column(db.String(255), nullable=True)
    system_locale 		= db.Column(db.String(255), nullable=True)

    @property
    def info(self):
        return {
            'last_update': self.last_update,
            'last_json': self.last_json,
            'agent_platform': self.agent_platform,
            'system_name': self.system_name,
            'logged_on_user': self.logged_on_user,
            'cpu_usage': self.cpu_usage,
            'cpu_count': self.cpu_count,
            'boot_time': self.boot_time,
            'publicIp': self.publicIp,
            'country': self.country
        }

class DeviceUsers(db.Model):
    __tablename__ = 'deviceusers'
    deviceuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('devices.deviceuuid', ondelete="CASCADE"), primary_key=True, default=uuid.uuid4)
    last_update = db.Column(db.Integer, nullable=False)
    last_json = db.Column(db.Integer, nullable=False)
    users_name = db.Column(db.String(255), nullable=False, primary_key=True)
    terminal = db.Column(db.String(255), nullable=False)
    host = db.Column(db.String(255), nullable=False)
    loggedin = db.Column(db.Integer, nullable=False)
    pid = db.Column(db.Integer, nullable=False)

#    device = relationship('Devices', back_populates='users')

    __table_args__ = (
        PrimaryKeyConstraint('deviceuuid', 'users_name', name='deviceuuid_users_name_pk'),
    )

class DevicePartitions(db.Model):
    __tablename__ = 'devicepartitions'
    deviceuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('devices.deviceuuid', ondelete="CASCADE"), primary_key=True, default=uuid.uuid4)
    last_update = db.Column(db.Integer, nullable=False)
    last_json = db.Column(db.Integer, nullable=False)
    partition_name = db.Column(db.String(255), nullable=False, primary_key=True)
    partition_device = db.Column(db.String(255), nullable=False)
    partition_fs_type = db.Column(db.String(255), nullable=False)

#    device = relationship('Devices', back_populates='partitions')

    __table_args__ = (
        PrimaryKeyConstraint('deviceuuid', 'partition_name', name='deviceuuid_partition_name_pk'),
    )

class DeviceCpu(db.Model):
    __tablename__ = 'devicecpu'
    deviceuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('devices.deviceuuid', ondelete="CASCADE"), primary_key=True, default=uuid.uuid4)
    last_update = db.Column(db.Integer, nullable=False)
    last_json = db.Column(db.Integer, nullable=False)
    cpu_name = db.Column(db.String(255), nullable=False)
    cpu_metrics_json = db.Column(JSONB, nullable=True)

#    device = relationship('Devices', back_populates='cpu')

class DeviceGpu(db.Model):
    __tablename__ = 'devicegpu'
    deviceuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('devices.deviceuuid', ondelete="CASCADE"), primary_key=True, default=uuid.uuid4)
    last_update = db.Column(db.Integer, nullable=False)
    last_json = db.Column(db.Integer, nullable=False)
    gpu_vendor = db.Column(db.String(255), nullable=False)
    gpu_product = db.Column(db.String(255), nullable=False)
    gpu_colour = db.Column(db.Integer, nullable=True)
    gpu_hres = db.Column(db.Integer, nullable=True)
    gpu_vres = db.Column(db.Integer, nullable=True)

#    device = relationship('Devices', back_populates='gpu')

class DeviceBios(db.Model):
    __tablename__ = 'devicebios'
    deviceuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('devices.deviceuuid', ondelete="CASCADE"), primary_key=True, default=uuid.uuid4)
    last_update = db.Column(db.Integer, nullable=False)
    last_json = db.Column(db.Integer, nullable=False)
    bios_vendor = db.Column(db.String(255), nullable=False)
    bios_name = db.Column(db.String(255), nullable=False)
    bios_serial = db.Column(db.String(255), nullable=False)
    bios_version = db.Column(db.String(255), nullable=False)

#    device = relationship('Devices', back_populates='bios')

class DeviceCollector(db.Model):
    __tablename__ = 'devicecollector'
    deviceuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('devices.deviceuuid', ondelete="CASCADE"), primary_key=True, default=uuid.uuid4)
    last_update = db.Column(db.Integer, nullable=False)
    last_json = db.Column(db.Integer, nullable=False)
    coll_version = db.Column(db.String(50), nullable=False)  # Changed from BigInteger to String(50) - see migration 62836f622435
    coll_install_dir = db.Column(db.String(255), nullable=False)

#    device = relationship('Devices', back_populates='collector')


## Added by John 24-jul-2024 16:46

class DevicePrinters(db.Model):
    __tablename__ = 'deviceprinters'
    deviceuuid 			= db.Column(UUID(as_uuid=True), db.ForeignKey('devices.deviceuuid', ondelete="CASCADE"), primary_key=True, default=uuid.uuid4)
    last_update 		= db.Column(db.Integer, 	nullable=False)
    last_json 			= db.Column(db.Integer, 	nullable=False)
    printer_name 		= db.Column(db.String(255), nullable=False, primary_key=True)
    printer_driver 		= db.Column(db.String(255), nullable=True)
    printer_port 		= db.Column(db.String(255), nullable=True)
    printer_location 	= db.Column(db.String(255), nullable=True)
    printer_status 		= db.Column(db.String(255), nullable=True)
    printer_default		= db.Column(db.Boolean, 	nullable=True)

#    device = relationship('Devices', back_populates='printers')

    __table_args__ = (
        PrimaryKeyConstraint('deviceuuid', 'printer_name', name='deviceuuid_printer_name_pk'),
    )

class DevicePciDevices(db.Model):
    __tablename__ = 'devicepcidevices'
    deviceuuid 			= db.Column(UUID(as_uuid=True), db.ForeignKey('devices.deviceuuid', ondelete="CASCADE"), primary_key=True, default=uuid.uuid4)
    last_update 		= db.Column(db.Integer, nullable=False)
    last_json 			= db.Column(db.Integer, nullable=False)
    pci_name 			= db.Column(db.String(255), nullable=False, primary_key=True)
    pci_class 			= db.Column(db.String(255), nullable=True)

#    device = relationship('Devices', back_populates='pcidevices')

    __table_args__ = (
        PrimaryKeyConstraint('deviceuuid', 'pci_name', name='deviceuuid_pci_name_pk'),
    )

class DeviceUsbDevices(db.Model):
    __tablename__ = 'deviceusbdevices'
    deviceuuid 			= db.Column(UUID(as_uuid=True), db.ForeignKey('devices.deviceuuid', ondelete="CASCADE"), primary_key=True, default=uuid.uuid4)
    last_update 		= db.Column(db.Integer, nullable=False)
    last_json 			= db.Column(db.Integer, nullable=False)
    usb_name 			= db.Column(db.String(255), nullable=False, primary_key=True)
    usb_address			= db.Column(db.String(255), nullable=True)

#    device = relationship('Devices', back_populates='usbdevices')

    __table_args__ = (
        PrimaryKeyConstraint('deviceuuid', 'usb_name', name='deviceuuid_usb_name_pk'),
    )

class DeviceDrivers(db.Model):
    __tablename__ = 'devicedrivers'
    deviceuuid 			= db.Column(UUID(as_uuid=True), db.ForeignKey('devices.deviceuuid', ondelete="CASCADE"), primary_key=True, default=uuid.uuid4)
    last_update 		= db.Column(db.Integer, nullable=False)
    last_json 			= db.Column(db.Integer, nullable=False)
    driver_name 		= db.Column(db.String(255), nullable=False, primary_key=True)
    driver_description 	= db.Column(db.String(255), nullable=True)
    driver_path			= db.Column(db.String(255), nullable=True)
    driver_type			= db.Column(db.String(255), nullable=True)
    driver_version		= db.Column(db.String(255), nullable=True)
    driver_date			= db.Column(db.Integer, 	nullable=True)

#    device = relationship('Devices', back_populates='usbdevices')

    __table_args__ = (
        PrimaryKeyConstraint('deviceuuid', 'driver_name', name='deviceuuid_driver_name_pk'),
    )



class DeviceRealtimeData(db.Model):
    __tablename__ = 'devicerealtimedata'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deviceuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('devices.deviceuuid', ondelete="CASCADE"), nullable=False)
    data_type = db.Column(db.String(255), nullable=False)
    data_value = db.Column(db.Text, nullable=False)  # Changed to Text for large JSON data
    last_updated = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()))

    # Relationship to device
    device = relationship('Devices', backref='realtime_data')

    def to_dict(self):
        return {
            'id': str(self.id),
            'deviceuuid': str(self.deviceuuid),
            'data_type': self.data_type,
            'data_value': self.data_value,
            'last_updated': self.last_updated
        }

# Create an unlogged table using a custom DDL statement
event.listen(
    DeviceRealtimeData.__table__,
    'after_create',
    DDL('ALTER TABLE devicerealtimedata SET UNLOGGED')
)

class DeviceRealtimeHistory(db.Model):
    __tablename__ = 'devicerealtimehistory'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deviceuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('devices.deviceuuid', ondelete="CASCADE"), nullable=False)
    data_type = db.Column(db.String(255), nullable=False)
    data_value = db.Column(db.Text, nullable=False)  # Changed to Text for large JSON data
    timestamp = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()))

    # Relationship to device
    device = relationship('Devices', backref='realtime_history')

    def to_dict(self):
        return {
            'id': str(self.id),
            'deviceuuid': str(self.deviceuuid),
            'data_type': self.data_type,
            'data_value': self.data_value,
            'timestamp': self.timestamp
        }

# Filepath: app/models/devices.py
# Add this new class for the DeviceConnectivity table

class DeviceConnectivity(db.Model):
    __tablename__ = 'deviceconnectivity'

    deviceuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('devices.deviceuuid', ondelete="CASCADE"), primary_key=True)
    is_online = db.Column(db.Boolean, default=False)
    last_online_change = db.Column(db.Integer, nullable=True)
    last_seen_online = db.Column(db.Integer, nullable=True)
    last_heartbeat = db.Column(db.Integer, nullable=True)
    agent_version = db.Column(db.String(50), nullable=True)
    connection_type = db.Column(db.String(50), nullable=True)
    connection_info = db.Column(db.JSON, nullable=True)

    # Relationship to device
    device = relationship('Devices', backref='connectivity', uselist=False)

    def to_dict(self):
        return {
            'deviceuuid': str(self.deviceuuid),
            'is_online': self.is_online,
            'last_online_change': self.last_online_change,
            'last_seen_online': self.last_seen_online,
            'last_heartbeat': self.last_heartbeat,
            'agent_version': self.agent_version,
            'connection_type': self.connection_type,
            'connection_info': self.connection_info,
            'online_status': 'Online' if self.is_online else 'Offline',
            'last_online_time': datetime.fromtimestamp(self.last_seen_online).strftime('%Y-%m-%d %H:%M:%S') if self.last_seen_online else None,
            'last_heartbeat_time': datetime.fromtimestamp(self.last_heartbeat).strftime('%Y-%m-%d %H:%M:%S') if self.last_heartbeat else None
        }