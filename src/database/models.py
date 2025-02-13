from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()

class ChecklistCategory(Base):
    __tablename__ = 'checklist_categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    
    sections = relationship("ChecklistSection", back_populates="category", cascade="all, delete-orphan")

class ChecklistSection(Base):
    __tablename__ = 'checklist_sections'
    
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey('checklist_categories.id', ondelete='CASCADE'), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    order = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    category = relationship("ChecklistCategory", back_populates="sections")
    items = relationship("ChecklistItem", back_populates="section", cascade="all, delete-orphan")

class ChecklistItem(Base):
    __tablename__ = 'checklist_items'
    
    id = Column(Integer, primary_key=True)
    section_id = Column(Integer, ForeignKey('checklist_sections.id', ondelete='CASCADE'), nullable=False)
    description = Column(String, nullable=False)
    is_completed = Column(Boolean, server_default='false')
    notes = Column(String)
    order = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    last_checked = Column(DateTime)
    checked_by = Column(String)
    
    section = relationship("ChecklistSection", back_populates="items") 