# Filepath: app/forms/csv_import_form.py
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import SubmitField
from wtforms.validators import DataRequired, ValidationError

class CsvImportForm(FlaskForm):
    """Form for uploading CSV files for organization/group import"""
    csv_file = FileField('CSV File', validators=[
        FileRequired(message='Please select a CSV file'),
        FileAllowed(['csv'], message='Only CSV files are allowed')
    ])
    submit = SubmitField('Upload and Preview')
