# Filepath: app/routes/devices/devices_widgets.py
from flask import render_template, jsonify
from sqlalchemy import desc
from app.models import DeviceMetadata, Devices
from sqlalchemy.orm import joinedload
from app.utilities.app_access_login_required import login_required
from app.utilities.app_logging_helper import log_with_route
from app.utilities.ui_devices_devicedetails import ANALYSIS_TYPE_LABELS
import logging
from . import devices_bp

def get_device_analyses(device_id):
    """Fetch and categorize all analyses for a device"""
    analyses = (DeviceMetadata.query
                .filter_by(deviceuuid=device_id)
                .filter_by(processing_status='processed')
                .order_by(desc(DeviceMetadata.created_at))
                .all())

    # Group analyses by type, keeping only most recent of each type
    categorized = {}
    for analysis in analyses:
        if analysis.metalogos_type not in categorized:
            # Format timestamp for template use
            timestamp_str = 'N/A'
            if analysis.analyzed_at:
                try:
                    # Handle both datetime objects and Unix timestamps
                    if hasattr(analysis.analyzed_at, 'strftime'):
                        timestamp_str = analysis.analyzed_at.strftime('%Y-%m-%d %H:%M')
                    else:
                        from datetime import datetime
                        ts = float(analysis.analyzed_at)
                        timestamp_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
                except Exception:
                    timestamp_str = str(analysis.analyzed_at)

            categorized[analysis.metalogos_type] = {
                'type': analysis.metalogos_type,
                'name': ANALYSIS_TYPE_LABELS.get(analysis.metalogos_type, analysis.metalogos_type),
                'content': analysis.ai_analysis,
                'score': analysis.score,
                'timestamp': analysis.analyzed_at,
                'timestamp_str': timestamp_str,
                'category': categorize_analysis(analysis.metalogos_type)
            }

    return categorized

def categorize_analysis(analysis_type):
    """Categorize analysis based on type"""
    categories = {
        'System': ['eventsFiltered-System', 'msinfo-SystemSoftwareConfig',
                  'msinfo-SystemHardwareConfig'],
        'Security': ['eventsFiltered-Security', 'authFiltered'],
        'Applications': ['eventsFiltered-Application', 'msinfo-InstalledPrograms',
                        'msinfo-RecentAppCrashes'],
        'Hardware': ['windrivers', 'msinfo-StorageInfo', 'msinfo-NetworkConfig'],
        'Logs': ['journalFiltered', 'syslogFiltered', 'kernFiltered']
    }

    for category, types in categories.items():
        if analysis_type in types:
            return category
    return 'Other'

@devices_bp.route('/device/<uuid:device_id>/analyses')
@login_required
def device_analyses(device_id):
    try:
        device = Devices.query.options(
            joinedload(Devices.tenant)
        ).get_or_404(device_id)

        analyses = get_device_analyses(device_id)
        log_with_route(logging.DEBUG, f"Found {len(analyses)} analyses for device {device_id}")

        # Category information
        category_icons = {
            'System': 'fa-cogs',
            'Security': 'fa-shield-alt',
            'Applications': 'fa-laptop-code',
            'Hardware': 'fa-microchip',
            'Logs': 'fa-clipboard-list',
            'Other': 'fa-layer-group'
        }

        # Count analyses per category
        analysis_counts = {}
        for analysis in analyses.values():
            category = analysis['category']
            analysis_counts[category] = analysis_counts.get(category, 0) + 1

        # Group analyses by category
        categorized_analyses = {}
        for analysis in analyses.values():
            category = analysis['category']
            if category not in categorized_analyses:
                categorized_analyses[category] = []
            categorized_analyses[category].append(analysis)

        return render_template('devices/device_analyses.html',
                             device=device,
                             analyses=categorized_analyses,
                             categories=list(category_icons.keys()),
                             category_icons=category_icons,
                             analysis_counts=analysis_counts)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log_with_route(logging.ERROR, f"Error loading device analyses: {str(e)}\n{error_details}")
        return jsonify({'error': f'Failed to load analyses: {str(e)}', 'details': error_details}), 500

@devices_bp.route('/api/device/<uuid:device_id>/analysis/<analysis_type>')
@login_required
def get_full_analysis(device_id, analysis_type):
    """API endpoint for fetching full analysis content"""
    try:
        analysis = (DeviceMetadata.query
                    .filter_by(deviceuuid=device_id,
                              metalogos_type=analysis_type,
                              processing_status='processed')
                    .order_by(desc(DeviceMetadata.created_at))
                    .first_or_404())

        return jsonify({
            'content': analysis.ai_analysis,
            'score': analysis.score,
            'timestamp': analysis.analyzed_at,
            'type': analysis.metalogos_type
        })

    except Exception as e:
        log_with_route(logging.ERROR, f"Error fetching analysis: {str(e)}")
        return jsonify({'error': 'Failed to fetch analysis'}), 500

@devices_bp.route('/device/<uuid:device_id>/export-pdf', methods=['GET'])
@login_required
def export_device_pdf(device_id):
    """Export device report as PDF"""
    log_with_route(logging.INFO, f"PDF export requested for device {device_id}")

    try:
        from weasyprint import HTML, CSS
        from flask import render_template, make_response
        from datetime import datetime
        import io

        log_with_route(logging.DEBUG, "WeasyPrint imported successfully")

        # Get device information
        device = Devices.query.get_or_404(device_id)
        log_with_route(logging.DEBUG, f"Found device: {device.devicename}")

        # Get device analyses
        analyses_data = get_device_analyses(device_id)

        # Convert analyses data to list format for template
        analyses = []
        for analysis_type, data in analyses_data.items():
            analyses.append({
                'name': analysis_type.replace('_', ' ').title(),
                'analysis': data['content'],
                'score': data['score'],
                'analyzed_at': datetime.fromtimestamp(data['timestamp']) if data['timestamp'] else None
            })

        # Sort analyses by timestamp (newest first)
        analyses.sort(key=lambda x: x['analyzed_at'] or datetime.min, reverse=True)

        # Prepare template data
        template_data = {
            'device': device,
            'analyses': analyses,
            'report_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'charts': None  # TODO: Implement chart capture
        }

        # Render HTML template
        html_content = render_template('devices/components/device_report_pdf.html', **template_data)

        # Generate PDF
        pdf_buffer = io.BytesIO()
        HTML(string=html_content).write_pdf(pdf_buffer)
        pdf_buffer.seek(0)

        # Create response
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="device_report_{device.devicename}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'

        log_with_route(logging.INFO, f"Generated PDF report for device {device.devicename}")
        return response

    except Exception as e:
        log_with_route(logging.ERROR, f"Error generating PDF report: {str(e)}")
        return jsonify({'error': 'Failed to generate PDF report'}), 500