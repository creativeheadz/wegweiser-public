# Filepath: app/routes/tenant/profile.py
# Filepath: app/routes/profile.py
from flask import Blueprint, session, render_template, request, redirect, url_for, flash, current_app
from app.utilities.app_access_login_required import login_required
from app.models import db, Accounts, UserTwoFactor
from app.forms.profile_form import ProfileForm  # Import the new form
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
import os
import logging
from app.utilities.app_logging_helper import log_with_route
from flask_wtf.csrf import CSRFProtect


profile_bp = Blueprint('profile_bp', __name__)
bcrypt = Bcrypt()

def ensure_user_upload_dir(user_uuid):
    """Create user-specific upload directory if it doesn't exist"""
    user_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(user_uuid))
    os.makedirs(user_upload_dir, exist_ok=True)
    return user_upload_dir

@profile_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user_id = session.get('user_id')
    user = Accounts.query.get(user_id)
    user_2fa = UserTwoFactor.query.filter_by(user_uuid=user.useruuid).first()


    if not user:
        log_with_route(logging.WARNING, f'User with ID {user_id} not found in the database.')
        flash('User not found.', 'danger')
        return redirect(url_for('login_bp.login'))

    form = ProfileForm(obj=user)

    # Initialize preference fields from user_preferences
    try:
        prefs = user.user_preferences or {}
        if request.method == 'GET' and hasattr(form, 'devices_default_view'):
            form.devices_default_view.data = prefs.get('devices_layout', 'card')
    except Exception as e:
        log_with_route(logging.WARNING, f"Unable to initialize user preference fields: {e}")


    log_with_route(logging.INFO, f"Form data received: {request.form}")

