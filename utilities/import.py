#!/usr/bin/env python3
import sys

import requests
import yaml

########################################
# Device model import
########################################


def get_or_create_manufacturer(netbox_url, headers, manufacturer_name, slug):
    url = f"{netbox_url}/api/dcim/manufacturers/?slug={slug}"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    results = resp.json()["results"]
    if results:
        print(
            f"[INFO] Manufacturer '{manufacturer_name}' (slug={slug}) already exists."
        )
        return results[0]

    url = f"{netbox_url}/api/dcim/manufacturers/"
    payload = {"name": manufacturer_name, "slug": slug}
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    created = resp.json()
    print(f"[INFO] Manufacturer '{manufacturer_name}' created (ID={created['id']}).")
    return created


def get_or_create_device_role(netbox_url, headers, role):
    name = role["name"]
    slug = role["slug"]
    url = f"{netbox_url}/api/dcim/device-roles/?slug={slug}"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    results = resp.json()["results"]
    if results:
        print(f"[INFO] Device Role '{name}' (slug={slug}) already exists.")
        return results[0]

    url = f"{netbox_url}/api/dcim/device-roles/"
    payload = {
        "name": name,
        "slug": slug,
        "color": role.get("color", "607d8b"),
        "vm_role": role.get("vm_role", False),
    }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    created = resp.json()
    print(f"[INFO] Device Role '{name}' created (ID={created['id']}).")
    return created

def get_or_create_interface_template(netbox_url, headers, device_type_id, interface_data):
    """
    Create interface template for a device type if it doesn't exist
    """
    name = interface_data["name"]
    url = f"{netbox_url}/api/dcim/interface-templates/?name={name}&devicetype_id={device_type_id}"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    results = resp.json()["results"]
    
    if results:
        print(f"[INFO] Interface template '{name}' already exists for device type ID={device_type_id}")
        return results[0]

    create_url = f"{netbox_url}/api/dcim/interface-templates/"
    payload = {
        "device_type": device_type_id,
        "name": name,
        "type": interface_data["type"],
        "mgmt_only": interface_data.get("mgmt_only", False)
    }
    resp = requests.post(create_url, headers=headers, json=payload)
    resp.raise_for_status()
    created = resp.json()
    print(f"[INFO] Interface template '{name}' created for device type ID={device_type_id}")
    return created

def get_or_create_device_type(netbox_url, headers, device_type, manufacturers_cache):
    manufacturer_slug = device_type["manufacturer"]
    if manufacturer_slug not in manufacturers_cache:
        print(
            f"[WARN] Manufacturer slug '{manufacturer_slug}' not found in cache. Skipping device type."
        )
        return None

    manufacturer_obj = manufacturers_cache[manufacturer_slug]
    slug = device_type["slug"]

    url = f"{netbox_url}/api/dcim/device-types/?slug={slug}&manufacturer_id={manufacturer_obj['id']}"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    results = resp.json()["results"]
    if results:
        print(
            f"[INFO] Device Type '{device_type['model']}' (slug={slug}) already exists."
        )
        return results[0]

    create_url = f"{netbox_url}/api/dcim/device-types/"
    payload = {
        "manufacturer": manufacturer_obj["id"],
        "model": device_type["model"],
        "slug": slug,
        "part_number": device_type.get("part_number", ""),
        "u_height": device_type.get("u_height", 1),
        "is_full_depth": device_type.get("is_full_depth", False),
        "comments": device_type.get("comments", ""),
    }
    resp = requests.post(create_url, headers=headers, json=payload)
    resp.raise_for_status()
    created_dt = resp.json()
    print(
        f"[INFO] Device Type '{created_dt['model']}' created (ID={created_dt['id']})."
    )
    # Create interface templates if defined
    if "interfaces" in device_type:
        for interface in device_type["interfaces"]:
            get_or_create_interface_template(netbox_url, headers, created_dt["id"], interface)

    return created_dt

########################################
# Subnets import
########################################


def get_or_create_region(netbox_url, headers, region_name):
    url = f"{netbox_url}/api/dcim/regions/?name={region_name}"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    results = resp.json()["results"]
    if results:
        print(f"[INFO] Region '{region_name}' already exists.")
        return results[0]

    create_url = f"{netbox_url}/api/dcim/regions/"
    payload = {"name": region_name, "slug": region_name.lower().replace(" ", "-")}
    resp = requests.post(create_url, headers=headers, json=payload)
    resp.raise_for_status()
    created = resp.json()
    print(f"[INFO] Region '{region_name}' created (ID={created['id']}).")
    return created


