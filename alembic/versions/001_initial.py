"""initial

Revision ID: 001
Revises: 
Create Date: 2024-02-12 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create checklist_categories table
    op.create_table(
        'checklist_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create checklist_sections table
    op.create_table(
        'checklist_sections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String()),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['category_id'], ['checklist_categories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create checklist_items table with essential fields
    op.create_table(
        'checklist_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('section_id', sa.Integer(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('is_completed', sa.Boolean(), server_default='false'),
        sa.Column('notes', sa.String()),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_checked', sa.DateTime()),
        sa.Column('checked_by', sa.String()),
        sa.ForeignKeyConstraint(['section_id'], ['checklist_sections.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Insert initial data for Catamaran checklist
    op.execute("""
        INSERT INTO checklist_categories (id, name, description) 
        VALUES 
        (1, 'Catamaran', 'Compliance checklist for catamarans operated by RED Hospitality and Leisure'),
        (2, 'Powerboat', 'Compliance checklist for powerboats operated by RED Hospitality and Leisure'),
        (3, 'Jet Ski', 'Compliance checklist for jet skis operated by RED Hospitality and Leisure'),
        (4, 'Sailing', 'Compliance checklist for sailing vessels operated by RED Hospitality and Leisure')
    """)

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
        op.execute(f"""
            INSERT INTO checklist_sections (id, category_id, name, description, "order") 
            VALUES ({section[0]}, {section[1]}, '{section[2]}', '{section[3]}', {section[0]})
        """)

    # Insert items for each section
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
        op.execute(f"""
            INSERT INTO checklist_items (section_id, description, "order") 
            VALUES ({item[0]}, '{item[1]}', {item[2]})
        """)

def downgrade():
    op.drop_table('checklist_items')
    op.drop_table('checklist_sections')
    op.drop_table('checklist_categories') 