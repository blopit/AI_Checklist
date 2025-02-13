from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get environment
ENV = os.getenv("ENV", "development")
logger.info(f"Running in {ENV} environment")

# SQLite database URL with absolute path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# In production (cPanel), we need to use a path relative to the home directory
if ENV == "production":
    # Get user's home directory (usually something like /home/username in cPanel)
    HOME_DIR = os.path.expanduser("~")
    DATABASE_PATH = os.path.join(HOME_DIR, "checklist.db")
else:
    # In development, use the project directory
    DATABASE_PATH = os.path.join(BASE_DIR, "checklist.db")

DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
logger.info(f"Creating database at: {DATABASE_PATH}")

# Create SQLAlchemy engine with SQLite
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # Needed for SQLite
)

# Create tables
with engine.connect() as conn:
    # Drop existing tables if they exist
    conn.execute(text("DROP TABLE IF EXISTS checklist_items"))
    conn.execute(text("DROP TABLE IF EXISTS checklist_sections"))
    conn.execute(text("DROP TABLE IF EXISTS checklist_categories"))
    
    # Create checklist_categories table
    conn.execute(text("""
        CREATE TABLE checklist_categories (
            id INTEGER PRIMARY KEY,
            name VARCHAR NOT NULL,
            description VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # Create checklist_sections table
    conn.execute(text("""
        CREATE TABLE checklist_sections (
            id INTEGER PRIMARY KEY,
            category_id INTEGER NOT NULL,
            name VARCHAR NOT NULL,
            description VARCHAR,
            "order" INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(category_id) REFERENCES checklist_categories(id) ON DELETE CASCADE
        )
    """))
    
    # Create checklist_items table
    conn.execute(text("""
        CREATE TABLE checklist_items (
            id INTEGER PRIMARY KEY,
            section_id INTEGER NOT NULL,
            description VARCHAR NOT NULL,
            is_completed BOOLEAN DEFAULT FALSE,
            notes VARCHAR,
            "order" INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_checked TIMESTAMP,
            checked_by VARCHAR,
            FOREIGN KEY(section_id) REFERENCES checklist_sections(id) ON DELETE CASCADE
        )
    """))
    
    # Insert categories
    conn.execute(text("""
        INSERT INTO checklist_categories (id, name, description) 
        VALUES 
        (1, 'Catamaran', 'Compliance checklist for catamarans operated by RED Hospitality and Leisure'),
        (2, 'Powerboat', 'Compliance checklist for powerboats operated by RED Hospitality and Leisure'),
        (3, 'Jet Ski', 'Compliance checklist for jet skis operated by RED Hospitality and Leisure'),
        (4, 'Sailing', 'Compliance checklist for sailing vessels operated by RED Hospitality and Leisure')
    """))
    
    # Insert sections
    sections = [
        (1, 1, 'Documentation & Certification', 'Required paperwork and certifications'),
        (2, 1, 'Vessel Condition & Structural Integrity', 'Physical condition of the vessel'),
        (3, 1, 'Safety Equipment', 'Required safety gear and equipment'),
        (4, 1, 'Navigation & Communication', 'Navigation systems and communication devices'),
        (5, 1, 'Crew Requirements & Training', 'Crew certifications and training requirements'),
        (6, 1, 'Environmental & Regulatory Compliance', 'Environmental regulations and requirements'),
        (7, 1, 'Maintenance & Record-Keeping', 'Maintenance logs and record keeping')
    ]
    
    for section in sections:
        conn.execute(text(f"""
            INSERT INTO checklist_sections (id, category_id, name, description, "order") 
            VALUES ({section[0]}, {section[1]}, '{section[2]}', '{section[3]}', {section[0]})
        """))
    
    # Insert items
    items = [
        # Documentation & Certification
        (1, "Valid vessel registration certificate", 1),
        (1, "Proof of ownership (bill of sale or title document)", 2),
        (1, "Current insurance policy documents", 3),
        (1, "Safety inspection certificates", 4),
        (1, "Radio license (if required)", 5),
        
        # Vessel Condition
        (2, "Hull inspection for cracks and corrosion", 1),
        (2, "Bridge deck structural integrity", 2),
        (2, "Engine function and maintenance", 3),
        (2, "Fuel lines and oil levels", 4),
        (2, "Electrical systems check", 5),
        (2, "Steering system operation", 6),
        
        # Safety Equipment
        (3, "USCG-approved life jackets for all passengers", 1),
        (3, "Throwable flotation devices", 2),
        (3, "Fire extinguishers inspection", 3),
        (3, "First aid kit supplies", 4),
        (3, "Emergency tiller/backup steering", 5),
        (3, "Bilge pump functionality", 6),
        
        # Navigation & Communication
        (4, "Navigation lights operational", 1),
        (4, "Compass and GPS functionality", 2),
        (4, "VHF radio test", 3),
        (4, "Emergency communication devices", 4),
        
        # Crew Requirements
        (5, "Valid skipper/captain license", 1),
        (5, "Crew safety training certificates", 2),
        (5, "Emergency drill records", 3),
        
        # Environmental Compliance
        (6, "Waste disposal systems", 1),
        (6, "Environmental regulation compliance", 2),
        (6, "Required safety placards", 3),
        
        # Maintenance
        (7, "Maintenance logbook current", 1),
        (7, "Safety equipment service dates", 2),
        (7, "System updates and checks", 3)
    ]
    
    for item in items:
        conn.execute(text(f"""
            INSERT INTO checklist_items (section_id, description, "order") 
            VALUES ({item[0]}, '{item[1]}', {item[2]})
        """))
    
    conn.commit()

print("Database populated successfully!") 