def get_or_create_site(netbox_url, headers, site_name, region_id=None):
    url = f"{netbox_url}/api/dcim/sites/?name={site_name}"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    results = resp.json()["results"]
    if results:
        print(f"[INFO] Site '{site_name}' already exists.")
        return results[0]

    create_url = f"{netbox_url}/api/dcim/sites/"
    payload = {"name": site_name, "slug": site_name.lower().replace(" ", "-")}
    if region_id:
        payload["region"] = region_id

    resp = requests.post(create_url, headers=headers, json=payload)
    resp.raise_for_status()
    created = resp.json()
    print(f"[INFO] Site '{site_name}' created (ID={created['id']}).")
    return created


def get_or_create_location(netbox_url, headers, location_name, site_id):
    url = f"{netbox_url}/api/dcim/locations/?name={location_name}&site_id={site_id}"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    results = resp.json()["results"]
    if results:
        print(
            f"[INFO] Location '{location_name}' already exists for site ID={site_id}."
        )
        return results[0]

    create_url = f"{netbox_url}/api/dcim/locations/"
    payload = {"name": location_name, "slug": location_name.lower(), "site": site_id}
    resp = requests.post(create_url, headers=headers, json=payload)
    resp.raise_for_status()
    created = resp.json()
    print(f"[INFO] Location '{location_name}' created (ID={created['id']}).")
    return created


def get_or_create_prefix_role(netbox_url, headers, role_name):
    """
    Creates or retrieves a prefix role with the given name.
    We'll build the slug from the role_name.
    """
    slug = role_name.lower().replace(" ", "-")
    url = f"{netbox_url}/api/ipam/roles/?slug={slug}"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    results = resp.json()["results"]
    if results:
        print(f"[INFO] Prefix Role '{role_name}' (slug={slug}) already exists.")
        return results[0]

    create_url = f"{netbox_url}/api/ipam/roles/"
    payload = {"name": role_name, "slug": slug}
    resp = requests.post(create_url, headers=headers, json=payload)
    resp.raise_for_status()
    created = resp.json()
    print(f"[INFO] Prefix Role '{role_name}' created (ID={created['id']}).")
    return created


def create_container_prefix(netbox_url, headers, cidr, description, role_id, site_id):
    """
    Create (or reuse) a prefix in NetBox with a given role and site.
    """
    check_url = f"{netbox_url}/api/ipam/prefixes/?prefix={cidr}"
    resp = requests.get(check_url, headers=headers)
    resp.raise_for_status()
    existing = resp.json()["results"]
    if existing:
        print(f"[WARN] Container prefix '{cidr}' already exists. Not recreating.")
        return existing[0]

    create_url = f"{netbox_url}/api/ipam/prefixes/"
    payload = {
        "prefix": cidr,
        "description": description,
        "role": role_id,
        "scope_type": "dcim.site",
        "scope_id": site_id,
    }
    resp = requests.post(create_url, headers=headers, json=payload)
    resp.raise_for_status()
    new_prefix = resp.json()
    print(f"[INFO] Container prefix '{cidr}' created (ID={new_prefix['id']}).")
    return new_prefix


########################################
# Divers Creation
########################################

def get_or_create_custom_field(netbox_url, headers, field_name, object_types, field_type, label=None, description=None, related_object_type=None):
    """
    Create a custom field in NetBox.
    Args:
        netbox_url (str): The NetBox URL
        headers (dict): Request headers
        field_name (str): Name of the custom field
        object_types (list): List of object types (e.g. ['dcim.device'])
        field_type (str): Type of field (e.g. 'integer', 'text', 'boolean', 'object')
        label (str, optional): Label for the field. Defaults to field_name
        description (str, optional): Description of the field. Defaults to field_name
        related_object_type (str, optional): Required for object type fields (e.g. 'ipam.vlan')
    """
    url = f"{netbox_url}/api/extras/custom-fields/"

    # Check if the custom field already exists
    response = requests.get(url, headers=headers, params={"name": field_name})
    if response.status_code == 200:
        existing_fields = response.json().get("results", [])
        if existing_fields:
            print(f"[INFO] Custom field '{field_name}' already exists.")
            return

    # Set defaults if not provided
    label = label or field_name
    description = description or field_name

    # Define the custom field payload
    custom_field_data = {
        "name": field_name,
        "label": label,
        "type": field_type,
        "description": description,
        "required": False,
        "default": "",
        "weight": 100,
        "filter_logic": "loose",
        "ui_visible": "always",
        "is_cloneable": True,
        "object_types": object_types,
        "related_object_type": related_object_type
    }

    # Add related_object_type if field_type is 'object'
    if field_type == "object" and related_object_type:
        custom_field_data["object_type"] = related_object_type
    elif field_type == "object" and not related_object_type:
        raise ValueError("related_object_type is required for object type fields")

    # Create the custom field
    create_response = requests.post(url, headers=headers, json=custom_field_data)
    if create_response.status_code == 201:
        print(f"[INFO] Custom field '{field_name}' created successfully.")
    else:
        print(f"[ERROR] Failed to create custom field: {create_response.text}")

