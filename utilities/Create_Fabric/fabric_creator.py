"""
Classe principale pour la création de fabric VXLAN dans NetBox
"""

import logging
from typing import Dict, List, Tuple, Optional

from config import FabricConfig, DeviceRoles, IPRoles, InterfaceTypes
from exceptions import DeviceCreationError, IPAllocationError, CablingError, FabricError
from helpers.netbox_backend import NetBoxBackend

logger = logging.getLogger(__name__)

class VXLANFabricCreator:
    """Gère la création d'une fabric VXLAN complète"""

    def __init__(self, netbox: NetBoxBackend):
        """
        Initialise le créateur de fabric
        
        Args:
            netbox: Instance de NetBoxBackend
        """
        self.nb = netbox
        self.config: Optional[FabricConfig] = None
        self._roles: Dict = {}
        self._ip_roles: Dict = {}

    def validate_prerequisites(self) -> bool:
        """
        Valide tous les prérequis nécessaires
        
        Returns:
            bool: True si tous les prérequis sont validés
        
        Raises:
            DeviceCreationError: Si un rôle d'équipement est manquant
            IPAllocationError: Si un rôle IP est manquant
        """
        try:
            # Validation des rôles d'équipements
            for role in DeviceRoles:
                role_obj = self.nb.get_device_role(role.value)
                if not role_obj:
                    raise DeviceCreationError(f"Role {role.value} not found")
                self._roles[role.value] = role_obj

            # Validation des rôles IP
            for role in IPRoles:
                ip_role = self.nb.nb.ipam.roles.get(slug=role.value)
                if not ip_role:
                    raise IPAllocationError(f"IP role {role.value} not found")
                self._ip_roles[role.value] = ip_role

            # Validation des types d'équipements
            device_types = [
                self.config.spine_type,
                self.config.leaf_type,
                self.config.access_type
            ]
            for dev_type in device_types:
                if not self.nb.get_device_type_by_slug(dev_type):
                    raise DeviceCreationError(f"Device type {dev_type} not found")

            return True

        except Exception as e:
            logger.error(f"Validation failed: {str(e)}")
            return False

    def get_or_create_site(self) -> dict:
        """
        Sélectionne un site existant ou en crée un nouveau
        
        Returns:
            dict: Objet site
        
        Raises:
            DeviceCreationError: Si la création/sélection échoue
        """
        existing_sites = self.nb.get_sites()
        if not existing_sites:
            raise DeviceCreationError("No sites found in NetBox")

        print("\nExisting Sites:")
        for idx, site in enumerate(existing_sites, start=1):
            print(f"  {idx}. {site.name} (slug={site.slug})")

        choice = input("Choose site number or 'new': ").strip().lower()
        
        if choice == "new":
            name = input("Site name: ").strip()
            code = input("Site code: ").strip().upper()
            if not all([name, code]):
                raise DeviceCreationError("Site name and code required")
            return self.nb.create_site(name, code.lower())
        
        try:
            return existing_sites[int(choice) - 1]
        except (ValueError, IndexError):
            raise DeviceCreationError("Invalid site selection")

    def create_spines(self, site) -> List[dict]:
        """
        Crée les switches spine
        
        Args:
            site: Objet site
            
        Returns:
            List[dict]: Liste des spines créés
            
        Raises:
            DeviceCreationError: Si la création échoue
        """
        spines = []
        for i in range(1, 3):  # Toujours 2 spines
            name = f"{self.config.site_code.lower()}dc_sp{i}_00"
            spine = self.nb.create_device(
                name=name,
                device_type_slug=self.config.spine_type,
                role_id=self._roles[DeviceRoles.SPINE.value].id,
                site_id=site.id
            )
            if not spine:
                raise DeviceCreationError(f"Failed to create spine {name}")
            spines.append(spine)
            logger.info(f"Created spine: {spine.name}")
        return spines

    def create_building_pair(self, site, building_num) -> Tuple[dict, dict]:
        """
        Crée une paire leaf/access pour un bâtiment
        
        Args:
            site: Objet site
            building_num: Numéro du bâtiment
            
        Returns:
            Tuple[dict, dict]: Paire (leaf, access)
            
        Raises:
            DeviceCreationError: Si la création échoue
        """
        try:
            # Création du location
            location_name = f"{self.config.site_code}{building_num}"
            location = self.nb.nb.dcim.locations.create(
                name=location_name,
                slug=location_name.lower(),
                site=site.id
            )

            # Création Leaf
            leaf_name = f"{self.config.site_code.lower()}{str(building_num).zfill(2)}_lf1_00"
            leaf = self.nb.create_device(
                name=leaf_name,
                device_type_slug=self.config.leaf_type,
                role_id=self._roles[DeviceRoles.LEAF.value].id,
                site_id=site.id,
                location_id=location.id
            )
            if not leaf:
                raise DeviceCreationError(f"Failed to create leaf {leaf_name}")

            # Création Access
            access_name = f"{self.config.site_code.lower()}{str(building_num).zfill(2)}_sw1_00"
            access = self.nb.create_device(
                name=access_name,
                device_type_slug=self.config.access_type,
                role_id=self._roles[DeviceRoles.ACCESS.value].id,
                site_id=site.id,
                location_id=location.id
            )
            if not access:
                raise DeviceCreationError(f"Failed to create access switch {access_name}")

            logger.info(f"Created leaf/access pair: {leaf_name} / {access_name}")
            return leaf, access

        except Exception as e:
            raise DeviceCreationError(f"Failed to create building pair: {str(e)}")

    def setup_cabling(self, leaf, spines, access) -> Tuple[dict, dict, dict, dict]:
        """
        Configure le câblage pour un ensemble leaf/spines/access
        
        Topologie:
        - Spine1.EthX -> LeafY.Eth1 (où X = numéro du leaf)
        - Spine2.EthX -> LeafY.Eth2 (où X = numéro du leaf)
        - LeafY.Eth3 -> AccessY.Eth1
        
        Args:
            leaf: Objet leaf
            spines: Liste des spines
            access: Objet access switch
            
        Returns:
            Tuple[dict, dict, dict, dict]: Interfaces connectées (leaf_if1, leaf_if2, spine1_if, spine2_if)
            
        Raises:
            CablingError: Si le câblage échoue
        """
        try:
            # Extraire le numéro du leaf (ex: pa01_lf1_00 -> 1)
            leaf_number = int(leaf.name.split('_')[0][-2:])
            
            # Leaf -> Spine1 (Leaf.Eth1 -> Spine1.EthX)
            leaf_if1 = self.nb.get_or_create_interface(
                leaf.id, "Ethernet1", InterfaceTypes.QSFPP.value
            )
            spine1_if = self.nb.get_or_create_interface(
                spines[0].id, f"Ethernet{leaf_number}", InterfaceTypes.QSFPP.value
            )
            if not self.nb.create_cable_if_not_exists(leaf_if1, spine1_if):
                raise CablingError(f"Failed to cable {leaf_if1.name} to {spine1_if.name}")
            logger.info(f"Connected {leaf.name}.Eth1 to {spines[0].name}.Eth{leaf_number}")

            # Leaf -> Spine2 (Leaf.Eth2 -> Spine2.EthX)
            leaf_if2 = self.nb.get_or_create_interface(
                leaf.id, "Ethernet2", InterfaceTypes.QSFPP.value
            )
            spine2_if = self.nb.get_or_create_interface(
                spines[1].id, f"Ethernet{leaf_number}", InterfaceTypes.QSFPP.value
            )
            if not self.nb.create_cable_if_not_exists(leaf_if2, spine2_if):
                raise CablingError(f"Failed to cable {leaf_if2.name} to {spine2_if.name}")
            logger.info(f"Connected {leaf.name}.Eth2 to {spines[1].name}.Eth{leaf_number}")

            # Leaf -> Access (Leaf.Eth3 -> Access.Eth1)
            leaf_if3 = self.nb.get_or_create_interface(
                leaf.id, "Ethernet3", InterfaceTypes.QSFPP.value
            )
            access_if = self.nb.get_or_create_interface(
                access.id, "Ethernet1", InterfaceTypes.QSFPP.value
            )
            if not self.nb.create_cable_if_not_exists(leaf_if3, access_if):
                raise CablingError(f"Failed to cable {leaf_if3.name} to {access_if.name}")
            logger.info(f"Connected {leaf.name}.Eth3 to {access.name}.Eth1")

            return leaf_if1, leaf_if2, spine1_if, spine2_if

        except ValueError as e:
            raise CablingError(f"Invalid device naming format: {str(e)}")
        except Exception as e:
            raise CablingError(f"Cabling failed: {str(e)}")

    def setup_ip_addressing(self, site, interfaces, devices) -> None:
        """
        Configure l'adressage IP pour les interfaces et les loopbacks
        
        Args:
            site: Objet site
            interfaces: Liste de tuples d'interfaces à connecter
            devices: Liste des équipements nécessitant un loopback
            
        Raises:
            IPAllocationError: Si l'allocation IP échoue
        """
        try:
            # Récupération des prefixes parents
            underlay_pfxs = self.nb.nb.ipam.prefixes.filter(
                role_id=self._ip_roles[IPRoles.UNDERLAY.value].id,
                scope_id=site.id
            )
            loopback_pfxs = self.nb.nb.ipam.prefixes.filter(
                role_id=self._ip_roles[IPRoles.LOOPBACK.value].id,
                scope_id=site.id
            )

            if not underlay_pfxs or not loopback_pfxs:
                raise IPAllocationError("Missing required prefix pools")

            parent_prefix = list(underlay_pfxs)[0]
            loopback_prefix = list(loopback_pfxs)[0]

            # Attribution des /31 pour les liens
            for if_a, if_b in interfaces:
                child_prefix = self.nb.allocate_prefix(
                    parent_prefix, 31, site.id,
                    self._ip_roles[IPRoles.UNDERLAY.value].id,
                    self.config.tenant_id
                )
                if not child_prefix:
                    raise IPAllocationError(f"Failed to allocate /31 for {if_a.name}-{if_b.name}")

                ips = self.nb.get_available_ips_in_prefix(child_prefix)
                if len(ips) < 2:
                    raise IPAllocationError(f"Not enough IPs in /31 for {if_a.name}-{if_b.name}")

                self.nb.assign_ip_to_interface(if_a, ips[0].address)
                self.nb.assign_ip_to_interface(if_b, ips[1].address)
                logger.info(f"Assigned IPs to {if_a.name}-{if_b.name}")

            # Attribution des loopbacks
            for device in devices:
                # Création de l'interface loopback
                loopback = self.nb.get_or_create_interface(
                    device.id,
                    "Loopback0",
                    InterfaceTypes.VIRTUAL.value
                )
                if not loopback:
                    raise IPAllocationError(f"Failed to create Loopback0 for {device.name}")

                # Allocation du /32
                loopback_32 = self.nb.allocate_prefix(
                    loopback_prefix, 32, site.id,
                    self._ip_roles[IPRoles.LOOPBACK.value].id,
                    self.config.tenant_id
                )
                if not loopback_32:
                    raise IPAllocationError(f"Failed to allocate /32 for {device.name}")

                ips = self.nb.get_available_ips_in_prefix(loopback_32)
                if not ips:
                    raise IPAllocationError(f"No IPs available in /32 for {device.name}")

                ip = self.nb.assign_ip_to_interface(loopback, ips[0].address)
                if ip:
                    logger.info(f"Assigned {ip.address} to {device.name} Loopback0")
                else:
                    raise IPAllocationError(f"Failed to assign IP to {device.name} Loopback0")

        except Exception as e:
            raise IPAllocationError(f"IP addressing failed: {str(e)}")

    def assign_asns(self, spines: List[dict], leaves: List[dict]) -> None:
        """
        Attribue les ASN aux équipements
        
        Args:
            spines: Liste des spines
            leaves: Liste des leaves
            
        Raises:
            DeviceCreationError: Si l'attribution des ASN échoue
        """
        try:
            # ASNs pour les spines
            for i, spine in enumerate(spines):
                asn = self.config.base_spine_asn + i
                if not self.nb.save_custom_fields(spine, {"ASN": asn}):
                    raise DeviceCreationError(f"Failed to assign ASN {asn} to {spine.name}")
                logger.info(f"Assigned ASN {asn} to {spine.name}")

            # ASNs pour les leaves
            for i, leaf in enumerate(leaves):
                asn = self.config.base_leaf_asn + i
                if not self.nb.save_custom_fields(leaf, {"ASN": asn}):
                    raise DeviceCreationError(f"Failed to assign ASN {asn} to {leaf.name}")
                logger.info(f"Assigned ASN {asn} to {leaf.name}")

        except Exception as e:
            raise DeviceCreationError(f"ASN assignment failed: {str(e)}")

    def create_fabric(self) -> Dict:
        """
        Processus principal de création de la fabric
        
        Returns:
            Dict: Résultat de la création
            
        Raises:
            FabricError: Si la création échoue
        """
        try:
            if not self.validate_prerequisites():
                raise FabricError("Prerequisites validation failed")

            # 1. Création/sélection du site
            site = self.get_or_create_site()
            self.config.site_code = site.name[:2].upper()

            # 2. Création des équipements
            spines = self.create_spines(site)
            leaves = []
            access_switches = []
            interface_pairs = []

            # 3. Création des paires leaf/access par bâtiment
            for building in range(1, self.config.num_buildings + 1):
                leaf, access = self.create_building_pair(site, building)
                leaves.append(leaf)
                access_switches.append(access)
                
                # 4. Câblage
                interfaces = self.setup_cabling(leaf, spines, access)
                interface_pairs.extend([
                    (interfaces[0], interfaces[2]),  # Leaf-Spine1
                    (interfaces[1], interfaces[3])   # Leaf-Spine2
                ])

            # 5. Configuration IP
            self.setup_ip_addressing(
                site=site,
                interfaces=interface_pairs,
                devices=spines + leaves  # Loopbacks uniquement pour spines et leaves
            )

            # 6. Attribution des ASN
            self.assign_asns(spines, leaves)

            logger.info("Fabric creation completed successfully")
            return {
                'site': site,
                'spines': spines,
                'leaves': leaves,
                'access_switches': access_switches
            }

        except Exception as e:
            logger.error(f"Fabric creation failed: {str(e)}")
            raise FabricError(f"Fabric creation failed: {str(e)}")