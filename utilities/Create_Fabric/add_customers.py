#!/usr/bin/env python3
"""
add_customer.py
==============
Script pour ajouter un nouveau client dans NetBox avec :
- Création du tenant
- Attribution des locations
- Allocation d'un préfixe /24
- Configuration VXLAN/VLAN
- Attribution des interfaces clients
"""

import sys
import logging
from typing import List, Optional
from dataclasses import dataclass

from helpers.netbox_backend import NetBoxBackend

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class CustomerConfig:
    """Configuration du client"""
    name: str
    slug: str
    vlan_id: int
    vni_id: int
    locations: List[dict]

class CustomerProvisioner:
    """Gère la provision d'un nouveau client dans NetBox"""

    def __init__(self, netbox: NetBoxBackend):
        self.netbox = netbox
        self.config: Optional[CustomerConfig] = None
        self.tenant: Optional[dict] = None
        self.vlan: Optional[dict] = None
        self.l2vpn: Optional[dict] = None

    def get_user_input(self) -> CustomerConfig:
        """Récupère les informations du client depuis l'utilisateur"""
        try:
            # Informations de base
            customer_name = input("Enter Customer Name: ").strip()
            if not customer_name:
                raise ValueError("Customer name is required")

            customer_slug = customer_name.lower().replace(" ", "-")
            
            # VLAN et VNI
            vlan_id = int(input("Enter VLAN ID (1-4094): ").strip())
            if not 1 <= vlan_id <= 4094:
                raise ValueError("VLAN ID must be between 1 and 4094")

            vni_id = int(input("Enter VNI ID: ").strip())
            if vni_id < 1:
                raise ValueError("VNI ID must be positive")

            # Sélection des locations
            locations = list(self.netbox.nb.dcim.locations.all())
            if not locations:
                raise ValueError("No locations found in NetBox")

            print("\nAvailable Locations:")
            for idx, loc in enumerate(locations):
                print(f"{idx}: {loc.name}")

            indices = input("Select locations (comma-separated indices): ").strip()
            selected_locations = [
                loc for i, loc in enumerate(locations)
                if str(i) in indices.split(",")
            ]

            if not selected_locations:
                raise ValueError("At least one location must be selected")

            return CustomerConfig(
                name=customer_name,
                slug=customer_slug,
                vlan_id=vlan_id,
                vni_id=vni_id,
                locations=selected_locations
            )

        except ValueError as e:
            logger.error(f"Invalid input: {str(e)}")
            sys.exit(1)

    def create_tenant(self) -> None:
        """Crée le tenant pour le client"""
        self.tenant = self.netbox.create_tenant(
            self.config.name,
            self.config.slug
        )
        if not self.tenant:
            raise RuntimeError(f"Failed to create tenant for {self.config.name}")
        
        logger.info(f"Created tenant: {self.tenant.name}")

    def assign_locations(self) -> None:
        """Assigne les locations au tenant"""
        for location in self.config.locations:
            try:
                location.tenant = self.tenant.id
                location.save()
                logger.info(f"Assigned location {location.name} to tenant")
            except Exception as e:
                logger.error(f"Failed to update location {location.name}: {str(e)}")

    def allocate_prefix(self) -> None:
        """Alloue un préfixe /24 pour le client"""
        try:
            role = self.netbox.nb.ipam.roles.get(slug="customerscontainer")
            if not role:
                raise ValueError("Customer container role not found")

            parent_prefixes = list(self.netbox.nb.ipam.prefixes.filter(role_id=role.id))
            if not parent_prefixes:
                raise ValueError("No available parent prefix found")

            customer_prefix = self.netbox.allocate_prefix(
                parent_prefixes[0], 24, None, None, self.tenant.id
            )
            if not customer_prefix:
                raise RuntimeError("Failed to allocate /24 prefix")

            logger.info(f"Allocated prefix: {customer_prefix.prefix}")
            return customer_prefix

        except Exception as e:
            logger.error(f"Prefix allocation failed: {str(e)}")
            raise

    def setup_vxlan(self) -> None:
        """Configure VXLAN et VLAN pour le client"""
        try:
            # Création du L2VPN
            self.l2vpn = self.netbox.create_l2vpn(
                self.config.vni_id,
                f"{self.config.name}_vpn",
                f"{self.config.slug}-vpn",
                self.tenant.id
            )
            if not self.l2vpn:
                raise RuntimeError("Failed to create L2VPN")

            # Création du VLAN
            self.vlan = self.netbox.create_vlan(
                self.config.vlan_id,
                f"{self.config.name}_vlan",
                f"{self.config.slug}-vlan",
                self.tenant.id
            )
            if not self.vlan:
                raise RuntimeError("Failed to create VLAN")

            # Création de la terminaison VXLAN
            vxlan_termination = self.netbox.create_vxlan_termination(
                self.l2vpn.id,
                "ipam.vlan",
                self.vlan.id
            )
            if not vxlan_termination:
                raise RuntimeError("Failed to create VXLAN termination")

            logger.info(f"Created VXLAN configuration for {self.config.name}")

        except Exception as e:
            logger.error(f"VXLAN setup failed: {str(e)}")
            raise

    def configure_interfaces(self) -> None:
        """Configure les interfaces client sur les leafs"""
        for location in self.config.locations:
            leaf_devices = self.netbox.nb.dcim.devices.filter(
                role="leaf",
                location_id=location.id
            )

            if not leaf_devices:
                logger.warning(f"No leaf devices found in location {location.name}")
                continue

            for device in leaf_devices:
                interface = self.netbox.get_or_create_interface(device.id, "Ethernet3")
                if not interface:
                    logger.error(f"Failed to get/create interface for {device.name}")
                    continue

                try:
                    interface.custom_field_data = {'Customer': self.tenant.id}
                    interface.save()
                    logger.info(f"Configured interface on {device.name}")
                except Exception as e:
                    logger.error(f"Failed to configure interface on {device.name}: {str(e)}")

    def provision(self) -> None:
        """Processus principal de provision du client"""
        try:
            # 1. Récupération des informations
            self.config = self.get_user_input()

            # 2. Création du tenant
            self.create_tenant()

            # 3. Attribution des locations
            self.assign_locations()

            # 4. Allocation du préfixe
            self.allocate_prefix()

            # 5. Configuration VXLAN
            self.setup_vxlan()

            # 6. Configuration des interfaces
            self.configure_interfaces()

            logger.info(f"Successfully provisioned customer: {self.config.name}")

        except Exception as e:
            logger.error(f"Customer provisioning failed: {str(e)}")
            sys.exit(1)

def main():
    """Point d'entrée principal"""
    try:
        # Connexion à NetBox
        netbox_url = input("Enter NetBox URL: ").strip()
        netbox_token = input("Enter NetBox API Token: ").strip()

        if not all([netbox_url, netbox_token]):
            raise ValueError("NetBox URL and token are required")

        netbox = NetBoxBackend(netbox_url, netbox_token)
        if not netbox.check_connection():
            raise ConnectionError("Failed to connect to NetBox")

        # Provision du client
        provisioner = CustomerProvisioner(netbox)
        provisioner.provision()

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()