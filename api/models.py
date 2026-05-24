from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

class Alert(db.Model):
    __tablename__ = 'alerts'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    severity = db.Column(db.String(50), nullable=False)
    honeypot_name = db.Column(db.String(100), nullable=False)
    honeypot_type = db.Column(db.String(100))
    source_ip = db.Column(db.String(45), nullable=False)
    event_type = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    raw_data = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'severity': self.severity,
            'honeypot_name': self.honeypot_name,
            'honeypot_type': self.honeypot_type,
            'source_ip': self.source_ip,
            'event_type': self.event_type,
            'description': self.description,
            'raw_data': self.raw_data
        }
