# Installation Guide

## Table of Contents

- [Installation Guide](#installation-guide)
  - [Table of Contents](#table-of-contents)
  - [Installing ContainerLab](#installing-containerlab)
  - [Installing Docker](#installing-docker)
  - [Images installation](#images-installation)
    - [Arista cEOS](#arista-ceos)
  - [Install Netbox and plugins](#install-netbox-and-plugins)
  - [Sources](#sources)

## Installing ContainerLab

ContainerLab can be installed using the installation script that detects the operating system type and installs the appropriate package:

```bash
# download and install the latest version (may require sudo)
bash -c "$(curl -sL https://get.containerlab.dev)"

# with wget
bash -c "$(wget -qO - https://get.containerlab.dev)"
```

## Installing Docker

This is the containerization engine used by ContainerLab.

```bash
# Update and install dependencies
sudo apt-get update
sudo apt-get install ca-certificates curl gnupg

# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add the repository to Apt sources:
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# To be able to execute docker with the current user
sudo usermod -aG docker $USER

# Create management network 
docker network create \
  --driver bridge \
  --subnet=172.20.20.0/24 \
  management
```

## Images installation

### Arista cEOS

To download and install the arista cEOS image, you need to be registered to [arista.com](https://www.arista.com/en/support/software-download).  
Once you created an account, please logged in and down the cEOS docker images.  

To add this new image to docker, please use the docker CLI command :

```bash
docker import cEOS64-lab-4.33.2F.tar.xz ceos:4.33.2F
```

## Install Netbox and plugins

  For this project, we need to install specific plugin :  
    - [Netbox Topology Views](https://github.com/netbox-community/netbox-topology-views)

  ```bash
  git clone -b release https://github.com/netbox-community/netbox-docker.git netbox
  cd netbox
  touch plugin_requirements.txt Dockerfile-Plugins docker-compose.override.yml
  cat <<EOF > plugin_requirements.txt
  netbox_topology_views
  EOF
  ```

  Create the Dockerfile used to build the custom Image

  ```bash
  cat << EOF > Dockerfile-Plugins
  FROM netboxcommunity/netbox:v4.2

  COPY ./plugin_requirements.txt /opt/netbox/
  RUN /usr/local/bin/uv pip install -r /opt/netbox/plugin_requirements.txt

  COPY configuration/configuration.py /etc/netbox/config/configuration.py
  COPY configuration/plugins.py /etc/netbox/config/plugins.py
  RUN SECRET_KEY="dummydummydummydummydummydummydummydummydummydummy" /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py collectstatic --no-input
  EOF
  ```

  > [!TIP]  
  > This `SECRET_KEY` is only used during the installation. There's no need to change it.

  Create the `docker-compose.override.yml`

  ```bash
  cat <<EOF > docker-compose.override.yml
  services:
    netbox:
      image: netbox:v4.2
      pull_policy: never
      ports:
        - 8000:8000
        - 8080:8080
        - 8081:8081
      build:
        context: .
        dockerfile: Dockerfile-Plugins
      networks:
        - management
    netbox-worker:
      image: netbox:v4.2
      pull_policy: never
      networks:
        - management
    netbox-housekeeping:
      image: netbox:v4.2
      pull_policy: never
      networks:
        - management
    postgres:
      networks:
        - management
    redis:
      networks:
        - management
    redis-cache:
      networks:
        - management

  networks:
    management:
      external: true
  EOF
  ```

  Enable the plugin by adding configuration in `configuration/plugins.py`

  ```python
  PLUGINS = [
      "netbox_topology_views"
  ]
  ```

  Build and Deploy

  ```bash
  docker compose build --no-cache
  docker compose up -d
  ```

  Create the first admin user :

  ```bash
  docker compose exec netbox /opt/netbox/netbox/manage.py createsuperuser
  ```

  You should be able to access to netbox via port `8080`

## Sources

- [ContainerLab](https://containerlab.dev/install/)
- [vrnetlab](https://containerlab.dev/manual/vrnetlab/#vrnetlab)
- [BrianLinkLetter](https://www.brianlinkletter.com/2019/03/vrnetlab-emulate-networks-using-kvm-and-docker/)
- [Docker Engine for Debian](https://docs.docker.com/engine/install/debian/)
