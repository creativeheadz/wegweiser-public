# Filepath: app/forms/snippet_form.py
# app/forms/snippet_form.py
from flask_wtf import FlaskForm
from wtforms import TextAreaField, StringField, FileField, SelectField, IntegerField
from wtforms.validators import DataRequired, Optional

class SnippetForm(FlaskForm):
    script_content = TextAreaField('Script Content', validators=[DataRequired()])
    script_type = SelectField('Script Type', 
                            choices=[('python', 'Python'), ('powershell', 'PowerShell')],
                            validators=[DataRequired()])
    snippet_name = StringField('Snippet Name', validators=[DataRequired()])
    metalogos_type = StringField('Metalogos Type', validators=[DataRequired()])
    private_key = FileField('Private Key File', validators=[DataRequired()])
    schedule_recurrence = StringField('Schedule Recurrence', 
                                    validators=[Optional()],
                                    description="e.g., 1h, 2d")
    target_devices = SelectField('Target Devices',
                               validators=[DataRequired()],
                               choices=[('ALL', 'All Devices'), 
                                      ('TEST', 'Test Device')])
    max_exec_secs = IntegerField('Maximum Execution Time (seconds)', 
                                validators=[DataRequired()])