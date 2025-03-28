"""
NetBox_backend.py
=================
A Python class to interact with NetBox using pynetbox.
"""

import logging
import pynetbox
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any
from functools import wraps

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InterfaceTypes(Enum):
    QSFPP = "40gbase-x-qsfpp"
    SFP = "1000base-x-sfp"
    SFP_PLUS = "10gbase-x-sfpp"
    QSFP28 = "100gbase-x-qsfp28"

class DeviceStatus(Enum):
    ACTIVE = "active"
    PLANNED = "planned"
    OFFLINE = "offline"
    FAILED = "failed"

def error_handler(func):
    """Décorateur pour la gestion uniforme des erreurs"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"{func.__name__} failed: {str(e)}")
            return None
    return wrapper

class NetBoxBackend:
    def __init__(self, url: str, token: str, verify_ssl: bool = True):
        """
        Initializes the NetBox API connection.
        
        Args:
            url (str): NetBox instance URL
            token (str): API token for authentication
            verify_ssl (bool): Whether to verify SSL certificates
        """
        self.url = url
        self.token = token
        self.nb = pynetbox.api(self.url, token=self.token)
        self.nb.http_session.verify = verify_ssl

    def validate_input(self, **kwargs) -> bool:
        """
        Validates input parameters.
        
        Args:
            **kwargs: Key-value pairs to validate
            
        Returns:
            bool: True if all inputs are valid
            
        Raises:
            ValueError: If any input is invalid
        """
        for key, value in kwargs.items():
            if value is None or (isinstance(value, str) and not value.strip()):
                raise ValueError(f"Invalid {key}: {value}")
        return True

    def check_connection(self) -> bool:
        """Verifies connection to NetBox instance"""
        try:
            self.nb.status()
            return True
        except Exception as e:
            logger.error(f"Connection check failed: {e}")
            return False

    ## ----------------------------------
    ## TENANTS MANAGEMENT
    ## ----------------------------------

    @error_handler
    def get_tenants(self) -> List:
        """Returns all tenants in NetBox."""
        return list(self.nb.tenancy.tenants.all())

    @error_handler
    def create_tenant(self, name: str, slug: str):
        """
        Creates a new tenant in NetBox.
        
        Args:
            name (str): Tenant name
            slug (str): URL-friendly slug
        """
        self.validate_input(name=name, slug=slug)
        return self.nb.tenancy.tenants.create({"name": name, "slug": slug})

    ## ----------------------------------
    ## SITES MANAGEMENT
    ## ----------------------------------

    @error_handler
    def get_sites(self) -> List:
        """Returns all sites in NetBox."""
        return list(self.nb.dcim.sites.all())

    @error_handler
    def create_site(self, name: str, slug: str, status: str = "active"):
        """
        Creates a new site in NetBox.
        
        Args:
            name (str): Site name
            slug (str): URL-friendly slug
            status (str): Site status
        """
        self.validate_input(name=name, slug=slug)
        return self.nb.dcim.sites.create({
            "name": name,
            "slug": slug,
            "status": status
        })

    ## ----------------------------------
    ## DEVICE MANAGEMENT
    ## ----------------------------------

    @error_handler
    def get_device_type_by_slug(self, slug: str) -> Optional[Dict]:
        """Returns a device type by slug."""
        self.validate_input(slug=slug)
        return self.nb.dcim.device_types.get(slug=slug)

    @error_handler
    def get_device_role(self, slug: str) -> Optional[Dict]:
        """Returns a device role by slug."""
        self.validate_input(slug=slug)
        return self.nb.dcim.device_roles.get(slug=slug)

    def device_exists(self, name: str) -> bool:
        """Checks if a device exists by name."""
        return bool(self.nb.dcim.devices.get(name=name))

    @error_handler
    def get_device_by_name(self, name: str) -> Optional[Dict]:
        """Returns a device by name."""
        self.validate_input(name=name)
        return self.nb.dcim.devices.get(name=name)

    @error_handler
    def create_device(self, name: str, device_type_slug: str, role_id: int, 
                     site_id: int, location_id: Optional[int] = None, 
                     status: str = DeviceStatus.ACTIVE.value):
        """
        Creates a device in NetBox if it doesn't already exist.
        
        Args:
            name (str): Device name
            device_type_slug (str): Device type slug
            role_id (int): Role ID
            site_id (int): Site ID
            location_id (Optional[int]): Location ID
            status (str): Device status
            
        Returns:
            Device object if successful, None otherwise
        """
        self.validate_input(name=name, device_type_slug=device_type_slug)
        
        if self.device_exists(name):
            return self.get_device_by_name(name)

        device_type = self.get_device_type_by_slug(device_type_slug)
        if not device_type:
            logger.error(f"Device type '{device_type_slug}' not found")
            return None
                
        try:
            device_data = {
                "name": name,
                "device_type": device_type.id,
                "role": role_id,
                "site": site_id,
                "location": location_id,
                "status": status
            }
            
            # Debug
            logger.debug("Creating device with data:")
            for key, value in device_data.items():
                logger.debug(f"{key}: {value} (type: {type(value)})")
            
            return self.nb.dcim.devices.create(device_data)
        
        except (ValueError, AttributeError) as e:
            logger.error(f"Error preparing device data: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error creating device: {str(e)}")
            return None

    ## ----------------------------------
    ## INTERFACES & CABLING
    ## ----------------------------------

    @error_handler
    def get_or_create_interface(self, device_id: int, if_name: str, 
                              if_type: str = InterfaceTypes.QSFPP.value):
        """
        Retrieves or creates an interface on a given device.
        
        Args:
            device_id (int): Device ID
            if_name (str): Interface name
            if_type (str): Interface type
        """
        self.validate_input(if_name=if_name)
        
        intf = self.nb.dcim.interfaces.get(device_id=device_id, name=if_name)
        if intf:
            return intf
            
        return self.nb.dcim.interfaces.create({
            "device": device_id,
            "name": if_name,
            "type": if_type,
        })

    @error_handler
    def create_cable_if_not_exists(self, intf_a, intf_b):
        """
        Creates a cable between two interfaces if it doesn't exist.
        
        Args:
            intf_a: First interface object
            intf_b: Second interface object
        """
        if not all([intf_a, intf_b]):
            logger.warning("Missing interfaces to create cable")
            return None

        return self.nb.dcim.cables.create({
            "a_terminations": [{"object_type": "dcim.interface", "object_id": intf_a.id}],
            "b_terminations": [{"object_type": "dcim.interface", "object_id": intf_b.id}],
            "status": "connected",
        })

    ## ----------------------------------
    ## NETWORK MANAGEMENT
    ## ----------------------------------

    @error_handler
    def create_vlan(self, vlan_id: int, vlan_name: str, slug: str, tenant_id: str):
        """Creates a VLAN in NetBox."""
        self.validate_input(vlan_name=vlan_name, slug=slug)
        return self.nb.ipam.vlans.create({
            "vid": vlan_id,
            "name": vlan_name,
            "slug": slug,
            "tenant": tenant_id,
        })

    @error_handler
    def create_l2vpn(self, vni_id: int, vpn_name: str, slug: str, tenant_id: str):
        """Creates an L2VPN in NetBox."""
        self.validate_input(vpn_name=vpn_name, slug=slug)
        return self.nb.vpn.l2vpns.create({
            "name": vpn_name,
            "slug": slug,
            "type": "vxlan-evpn",
            "tenant": tenant_id,
            "identifier": vni_id
        })

    @error_handler
    def create_vxlan_termination(self, l2vpn_id: int, assigned_object_type: str, 
                                assigned_object_id: int):
        """Creates a VXLAN termination for L2VPN."""
        return self.nb.vpn.l2vpn_terminations.create({
            "l2vpn": l2vpn_id,
            "assigned_object_type": assigned_object_type,
            "assigned_object_id": assigned_object_id
        })

    @error_handler
    def allocate_prefix(self, parent_prefix, prefix_length: int, 
                       site_id: int, role_id: int, tenant_id: int):
        """
        Allocates a child subnet from a parent prefix.
        
        Args:
            parent_prefix: Parent prefix object
            prefix_length (int): Length of the child prefix
            site_id (int): Site ID
            role_id (int): Role ID
            tenant_id (int): Tenant ID
        """
        return parent_prefix.available_prefixes.create({
            "prefix_length": prefix_length,
            "site": site_id,
            "role": role_id,
            "tenant": tenant_id
        })

    @error_handler
    def assign_ip_to_interface(self, interface, ip_address: str, 
                             status: str = DeviceStatus.ACTIVE.value):
        """Assigns an IP address to an interface."""
        self.validate_input(ip_address=ip_address)
        return self.nb.ipam.ip_addresses.create({
            "address": ip_address,
            "assigned_object_id": interface.id,
            "assigned_object_type": "dcim.interface",
            "status": status,
        })

    @error_handler
    def get_available_ips_in_prefix(self, prefix) -> List:
        """Fetches available IPs within a prefix."""
        if not hasattr(prefix, "available_ips"):
            logger.error(f"Invalid prefix object: {prefix}")
            return []
        return list(prefix.available_ips.list())

    @error_handler
    def save_custom_fields(self, device, fields: Dict[str, Any]) -> bool:
        """
        Saves custom fields for a device.
        
        Args:
            device: Device object
            fields (Dict[str, Any]): Custom fields to save
        """
        for key, value in fields.items():
            device.custom_fields[key] = value
        device.save()
        return True

    @error_handler
    def cleanup_unused_devices(self, older_than_days: int = 30):
        """
        Removes devices that haven't been updated in specified days.
        
        Args:
            older_than_days (int): Number of days of inactivity
        """
        cutoff = datetime.now() - timedelta(days=older_than_days)
        devices = self.nb.dcim.devices.filter(last_updated__lt=cutoff)
        for device in devices:
            device.delete()