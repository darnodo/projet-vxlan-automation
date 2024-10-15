# VXLAN EVPN Automation Project

This project aims to automate the creation and management of a VXLAN EVPN test lab using ContainerLab, Arista cEOS, Nokia SRLinux, and Netbox. The automation is primarily achieved through Ansible and Python scripts.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Usage](#usage)
4. [License](#license)
5. [Sources](#sources)

## Prerequisites

- Docker, ContainerLab, and Ansible installed.
- Images for Arista cEOS, Nokia SRLinux, and Linux Alpine downloaded.
- Python 3.13 with the necessary libraries installed (see `requirements.txt`).

## Installation

1. **Clone the Repository**:

    ```bash
    git clone https://github.com/MasqAs/projet-vxlan-automation.git
    cd vxlan-evpn-automation-project
    ```

2. **Install Python Dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

3. **Install Depedencies**:

    The instructions are described here : [Installation Documentation](./documentation/INSTALLATION.md)

4. **Start the Automation**:

    Follow the steps in [Usage](#usage) to start your lab.

## Usage

1. **Set Up the Lab**:

    ```bash
    sudo containerlab deploy --topo containerlab/lab_definition.yml
    ```

2. **Configure Netbox**:

    ```bash
    git clone -b release https://github.com/netbox-community/netbox-docker.git
    cd netbox-docker
    tee docker-compose.override.yml <<EOF
    services:
        netbox:
            ports:
                - 8000:8080
    EOF
    docker compose pull
    docker compose up
    ```

3. **(Additional Steps)**:

    Follow the additional instructions in `documentation/USAGE.md`.

## License

This project is licensed under the APACHE license. See the [LICENSE](LICENSE) file for more information.

## Sources

- [ContainerLab](https://containerlab.dev/)
- [The ASCII Construct](https://www.theasciiconstruct.com/post/multivendor-evpn-vxlan-l2-overlay/)
