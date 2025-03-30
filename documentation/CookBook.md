# CookBook

>[!WARNING]
>
> Work in progress
>

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
