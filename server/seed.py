import sys
import os

# Adjust path to import from app directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal, engine
from app.models import Base
from app.models.user import User
from app.models.project import Project
from app.models.endpoint import Endpoint
from app.core.security import get_password_hash

def seed_database():
    print("Wiping existing database tables to synchronize schema changes...")
    Base.metadata.drop_all(bind=engine)
    print("Re-creating clean database tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        users_data = [
            {
                "email": "admin@pulseguard.io",
                "password": "adminpassword123",
                "project_name": "Admin Platform Workspace",
                "endpoints": [
                    {
                        "name": "Production Gatekeeper",
                        "url": "https://httpbin.org/status/200",
                        "method": "GET",
                        "check_interval": 10
                    },
                    {
                        "name": "User Account Service",
                        "url": "https://httpbin.org/status/200",
                        "method": "GET",
                        "check_interval": 30
                    },
                    {
                        "name": "Legacy Auth Sync",
                        "url": "https://httpbin.org/status/500", # Will fail to trigger AI diagnostics
                        "method": "POST",
                        "check_interval": 10
                    }
                ]
            },
            {
                "email": "test@pulseguard.io",
                "password": "testpassword123",
                "project_name": "Developer Testing Sandbox",
                "endpoints": [
                    {
                        "name": "Staging Backend",
                        "url": "https://httpbin.org/status/200",
                        "method": "GET",
                        "check_interval": 10
                    },
                    {
                        "name": "Broken External API",
                        "url": "https://httpbin.org/status/502", # Will fail
                        "method": "GET",
                        "check_interval": 10
                    }
                ]
            }
        ]
        
        for u_data in users_data:
            print(f"Creating user: {u_data['email']}...")
            new_user = User(
                email=u_data["email"],
                hashed_password=get_password_hash(u_data["password"])
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            # 2. Create a default project
            print(f"Creating project '{u_data['project_name']}' for {u_data['email']}...")
            project = Project(
                name=u_data["project_name"],
                description="Seeded default workspace for service monitoring.",
                owner_id=new_user.id
            )
            db.add(project)
            db.commit()
            db.refresh(project)
            
            # 3. Create mock endpoints
            for ep_data in u_data["endpoints"]:
                print(f"Adding endpoint '{ep_data['name']}' to project '{project.name}'...")
                endpoint = Endpoint(
                    name=ep_data["name"],
                    url=ep_data["url"],
                    method=ep_data["method"],
                    check_interval=ep_data["check_interval"],
                    project_id=project.id,
                    is_active=True
                )
                db.add(endpoint)
            db.commit()
            
        print("\n" + "="*50)
        print(" 🎉 Database seeded successfully!")
        print("You can log in with:")
        for u_data in users_data:
            print(f"  - Email:    {u_data['email']}")
            print(f"    Password: {u_data['password']}")
        print("="*50 + "\n")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
