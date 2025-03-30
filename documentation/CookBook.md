# CookBook

>[!WARNING]
>
> Work in progress
>

## Introduction

Intro here

## Prepare data

### Popule data in Netbox

Generate a Netbox token via webui and execute the python script, and on utilities folder start population :

```bash
uv run import.py http://localhost:8080 YOUR_TOKEN Devices/devices_model.yml
```

## Create Fabric

```bash
uv run Create_Fabric/main.py
NetBox URL: http://localhost:8080                   
NetBox API Token: 
Number of buildings (1-5): 4
Spine device type slug: ceos
Leaf device type slug: ceos
Access switch device type slug: ceos

Existing Sites:
  1. Paris (slug=paris)
Choose site number or 'new': 1
```

## Add Customer 

```bash
❯ uv run Create_Fabric/add_customers.py
Enter NetBox URL: http://localhost:8080
Enter NetBox API Token: 4e58e40e6b19d7f6cc53ae5665ca7ddd00558e71
Enter Customer Name: Orange
Enter VLAN ID (1-4094): 10
Enter VNI ID: 10010

Available Locations:
0: PA1
1: PA2
2: PA3
3: PA4
Select locations (comma-separated indices): 0,2
```

## Apply template

### Import to Netbox

Import template :
Operation > Data Sources > +Add
Name : Templates
Type : Local
URL : /tmp/templates

Click on Sync  

![alt text](assets/images/cookbook/templates_files.png)

On provisioning > Config Templates :
Create 3 Templates, one per role :
Name : Leaf, Access or Spine
Data Source : Templates
File : spine.j2

![alt text](<assets/images/cookbook/config template.png>)

At the end :

![alt text](assets/images/cookbook/all_templates.png)

### Reconfigre devices

Devices > Devices  
Filter by role :  
![alt text](assets/images/cookbook/role_filter.png)  

Select all and Edit Selected :

![alt text](assets/images/cookbook/edit_selected.png)  

On configuration part, for Config Template option : select the one that match with the device role

![alt text](assets/images/cookbook/spine_template.png)

Do the same for the 3 roles : Spine, Leaf and Access

