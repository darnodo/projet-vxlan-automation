"""Exceptions personnalisées pour la création de fabric VXLAN"""

class FabricError(Exception):
    """Erreur de base pour la fabric"""
    pass

class DeviceCreationError(FabricError):
    """Erreur lors de la création d'un équipement"""
    pass

class IPAllocationError(FabricError):
    """Erreur lors de l'allocation d'adresses IP"""
    pass

class CablingError(FabricError):
    """Erreur lors du câblage"""
    pass