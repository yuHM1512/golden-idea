from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class FileAttachment(Base):
    __tablename__ = "file_attachments"

    id = Column(Integer, primary_key=True, index=True)
    idea_id = Column(Integer, ForeignKey("ideas.id"), nullable=False)

    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)  # UUID-based filename
    file_type = Column(String(50), nullable=False)  # jpg, png, mp4, etc
    file_size = Column(Integer, nullable=False)  # in bytes
    file_path = Column(String(500), nullable=False)  # relative path to file
    storage_provider = Column(String(50), nullable=False, default="local")
    external_file_id = Column(String(255), nullable=True)
    external_folder_id = Column(String(255), nullable=True)
    external_url = Column(String(500), nullable=True)
    mime_type = Column(String(255), nullable=True)

    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    idea = relationship("Idea", back_populates="attachments")
