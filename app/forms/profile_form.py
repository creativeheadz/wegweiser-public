# Filepath: app/forms/profile_form.py
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, EmailField, TextAreaField, SelectField, DateField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional

class ProfileForm(FlaskForm):
    firstname = StringField('First Name', validators=[DataRequired(), Length(max=50)], render_kw={"autocomplete": "given-name"})
    lastname = StringField('Last Name', validators=[DataRequired(), Length(max=50)], render_kw={"autocomplete": "family-name"})
    companyemail = EmailField('Email', validators=[DataRequired(), Email()], render_kw={"autocomplete": "email"})
    phone = StringField('Phone', validators=[Length(max=15)], render_kw={"autocomplete": "tel"})
    date_of_birth = DateField('Date of Birth', format='%Y-%m-%d', validators=[Optional()], render_kw={"autocomplete": "bday"})
    country = SelectField('Country', choices=[], validators=[Optional()], render_kw={"autocomplete": "country"})
    city = StringField('City', validators=[Length(max=100)], render_kw={"autocomplete": "address-level2"})
    state = StringField('State', validators=[Length(max=100)], render_kw={"autocomplete": "address-level1"})
    zip = StringField('Zip', validators=[Length(max=10)], render_kw={"autocomplete": "postal-code"})
    address = TextAreaField('Address', validators=[Length(max=200)], render_kw={"autocomplete": "street-address"})
    position = StringField('Position', validators=[Optional(), Length(max=100)], render_kw={"autocomplete": "organization-title"})
    password = PasswordField('Password', validators=[Optional(), Length(min=8)], render_kw={"autocomplete": "new-password"})
    profile_picture = FileField('Profile Picture', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])

    devices_default_view = SelectField(
        'Devices Default View',
        choices=[('card', 'Card View'), ('list', 'List View')],
        validators=[Optional()]
    )
    submit = SubmitField('Update Profile')