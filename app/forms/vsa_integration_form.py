# Filepath: app/forms/vsa_integration_form.py
# app/forms/vsa_integration_form.py

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, URL

class VSAConnectionForm(FlaskForm):
    endpoint = StringField('Endpoint', validators=[DataRequired(), URL()], 
                           render_kw={"placeholder": "https://your-vsa-instance.com/api/v3/"})
    token_id = StringField('Token ID', validators=[DataRequired()],
                           render_kw={"placeholder": "Enter your Token ID"})
    token_secret = StringField('Token Secret', validators=[DataRequired()],
                               render_kw={"placeholder": "Enter your Token Secret"})
    submit = SubmitField('Verify Connection')

class VSASelectionForm(FlaskForm):
    submit = SubmitField('Import Selected Items')

class VSAConfirmationForm(FlaskForm):
    submit = SubmitField('Confirm Import')

class VSASelectionForm(FlaskForm):
    submit = SubmitField('Next')