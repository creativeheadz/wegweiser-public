# Guided Tour System Documentation

## Overview

The Wegweiser guided tour system provides an interactive way to onboard users and guide them through key features of the application. Built on Shepherd.js, it offers a modular, database-driven approach to creating and managing tours across all pages.

## Architecture

### Components

1. **Database Models** (`app/models/guided_tours.py`)
   - `GuidedTour`: Stores tour configurations and steps
   - `TourProgress`: Tracks user progress through tours

2. **Utility Functions** (`app/utilities/guided_tour_manager.py`)
   - Tour creation, retrieval, and management functions
   - Progress tracking and validation

3. **JavaScript Component** (`app/static/js/common/guided-tour.js`)
   - Reusable Shepherd.js wrapper
   - Automatic tour initialization and progress tracking

4. **Template Macros** (`app/templates/components/guided_tour.html`)
   - Reusable UI components for tour integration

5. **Admin Interface** (`app/templates/administration/admin_tours.html`)
   - Complete CRUD interface for tour management

## Quick Start

### Adding Tours to a Page

1. **Update the route handler:**
```python
from app.utilities.guided_tour_manager import get_tour_for_page

@your_bp.route('/your-page')
def your_page():
    user_id = session.get('user_id')
    tour_data = get_tour_for_page('your-page-identifier', user_id)
    return render_template('your-template.html', tour_data=tour_data)
```

2. **Update the template:**
```html
{% from 'components/guided_tour.html' import tour_breadcrumb_button, include_tour_system %}

<!-- Add tour button to breadcrumb -->
{% call breadcrumb(title='Your Page') %}
    {{ tour_breadcrumb_button(tour_data) }}
{% endcall %}

<!-- Include tour system at the end -->
{{ include_tour_system('your-page-identifier', tour_data) }}
```

3. **Create the tour in admin interface** at `/admin/tours`

## Page Identifiers

Page identifiers are unique strings that connect tours to specific pages:

| Page | URL | Page Identifier |
|------|-----|----------------|
| Dashboard | `/dashboard` | `dashboard` |
| Devices | `/devices` | `devices` |
| Organizations | `/organisations` | `organisations` |
| Groups | `/groups` | `groups` |
| Quick Start | `/quickstart` | `quickstart` |

### Naming Convention
- Use lowercase letters
- Replace spaces with hyphens
- Keep descriptive but concise
- Must be unique across the application

## Tour Management

### Admin Interface (`/admin/tours`)

**Actions Available:**
- **Create**: Build new tours with visual step editor
- **Edit**: Modify existing tour content and settings
- **Preview**: See tours as users would experience them
- **Toggle**: Activate/deactivate tours for users
- **Delete**: Permanently remove tours

**Tour Properties:**
- **Page Identifier**: Unique identifier linking tour to page
- **Tour Name**: Display name for the tour
- **Description**: Brief explanation of tour content
- **Auto-start**: Whether tour starts automatically for new users
- **Active Status**: Controls tour visibility to users

### Tour Steps

Each tour consists of multiple steps with these properties:

- **Step ID**: Unique identifier for the step
- **Text**: Content displayed to users
- **Title**: Optional step title
- **Target Element**: CSS selector for element to highlight
- **Position**: Where to display the tour popup (top, bottom, left, right, center)

## Database Schema

### GuidedTour Table
```sql
tour_id          UUID PRIMARY KEY
page_identifier  VARCHAR(100) UNIQUE
page_title       VARCHAR(255)
tour_name        VARCHAR(255)
tour_description TEXT
is_active        BOOLEAN
auto_start       BOOLEAN
tour_config      JSONB
steps            JSONB
created_at       BIGINT
updated_at       BIGINT
created_by       UUID
version          INTEGER
```

### TourProgress Table
```sql
progress_id      UUID PRIMARY KEY
user_id          UUID FOREIGN KEY
tour_id          UUID FOREIGN KEY
completed_steps  JSONB
is_completed     BOOLEAN
last_step        VARCHAR(100)
started_at       BIGINT
completed_at     BIGINT
last_accessed    BIGINT
```

## API Endpoints

### User-facing APIs
- `POST /api/tours/step-complete` - Mark step as completed
- `POST /api/tours/complete` - Mark entire tour as completed
- `POST /api/tours/reset` - Reset user progress
- `GET /api/tours/progress/<page_identifier>` - Get user progress

### Admin APIs
- `GET /admin/tours` - Tour management interface
- `POST /admin/tours/create` - Create new tour
- `GET /admin/tours/<tour_id>` - Get tour details
- `POST /admin/tours/<tour_id>/update` - Update existing tour
- `POST /admin/tours/<tour_id>/toggle` - Toggle tour status
- `DELETE /admin/tours/<tour_id>` - Delete tour

## Template Macros

### Available Macros

```html
<!-- Basic tour button -->
{{ tour_button(tour_data) }}

<!-- Tour button for breadcrumbs -->
{{ tour_breadcrumb_button(tour_data) }}

<!-- Progress indicator -->
{{ tour_progress_indicator(tour_data) }}

<!-- Complete tour card -->
{{ tour_card(tour_data) }}

<!-- Floating help button -->
{{ tour_floating_button(tour_data) }}

<!-- Include complete tour system -->
{{ include_tour_system('page-identifier', tour_data) }}
```

## JavaScript API

### Global Object
```javascript
window.guidedTourManager
```

### Methods
```javascript
// Initialize tour
guidedTourManager.init(tourData, pageIdentifier)

// Start tour manually
guidedTourManager.startTour()

// Reset progress
guidedTourManager.resetProgress()

// Check if tour is available
guidedTourManager.isAvailable()

// Get progress information
guidedTourManager.getProgress()
```

## Troubleshooting

### Tour Not Showing
1. Check if tour is active in admin interface
2. Verify page identifier matches between route and database
3. Ensure `tour_data` is passed to template
4. Confirm template includes tour macros

### Tour Button Missing
1. Verify route calls `get_tour_for_page()`
2. Check template imports tour macros
3. Ensure `tour_breadcrumb_button()` is in breadcrumb

### Progress Not Saving
1. Check browser console for API errors
2. Verify CSRF token is available
3. Confirm user is logged in
4. Check server logs for backend errors

## Best Practices

### Tour Design
- Keep steps concise and actionable
- Use clear, descriptive step titles
- Target specific UI elements when possible
- Test tours on different screen sizes

### Content Management
- Write step content in plain language
- Focus on user benefits, not features
- Include clear next steps
- Update tours when UI changes

### Performance
- Only load tours on pages that need them
- Use auto-start sparingly
- Monitor tour completion rates
- Remove outdated tours

## Migration

### Initial Setup
Run the migration command to create tables and sample data:
```bash
flask init-tours
```

### Existing Tours
The system includes a migration utility to convert hardcoded tours:
```python
from app.utilities.migrate_quickstart_tour import run_migration
run_migration()
```

## Security

- Admin tour management requires admin role
- User progress is isolated by user ID
- CSRF protection on all tour APIs
- Input validation on tour content

## Future Enhancements

- Advanced analytics and completion tracking
- A/B testing for different tour versions
- Conditional tours based on user roles
- Integration with help documentation
- Multi-language tour support
