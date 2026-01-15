from typing import Dict, Any, List
import logging
from flask import current_app
from app.utilities.app_logging_helper import log_with_route
from app.models import (
    db, Devices, Groups, Organisations, Tenants,
    DeviceMetadata, TenantMetadata
)


class MSPBusinessImpactAnalyzer:
    """Analyze business impact of technical issues for MSPs"""

    @staticmethod
    def analyze_impact(entity_type: str, entity_uuid: str, issue_type: str) -> Dict[str, Any]:
        """Analyze business impact of an issue"""
        impact = {
            "severity": "Medium",
            "client_impact": "May affect some services",
            "revenue_risk": "Low",
            "mitigation_time": "1-2 hours",
            "resources_needed": ["Technician"],
            "sla_implications": "Within standard SLA"
        }

        try:
            # Get entity
            if entity_type == "device":
                entity = Devices.query.get(entity_uuid)
                if not entity:
                    return impact

                # Get device's group and organization
                group = Groups.query.get(entity.groupuuid) if entity.groupuuid else None
                org = Organisations.query.get(group.orguuid) if group else None

                # Analyze based on device metadata
                if issue_type == "security":
                    # Check security events
                    metadata = DeviceMetadata.query.filter_by(
                        deviceuuid=entity_uuid,
                        metalogos_type='eventsFiltered-Security'
                    ).order_by(DeviceMetadata.created_at.desc()).first()

                    if metadata and metadata.score is not None:
                        if metadata.score < 50:
                            impact["severity"] = "Critical"
                            impact["client_impact"] = "Immediate security threat"
                            impact["revenue_risk"] = "High"
                            impact["mitigation_time"] = "ASAP (within hours)"
                            impact["resources_needed"] = ["Senior Security Specialist", "Technician"]
                            impact["sla_implications"] = "Emergency response required"
                        elif metadata.score < 70:
                            impact["severity"] = "High"
                            impact["client_impact"] = "Potential security vulnerability"
                            impact["revenue_risk"] = "Medium"
                            impact["mitigation_time"] = "Today"
                            impact["resources_needed"] = ["Security Specialist"]
                            impact["sla_implications"] = "Priority response"

                elif issue_type == "performance":
                    # Check system events
                    metadata = DeviceMetadata.query.filter_by(
                        deviceuuid=entity_uuid,
                        metalogos_type='eventsFiltered-System'
                    ).order_by(DeviceMetadata.created_at.desc()).first()

                    if metadata and metadata.score is not None:
                        if metadata.score < 50:
                            impact["severity"] = "High"
                            impact["client_impact"] = "Significant performance degradation"
                            impact["revenue_risk"] = "Medium"
                            impact["mitigation_time"] = "4-8 hours"
                            impact["resources_needed"] = ["Systems Engineer", "Technician"]
                            impact["sla_implications"] = "Approaching SLA breach"
                        elif metadata.score < 70:
                            impact["severity"] = "Medium"
                            impact["client_impact"] = "Moderate performance issues"
                            impact["revenue_risk"] = "Low"
                            impact["mitigation_time"] = "24 hours"
                            impact["resources_needed"] = ["Technician"]
                            impact["sla_implications"] = "Within standard SLA"

                # Consider device role - placeholder for future role detection
                # TODO: Implement device role detection based on device characteristics

                # Adjust based on organization SLA if available
                if org:
                    tenant = Tenants.query.get(org.tenantuuid)
                    if tenant:
                        sla_info = tenant.get_customer_sla(org.orguuid)
                        if sla_info and sla_info.get('type') == 'Premium':
                            impact["sla_implications"] = "Premium SLA - requires immediate attention"
                            impact["revenue_risk"] = "High"  # Risk to high-value client relationship

            elif entity_type in ["group", "organisation"]:
                # For group/org level, impact is based on aggregate device issues
                if entity_type == "group":
                    entity = Groups.query.get(entity_uuid)
                    if not entity:
                        return impact
                    devices = Devices.query.filter_by(groupuuid=entity_uuid).all()
                else:
                    entity = Organisations.query.get(entity_uuid)
                    if not entity:
                        return impact
                    groups = Groups.query.filter_by(orguuid=entity_uuid).all()
                    group_ids = [group.groupuuid for group in groups]
                    devices = Devices.query.filter(Devices.groupuuid.in_(group_ids)).all()

                if not devices:
                    return impact

                # Count devices with issues
                issue_count = 0
                critical_issues = 0

                for device in devices:
                    if issue_type == "security":
                        metadata = DeviceMetadata.query.filter_by(
                            deviceuuid=device.deviceuuid,
                            metalogos_type='eventsFiltered-Security'
                        ).order_by(DeviceMetadata.created_at.desc()).first()
                    else:  # performance or general
                        metadata = DeviceMetadata.query.filter_by(
                            deviceuuid=device.deviceuuid,
                            metalogos_type='eventsFiltered-System'
                        ).order_by(DeviceMetadata.created_at.desc()).first()

                    if metadata and metadata.score is not None and metadata.score < 70:
                        issue_count += 1
                        if metadata.score < 50:
                            critical_issues += 1

                # Determine impact based on percentage of affected devices
                total_devices = len(devices)
                if total_devices > 0:
                    affected_percentage = (issue_count / total_devices) * 100
                    critical_percentage = (critical_issues / total_devices) * 100

                    if critical_percentage >= 20 or (critical_issues >= 3 and issue_type == "security"):
                        impact["severity"] = "Critical"
                        impact["client_impact"] = f"Widespread critical issues affecting {critical_percentage:.0f}% of devices"
                        impact["revenue_risk"] = "High"
                        impact["mitigation_time"] = "Immediate response required"
                        impact["resources_needed"] = ["Senior Engineer", "Project Manager", "Multiple Technicians"]
                        impact["sla_implications"] = "SLA breach likely"
                    elif affected_percentage >= 30 or critical_issues > 0:
                        impact["severity"] = "High"
                        impact["client_impact"] = f"Significant issues affecting {affected_percentage:.0f}% of devices"
                        impact["revenue_risk"] = "Medium"
                        impact["mitigation_time"] = "Response within hours"
                        impact["resources_needed"] = ["Engineer", "Multiple Technicians"]
                        impact["sla_implications"] = "Priority response required"
                    elif affected_percentage >= 10:
                        impact["severity"] = "Medium"
                        impact["client_impact"] = f"Issues affecting {affected_percentage:.0f}% of devices"
                        impact["revenue_risk"] = "Low"
                        impact["mitigation_time"] = "24-48 hours"
                        impact["resources_needed"] = ["Technician"]
                        impact["sla_implications"] = "Standard SLA response"

                # Adjust for organization size/importance if available
                if entity_type == "organisation":
                    # Check if this is a significant client
                    tenant = Tenants.query.get(entity.tenantuuid)
                    if tenant:
                        orgs_count = Organisations.query.filter_by(tenantuuid=tenant.tenantuuid).count()
                        if orgs_count > 0:
                            # Count devices across all orgs to see relative importance
                            all_devices_count = Devices.query.filter_by(tenantuuid=tenant.tenantuuid).count()
                            org_devices_count = len(devices)

                            if all_devices_count > 0:
                                org_importance = org_devices_count / all_devices_count

                                # If this org represents a significant portion of devices
                                if org_importance > 0.25:  # More than 25% of all devices
                                    # Increase severity and risk
                                    impact_levels = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}
                                    current_level = impact_levels.get(impact["severity"], 1)
                                    new_level = min(current_level + 1, 3)

                                    for level_name, level_value in impact_levels.items():
                                        if level_value == new_level:
                                            impact["severity"] = level_name
                                            break

                                    impact["client_impact"] += " (Major client)"
                                    impact["revenue_risk"] = "High"
                                    impact["sla_implications"] = "Prioritize response to protect client relationship"

            elif entity_type == "tenant":
                # For tenant level, this is an MSP-wide issue
                entity = Tenants.query.get(entity_uuid)
                if not entity:
                    return impact

                # For tenant-wide issues, consider total device count with issues
                if issue_type == "security":
                    # Count devices with security issues
                    security_metadata = DeviceMetadata.query.join(Devices).filter(
                        Devices.tenantuuid == entity_uuid,
                        DeviceMetadata.metalogos_type == 'eventsFiltered-Security',
                        DeviceMetadata.score < 70
                    ).count()

                    total_devices = Devices.query.filter_by(tenantuuid=entity_uuid).count()

                    if total_devices > 0:
                        affected_percentage = (security_metadata / total_devices) * 100

                        if affected_percentage >= 15:
                            impact["severity"] = "Critical"
                            impact["client_impact"] = "Widespread security issues affecting multiple clients"
                            impact["revenue_risk"] = "Very High"
                            impact["mitigation_time"] = "All hands response required"
                            impact["resources_needed"] = ["Security Team", "Technical Director", "Account Managers"]
                            impact["sla_implications"] = "Multiple SLA breaches likely"
                        elif affected_percentage >= 5:
                            impact["severity"] = "High"
                            impact["client_impact"] = "Security issues affecting multiple clients"
                            impact["revenue_risk"] = "High"
                            impact["mitigation_time"] = "Coordinated response plan needed"
                            impact["resources_needed"] = ["Security Specialist", "Multiple Technicians"]
                            impact["sla_implications"] = "Potential SLA breaches"

                elif issue_type == "performance":
                    # Similar logic for performance issues
                    perf_metadata = DeviceMetadata.query.join(Devices).filter(
                        Devices.tenantuuid == entity_uuid,
                        DeviceMetadata.metalogos_type.in_(['eventsFiltered-System', 'eventsFiltered-Application']),
                        DeviceMetadata.score < 70
                    ).count()

                    total_devices = Devices.query.filter_by(tenantuuid=entity_uuid).count()

                    if total_devices > 0:
                        affected_percentage = (perf_metadata / total_devices) * 100

                        if affected_percentage >= 20:
                            impact["severity"] = "High"
                            impact["client_impact"] = "Widespread performance issues affecting multiple clients"
                            impact["revenue_risk"] = "High"
                            impact["mitigation_time"] = "Coordinated response plan needed"
                            impact["resources_needed"] = ["Systems Engineer", "Multiple Technicians"]
                            impact["sla_implications"] = "Potential SLA breaches"

        except Exception as e:
            log_with_route(logging.ERROR, f"Error in business impact analysis: {str(e)}")

        return impact