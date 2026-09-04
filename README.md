# linode-ansible-setup
A set of ansible playbooks to set up and configure one or more linodes

This project uses example code from the Linode documentation repository found at https://github.com/linode/docs-cloud-projects/


## Requirements

### Local Requirements

* A unix-like operating system like Linux or MacOS is required to run the ansible playbooks. I have not tested this on Windows.
* curl: to fetch setup scripts, but you can also use your browser to download them.
* ssh: to connect to your Linode(s) and run the ansible playbooks
* git: to work with this repository locally

### Linode Requirements

* An API Token, also known as a PAT.
* A Linode firewall. Instructions for setting this up are below.

## Setup

### Linode Account

If you don't already have a linode account, now would be a good time to create one. You can do that at https://www.linode.com/
The rest of this document is just academic without access.

A credit card is required to create a linode account, but you can use the [free $100 credit](https://www.akamai.com/lp/free-credit-100) to get started.

### PAT

Next, log in to your account and follow [linode's documentation to create a PAT](https://www.linode.com/docs/products/platform/accounts/guides/manage-api-tokens/#create-an-api-token)
It's a good idea to create a PAT specifically for this project, and not reuse one you may have created for other purposes.

You will need the following permissions for your PAT, everything else can be set to No Access unless you want to use the PAT for other purposes:
* Read/Write:
    * Domains: This is required to set up the DNS records for your domain name.
    * Firewalls:  This is required to set up access between Linodes in the same cluster.
    * Images:  This is optional.
    * IPs:  This is optional.
    * Linodes:  This is required to create and manage your Linode(s).
    * Monitor:  This is required as setting up a linode involves setting up a few monitors as well.
    * Volumes:  This is optional, and required if you need to create additional volumes to hold data.
    * VPCs:  This is required to create a private subnet for your Linodes in a region to communicate with each other.
* Read Only:
    * Events: This is required to monitor the status of your Linode(s) and to see when they have started.

### Firewall

Next, [create a firewall](https://techdocs.akamai.com/cloud-computing/docs/create-a-cloud-firewall) that will restrict general access to your Linode by default
and only permit SSH access. If you have a fixed IP address or subnet, you can restrict SSH access to that address or subnet.

The `Public Firewall Template` is a good starting point that only allows incoming ssh and ICMP traffic.

![Public Firewall Template](/docs/images/create-a-firewall.jpg)

The scripts in this repository only require ssh access to run the playbooks. If your project requires additional access, we recommend setting up a different
firewall for that purpose.


### Local setup

Next we will set up your local environment to run the ansible playbooks.

#### 1. Get the right version of python

If you're on MacOS, you most likely have an older version of Python whereas the scripts used in this project require at least Python 3.11.
The latest version as of this writing (September 2026) is 3.14 and 3.15 is expected in October 2026.
The least intrusive way to install a new version of Python is to use Rye.

```command
curl -o get-rye.sh -fsS https://rye.astral.sh/get

# Verify that get-rye.sh is safe to run by viewing the source, then proceed

chmod +x get-rye.sh

./get-rye.sh
```

This will ask you a few questions about the installation and should also set up the latest version of Python. You will need to set your shell's PATH variable
(or restart your shell) to be able to run the correct version of Python.


#### 2. Install Ansible

First clone this repository locally and create a python virtual environment - you only need this step once.

```command
git clone https://github.com/bluesmoon/linode-ansible-setup.git

python3 -m venv env
```

Next switch to this environment. You need to switch to the environment any time you start in a new shell.

```command
source env/bin/activate
```

Then setup dependencies in the environment.  You can run this step any time dependencies change or new versions become available upstream.

```command
pip install -U pip
pip install -r requirements.txt

ansible-galaxy collection install -r collections.yml
ansible --version
```


#### 3. Encrypt secrets with Ansible vault

All secrets are encrypted with Ansible vault for best practices. To run the next commands you will need to first set up your vault password.
The [ansible vault documentation](https://docs.rockylinux.org/books/learning_ansible/08-management-server-optimizations/#using-vault) explains how to
set up a vault password file and use it with Ansible. You can either use `/etc/ansible/ansible.cfg` or `~/.ansible.cfg`.

If you're on MacOS, you can also [use the Keychain to store your vault password](https://samdoran.com/ansible-vault-and-macos-keychain-access/).

Encrypt your Linode root password and valid APIv4 token with ansible-vault. Replace `ROOT_PASSWORD`, and `SUDO_PASSWORD` with your own preferred strong passwords
and `LINODE_PAT` with your own access token created above.

```command
rm -f group_vars/secret_vars
ansible-vault encrypt_string 'LINODE_PAT' --name 'api_token' >> group_vars/secret_vars
ansible-vault encrypt_string 'ROOT_PASSWORD' --name 'root_password' >> group_vars/secret_vars
ansible-vault encrypt_string 'SUDO_PASSWORD' --name 'sudo_password' >> group_vars/secret_vars
```

These commands will create or overwrite the file `group_vars/secret_vars` with your encrypted secrets.
You may store this file in your shared vault for other members of your team to use.

The `.gitignore` file is set up to ignore the `group_vars/secret_vars` file, so changes you make will not
be accidentally committed to version control.

The file included as part of this repository contains the example secrets used above and do not actually work.
(You need a valid Linode Token before starting anything).
