# Filepath: app/tasks/test_analysis.py
# app/tasks/test_analysis.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app import create_app  # Import your Flask app factory function
from app.models import db, DeviceMetadata
from app.tasks.base.scheduler import AnalysisScheduler
from app.tasks.journal.analyzer import JournalAnalyzer

def test_pending_analysis():
    # Use Flask's application context
    app = create_app()  # Adjust if your create_app requires arguments
    with app.app_context():
        pending = DeviceMetadata.query.filter_by(
            metalogos_type='journalFiltered',  # Correct type from DB
            processing_status='pending'
        ).first()
        
        if not pending:
            print("No pending journal analyses found")
            return
            
        print(f"Found pending analysis for device: {pending.deviceuuid}")
        
        scheduler = AnalysisScheduler()
        scheduler.register_analyzer(JournalAnalyzer)
        
        result = scheduler.schedule_analysis(
            str(pending.deviceuuid),
            str(pending.metadatauuid),
            'journalFiltered'  # Match exact type
        )
        
        print(f"Analysis scheduled with result: {result}")
    
if __name__ == "__main__":
    test_pending_analysis()