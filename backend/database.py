from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import json
from datetime import datetime
from config import settings

# Create engine
# SQLite needs connect_args={"check_same_thread": False}
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class HCP(Base):
    __tablename__ = "hcps"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    specialty = Column(String(100), nullable=False)
    clinic = Column(String(150), nullable=True)
    email = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)

    # Relationships
    interactions = relationship("Interaction", back_populates="hcp", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "specialty": self.specialty,
            "clinic": self.clinic,
            "email": self.email,
            "phone": self.phone
        }

class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    hcp_id = Column(Integer, ForeignKey("hcps.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(50), nullable=False)  # Meeting, Email, Call, etc.
    date = Column(String(50), nullable=False)  # YYYY-MM-DD
    time = Column(String(50), nullable=False)  # HH:MM
    attendees = Column(String(255), nullable=True)
    topics_discussed = Column(Text, nullable=True)
    sentiment = Column(String(20), nullable=True)  # Positive, Neutral, Negative
    outcomes = Column(Text, nullable=True)
    follow_up_actions = Column(Text, nullable=True)
    materials_shared = Column(Text, nullable=True)  # JSON-encoded array of strings
    samples_distributed = Column(Text, nullable=True)  # JSON-encoded array of strings
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    hcp = relationship("HCP", back_populates="interactions")

    def to_dict(self):
        return {
            "id": self.id,
            "hcp_id": self.hcp_id,
            "hcp_name": self.hcp.name if self.hcp else "Unknown",
            "type": self.type,
            "date": self.date,
            "time": self.time,
            "attendees": self.attendees,
            "topics_discussed": self.topics_discussed,
            "sentiment": self.sentiment,
            "outcomes": self.outcomes,
            "follow_up_actions": self.follow_up_actions,
            "materials_shared": json.loads(self.materials_shared) if self.materials_shared else [],
            "samples_distributed": json.loads(self.samples_distributed) if self.samples_distributed else []
        }

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Check if we already have HCPs
        if db.query(HCP).count() == 0:
            # Seed HCPs
            hcps = [
                HCP(name="Dr. Amanda Smith", specialty="Oncology", clinic="Metro Cancer Center", email="amanda.smith@metro.org", phone="555-0192"),
                HCP(name="Dr. Rajesh Sharma", specialty="Cardiology", clinic="Apex Heart Institute", email="r.sharma@apexheart.com", phone="555-0143"),
                HCP(name="Dr. Sarah Jenkins", specialty="Pediatrics", clinic="St. Jude Children's Clinic", email="sjenkins@stjude.org", phone="555-0187"),
                HCP(name="Dr. David Cho", specialty="Neurology", clinic="Neurological Specialists", email="dcho@neurospec.com", phone="555-0165"),
                HCP(name="Dr. Elena Rostova", specialty="Endocrinology", clinic="Valley Health Clinic", email="e.rostova@valleyhealth.net", phone="555-0121")
            ]
            db.add_all(hcps)
            db.commit()

            # Seed a sample interaction for Dr. Amanda Smith
            smith = db.query(HCP).filter_by(name="Dr. Amanda Smith").first()
            if smith:
                sample_interaction = Interaction(
                    hcp_id=smith.id,
                    type="Meeting",
                    date="2026-07-15",
                    time="14:30",
                    attendees="Dr. Amanda Smith, Representative John Doe",
                    topics_discussed="Discussed OncoBoost efficacy and patient safety trials. Reviewed clinical endpoints from Phase III trial data.",
                    sentiment="Positive",
                    outcomes="Dr. Smith expressed high interest in the new dosing schedule and requested additional literature on Phase III clinical data.",
                    follow_up_actions="Schedule follow-up meeting in 2 weeks. Send OncoBoost Phase III PDF.",
                    materials_shared=json.dumps(["OncoBoost Phase III PDF Brochure", "Dosing Guide"]),
                    samples_distributed=json.dumps(["OncoBoost 10mg Starter Kit"])
                )
                db.add(sample_interaction)
                db.commit()
    finally:
        db.close()
