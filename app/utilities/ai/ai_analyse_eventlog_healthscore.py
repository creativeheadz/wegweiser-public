# Filepath: app/utilities/ai/ai_analyse_eventlog_healthscore.py
# Filepath: app/utilities/ai_analyse_eventlog_healthscore.py
import os
from flask import current_app
from app.utilities.log_utils import load_logs_from_file, group_logs_by_date
from app.utilities.analysis_utils import process_machine_logs
from app.utilities.ollama_analysis import analyze_logs_with_ollama, calculate_overall_health_score
import logging
from app.utilities.app_logging_helper import log_with_route
from ...extensions import celery
import json
from flask import current_app
from app import create_app  # Ensure you import your app creation function


DEVICE_FILES_DIR = '/home/wegweiseruser/wegweiser/deviceFiles'

def save_results(results, directory, filename):
    """Save the results to the device's own directory."""
    filepath = os.path.join(directory, filename)
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2)
    log_with_route(logging.INFO, f"Results saved to {filepath}", source_type="Celery Task")

def write_summary(machine_id, summary, directory, filename):
    """Write the summary to a file in the device's own directory."""
    filepath = os.path.join(directory, f"{machine_id}_{filename}")
    with open(filepath, 'w') as f:
        f.write(summary)
    log_with_route(logging.INFO, f"Summary for {machine_id} saved to {filepath}", source_type="Celery Task")

@celery.task
def analyse_eventlog_healthscore():
    """
    Celery task to analyze logs for each machine in the deviceFiles directory and calculate health scores.
    Results will be saved in the same directory as the logs.
    """
    with current_app.app_context():
        log_with_route(logging.INFO, "Starting event log health score analysis.", source_type="Celery Task")

        # Traverse the /deviceFiles directory to find and process logs
        for root, dirs, files in os.walk(DEVICE_FILES_DIR):
            machine_id = os.path.basename(root)
            
            # Only process directories that represent machines (i.e., have the required log files)
            if 'events-Application.json' in files and 'events-Security.json' in files and 'events-System.json' in files:
                log_with_route(logging.INFO, f"Processing logs for machine {machine_id}", source_type="Celery Task")
                
                try:
                    # Load logs from the relevant files
                    application_logs = load_logs_from_file(os.path.join(root, 'events-Application.json'))
                    security_logs = load_logs_from_file(os.path.join(root, 'events-Security.json'))
                    system_logs = load_logs_from_file(os.path.join(root, 'events-System.json'))
                    
                    # Combine logs
                    all_logs = application_logs + security_logs + system_logs
                    
                    # Group logs by date
                    grouped_logs = group_logs_by_date(all_logs)
                    
                    # Process logs for the machine
                    hourly_counts, daily_counts, event_type_counts = process_machine_logs(machine_id, all_logs)
                    
                    # Analyze logs with Ollama for each machine
                    daily_analyses, daily_health_scores = analyze_logs_with_ollama(grouped_logs, model="qwen2.5:latest")
                    overall_health_score = calculate_overall_health_score(daily_health_scores)
                    
                    # Prepare the machine results
                    machine_results = {
                        'machine_id': machine_id,
                        'hourly_counts': hourly_counts,
                        'daily_counts': daily_counts,
                        'event_type_counts': event_type_counts,
                        'daily_analyses': daily_analyses,
                        'daily_health_scores': daily_health_scores,
                        'overall_health_score': overall_health_score
                    }
                    
                    # Save the results and summaries in the device's own directory
                    save_results(machine_results, root, f"{machine_id}_results.json")
                    write_summary(machine_id, json.dumps(daily_analyses, indent=2), root, "daily_analyses.json")
                    write_summary(machine_id, json.dumps(daily_health_scores, indent=2), root, "daily_health_scores.json")
                    
                    log_with_route(logging.INFO, f"Overall Health Score for machine {machine_id}: {overall_health_score}", source_type="Celery Task")
                
                except Exception as e:
                    log_with_route(logging.ERROR, f"Failed to process logs for machine {machine_id}: {e}", source_type="Celery Task")
                    continue
        
        log_with_route(logging.INFO, "Event log health score analysis completed.", source_type="Celery Task")


def run():
    """
    Function to manually trigger the Celery task.
    """
    app = create_app()  # Create the app instance
    with app.app_context():  # Use app's context explicitly
        analyse_eventlog_healthscore.delay()  # Trigger Celery task asynchronously

