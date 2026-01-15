# Filepath: app/forms/chat_form.py
# /app/forms/chat_form.py

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

class ChatForm(FlaskForm):
    message = StringField('Message', validators=[DataRequired()], render_kw={"placeholder": "Type your message"})
    submit = SubmitField('Send')
