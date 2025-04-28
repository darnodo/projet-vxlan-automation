# Description

Here’s a high-level tour of the repository and how its pieces fit together:

## 1. Top-level scripts
- **main.py**
  - Entry point for VXLAN-Fabric creation.
  - Prompts for NetBox URL/token, number of buildings, and device-type slugs.
  - Validates input, connects to NetBox, builds a `FabricConfig`, and invokes `VXLANFabricCreator.create_fabric()`.
  - Logs out the new site, spines, leaves and access switches.

- **add_customers.py**
  - Entry point for “customer” provisioning under an existing Fabric.
  - Prompts for NetBox URL/token and customer details (name, VLAN/VNI, locations).
  - Creates a tenant, assigns selected locations, allocates a /24 prefix, configures VLAN/L2VPN/VXLAN, and tags client interfaces on leaf switches.

## 2. Configuration & constants
- **config.py**
  - Dataclasses and Enums defining:
    - Interface types (QSFP, SFP, virtual…)
    - Device roles (spine/leaf/access)
    - IP-prefix roles (underlay, loopback)
    - Default ASNs
  - `FabricConfig` dataclass holds all parameters for fabric build.

## 3. Exceptions
- **exceptions.py**
  - Custom exception hierarchy:
    - `FabricError` base class
    - `DeviceCreationError`, `IPAllocationError`, `CablingError` for granular error handling.

## 4. NetBox API backend
- **helpers/netbox_backend.py**
  - `NetBoxBackend` wraps `pynetbox` and exposes:
    - Tenant, Site, Device, VLAN, L2VPN, VXLAN-termination CRUD
    - Interface management and cabling
    - Prefix allocation and IP assignment
    - Custom-fields saving and cleanup routines
  - Uniform error-handler decorator logs errors and returns `None`.

## 5. Fabric-creator core
- **fabric_creator.py**
  - `VXLANFabricCreator` orchestrates the fabric build:
    1. `validate_prerequisites()`: Check roles, IP-roles, and device types exist in NetBox
    2. `get_or_create_site()`: List or create a site
    3. `create_spines()`: Always create two spine switches
    4. `create_building_pair()`: For each building, create a leaf + access switch under a new Location
    5. `setup_cabling()`: Cable leaf↔spines and leaf↔access ports
    6. `setup_ip_addressing()`: Carve /31 underlay links and /32 loopbacks, assign to interfaces
    7. `assign_asns()`: Stamp ASN custom-fields on spines and leaves
    8. `create_fabric()`: Glue it all together, capture and return the site/devices created

## 6. How to use
- Ensure you have Python 3 and install `pynetbox`.
- Export or enter your NetBox URL and API token.
- Run `main.py` to spin up a new VXLAN fabric.
- Run `add_customers.py` to onboard new tenants into an existing fabric.

---

This codebase gives you a higher-level, interactive automation layer atop NetBox, so you can script consistent VXLAN fabrics and customer provisioning without hand-crafting each object in the UI.
