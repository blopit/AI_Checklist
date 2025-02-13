from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()

class Checklist(Base):
    __tablename__ = 'checklists'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    
    items = relationship("ChecklistItem", back_populates="checklist", cascade="all, delete-orphan")

class ChecklistItem(Base):
    __tablename__ = 'checklist_items'
    
    id = Column(Integer, primary_key=True)
    checklist_id = Column(Integer, ForeignKey('checklists.id', ondelete='CASCADE'), nullable=False)
    description = Column(String, nullable=False)
    is_completed = Column(Boolean, server_default='false')
    created_at = Column(DateTime, server_default=func.now())
    
    checklist = relationship("Checklist", back_populates="items") 