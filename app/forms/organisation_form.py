# Filepath: app/forms/organisation_form.py
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length

class OrganisationForm(FlaskForm):
    orgname = StringField('Organisation Name', validators=[DataRequired(), Length(min=2, max=100)])
    groupname = StringField('Initial Group Name', validators=[DataRequired(), Length(min=2, max=100)])
    submit = SubmitField('Create Organisation')