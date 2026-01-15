#!/usr/bin/env python3
"""
Fix HTML corruption in device analysis data
"""
from app import create_app, db
from sqlalchemy import text

def fix_device_html_corruption():
    app = create_app()
    with app.app_context():
        print("Fixing HTML corruption in device analyses...")
        
        # Fix ```html markers in device analyses
        result1 = db.session.execute(text("""
            UPDATE devicemetadata 
            SET ai_analysis = REPLACE(ai_analysis, '```html\n', '')
            WHERE ai_analysis LIKE '%```html%'
            AND processing_status = 'processed'
        """))
        
        print(f"Fixed {result1.rowcount} device analyses with ```html corruption")
        
        # Fix trailing ``` markers
        result2 = db.session.execute(text("""
            UPDATE devicemetadata 
            SET ai_analysis = REPLACE(ai_analysis, '\n```', '')
            WHERE ai_analysis LIKE '%\n```%'
            AND processing_status = 'processed'
        """))
        
        print(f"Fixed {result2.rowcount} device analyses with trailing ``` corruption")
        
        # Fix any remaining ``` markers
        result3 = db.session.execute(text("""
            UPDATE devicemetadata 
            SET ai_analysis = REPLACE(ai_analysis, '```', '')
            WHERE ai_analysis LIKE '%```%'
            AND processing_status = 'processed'
        """))
        
        print(f"Fixed {result3.rowcount} device analyses with remaining ``` corruption")
        
        db.session.commit()
        print("Device analysis cleanup completed successfully!")
        
        # Verify the fix for the specific device
        device_uuid = '510a188e-ca5b-48cc-8fe7-173f14fa8928'
        result = db.session.execute(text("""
            SELECT COUNT(*) as corrupted_count
            FROM devicemetadata 
            WHERE deviceuuid = :device_uuid
            AND processing_status = 'processed'
            AND ai_analysis LIKE '%```html%'
        """), {'device_uuid': device_uuid}).scalar()
        
        print(f"\nVerification for device {device_uuid}:")
        print(f"Remaining corrupted analyses: {result}")

if __name__ == "__main__":
    fix_device_html_corruption()
