# Filepath: app/forms/two_factor.py
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp

class TwoFactorForm(FlaskForm):
    token = StringField('Authentication Code', 
        validators=[
            DataRequired(),
            Length(min=6, max=6),
            Regexp('^[0-9]*$', message='Code must contain only numbers')
        ],
        render_kw={"placeholder": "Enter 6-digit code", "autocomplete": "one-time-code"}
    )
    submit = SubmitField('Verify')

class BackupCodeForm(FlaskForm):
    code = StringField('Backup Code', 
        validators=[
            DataRequired(),
            Length(min=11, max=11),
            Regexp(r'^[A-Z0-9\-]+$', message='Backup code must contain only letters, numbers, and hyphens.')
        ],
        render_kw={"placeholder": "Enter backup code"}
    )
    submit = SubmitField('Verify')

class EnableTwoFactorForm(FlaskForm):
    token = StringField('Verification Code',
        validators=[
            DataRequired(),
            Length(min=6, max=6),
            Regexp('^[0-9]*$', message='Code must contain only numbers')
        ],
        render_kw={"placeholder": "Enter 6-digit code from authenticator app"}
    )
    submit = SubmitField('Enable 2FA')