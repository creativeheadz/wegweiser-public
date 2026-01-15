# Filepath: app/forms/device_forms.py
# app/forms/device_forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired

class ManualDeviceProfilerForm(FlaskForm):
    device_name = StringField('Device Name', validators=[DataRequired()])
    manufacturer = StringField('Manufacturer', validators=[DataRequired()])
    device_type = StringField('Device Type', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    submit = SubmitField('Analyze Device')

class AIQuestionsForm(FlaskForm):
    # This will be dynamically populated
    submit = SubmitField('Submit Answers')

class SaveProfileForm(FlaskForm):
    submit = SubmitField('Save Device Profile')