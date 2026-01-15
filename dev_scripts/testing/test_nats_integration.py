# Filepath: tests/test_nats_integration.py
"""
NATS Integration Tests

Comprehensive tests for NATS integration including tenant isolation,
message routing, and performance validation.
"""

import asyncio
import json
import pytest
import time
import uuid
from unittest.mock import Mock, patch, AsyncMock

from app import create_app
from app.models import db, Tenants, Devices, Groups, Organisations, DeviceConnectivity
from app.utilities.nats_manager import (
    NATSConnectionManager, NATSSubjectValidator, NATSMessage,
    NATSPublisher, NATSSubscriber
)
from app.handlers.nats.message_handlers import (
    HeartbeatHandler, CommandResponseHandler, NATSMessageRouter
)


@pytest.fixture
def app():
    """Create test Flask application"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def sample_tenant(app):
    """Create sample tenant for testing"""
    with app.app_context():
        tenant = Tenants(
            tenantuuid=str(uuid.uuid4()),
            tenantname="Test Tenant",
            email="test@example.com"
        )
        db.session.add(tenant)
        
        org = Organisations(
            orguuid=str(uuid.uuid4()),
            orgname="Test Org",
            tenantuuid=tenant.tenantuuid
        )
        db.session.add(org)
        
        group = Groups(
            groupuuid=str(uuid.uuid4()),
            groupname="Test Group",
            orguuid=org.orguuid,
            tenantuuid=tenant.tenantuuid
        )
        db.session.add(group)
        
        device = Devices(
            deviceuuid=str(uuid.uuid4()),
            devicename="Test Device",
            groupuuid=group.groupuuid,
            orguuid=org.orguuid,
            tenantuuid=tenant.tenantuuid
        )
        db.session.add(device)
        
        db.session.commit()
        
        return {
            'tenant': tenant,
            'org': org,
            'group': group,
            'device': device
        }


class TestNATSSubjectValidator:
    """Test NATS subject validation and construction"""
    
    def test_validate_tenant_uuid(self):
        """Test tenant UUID validation"""
        valid_uuid = str(uuid.uuid4())
        assert NATSSubjectValidator.validate_tenant_uuid(valid_uuid) is True
        assert NATSSubjectValidator.validate_tenant_uuid("invalid-uuid") is False
        assert NATSSubjectValidator.validate_tenant_uuid("") is False
    
    def test_validate_device_uuid(self):
        """Test device UUID validation"""
        valid_uuid = str(uuid.uuid4())
        assert NATSSubjectValidator.validate_device_uuid(valid_uuid) is True
        assert NATSSubjectValidator.validate_device_uuid("invalid-uuid") is False
    
    def test_construct_subject(self):
        """Test subject construction"""
        tenant_uuid = str(uuid.uuid4())
        device_uuid = str(uuid.uuid4())
        message_type = "heartbeat"
        
        expected = f"tenant.{tenant_uuid}.device.{device_uuid}.heartbeat"
        result = NATSSubjectValidator.construct_subject(tenant_uuid, device_uuid, message_type)
        
        assert result == expected
    
    def test_construct_subject_sanitizes_message_type(self):
        """Test that message type is sanitized"""
        tenant_uuid = str(uuid.uuid4())
        device_uuid = str(uuid.uuid4())
        message_type = "test.message type"
        
        result = NATSSubjectValidator.construct_subject(tenant_uuid, device_uuid, message_type)
        assert "test_message_type" in result
    
    def test_parse_subject(self):
        """Test subject parsing"""
        tenant_uuid = str(uuid.uuid4())
        device_uuid = str(uuid.uuid4())
        subject = f"tenant.{tenant_uuid}.device.{device_uuid}.heartbeat"
        
        result = NATSSubjectValidator.parse_subject(subject)
        
        assert result['tenant_uuid'] == tenant_uuid
        assert result['device_uuid'] == device_uuid
        assert result['message_type'] == 'heartbeat'
    
    def test_parse_invalid_subject(self):
        """Test parsing invalid subject raises error"""
        with pytest.raises(ValueError):
            NATSSubjectValidator.parse_subject("invalid.subject")
    
    def test_get_tenant_wildcard(self):
        """Test tenant wildcard generation"""
        tenant_uuid = str(uuid.uuid4())
        expected = f"tenant.{tenant_uuid}.>"
        result = NATSSubjectValidator.get_tenant_wildcard(tenant_uuid)
        assert result == expected


class TestNATSConnectionManager:
    """Test NATS connection management"""
    
    @pytest.mark.asyncio
    async def test_get_tenant_credentials(self):
        """Test tenant credential generation"""
        manager = NATSConnectionManager()
        tenant_uuid = str(uuid.uuid4())
        
        credentials = await manager.get_tenant_credentials(tenant_uuid)
        
        assert credentials.tenant_uuid == tenant_uuid
        assert credentials.username == f"tenant_{tenant_uuid}"
        assert len(credentials.password) == 32
        assert f"tenant.{tenant_uuid}.>" in credentials.permissions['publish']
        assert f"tenant.{tenant_uuid}.>" in credentials.permissions['subscribe']
    
    def test_generate_password(self):
        """Test password generation"""
        manager = NATSConnectionManager()
        password = manager._generate_password()
        
        assert len(password) == 32
        assert password.isalnum()


class TestHeartbeatHandler:
    """Test heartbeat message handling"""
    
    @pytest.mark.asyncio
    async def test_process_heartbeat_message(self, app, sample_tenant):
        """Test processing heartbeat message"""
        with app.app_context():
            handler = HeartbeatHandler()
            
            # Create test message
            message = NATSMessage(
                tenant_uuid=str(sample_tenant['tenant'].tenantuuid),
                device_uuid=str(sample_tenant['device'].deviceuuid),
                message_type="heartbeat",
                payload={
                    "device_uuid": str(sample_tenant['device'].deviceuuid),
                    "session_id": str(uuid.uuid4()),
                    "timestamp": int(time.time()),
                    "system_info": {
                        "hostname": "test-host",
                        "platform": "Linux",
                        "cpu_count": 4
                    },
                    "status": {
                        "is_connected": True,
                        "connection_type": "nats",
                        "nats_server": "nats://test:4222"
                    }
                },
                timestamp=int(time.time()),
                message_id=str(uuid.uuid4())
            )
            
            # Process message
            result = await handler.process_message(message)
            
            assert result is True
            
            # Verify connectivity record was created/updated
            connectivity = DeviceConnectivity.query.filter_by(
                deviceuuid=sample_tenant['device'].deviceuuid
            ).first()
            
            assert connectivity is not None
            assert connectivity.is_online is True
            assert connectivity.connection_type == "nats"
    
    @pytest.mark.asyncio
    async def test_validate_tenant_context(self, app, sample_tenant):
        """Test tenant context validation"""
        with app.app_context():
            handler = HeartbeatHandler()
            
            # Valid message
            valid_message = NATSMessage(
                tenant_uuid=str(sample_tenant['tenant'].tenantuuid),
                device_uuid=str(sample_tenant['device'].deviceuuid),
                message_type="heartbeat",
                payload={},
                timestamp=int(time.time()),
                message_id=str(uuid.uuid4())
            )
            
            assert handler.validate_tenant_context(valid_message) is True
            
            # Invalid tenant
            invalid_tenant_message = NATSMessage(
                tenant_uuid=str(uuid.uuid4()),
                device_uuid=str(sample_tenant['device'].deviceuuid),
                message_type="heartbeat",
                payload={},
                timestamp=int(time.time()),
                message_id=str(uuid.uuid4())
            )
            
            assert handler.validate_tenant_context(invalid_tenant_message) is False
            
            # Invalid device
            invalid_device_message = NATSMessage(
                tenant_uuid=str(sample_tenant['tenant'].tenantuuid),
                device_uuid=str(uuid.uuid4()),
                message_type="heartbeat",
                payload={},
                timestamp=int(time.time()),
                message_id=str(uuid.uuid4())
            )
            
            assert handler.validate_tenant_context(invalid_device_message) is False


class TestNATSMessageRouter:
    """Test message routing"""
    
    @pytest.mark.asyncio
    async def test_route_heartbeat_message(self, app, sample_tenant):
        """Test routing heartbeat message"""
        with app.app_context():
            router = NATSMessageRouter()
            
            message = NATSMessage(
                tenant_uuid=str(sample_tenant['tenant'].tenantuuid),
                device_uuid=str(sample_tenant['device'].deviceuuid),
                message_type="heartbeat",
                payload={
                    "device_uuid": str(sample_tenant['device'].deviceuuid),
                    "session_id": str(uuid.uuid4()),
                    "timestamp": int(time.time()),
                    "system_info": {"hostname": "test"},
                    "status": {"is_connected": True}
                },
                timestamp=int(time.time()),
                message_id=str(uuid.uuid4())
            )
            
            result = await router.route_message(message)
            assert result is True
            
            stats = router.get_stats()
            assert stats['total_messages'] == 1
            assert stats['handler_stats']['heartbeat']['processed_messages'] == 1
    
    @pytest.mark.asyncio
    async def test_route_unknown_message_type(self, app, sample_tenant):
        """Test routing unknown message type"""
        with app.app_context():
            router = NATSMessageRouter()
            
            message = NATSMessage(
                tenant_uuid=str(sample_tenant['tenant'].tenantuuid),
                device_uuid=str(sample_tenant['device'].deviceuuid),
                message_type="unknown_type",
                payload={},
                timestamp=int(time.time()),
                message_id=str(uuid.uuid4())
            )
            
            result = await router.route_message(message)
            assert result is False
            
            stats = router.get_stats()
            assert stats['routing_errors'] == 1


class TestTenantIsolation:
    """Test tenant isolation in NATS integration"""
    
    def test_subject_isolation(self):
        """Test that subjects are properly isolated by tenant"""
        tenant1_uuid = str(uuid.uuid4())
        tenant2_uuid = str(uuid.uuid4())
        device_uuid = str(uuid.uuid4())
        
        subject1 = NATSSubjectValidator.construct_subject(tenant1_uuid, device_uuid, "heartbeat")
        subject2 = NATSSubjectValidator.construct_subject(tenant2_uuid, device_uuid, "heartbeat")
        
        # Subjects should be different even with same device UUID
        assert subject1 != subject2
        assert tenant1_uuid in subject1
        assert tenant2_uuid in subject2
        assert tenant1_uuid not in subject2
        assert tenant2_uuid not in subject1
    
    def test_wildcard_isolation(self):
        """Test that wildcard subjects are tenant-isolated"""
        tenant1_uuid = str(uuid.uuid4())
        tenant2_uuid = str(uuid.uuid4())
        
        wildcard1 = NATSSubjectValidator.get_tenant_wildcard(tenant1_uuid)
        wildcard2 = NATSSubjectValidator.get_tenant_wildcard(tenant2_uuid)
        
        assert wildcard1 != wildcard2
        assert tenant1_uuid in wildcard1
        assert tenant2_uuid in wildcard2


class TestNATSRoutes:
    """Test NATS API routes"""
    
    def test_health_check(self, client):
        """Test NATS health check endpoint"""
        response = client.get('/api/nats/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'status' in data
        assert 'components' in data
        assert 'metrics' in data
    
    def test_get_device_tenant(self, client, app, sample_tenant):
        """Test getting device tenant info"""
        with app.app_context():
            device_uuid = sample_tenant['device'].deviceuuid
            response = client.get(f'/api/nats/device/{device_uuid}/tenant')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['tenant_uuid'] == str(sample_tenant['tenant'].tenantuuid)
    
    def test_get_device_tenant_not_found(self, client):
        """Test getting tenant for non-existent device"""
        fake_uuid = str(uuid.uuid4())
        response = client.get(f'/api/nats/device/{fake_uuid}/tenant')
        assert response.status_code == 404


if __name__ == '__main__':
    pytest.main([__file__])
