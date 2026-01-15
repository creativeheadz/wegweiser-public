# Filepath: app/utilities/migrate_quickstart_tour.py
"""
Migration utility to convert the existing hardcoded quickstart tour 
to the new database-driven guided tour system.
"""

import logging
from app.models import db, GuidedTour
from app.utilities.app_logging_helper import log_with_route


def migrate_quickstart_tour():
    """
    Create the quickstart tour in the database using the existing tour content.
    """
    try:
        # Check if quickstart tour already exists
        existing_tour = GuidedTour.get_by_page('quickstart')
        if existing_tour:
            log_with_route(logging.INFO, "Quickstart tour already exists in database")
            return existing_tour

        # Define the quickstart tour steps based on the existing implementation
        quickstart_steps = [
            {
                "id": "welcome",
                "title": "Welcome to Wegweiser",
                "text": "Welcome to Wegweiser! Let's show you around the Quick Start guide.",
                "attachTo": {
                    "element": "#step1",
                    "on": "bottom"
                }
            },
            {
                "id": "structure",
                "title": "Create Customer Structure",
                "text": "First, create your customer structure with organizations and groups. This is essential before you can deploy agents.",
                "attachTo": {
                    "element": "#step1",
                    "on": "right"
                }
            },
            {
                "id": "agents",
                "title": "Deploy Agents",
                "text": "Then deploy agents to your customer devices for monitoring. Each agent requires a specific group UUID.",
                "attachTo": {
                    "element": "#step2",
                    "on": "right"
                }
            },
            {
                "id": "data",
                "title": "Explore Data & Health Scores",
                "text": "Explore the collected data and monitor health scores across your organization. Our AI analyzes over 200 metrics.",
                "attachTo": {
                    "element": "#step3",
                    "on": "right"
                }
            },
            {
                "id": "premium",
                "title": "Premium Features",
                "text": "Finally, unlock premium features with WegCoins to enhance your MSP capabilities with AI-driven insights.",
                "attachTo": {
                    "element": "#step4",
                    "on": "right"
                }
            }
        ]

        # Tour configuration
        tour_config = {
            "useModalOverlay": True,
            "defaultStepOptions": {
                "classes": "shadow-md bg-purple-dark",
                "scrollTo": True,
                "cancelIcon": {
                    "enabled": True
                }
            }
        }

        # Create the tour
        tour = GuidedTour(
            page_identifier='quickstart',
            page_title='Quick Start Guide',
            tour_name='Wegweiser Quick Start Tour',
            tour_description='Learn how to set up your MSP monitoring solution with Wegweiser',
            is_active=True,
            auto_start=True,  # Auto-start for first-time users
            tour_config=tour_config,
            steps=quickstart_steps
        )

        db.session.add(tour)
        db.session.commit()

        log_with_route(logging.INFO, "Successfully migrated quickstart tour to database")
        return tour

    except Exception as e:
        log_with_route(logging.ERROR, f"Error migrating quickstart tour: {str(e)}")
        db.session.rollback()
        return None


