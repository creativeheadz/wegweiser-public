# Filepath: app/models/guided_tours.py
import uuid
import time
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from . import db


class GuidedTour(db.Model):
    """
    Model for storing guided tour configurations for different pages.
    Allows centralized management of tour content across the application.
    """
    __tablename__ = 'guided_tours'
    
    # Primary key
    tour_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Page identification
    page_identifier = db.Column(db.String(100), nullable=False, unique=True)  # e.g., 'quickstart', 'dashboard', 'devices'
    page_title = db.Column(db.String(255), nullable=False)  # Human-readable page name
    
    # Tour metadata
    tour_name = db.Column(db.String(255), nullable=False)
    tour_description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    auto_start = db.Column(db.Boolean, default=False, nullable=False)  # Whether to auto-start on first visit
    
    # Tour configuration
    tour_config = db.Column(JSONB, nullable=True)  # Shepherd.js configuration options
    steps = db.Column(JSONB, nullable=False)  # Array of tour steps
    
    # Metadata
    created_at = db.Column(db.BigInteger, nullable=False, default=lambda: int(time.time()))
    updated_at = db.Column(db.BigInteger, nullable=False, default=lambda: int(time.time()))
    created_by = db.Column(UUID(as_uuid=True), nullable=True)  # User who created the tour
    
    # Version control
    version = db.Column(db.Integer, default=1, nullable=False)
    
    def __repr__(self):
        return f'<GuidedTour {self.page_identifier}: {self.tour_name}>'
    
    def to_dict(self):
        """Convert tour to dictionary for JSON serialization."""
        return {
            'tour_id': str(self.tour_id),
            'page_identifier': self.page_identifier,
            'page_title': self.page_title,
            'tour_name': self.tour_name,
            'tour_description': self.tour_description,
            'is_active': self.is_active,
            'auto_start': self.auto_start,
            'tour_config': self.tour_config or {},
            'steps': self.steps or [],
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'version': self.version
        }
    
    def update_steps(self, steps_data):
        """Update tour steps and increment version."""
        self.steps = steps_data
        self.updated_at = int(time.time())
        self.version += 1
        db.session.commit()
    
    def update_config(self, config_data):
        """Update tour configuration."""
        self.tour_config = config_data
        self.updated_at = int(time.time())
        db.session.commit()
    
    @classmethod
    def get_by_page(cls, page_identifier):
        """Get active tour for a specific page."""
        return cls.query.filter_by(
            page_identifier=page_identifier,
            is_active=True
        ).first()
    
    @classmethod
    def get_all_active(cls):
        """Get all active tours."""
        return cls.query.filter_by(is_active=True).all()


class TourProgress(db.Model):
    """
    Model for tracking user progress through guided tours.
    Stores completion status and step progress for each user.
    """
    __tablename__ = 'tour_progress'
    
    # Primary key
    progress_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign keys
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('accounts.useruuid'), nullable=False)
    tour_id = db.Column(UUID(as_uuid=True), db.ForeignKey('guided_tours.tour_id'), nullable=False)
    
    # Progress tracking
    completed_steps = db.Column(JSONB, default=list, nullable=False)  # Array of completed step IDs
    is_completed = db.Column(db.Boolean, default=False, nullable=False)
    last_step = db.Column(db.String(100), nullable=True)  # ID of last viewed step
    
    # Timestamps
    started_at = db.Column(db.BigInteger, nullable=False, default=lambda: int(time.time()))
    completed_at = db.Column(db.BigInteger, nullable=True)
    last_accessed = db.Column(db.BigInteger, nullable=False, default=lambda: int(time.time()))
    
    # Relationships
    tour = relationship('GuidedTour', backref='progress_records')
    
    # Unique constraint to ensure one progress record per user per tour
    __table_args__ = (
        db.UniqueConstraint('user_id', 'tour_id', name='_user_tour_progress_uc'),
    )
    
    def __repr__(self):
        return f'<TourProgress {self.user_id}: {self.tour_id}>'
    
    def mark_step_complete(self, step_id):
        """Mark a specific step as completed."""
        if self.completed_steps is None:
            self.completed_steps = []
        
        if step_id not in self.completed_steps:
            self.completed_steps.append(step_id)
            self.last_step = step_id
            self.last_accessed = int(time.time())
            
            # Check if all steps are completed
            tour = GuidedTour.query.get(self.tour_id)
            if tour and tour.steps:
                total_steps = len(tour.steps)
                if len(self.completed_steps) >= total_steps:
                    self.is_completed = True
                    self.completed_at = int(time.time())
            
            db.session.commit()
    
    def reset_progress(self):
        """Reset tour progress for the user."""
        self.completed_steps = []
        self.is_completed = False
        self.last_step = None
        self.completed_at = None
        self.last_accessed = int(time.time())
        db.session.commit()
    
    @classmethod
    def get_user_progress(cls, user_id, tour_id):
        """Get progress for a specific user and tour."""
        return cls.query.filter_by(user_id=user_id, tour_id=tour_id).first()
    
    @classmethod
    def create_or_update(cls, user_id, tour_id):
        """Create new progress record or return existing one."""
        progress = cls.get_user_progress(user_id, tour_id)
        if not progress:
            progress = cls(user_id=user_id, tour_id=tour_id)
            db.session.add(progress)
            db.session.commit()
        else:
            progress.last_accessed = int(time.time())
            db.session.commit()
        return progress