########################################
# MAIN
########################################


def main():
    if len(sys.argv) != 5:
        print(
            "Usage: python import_netbox.py <NETBOX_URL> <NETBOX_TOKEN> <DEVICE_MODEL_YML> <SUBNETS_YML>"
        )
        sys.exit(1)

    netbox_url = sys.argv[1].rstrip("/")
    netbox_token = sys.argv[2]
    device_model_file = sys.argv[3]
    subnets_file = sys.argv[4]

    headers = {
        "Authorization": f"Token {netbox_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # 1) Load device_model.yml
    with open(device_model_file, "r") as f:
        device_model_data = yaml.safe_load(f)

    # 2) Load subnets.yml
    with open(subnets_file, "r") as f:
        subnets_data = yaml.safe_load(f)

    # Divers Creation
    get_or_create_custom_field(netbox_url, headers, "ASN", ["dcim.device"], "integer", "ASN", "Autonomous System Number")
    #get_or_create_custom_field(netbox_url, headers, "Customer", ["dcim.interface"], "object", "Customer", "Customer Name", "tenancy.tenant")

    ######################################################
    # device_model.yml : manufacturers, roles, types
    ######################################################

    manufacturers_cache = {}
    if "manufacturers" in device_model_data:
        for mf in device_model_data["manufacturers"]:
            name = mf["name"]
            slug = mf["slug"]
            mf_obj = get_or_create_manufacturer(netbox_url, headers, name, slug)
            manufacturers_cache[slug] = mf_obj

    if "device_roles" in device_model_data:
        for role in device_model_data["device_roles"]:
            get_or_create_device_role(netbox_url, headers, role)

    if "device_types" in device_model_data:
        for dt in device_model_data["device_types"]:
            device_type = get_or_create_device_type(netbox_url, headers, dt, manufacturers_cache)
            if not device_type:
                print(f"[ERROR] Failed to create device type for {dt.get('model', 'unknown')}")

    ######################################################
    # subnets.yml : Region, Site, Containers, etc.
    ######################################################

    region_name = subnets_data.get("Location", {}).get("Region", "Europe")
    region_obj = get_or_create_region(netbox_url, headers, region_name)
    region_id = region_obj["id"]

    city_name = subnets_data.get("Location", {}).get("City", "Paris")
    site_obj = get_or_create_site(netbox_url, headers, city_name, region_id=region_id)
    site_id = site_obj["id"]

    # For each container key, create a prefix role and a prefix
    containers = subnets_data.get("Containers", {})
    for container_name, c_data in containers.items():
        # Attempt to fix any 'cirdr' -> 'cidr' typos by reading "cidr" if possible
        cidr = c_data.get("cidr")
        description = c_data.get("description", f"{container_name} prefix")

        # 1) Create a prefix role named after the container key
        #    e.g., container_name='UnderlayContainer' => role = UnderlayContainer
        role_obj = get_or_create_prefix_role(netbox_url, headers, container_name)
        role_id = role_obj["id"]

        # 2) Create the prefix with that role, attached to the site
        create_container_prefix(
            netbox_url, headers, cidr, description, role_id, site_id
        )

    # Optionally handle buildings as locations
    buildings = subnets_data.get("Buildings", {})
    for building_name in buildings.keys():
        get_or_create_location(netbox_url, headers, building_name, site_id)

    print("[INFO] Script completed successfully!")


if __name__ == "__main__":
    main()
