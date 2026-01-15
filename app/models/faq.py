# Filepath: app/models/faq.py
from . import db

class FAQ(db.Model):
    __tablename__ = 'faqs'
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(255), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    order = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        """Convert FAQ object to dictionary for JSON serialization."""
        # Ensure answer is a string, not a Markup object
        answer_str = str(self.answer) if hasattr(self.answer, '__html__') else self.answer
        return {
            'id': self.id,
            'question': self.question,
            'answer': answer_str,
            'order': self.order
        }