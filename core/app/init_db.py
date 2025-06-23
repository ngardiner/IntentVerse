"""
Initialize the database with default data.
This script creates the default admin user if it doesn't exist.
"""

import logging
from sqlmodel import Session, select

from .database import engine
from .models import User, UserGroup, UserGroupLink
from .security import get_password_hash

def init_default_admin():
    """
    Create the default admin user if it doesn't exist.
    Username: admin
    Password: IntentVerse
    """
    with Session(engine) as session:
        # Check if admin user exists
        admin = session.exec(select(User).where(User.username == "admin")).first()
        
        if not admin:
            logging.info("Creating default admin user")
            
            # Create admin user
            hashed_password = get_password_hash("IntentVerse")
            admin = User(
                username="admin",
                hashed_password=hashed_password,
                full_name="Administrator",
                is_admin=True
            )
            
            session.add(admin)
            session.commit()
            session.refresh(admin)
            
            logging.info("Default admin user created successfully")
            
            # Create default groups
            admin_group = UserGroup(name="Administrators", description="Users with full administrative access")
            users_group = UserGroup(name="Users", description="Regular users with standard permissions")
            
            session.add(admin_group)
            session.add(users_group)
            session.commit()
            session.refresh(admin_group)
            
            # Add admin to admin group
            admin_link = UserGroupLink(user_id=admin.id, group_id=admin_group.id)
            session.add(admin_link)
            session.commit()
            
            logging.info("Default groups created successfully")
        else:
            logging.info("Default admin user already exists")

def init_db():
    """
    Initialize the database with default data.
    """
    init_default_admin()