# Filepath: app/forms/register.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from app.models import InviteCodes  # We'll create this model

class RegistrationForm(FlaskForm):
    firstname = StringField('First Name', 
        validators=[DataRequired(), Length(min=1, max=50)], 
        render_kw={"placeholder": "Enter your first name"}
    )
    lastname = StringField('Last Name', 
        validators=[DataRequired(), Length(min=1, max=50)], 
        render_kw={"placeholder": "Enter your last name"}
    )
    companyname = StringField('Company Name', 
        validators=[DataRequired(), Length(min=3, max=100)], 
        render_kw={"placeholder": "Enter your company name"}
    )
    companyemail = StringField('Company Email', 
        validators=[DataRequired(), Email()], 
        render_kw={"placeholder": "Enter your company email", "autocomplete": "username"}
    )
    password = PasswordField('Password', 
        validators=[
            DataRequired(),
            Length(min=8, max=100),
            EqualTo('confirm_password', message='Passwords must match')
        ], 
        render_kw={"placeholder": "Enter your password", "autocomplete": "new-password"}
    )
    confirm_password = PasswordField('Confirm Password',
        validators=[DataRequired()],
        render_kw={"placeholder": "Confirm your password", "autocomplete": "new-password"}
    )
    submit = SubmitField('Register')