"""
Script principal pour la création de fabric VXLAN dans NetBox
"""

import sys
import getpass
import logging
from typing import Dict

from config import FabricConfig
from exceptions import FabricError
from fabric_creator import VXLANFabricCreator
from helpers.netbox_backend import NetBoxBackend

# Configuration du logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_user_input() -> Dict:
    """
    Récupère les entrées utilisateur pour la configuration de la fabric
    
    Returns:
        Dict: Dictionnaire contenant les paramètres de configuration
        
    Raises:
        FabricError: Si les entrées sont invalides
    """
    try:
        return {
            'netbox_url': input("NetBox URL: ").strip(),
            'netbox_token': getpass.getpass("NetBox API Token: "),
            'num_buildings': int(input("Number of buildings (1-5): ").strip()),
            'spine_type_slug': input("Spine device type slug: ").strip(),
            'leaf_type_slug': input("Leaf device type slug: ").strip(),
            'access_type_slug': input("Access switch device type slug: ").strip(),
        }
    except ValueError as error:
        raise FabricError(f"Invalid input: {str(error)}")

def validate_input(fabric_config: Dict) -> None:
    """
    Valide les entrées utilisateur pour la configuration de la fabric
    
    Args:
        fabric_config: Dictionnaire contenant les paramètres de configuration
        
    Raises:
        FabricError: Si la validation échoue
    """
    # Validation des paramètres de connexion NetBox
    if not all([fabric_config['netbox_url'], fabric_config['netbox_token']]):
        raise FabricError("NetBox URL and token are required")
    
    # Validation du nombre de bâtiments
    if not 1 <= fabric_config['num_buildings'] <= 5:
        raise FabricError("Number of buildings must be between 1 and 5")
    
    # Validation des types d'équipements
    required_device_types = [
        fabric_config['spine_type_slug'],
        fabric_config['leaf_type_slug'],
        fabric_config['access_type_slug']
    ]
    if not all(required_device_types):
        raise FabricError("All device type slugs are required")

def main():
    """Point d'entrée principal du script"""
    try:
        # 1. Récupération des entrées utilisateur
        fabric_config = get_user_input()
        validate_input(fabric_config)

        # 2. Initialisation de la connexion NetBox
        netbox_backend = NetBoxBackend(
            fabric_config['netbox_url'],
            fabric_config['netbox_token']
        )
        
        if not netbox_backend.check_connection():
            raise FabricError("Failed to connect to NetBox")

        # 3. Configuration de la fabric
        fabric_settings = FabricConfig(
            site_code="",  # Sera défini plus tard
            num_buildings=fabric_config['num_buildings'],
            spine_type=fabric_config['spine_type_slug'],
            leaf_type=fabric_config['leaf_type_slug'],
            access_type=fabric_config['access_type_slug']
        )

        # 4. Création de la fabric
        fabric_creator = VXLANFabricCreator(netbox_backend)
        fabric_creator.config = fabric_settings
        fabric_result = fabric_creator.create_fabric()

        # 5. Affichage du résultat
        logger.info("=== Fabric Creation Completed ===")
        logger.info(f"Site: {fabric_result['site'].name}")
        logger.info("Spines: %s", [spine.name for spine in fabric_result['spines']])
        logger.info("Leaves: %s", [leaf.name for leaf in fabric_result['leaves']])
        logger.info("Access Switches: %s", 
                   [access.name for access in fabric_result['access_switches']])

    except FabricError as fabric_error:
        logger.error("Fabric creation error: %s", str(fabric_error))
        sys.exit(1)
    except Exception as unexpected_error:
        logger.error("Unexpected error: %s", str(unexpected_error))
        sys.exit(1)

if __name__ == "__main__":
    main()