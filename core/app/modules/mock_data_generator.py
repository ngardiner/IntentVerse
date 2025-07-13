"""
Mock data generator for IntentVerse modules.
Provides realistic but safe mock data for sandbox environments.
"""

import random
import string
from datetime import datetime, timedelta
from typing import Dict, Any, List
import uuid


class MockDataGenerator:
    """
    Generates realistic mock data for various module types.
    All data is clearly marked as mock/sandbox data.
    """
    
    def __init__(self):
        self.first_names = [
            "Alice", "Bob", "Charlie", "Diana", "Edward", "Fiona", "George", "Helen",
            "Ian", "Julia", "Kevin", "Laura", "Michael", "Nancy", "Oliver", "Patricia",
            "Quinn", "Rachel", "Samuel", "Teresa", "Ursula", "Victor", "Wendy", "Xavier",
            "Yvonne", "Zachary"
        ]
        
        self.last_names = [
            "Anderson", "Brown", "Clark", "Davis", "Evans", "Foster", "Garcia", "Harris",
            "Johnson", "King", "Lewis", "Miller", "Nelson", "O'Connor", "Parker", "Quinn",
            "Roberts", "Smith", "Taylor", "Underwood", "Valdez", "Wilson", "Young", "Zhang"
        ]
        
        self.departments = [
            "Engineering", "Marketing", "Sales", "HR", "Finance", "Operations", 
            "IT", "Legal", "Research", "Customer Support", "Product", "Security"
        ]
        
        self.job_titles = [
            "Manager", "Director", "Analyst", "Specialist", "Coordinator", "Lead",
            "Senior", "Junior", "Associate", "Principal", "Vice President", "Engineer"
        ]
        
        self.company_names = [
            "TechCorp", "DataSystems", "CloudWorks", "SecureNet", "InnovateLab",
            "DigitalFlow", "SmartSolutions", "NextGen", "ProActive", "GlobalTech"
        ]
        
        self.server_types = [
            "Web Server", "Database Server", "Application Server", "File Server",
            "Mail Server", "DNS Server", "DHCP Server", "Print Server", "Backup Server"
        ]
        
        self.operating_systems = [
            "Windows Server 2019", "Windows Server 2022", "Ubuntu 20.04", "Ubuntu 22.04",
            "CentOS 7", "CentOS 8", "Red Hat Enterprise Linux 8", "Debian 11"
        ]
        
        self.cloud_services = [
            "EC2", "S3", "RDS", "Lambda", "VPC", "ELB", "CloudFront", "Route53",
            "Virtual Machines", "Storage Accounts", "App Services", "SQL Database",
            "Compute Engine", "Cloud Storage", "Cloud SQL", "Kubernetes Engine"
        ]
    
    def generate_users(self, count: int = 10) -> List[Dict[str, Any]]:
        """Generate mock user data."""
        users = []
        
        for i in range(count):
            first_name = random.choice(self.first_names)
            last_name = random.choice(self.last_names)
            department = random.choice(self.departments)
            job_title = random.choice(self.job_titles)
            
            user = {
                "id": f"user_{i+1:03d}",
                "username": f"{first_name.lower()}.{last_name.lower()}",
                "email": f"{first_name.lower()}.{last_name.lower()}@sandbox.local",
                "first_name": first_name,
                "last_name": last_name,
                "display_name": f"{first_name} {last_name}",
                "department": department,
                "job_title": f"{job_title} - {department}",
                "employee_id": f"EMP{i+1000:04d}",
                "phone": f"+1-555-{random.randint(100, 999):03d}-{random.randint(1000, 9999):04d}",
                "office_location": f"Building {random.choice(['A', 'B', 'C'])}, Floor {random.randint(1, 10)}",
                "manager": f"manager_{random.randint(1, 5):03d}" if i > 5 else None,
                "status": random.choice(["Active", "Active", "Active", "Inactive"]),  # Mostly active
                "created_date": (datetime.now() - timedelta(days=random.randint(30, 365))).isoformat(),
                "last_login": (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat(),
                "groups": random.sample(["Domain Users", "IT Staff", "Managers", "Developers", "Sales Team"], 
                                      random.randint(1, 3)),
                "is_sandbox": True
            }
            users.append(user)
        
        return users
    
    def generate_servers(self, count: int = 10) -> List[Dict[str, Any]]:
        """Generate mock server data."""
        servers = []
        
        for i in range(count):
            server_type = random.choice(self.server_types)
            os = random.choice(self.operating_systems)
            
            server = {
                "id": f"srv_{i+1:03d}",
                "hostname": f"sandbox-{server_type.lower().replace(' ', '-')}-{i+1:02d}",
                "ip_address": f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}",
                "server_type": server_type,
                "operating_system": os,
                "cpu_cores": random.choice([2, 4, 8, 16]),
                "memory_gb": random.choice([4, 8, 16, 32, 64]),
                "disk_gb": random.choice([100, 250, 500, 1000, 2000]),
                "status": random.choice(["Running", "Running", "Running", "Stopped", "Maintenance"]),
                "uptime_days": random.randint(1, 365),
                "last_backup": (datetime.now() - timedelta(days=random.randint(0, 7))).isoformat(),
                "installed_date": (datetime.now() - timedelta(days=random.randint(30, 730))).isoformat(),
                "location": f"Datacenter {random.choice(['East', 'West', 'Central'])}",
                "owner": random.choice(self.departments),
                "maintenance_window": f"{random.choice(['Sunday', 'Saturday'])} {random.randint(1, 6):02d}:00",
                "is_sandbox": True
            }
            servers.append(server)
        
        return servers
    
    def generate_applications(self, count: int = 10) -> List[Dict[str, Any]]:
        """Generate mock application data."""
        applications = []
        app_types = ["Web Application", "Desktop Application", "Mobile App", "Service", "API"]
        
        for i in range(count):
            app_type = random.choice(app_types)
            
            application = {
                "id": f"app_{i+1:03d}",
                "name": f"Sandbox {app_type} {i+1}",
                "type": app_type,
                "version": f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
                "description": f"Mock {app_type.lower()} for testing and demonstration",
                "owner": random.choice(self.departments),
                "status": random.choice(["Active", "Active", "Development", "Deprecated"]),
                "url": f"https://sandbox-app-{i+1}.local" if app_type == "Web Application" else None,
                "port": random.randint(8000, 9999) if app_type in ["Web Application", "API"] else None,
                "database": f"sandbox_db_{i+1}" if random.choice([True, False]) else None,
                "last_deployment": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
                "health_check_url": f"/health" if app_type in ["Web Application", "API"] else None,
                "dependencies": random.sample(["Database", "Cache", "Queue", "Storage", "Auth"], 
                                            random.randint(1, 3)),
                "is_sandbox": True
            }
            applications.append(application)
        
        return applications
    
    def generate_network_devices(self, count: int = 10) -> List[Dict[str, Any]]:
        """Generate mock network device data."""
        devices = []
        device_types = ["Router", "Switch", "Firewall", "Access Point", "Load Balancer"]
        
        for i in range(count):
            device_type = random.choice(device_types)
            
            device = {
                "id": f"net_{i+1:03d}",
                "name": f"sandbox-{device_type.lower()}-{i+1:02d}",
                "type": device_type,
                "ip_address": f"10.0.{random.randint(1, 254)}.{random.randint(1, 254)}",
                "mac_address": ":".join([f"{random.randint(0, 255):02x}" for _ in range(6)]),
                "model": f"{random.choice(['Cisco', 'Juniper', 'HP', 'Dell'])} {device_type} {random.randint(1000, 9999)}",
                "firmware_version": f"{random.randint(1, 9)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
                "location": f"Rack {random.randint(1, 20)}, Unit {random.randint(1, 42)}",
                "status": random.choice(["Online", "Online", "Online", "Offline", "Warning"]),
                "uptime_hours": random.randint(1, 8760),
                "port_count": random.choice([24, 48, 96]) if device_type == "Switch" else random.randint(4, 16),
                "vlan_count": random.randint(1, 10) if device_type in ["Switch", "Router"] else 0,
                "last_config_change": (datetime.now() - timedelta(days=random.randint(1, 90))).isoformat(),
                "is_sandbox": True
            }
            devices.append(device)
        
        return devices
    
    def generate_cloud_resources(self, count: int = 10) -> List[Dict[str, Any]]:
        """Generate mock cloud resource data."""
        resources = []
        providers = ["AWS", "Azure", "GCP"]
        
        for i in range(count):
            provider = random.choice(providers)
            service = random.choice(self.cloud_services)
            
            resource = {
                "id": f"cloud_{i+1:03d}",
                "name": f"sandbox-{service.lower()}-{i+1:02d}",
                "provider": provider,
                "service": service,
                "region": random.choice(["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]),
                "resource_id": f"{provider.lower()}-{uuid.uuid4().hex[:8]}",
                "status": random.choice(["Running", "Running", "Stopped", "Pending"]),
                "instance_type": random.choice(["t3.micro", "t3.small", "t3.medium", "m5.large"]) if service in ["EC2", "Virtual Machines"] else None,
                "storage_gb": random.choice([20, 50, 100, 500]) if service in ["S3", "Storage Accounts"] else None,
                "monthly_cost": round(random.uniform(10, 500), 2),
                "created_date": (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat(),
                "last_modified": (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat(),
                "tags": {
                    "Environment": "Sandbox",
                    "Owner": random.choice(self.departments),
                    "Project": f"Project-{random.randint(1, 10)}"
                },
                "is_sandbox": True
            }
            resources.append(resource)
        
        return resources
    
    def generate_security_events(self, count: int = 20) -> List[Dict[str, Any]]:
        """Generate mock security event data."""
        events = []
        event_types = ["Login Attempt", "File Access", "Network Connection", "Policy Violation", "Malware Detection"]
        severities = ["Low", "Medium", "High", "Critical"]
        
        for i in range(count):
            event_type = random.choice(event_types)
            severity = random.choice(severities)
            
            event = {
                "id": f"sec_{i+1:03d}",
                "timestamp": (datetime.now() - timedelta(minutes=random.randint(0, 10080))).isoformat(),  # Last week
                "event_type": event_type,
                "severity": severity,
                "source_ip": f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}",
                "user": f"user_{random.randint(1, 100):03d}",
                "description": f"Mock {event_type.lower()} event for testing",
                "status": random.choice(["Open", "Investigating", "Resolved", "False Positive"]),
                "assigned_to": random.choice(["Security Team", "IT Admin", "Incident Response"]),
                "resolution_time": random.randint(5, 240) if random.choice([True, False]) else None,
                "is_sandbox": True
            }
            events.append(event)
        
        return events
    
    def generate_sample_scenario(self, scenario_type: str) -> Dict[str, Any]:
        """Generate a complete scenario with related data."""
        scenarios = {
            "security_incident": {
                "name": "Security Incident Response",
                "description": "Simulated security incident for training",
                "users": self.generate_users(20),
                "servers": self.generate_servers(15),
                "security_events": self.generate_security_events(50),
                "incident_timeline": [
                    {"time": "09:00", "event": "Suspicious login detected"},
                    {"time": "09:15", "event": "Multiple failed authentication attempts"},
                    {"time": "09:30", "event": "Security team notified"},
                    {"time": "10:00", "event": "Investigation started"},
                    {"time": "11:30", "event": "Threat contained"}
                ]
            },
            "infrastructure_deployment": {
                "name": "Infrastructure Deployment",
                "description": "New infrastructure deployment scenario",
                "servers": self.generate_servers(25),
                "applications": self.generate_applications(15),
                "network_devices": self.generate_network_devices(10),
                "deployment_plan": [
                    {"phase": 1, "description": "Network infrastructure setup"},
                    {"phase": 2, "description": "Server deployment"},
                    {"phase": 3, "description": "Application installation"},
                    {"phase": 4, "description": "Testing and validation"}
                ]
            },
            "cloud_migration": {
                "name": "Cloud Migration Project",
                "description": "Migration from on-premises to cloud",
                "servers": self.generate_servers(20),
                "cloud_resources": self.generate_cloud_resources(30),
                "applications": self.generate_applications(12),
                "migration_phases": [
                    {"phase": "Assessment", "status": "Completed"},
                    {"phase": "Planning", "status": "Completed"},
                    {"phase": "Migration", "status": "In Progress"},
                    {"phase": "Validation", "status": "Pending"}
                ]
            }
        }
        
        return scenarios.get(scenario_type, {})
    
    def generate_realistic_names(self, count: int) -> List[str]:
        """Generate realistic but clearly fake names."""
        names = []
        for _ in range(count):
            first = random.choice(self.first_names)
            last = random.choice(self.last_names)
            names.append(f"{first} {last}")
        return names
    
    def generate_safe_ip_addresses(self, count: int) -> List[str]:
        """Generate IP addresses in safe/private ranges."""
        ips = []
        ranges = [
            (192, 168),  # 192.168.x.x
            (10, 0),     # 10.0.x.x
            (172, 16)    # 172.16.x.x
        ]
        
        for _ in range(count):
            range_choice = random.choice(ranges)
            ip = f"{range_choice[0]}.{range_choice[1]}.{random.randint(1, 254)}.{random.randint(1, 254)}"
            ips.append(ip)
        
        return ips
    
    def generate_sandbox_domains(self, count: int) -> List[str]:
        """Generate clearly marked sandbox domain names."""
        domains = []
        tlds = [".local", ".sandbox", ".test", ".example"]
        
        for i in range(count):
            company = random.choice(self.company_names).lower()
            tld = random.choice(tlds)
            domain = f"sandbox-{company}-{i+1}{tld}"
            domains.append(domain)
        
        return domains