# Populate country choices
    form.country.choices = [
        ('Afghanistan', 'Afghanistan'), ('Albania', 'Albania'), ('Algeria', 'Algeria'), 
        ('Andorra', 'Andorra'), ('Angola', 'Angola'), ('Antigua and Barbuda', 'Antigua and Barbuda'), 
        ('Argentina', 'Argentina'), ('Armenia', 'Armenia'), ('Australia', 'Australia'), 
        ('Austria', 'Austria'), ('Azerbaijan', 'Azerbaijan'), ('Bahamas', 'Bahamas'), 
        ('Bahrain', 'Bahrain'), ('Bangladesh', 'Bangladesh'), ('Barbados', 'Barbados'), 
        ('Belarus', 'Belarus'), ('Belgium', 'Belgium'), ('Belize', 'Belize'), 
        ('Benin', 'Benin'), ('Bhutan', 'Bhutan'), ('Bolivia', 'Bolivia'), 
        ('Bosnia and Herzegovina', 'Bosnia and Herzegovina'), ('Botswana', 'Botswana'), 
        ('Brazil', 'Brazil'), ('Brunei', 'Brunei'), ('Bulgaria', 'Bulgaria'), 
        ('Burkina Faso', 'Burkina Faso'), ('Burundi', 'Burundi'), ('Cabo Verde', 'Cabo Verde'), 
        ('Cambodia', 'Cambodia'), ('Cameroon', 'Cameroon'), ('Canada', 'Canada'), 
        ('Central African Republic', 'Central African Republic'), ('Chad', 'Chad'), 
        ('Chile', 'Chile'), ('China', 'China'), ('Colombia', 'Colombia'), 
        ('Comoros', 'Comoros'), ('Congo', 'Congo'), ('Congo, Democratic Republic of the', 'Congo, Democratic Republic of the'), 
        ('Costa Rica', 'Costa Rica'), ('Croatia', 'Croatia'), ('Cuba', 'Cuba'), 
        ('Cyprus', 'Cyprus'), ('Czech Republic', 'Czech Republic'), ('Denmark', 'Denmark'), 
        ('Djibouti', 'Djibouti'), ('Dominica', 'Dominica'), ('Dominican Republic', 'Dominican Republic'), 
        ('East Timor', 'East Timor'), ('Ecuador', 'Ecuador'), ('Egypt', 'Egypt'), 
        ('El Salvador', 'El Salvador'), ('Equatorial Guinea', 'Equatorial Guinea'), ('Eritrea', 'Eritrea'), 
        ('Estonia', 'Estonia'), ('Eswatini', 'Eswatini'), ('Ethiopia', 'Ethiopia'), 
        ('Fiji', 'Fiji'), ('Finland', 'Finland'), ('France', 'France'), 
        ('Gabon', 'Gabon'), ('Gambia', 'Gambia'), ('Georgia', 'Georgia'), 
        ('Germany', 'Germany'), ('Ghana', 'Ghana'), ('Greece', 'Greece'), 
        ('Grenada', 'Grenada'), ('Guatemala', 'Guatemala'), ('Guinea', 'Guinea'), 
        ('Guinea-Bissau', 'Guinea-Bissau'), ('Guyana', 'Guyana'), ('Haiti', 'Haiti'), 
        ('Honduras', 'Honduras'), ('Hungary', 'Hungary'), ('Iceland', 'Iceland'), 
        ('India', 'India'), ('Indonesia', 'Indonesia'), ('Iran', 'Iran'), 
        ('Iraq', 'Iraq'), ('Ireland', 'Ireland'), ('Israel', 'Israel'), 
        ('Italy', 'Italy'), ('Jamaica', 'Jamaica'), ('Japan', 'Japan'), 
        ('Jordan', 'Jordan'), ('Kazakhstan', 'Kazakhstan'), ('Kenya', 'Kenya'), 
        ('Kiribati', 'Kiribati'), ('Korea, North', 'Korea, North'), ('Korea, South', 'Korea, South'), 
        ('Kuwait', 'Kuwait'), ('Kyrgyzstan', 'Kyrgyzstan'), ('Laos', 'Laos'), 
        ('Latvia', 'Latvia'), ('Lebanon', 'Lebanon'), ('Lesotho', 'Lesotho'), 
        ('Liberia', 'Liberia'), ('Libya', 'Libya'), ('Liechtenstein', 'Liechtenstein'), 
        ('Lithuania', 'Lithuania'), ('Luxembourg', 'Luxembourg'), ('Madagascar', 'Madagascar'), 
        ('Malawi', 'Malawi'), ('Malaysia', 'Malaysia'), ('Maldives', 'Maldives'), 
        ('Mali', 'Mali'), ('Malta', 'Malta'), ('Marshall Islands', 'Marshall Islands'), 
        ('Mauritania', 'Mauritania'), ('Mauritius', 'Mauritius'), ('Mexico', 'Mexico'), 
        ('Micronesia', 'Micronesia'), ('Moldova', 'Moldova'), ('Monaco', 'Monaco'), 
        ('Mongolia', 'Mongolia'), ('Montenegro', 'Montenegro'), ('Morocco', 'Morocco'), 
        ('Mozambique', 'Mozambique'), ('Myanmar', 'Myanmar'), ('Namibia', 'Namibia'), 
        ('Nauru', 'Nauru'), ('Nepal', 'Nepal'), ('Netherlands', 'Netherlands'), 
        ('New Zealand', 'New Zealand'), ('Nicaragua', 'Nicaragua'), ('Niger', 'Niger'), 
        ('Nigeria', 'Nigeria'), ('North Macedonia', 'North Macedonia'), ('Norway', 'Norway'), 
        ('Oman', 'Oman'), ('Pakistan', 'Pakistan'), ('Palau', 'Palau'), 
        ('Panama', 'Panama'), ('Papua New Guinea', 'Papua New Guinea'), ('Paraguay', 'Paraguay'), 
        ('Peru', 'Peru'), ('Philippines', 'Philippines'), ('Poland', 'Poland'), 
        ('Portugal', 'Portugal'), ('Qatar', 'Qatar'), ('Romania', 'Romania'), 
        ('Russia', 'Russia'), ('Rwanda', 'Rwanda'), ('Saint Kitts and Nevis', 'Saint Kitts and Nevis'), 
        ('Saint Lucia', 'Saint Lucia'), ('Saint Vincent and the Grenadines', 'Saint Vincent and the Grenadines'), 
        ('Samoa', 'Samoa'), ('San Marino', 'San Marino'), ('Sao Tome and Principe', 'Sao Tome and Principe'), 
        ('Saudi Arabia', 'Saudi Arabia'), ('Senegal', 'Senegal'), ('Serbia', 'Serbia'), 
        ('Seychelles', 'Seychelles'), ('Sierra Leone', 'Sierra Leone'), ('Singapore', 'Singapore'), 
        ('Slovakia', 'Slovakia'), ('Slovenia', 'Slovenia'), ('Solomon Islands', 'Solomon Islands'), 
        ('Somalia', 'Somalia'), ('South Africa', 'South Africa'), ('Spain', 'Spain'), 
        ('Sri Lanka', 'Sri Lanka'), ('Sudan', 'Sudan'), ('Suriname', 'Suriname'), 
        ('Sweden', 'Sweden'), ('Switzerland', 'Switzerland'), ('Syria', 'Syria'), 
        ('Taiwan', 'Taiwan'), ('Tajikistan', 'Tajikistan'), ('Tanzania', 'Tanzania'), 
        ('Thailand', 'Thailand'), ('Togo', 'Togo'), ('Tonga', 'Tonga'), 
        ('Trinidad and Tobago', 'Trinidad and Tobago'), ('Tunisia', 'Tunisia'), ('Turkey', 'Turkey'), 
        ('Turkmenistan', 'Turkmenistan'), ('Tuvalu', 'Tuvalu'), ('Uganda', 'Uganda'), 
        ('Ukraine', 'Ukraine'), ('United Arab Emirates', 'United Arab Emirates'), ('United Kingdom', 'United Kingdom'), 
        ('United States', 'United States'), ('Uruguay', 'Uruguay'), ('Uzbekistan', 'Uzbekistan'), 
        ('Vanuatu', 'Vanuatu'), ('Vatican City', 'Vatican City'), ('Venezuela', 'Venezuela'), 
        ('Vietnam', 'Vietnam'), ('Yemen', 'Yemen'), ('Zambia', 'Zambia'), 
        ('Zimbabwe', 'Zimbabwe')
    ]

    if form.validate_on_submit():
        log_with_route(logging.INFO, f"Updating user profile for user ID {user_id}")
        try:
            # Update basic user fields
            user.firstname = form.firstname.data
            user.lastname = form.lastname.data
            user.companyemail = form.companyemail.data
            user.phone = form.phone.data
            user.date_of_birth = form.date_of_birth.data
            user.country = form.country.data
            user.city = form.city.data
            user.state = form.state.data
            user.zip = form.zip.data
            user.address = form.address.data
            user.position = form.position.data

            if form.password.data:
                user.password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')

            # Persist UI preferences
            if hasattr(form, 'devices_default_view'):
                if user.user_preferences is None:
                    user.user_preferences = {}
                if form.devices_default_view.data in ('list', 'card'):
                    user.user_preferences['devices_layout'] = form.devices_default_view.data

            # Handle profile picture upload
            if 'profile_picture' in request.files:
                file = request.files['profile_picture']
                if file and file.filename:
                    # Create user-specific directory
                    user_upload_dir = ensure_user_upload_dir(user.useruuid)
                    
                    # Set filename to logo.png
                    filename = 'logo.png'
                    file_path = os.path.join(user_upload_dir, filename)
                    
                    # Save the file
                    file.save(file_path)
                    
                    # Update the database with the relative path
                    relative_path = os.path.join('images/profilepictures', str(user.useruuid), filename)
                    user.profile_picture = relative_path
                    
                    log_with_route(logging.INFO, f"Profile picture saved at: {file_path}")

            db.session.commit()
            flash('Profile updated successfully.', 'success')
            log_with_route(logging.INFO, f"Profile updated successfully for user ID {user_id}")
            return redirect(url_for('profile_bp.profile'))

        except Exception as e:
            db.session.rollback()
            log_with_route(logging.ERROR, f'Error updating profile for user {user_id}: {e}', exc_info=True)
            flash('An error occurred while updating the profile.', 'danger')

    return render_template('user/index.html', form=form, user=user, user_2fa=user_2fa)