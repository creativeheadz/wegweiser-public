# Filepath: app/forms/rss_feed_form.py
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField
from wtforms.validators import DataRequired, URL

class RSSFeedForm(FlaskForm):
    name = StringField('Feed Name', validators=[DataRequired()])
    url = StringField('Feed URL', validators=[DataRequired(), URL()])
    is_active = BooleanField('Active')