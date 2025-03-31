# VXLAN EVPN Automation Project

This project aims to automate the creation and management of a VXLAN EVPN test lab using ContainerLab, Arista cEOS and Netbox 4.2.  
The automation is primarily achieved through Netbox Render Config and Python scripts.

## Table of Contents

- [VXLAN EVPN Automation Project](#vxlan-evpn-automation-project)
  - [Table of Contents](#table-of-contents)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Usage](#usage)
  - [Sources](#sources)

## Prerequisites

- Docker, ContainerLab, and Ansible installed.
- Images for Arista cEOS, Nokia SRLinux, and Linux Alpine downloaded.
- Python 3.13 with the necessary libraries installed (see `requirements.txt`).

## Installation

1. **Clone the Repository**:

    ```bash
    git clone https://github.com/darnodo/projet-vxlan-automation.git
    cd vxlan-evpn-automation-project
    ```

2. **Install Python Dependencies**:

    ```bash
    uv sync
    ```

3. **Install Depedencies**:

    The instructions are described here : [Installation Documentation](./documentation/INSTALLATION.md)

4. **Start the Automation**:

    Follow the steps in [Usage](#usage) to start your lab.

## Usage

- **Set Up  Lab**:

  ```bash
  sudo containerlab deploy --topo containerlab/fabric_vxlan.yml
  ```

- **Set Up Netbox**:

  All details on installation [documentation](./documentation/INSTALLATION.md#install-netbox-and-plugins)

## Sources

- [ContainerLab](https://containerlab.dev/)
- [NetBox Docker Plugin](https://github.com/netbox-community/netbox-docker/wiki/Using-Netbox-Plugins)
- [Vector Netbox](https://www.vectornetworksllc.com/post/generating-network-device-configurations-from-netbox)
