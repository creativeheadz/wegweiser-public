# Filepath: app/forms/group_form.py
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, HiddenField  # Added HiddenField
from wtforms.validators import DataRequired, Length

class GroupForm(FlaskForm):
    groupname = StringField('Group Name', validators=[DataRequired(), Length(min=2, max=100)])
    orgselect = SelectField('Organization', choices=[], validators=[DataRequired()])
    orguuid = HiddenField('Organisation UUID')  # For when we want to preset the org
    submit = SubmitField('Create Group')
    
class AddGroupForm(FlaskForm):
    groupname = StringField('Group Name', validators=[DataRequired(), Length(min=2, max=100)])
    orguuid = HiddenField('Organisation UUID')
    submit = SubmitField('Add Group')