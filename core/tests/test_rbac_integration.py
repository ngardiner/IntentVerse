"""
Test RBAC integration and functionality.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import User, Role, Permission, UserRoleLink, RolePermissionLink
from app.rbac import PermissionChecker, initialize_rbac_system
from app.security import get_password_hash


def test_permission_checker_basic_functionality(session: Session):
    """Test basic permission checking functionality."""
    # Initialize RBAC system
    initialize_rbac_system(session)
    
    # Create a test user
    user = User(
        username="testuser",
        hashed_password=get_password_hash("testpass"),
        email="test@example.com"
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Get the user role and assign it to the user
    user_role = session.exec(select(Role).where(Role.name == "user")).first()
    assert user_role is not None
    
    user_role_link = UserRoleLink(user_id=user.id, role_id=user_role.id)
    session.add(user_role_link)
    session.commit()
    
    # Test permission checking
    checker = PermissionChecker(session)
    
    # User should have basic permissions
    assert checker.has_permission(user, "users.read")
    assert checker.has_permission(user, "groups.read")
    assert checker.has_permission(user, "timeline.read")
    
    # User should not have admin permissions
    assert not checker.has_permission(user, "users.create")
    assert not checker.has_permission(user, "admin.all")


def test_admin_permissions(session: Session):
    """Test admin user permissions."""
    # Initialize RBAC system
    initialize_rbac_system(session)
    
    # Create an admin user
    admin_user = User(
        username="admin",
        hashed_password=get_password_hash("adminpass"),
        email="admin@example.com",
        is_admin=True
    )
    session.add(admin_user)
    session.commit()
    session.refresh(admin_user)
    
    # Get the admin role and assign it to the user
    admin_role = session.exec(select(Role).where(Role.name == "admin")).first()
    assert admin_role is not None
    
    admin_role_link = UserRoleLink(user_id=admin_user.id, role_id=admin_role.id)
    session.add(admin_role_link)
    session.commit()
    
    # Test permission checking
    checker = PermissionChecker(session)
    
    # Admin should have all permissions
    assert checker.has_permission(admin_user, "admin.all")
    assert checker.has_permission(admin_user, "users.create")
    assert checker.has_permission(admin_user, "users.delete")
    assert checker.has_permission(admin_user, "filesystem.write")
    assert checker.has_permission(admin_user, "database.execute")
    
    # Test wildcard permissions
    assert checker.has_permission(admin_user, "any.random.permission")


def test_wildcard_permissions(session: Session):
    """Test wildcard permission functionality."""
    # Initialize RBAC system
    initialize_rbac_system(session)
    
    # Create a test user
    user = User(
        username="fsuser",
        hashed_password=get_password_hash("testpass"),
        email="fsuser@example.com"
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Get the filesystem_manager role and assign it to the user
    fs_role = session.exec(select(Role).where(Role.name == "filesystem_manager")).first()
    assert fs_role is not None
    
    user_role_link = UserRoleLink(user_id=user.id, role_id=fs_role.id)
    session.add(user_role_link)
    session.commit()
    
    # Test permission checking
    checker = PermissionChecker(session)
    
    # User should have filesystem wildcard permissions
    assert checker.has_permission(user, "filesystem.read")
    assert checker.has_permission(user, "filesystem.write")
    assert checker.has_permission(user, "filesystem.delete")
    assert checker.has_permission(user, "filesystem.anything")
    
    # User should not have other permissions
    assert not checker.has_permission(user, "database.read")
    assert not checker.has_permission(user, "users.create")


def test_rbac_api_endpoints(client: TestClient, session: Session):
    """Test RBAC management API endpoints."""
    # Initialize RBAC system
    initialize_rbac_system(session)
    
    # Create an admin user and get token
    admin_user = User(
        username="admin_api",
        hashed_password=get_password_hash("adminpass"),
        email="admin_api@example.com",
        is_admin=True
    )
    session.add(admin_user)
    session.commit()
    session.refresh(admin_user)
    
    # Assign admin role
    admin_role = session.exec(select(Role).where(Role.name == "admin")).first()
    admin_role_link = UserRoleLink(user_id=admin_user.id, role_id=admin_role.id)
    session.add(admin_role_link)
    session.commit()
    
    # Login to get token
    login_response = client.post("/auth/login", data={
        "username": "admin_api",
        "password": "adminpass"
    })
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test getting roles
    response = client.get("/roles/", headers=headers)
    assert response.status_code == 200
    roles = response.json()
    assert len(roles) > 0
    assert any(role["name"] == "admin" for role in roles)
    
    # Test getting permissions
    response = client.get("/permissions/", headers=headers)
    assert response.status_code == 200
    permissions = response.json()
    assert len(permissions) > 0
    assert any(perm["name"] == "admin.all" for perm in permissions)
    
    # Test creating a new role
    new_role_data = {
        "name": "test_role",
        "description": "A test role"
    }
    response = client.post("/roles/", json=new_role_data, headers=headers)
    assert response.status_code == 200
    created_role = response.json()
    assert created_role["name"] == "test_role"
    assert created_role["description"] == "A test role"
    assert not created_role["is_system_role"]


def test_permission_denied_for_regular_user(client: TestClient, session: Session):
    """Test that regular users are denied access to admin endpoints."""
    # Initialize RBAC system
    initialize_rbac_system(session)
    
    # Create a regular user
    user = User(
        username="regular_user",
        hashed_password=get_password_hash("userpass"),
        email="user@example.com"
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Assign user role
    user_role = session.exec(select(Role).where(Role.name == "user")).first()
    user_role_link = UserRoleLink(user_id=user.id, role_id=user_role.id)
    session.add(user_role_link)
    session.commit()
    
    # Login to get token
    login_response = client.post("/auth/login", data={
        "username": "regular_user",
        "password": "userpass"
    })
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test that user cannot create other users
    new_user_data = {
        "username": "another_user",
        "password": "password123"
    }
    response = client.post("/users/", json=new_user_data, headers=headers)
    assert response.status_code == 403
    
    # Test that user cannot access roles
    response = client.get("/roles/", headers=headers)
    assert response.status_code == 403
    
    # Test that user cannot create roles
    new_role_data = {
        "name": "unauthorized_role",
        "description": "Should not be created"
    }
    response = client.post("/roles/", json=new_role_data, headers=headers)
    assert response.status_code == 403


def test_user_can_view_own_details(client: TestClient, session: Session):
    """Test that users can view their own details."""
    # Initialize RBAC system
    initialize_rbac_system(session)
    
    # Create a regular user
    user = User(
        username="self_view_user",
        hashed_password=get_password_hash("userpass"),
        email="selfview@example.com"
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Assign user role
    user_role = session.exec(select(Role).where(Role.name == "user")).first()
    user_role_link = UserRoleLink(user_id=user.id, role_id=user_role.id)
    session.add(user_role_link)
    session.commit()
    
    # Login to get token
    login_response = client.post("/auth/login", data={
        "username": "self_view_user",
        "password": "userpass"
    })
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test that user can view their own details
    response = client.get("/users/me", headers=headers)
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["username"] == "self_view_user"
    assert "roles" in user_data
    assert "permissions" in user_data
    
    # Test that user can view their own details by ID
    response = client.get(f"/users/{user.id}", headers=headers)
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["username"] == "self_view_user"