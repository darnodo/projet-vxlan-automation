"""Configuration et constantes pour la création de fabric VXLAN"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

class InterfaceTypes(Enum):
    """Types d'interfaces supportés"""
    QSFPP = "40gbase-x-qsfpp"
    SFP = "1000base-x-sfp"
    SFP_PLUS = "10gbase-x-sfpp"
    VIRTUAL = "virtual"

class DeviceRoles(Enum):
    """Rôles des équipements"""
    SPINE = "spine"
    LEAF = "leaf"
    ACCESS = "access"

class IPRoles(Enum):
    """Rôles des préfixes IP"""
    UNDERLAY = "underlaycontainer"
    LOOPBACK = "loopbackcontainer"

@dataclass
class FabricConfig:
    """Configuration de la fabric VXLAN"""
    site_code: str
    num_buildings: int
    spine_type: str
    leaf_type: str
    access_type: str
    tenant_id: Optional[int] = None
    base_spine_asn: int = 65001
    base_leaf_asn: int = 65101