"""
Certificate Authority tool implementation.
Mock PKI Certificate Authority environment for sandbox testing.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import random
import hashlib
import uuid

# Import the base template from the parent directory
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from base_module_template import SandboxModule
from mock_data_generator import MockDataGenerator

logger = logging.getLogger(__name__)


class CertificateAuthorityTool(SandboxModule):
    """
    Certificate Authority module implementation for sandbox environment.
    Provides mock PKI functionality for learning and testing.
    """
    
    def __init__(self):
        super().__init__(
            module_id="certificate_authority",
            category="identity",
            display_name="Certificate Authority",
            description="Mock PKI Certificate Authority environment for certificate lifecycle management"
        )
        self.mock_generator = MockDataGenerator()
        self.ca_name = "Sandbox Root CA"
        self.ca_subject = "CN=Sandbox Root CA, O=Sandbox Organization, C=US"
        self.initialize_mock_data()
    
    def get_schema(self) -> Dict[str, Any]:
        """Return the UI schema for this module."""
        from .schema import UI_SCHEMA
        return UI_SCHEMA
    
    def initialize_mock_data(self) -> Dict[str, Any]:
        """Initialize mock Certificate Authority data."""
        mock_data = {
            "initialized_at": datetime.utcnow().isoformat(),
            "module_id": self.module_id,
            "data_version": "1.0.0",
            "ca_info": {
                "ca_name": self.ca_name,
                "ca_subject": self.ca_subject,
                "serial_number": "1A2B3C4D5E6F7890",
                "valid_from": "2020-01-01T00:00:00Z",
                "valid_to": "2030-01-01T00:00:00Z",
                "key_algorithm": "RSA",
                "key_size": 4096,
                "signature_algorithm": "SHA256withRSA",
                "crl_distribution_points": ["http://crl.sandbox.local/sandbox-root-ca.crl"],
                "ocsp_url": "http://ocsp.sandbox.local",
                "is_sandbox": True
            }
        }
        
        # Generate certificate templates
        certificate_templates = [
            {
                "id": "template_001",
                "name": "Web Server",
                "description": "Template for web server certificates",
                "key_usage": ["Digital Signature", "Key Encipherment"],
                "extended_key_usage": ["Server Authentication"],
                "validity_period": 365,
                "key_size": 2048,
                "subject_name_format": "CN={CommonName}, O=Sandbox Organization",
                "san_enabled": True,
                "auto_enrollment": False,
                "status": "Active",
                "created_date": "2020-01-15T10:00:00Z",
                "is_sandbox": True
            },
            {
                "id": "template_002",
                "name": "User Authentication",
                "description": "Template for user authentication certificates",
                "key_usage": ["Digital Signature", "Key Agreement"],
                "extended_key_usage": ["Client Authentication", "Email Protection"],
                "validity_period": 730,
                "key_size": 2048,
                "subject_name_format": "CN={UserPrincipalName}, O=Sandbox Organization",
                "san_enabled": True,
                "auto_enrollment": True,
                "status": "Active",
                "created_date": "2020-01-15T10:00:00Z",
                "is_sandbox": True
            },
            {
                "id": "template_003",
                "name": "Code Signing",
                "description": "Template for code signing certificates",
                "key_usage": ["Digital Signature"],
                "extended_key_usage": ["Code Signing"],
                "validity_period": 1095,
                "key_size": 4096,
                "subject_name_format": "CN={CommonName}, O=Sandbox Organization",
                "san_enabled": False,
                "auto_enrollment": False,
                "status": "Active",
                "created_date": "2020-02-01T09:00:00Z",
                "is_sandbox": True
            },
            {
                "id": "template_004",
                "name": "Device Certificate",
                "description": "Template for device/machine certificates",
                "key_usage": ["Digital Signature", "Key Encipherment"],
                "extended_key_usage": ["Client Authentication", "Server Authentication"],
                "validity_period": 365,
                "key_size": 2048,
                "subject_name_format": "CN={MachineName}.sandbox.local, O=Sandbox Organization",
                "san_enabled": True,
                "auto_enrollment": True,
                "status": "Active",
                "created_date": "2020-03-15T14:30:00Z",
                "is_sandbox": True
            }
        ]
        
        mock_data["certificate_templates"] = certificate_templates
        
        # Generate issued certificates
        certificates = []
        for i in range(50):
            template = random.choice(certificate_templates)
            issue_date = datetime.now() - timedelta(days=random.randint(1, 365))
            expiry_date = issue_date + timedelta(days=template["validity_period"])
            
            # Generate realistic subject names based on template
            if "Web Server" in template["name"]:
                common_name = f"web{i+1:02d}.sandbox.local"
                subject = f"CN={common_name}, O=Sandbox Organization"
            elif "User" in template["name"]:
                user = random.choice(self.mock_generator.first_names)
                common_name = f"{user.lower()}.user@sandbox.local"
                subject = f"CN={common_name}, O=Sandbox Organization"
            elif "Code" in template["name"]:
                common_name = f"Developer {i+1}"
                subject = f"CN={common_name}, O=Sandbox Organization"
            else:
                common_name = f"device{i+1:02d}.sandbox.local"
                subject = f"CN={common_name}, O=Sandbox Organization"
            
            cert = {
                "id": f"cert_{i+1:03d}",
                "serial_number": f"{random.randint(1000000000, 9999999999):010X}",
                "subject": subject,
                "common_name": common_name,
                "template_name": template["name"],
                "template_id": template["id"],
                "issuer": self.ca_subject,
                "issued_date": issue_date.isoformat(),
                "expiry_date": expiry_date.isoformat(),
                "status": self._determine_cert_status(issue_date, expiry_date),
                "key_algorithm": "RSA",
                "key_size": template["key_size"],
                "signature_algorithm": "SHA256withRSA",
                "thumbprint": hashlib.sha1(f"{subject}{issue_date}".encode()).hexdigest().upper(),
                "san_entries": self._generate_san_entries(common_name, template) if template["san_enabled"] else [],
                "revocation_date": None,
                "revocation_reason": None,
                "is_sandbox": True
            }
            
            # Randomly revoke some certificates
            if random.random() < 0.05:  # 5% chance of revocation
                cert["status"] = "Revoked"
                cert["revocation_date"] = (issue_date + timedelta(days=random.randint(30, 300))).isoformat()
                cert["revocation_reason"] = random.choice([
                    "Key Compromise", "CA Compromise", "Affiliation Changed", 
                    "Superseded", "Cessation of Operation"
                ])
            
            certificates.append(cert)
        
        mock_data["certificates"] = certificates
        
        # Generate certificate requests
        certificate_requests = []
        for i in range(15):
            template = random.choice(certificate_templates)
            request_date = datetime.now() - timedelta(days=random.randint(0, 30))
            
            request = {
                "id": f"req_{i+1:03d}",
                "request_id": str(uuid.uuid4()),
                "subject": f"CN=pending{i+1:02d}.sandbox.local, O=Sandbox Organization",
                "template_name": template["name"],
                "template_id": template["id"],
                "requester": f"user{i+1:02d}@sandbox.local",
                "request_date": request_date.isoformat(),
                "status": random.choice(["Pending", "Pending", "Approved", "Denied"]),
                "key_size": template["key_size"],
                "san_entries": [f"pending{i+1:02d}.sandbox.local", f"alt{i+1:02d}.sandbox.local"],
                "approval_date": None,
                "approver": None,
                "denial_reason": None,
                "is_sandbox": True
            }
            
            if request["status"] == "Approved":
                request["approval_date"] = (request_date + timedelta(days=random.randint(1, 5))).isoformat()
                request["approver"] = "ca.admin@sandbox.local"
            elif request["status"] == "Denied":
                request["approval_date"] = (request_date + timedelta(days=random.randint(1, 3))).isoformat()
                request["approver"] = "ca.admin@sandbox.local"
                request["denial_reason"] = random.choice([
                    "Invalid subject name", "Unauthorized requester", "Template not available"
                ])
            
            certificate_requests.append(request)
        
        mock_data["certificate_requests"] = certificate_requests
        
        # Generate CRL status information
        crl_status = {
            "last_publication": (datetime.now() - timedelta(hours=random.randint(1, 24))).isoformat(),
            "next_publication": (datetime.now() + timedelta(hours=random.randint(1, 168))).isoformat(),
            "publication_interval": "Weekly",
            "crl_number": random.randint(1000, 9999),
            "revoked_certificates_count": len([c for c in certificates if c["status"] == "Revoked"]),
            "distribution_points": [
                {
                    "url": "http://crl.sandbox.local/sandbox-root-ca.crl",
                    "status": "Active",
                    "last_update": (datetime.now() - timedelta(hours=2)).isoformat()
                },
                {
                    "url": "ldap://ldap.sandbox.local/CN=Sandbox Root CA,CN=CDP,CN=Public Key Services",
                    "status": "Active", 
                    "last_update": (datetime.now() - timedelta(hours=2)).isoformat()
                }
            ],
            "ocsp_service": {
                "url": "http://ocsp.sandbox.local",
                "status": "Running",
                "response_time_ms": random.randint(50, 200),
                "requests_per_hour": random.randint(100, 1000)
            },
            "is_sandbox": True
        }
        
        mock_data["crl_status"] = crl_status
        
        self.mock_data = mock_data
        return mock_data
    
    def _determine_cert_status(self, issue_date: datetime, expiry_date: datetime) -> str:
        """Determine certificate status based on dates."""
        now = datetime.now()
        
        if expiry_date < now:
            return "Expired"
        elif (expiry_date - now).days <= 30:
            return "Expiring Soon"
        else:
            return "Valid"
    
    def _generate_san_entries(self, common_name: str, template: Dict[str, Any]) -> List[str]:
        """Generate Subject Alternative Name entries."""
        san_entries = [common_name]
        
        if "web" in common_name.lower():
            # Add additional DNS names for web servers
            base_name = common_name.replace("web", "www")
            san_entries.append(base_name)
            san_entries.append(f"api.{common_name.split('.', 1)[1]}")
        elif "device" in common_name.lower():
            # Add IP address for devices
            san_entries.append(f"192.168.1.{random.randint(10, 250)}")
        
        return san_entries
    
    def get_tools(self) -> Dict[str, Any]:
        """Return available tools for Certificate Authority management."""
        return {
            "list_certificates": {
                "name": "list_certificates",
                "description": "List all issued certificates with filtering options",
                "method": self.list_certificates,
                "parameters": {
                    "filter": {"type": "string", "description": "Filter by subject, serial number, or common name"},
                    "status": {"type": "string", "enum": ["All", "Valid", "Expired", "Expiring Soon", "Revoked"]},
                    "template": {"type": "string", "description": "Filter by certificate template"}
                },
                "is_sandbox": True
            },
            "issue_certificate": {
                "name": "issue_certificate",
                "description": "Issue a new certificate from a template",
                "method": self.issue_certificate,
                "parameters": {
                    "template_id": {"type": "string", "required": True},
                    "subject": {"type": "string", "required": True},
                    "san_entries": {"type": "array", "description": "Subject Alternative Names"},
                    "validity_days": {"type": "integer", "description": "Override template validity period"}
                },
                "is_sandbox": True
            },
            "revoke_certificate": {
                "name": "revoke_certificate",
                "description": "Revoke an issued certificate",
                "method": self.revoke_certificate,
                "parameters": {
                    "serial_number": {"type": "string", "required": True},
                    "reason": {"type": "string", "enum": ["Key Compromise", "CA Compromise", "Affiliation Changed", "Superseded", "Cessation of Operation"], "required": True}
                },
                "is_sandbox": True
            },
            "renew_certificate": {
                "name": "renew_certificate",
                "description": "Renew an existing certificate",
                "method": self.renew_certificate,
                "parameters": {
                    "serial_number": {"type": "string", "required": True},
                    "validity_days": {"type": "integer", "description": "Validity period for renewed certificate"}
                },
                "is_sandbox": True
            },
            "validate_certificate": {
                "name": "validate_certificate",
                "description": "Validate certificate chain and status",
                "method": self.validate_certificate,
                "parameters": {
                    "serial_number": {"type": "string", "required": True},
                    "check_revocation": {"type": "boolean", "default": True}
                },
                "is_sandbox": True
            },
            "publish_crl": {
                "name": "publish_crl",
                "description": "Publish Certificate Revocation List",
                "method": self.publish_crl,
                "parameters": {
                    "force_publish": {"type": "boolean", "default": False}
                },
                "is_sandbox": True
            },
            "get_ca_info": {
                "name": "get_ca_info",
                "description": "Get Certificate Authority information and statistics",
                "method": self.get_ca_info,
                "parameters": {},
                "is_sandbox": True
            },
            "manage_templates": {
                "name": "manage_templates",
                "description": "Manage certificate templates",
                "method": self.manage_templates,
                "parameters": {
                    "action": {"type": "string", "enum": ["list", "create", "modify", "disable"], "required": True},
                    "template_id": {"type": "string", "description": "Template ID for modify/disable actions"},
                    "template_data": {"type": "object", "description": "Template configuration for create/modify"}
                },
                "is_sandbox": True
            },
            "process_certificate_request": {
                "name": "process_certificate_request",
                "description": "Approve or deny pending certificate requests",
                "method": self.process_certificate_request,
                "parameters": {
                    "request_id": {"type": "string", "required": True},
                    "action": {"type": "string", "enum": ["approve", "deny"], "required": True},
                    "reason": {"type": "string", "description": "Reason for denial"}
                },
                "is_sandbox": True
            },
            "check_ocsp_status": {
                "name": "check_ocsp_status",
                "description": "Check OCSP service status and certificate revocation",
                "method": self.check_ocsp_status,
                "parameters": {
                    "serial_number": {"type": "string", "description": "Check specific certificate"}
                },
                "is_sandbox": True
            }
        }
    
    def list_certificates(self, **kwargs) -> Dict[str, Any]:
        """List issued certificates with filtering options."""
        try:
            certificates = self.mock_data.get("certificates", [])
            filter_text = kwargs.get("filter", "").lower()
            status_filter = kwargs.get("status", "All")
            template_filter = kwargs.get("template", "")
            
            # Apply filters
            filtered_certs = certificates
            
            if filter_text:
                filtered_certs = [
                    cert for cert in filtered_certs
                    if (filter_text in cert["subject"].lower() or
                        filter_text in cert["serial_number"].lower() or
                        filter_text in cert["common_name"].lower())
                ]
            
            if status_filter != "All":
                filtered_certs = [
                    cert for cert in filtered_certs
                    if cert["status"] == status_filter
                ]
            
            if template_filter:
                filtered_certs = [
                    cert for cert in filtered_certs
                    if template_filter.lower() in cert["template_name"].lower()
                ]
            
            return {
                "tool": "list_certificates",
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "certificates": filtered_certs,
                    "total_count": len(filtered_certs),
                    "filters_applied": {
                        "filter": filter_text,
                        "status": status_filter,
                        "template": template_filter
                    }
                },
                "is_sandbox": True
            }
            
        except Exception as e:
            logger.error(f"Error in list_certificates: {e}")
            return {
                "tool": "list_certificates",
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "is_sandbox": True
            }
    
    def get_ca_info(self, **kwargs) -> Dict[str, Any]:
        """Get Certificate Authority information and statistics."""
        try:
            ca_info = self.mock_data.get("ca_info", {})
            certificates = self.mock_data.get("certificates", [])
            requests = self.mock_data.get("certificate_requests", [])
            
            statistics = {
                "total_certificates": len(certificates),
                "valid_certificates": len([c for c in certificates if c["status"] == "Valid"]),
                "expired_certificates": len([c for c in certificates if c["status"] == "Expired"]),
                "expiring_soon": len([c for c in certificates if c["status"] == "Expiring Soon"]),
                "revoked_certificates": len([c for c in certificates if c["status"] == "Revoked"]),
                "pending_requests": len([r for r in requests if r["status"] == "Pending"]),
                "certificates_issued_this_month": len([
                    c for c in certificates 
                    if (datetime.now() - datetime.fromisoformat(c["issued_date"].replace('Z', '+00:00'))).days <= 30
                ])
            }
            
            return {
                "tool": "get_ca_info",
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "ca_info": ca_info,
                    "statistics": statistics,
                    "crl_status": self.mock_data.get("crl_status", {})
                },
                "is_sandbox": True
            }
            
        except Exception as e:
            logger.error(f"Error in get_ca_info: {e}")
            return {
                "tool": "get_ca_info",
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "is_sandbox": True
            }
    
    # Mock implementations for other tools
    def issue_certificate(self, **kwargs) -> Dict[str, Any]:
        """Mock implementation - issue certificate."""
        return {
            "tool": "issue_certificate",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "message": "Mock certificate issued successfully",
                "serial_number": f"{random.randint(1000000000, 9999999999):010X}",
                "thumbprint": hashlib.sha1(f"mock_cert_{datetime.now()}".encode()).hexdigest().upper()
            },
            "is_sandbox": True
        }
    
    def revoke_certificate(self, **kwargs) -> Dict[str, Any]:
        """Mock implementation - revoke certificate."""
        return {
            "tool": "revoke_certificate",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"message": "Mock certificate revocation completed"},
            "is_sandbox": True
        }
    
    def renew_certificate(self, **kwargs) -> Dict[str, Any]:
        """Mock implementation - renew certificate."""
        return {
            "tool": "renew_certificate",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"message": "Mock certificate renewal completed"},
            "is_sandbox": True
        }
    
    def validate_certificate(self, **kwargs) -> Dict[str, Any]:
        """Mock implementation - validate certificate."""
        return {
            "tool": "validate_certificate",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "valid": True,
                "chain_valid": True,
                "revocation_status": "Good",
                "message": "Mock certificate validation completed"
            },
            "is_sandbox": True
        }
    
    def publish_crl(self, **kwargs) -> Dict[str, Any]:
        """Mock implementation - publish CRL."""
        return {
            "tool": "publish_crl",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"message": "Mock CRL publication completed"},
            "is_sandbox": True
        }
    
    def manage_templates(self, **kwargs) -> Dict[str, Any]:
        """Mock implementation - manage templates."""
        return {
            "tool": "manage_templates",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"message": "Mock template management completed"},
            "is_sandbox": True
        }
    
    def process_certificate_request(self, **kwargs) -> Dict[str, Any]:
        """Mock implementation - process certificate request."""
        return {
            "tool": "process_certificate_request",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"message": "Mock certificate request processing completed"},
            "is_sandbox": True
        }
    
    def check_ocsp_status(self, **kwargs) -> Dict[str, Any]:
        """Mock implementation - check OCSP status."""
        return {
            "tool": "check_ocsp_status",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "ocsp_status": "Good",
                "response_time": f"{random.randint(50, 200)}ms",
                "message": "Mock OCSP status check completed"
            },
            "is_sandbox": True
        }