def create_sample_tours():
    """
    Create sample tours for other key pages to demonstrate the system.
    """
    try:
        sample_tours = [
            {
                'page_identifier': 'dashboard',
                'page_title': 'Dashboard',
                'tour_name': 'Dashboard Overview Tour',
                'tour_description': 'Get familiar with your main dashboard and key metrics',
                'auto_start': False,
                'steps': [
                    {
                        'id': 'welcome_dashboard',
                        'title': 'Welcome to Your Dashboard',
                        'text': 'This is your main dashboard where you can see an overview of all your managed devices and organizations.',
                        'attachTo': {
                            'element': '.main-content',
                            'on': 'center'
                        }
                    },
                    {
                        'id': 'device_stats',
                        'title': 'Device Statistics',
                        'text': 'These cards show you the breakdown of devices by operating system across all your customers.',
                        'attachTo': {
                            'element': '.dashboard-stat',
                            'on': 'bottom'
                        }
                    },
                    {
                        'id': 'wegcoins',
                        'title': 'WegCoin Balance',
                        'text': 'Keep track of your WegCoin balance and spending for premium AI features.',
                        'attachTo': {
                            'element': '[data-bs-target="#wegcoin-modal"]',
                            'on': 'left'
                        }
                    }
                ]
            },
            {
                'page_identifier': 'devices',
                'page_title': 'Device Management',
                'tour_name': 'Device Management Tour',
                'tour_description': 'Learn how to manage and monitor your customer devices',
                'auto_start': False,
                'steps': [
                    {
                        'id': 'device_list',
                        'title': 'Device Overview',
                        'text': 'Here you can see all devices across your customer organizations. Use filters to find specific devices.',
                        'attachTo': {
                            'element': '.device-grid',
                            'on': 'top'
                        }
                    },
                    {
                        'id': 'health_scores',
                        'title': 'Health Scores',
                        'text': 'Each device has a health score based on AI analysis of over 200 metrics. Green is healthy, red needs attention.',
                        'attachTo': {
                            'element': '.health-gauge',
                            'on': 'bottom'
                        }
                    },
                    {
                        'id': 'device_actions',
                        'title': 'Device Actions',
                        'text': 'Click on any device to view detailed information, run AI analysis, or perform management tasks.',
                        'attachTo': {
                            'element': '.device-card',
                            'on': 'right'
                        }
                    }
                ]
            },
            {
                'page_identifier': 'organizations',
                'page_title': 'Organizations',
                'tour_name': 'Organization Management Tour',
                'tour_description': 'Learn how to manage your customer organizations',
                'auto_start': False,
                'steps': [
                    {
                        'id': 'org_overview',
                        'title': 'Customer Organizations',
                        'text': 'This page shows all your customer organizations. Each organization represents one of your MSP clients.',
                        'attachTo': {
                            'element': '.organizations-grid',
                            'on': 'top'
                        }
                    },
                    {
                        'id': 'org_health',
                        'title': 'Organization Health',
                        'text': 'Each organization has an overall health score that aggregates the health of all devices within it.',
                        'attachTo': {
                            'element': '.org-health-indicator',
                            'on': 'bottom'
                        }
                    },
                    {
                        'id': 'add_org',
                        'title': 'Add New Organization',
                        'text': 'Use this button to add new customer organizations to your MSP tenant.',
                        'attachTo': {
                            'element': '[data-bs-target="#addOrganisationModal"]',
                            'on': 'left'
                        }
                    }
                ]
            }
        ]

        created_tours = []
        for tour_data in sample_tours:
            # Check if tour already exists
            existing_tour = GuidedTour.get_by_page(tour_data['page_identifier'])
            if existing_tour:
                log_with_route(logging.INFO, f"Tour for {tour_data['page_identifier']} already exists")
                continue

            tour = GuidedTour(
                page_identifier=tour_data['page_identifier'],
                page_title=tour_data['page_title'],
                tour_name=tour_data['tour_name'],
                tour_description=tour_data['tour_description'],
                is_active=True,
                auto_start=tour_data['auto_start'],
                tour_config={
                    "useModalOverlay": True,
                    "defaultStepOptions": {
                        "classes": "shadow-md bg-purple-dark",
                        "scrollTo": True
                    }
                },
                steps=tour_data['steps']
            )

            db.session.add(tour)
            created_tours.append(tour)

        if created_tours:
            db.session.commit()
            log_with_route(logging.INFO, f"Created {len(created_tours)} sample tours")

        return created_tours

    except Exception as e:
        log_with_route(logging.ERROR, f"Error creating sample tours: {str(e)}")
        db.session.rollback()
        return []


def run_migration():
    """
    Run the complete migration process.
    """
    log_with_route(logging.INFO, "Starting guided tour migration")
    
    # Migrate quickstart tour
    quickstart_tour = migrate_quickstart_tour()
    
    # Create sample tours
    sample_tours = create_sample_tours()
    
    total_created = (1 if quickstart_tour else 0) + len(sample_tours)
    log_with_route(logging.INFO, f"Migration complete. Created {total_created} tours.")
    
    return total_created > 0


if __name__ == '__main__':
    # This allows the script to be run directly for testing
    from app import create_app
    
    app = create_app()
    with app.app_context():
        run_migration()
