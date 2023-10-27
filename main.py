import requests
import subprocess
from jinja2 import Environment, FileSystemLoader
import socket

# Get system IP
# Get the hostname of the system
hostname = socket.gethostname()

# Get the IP address of the system
ip_address = socket.gethostbyname(hostname)

# Openshift vars
openshift_api_url = "https://api.cluster:6443"
openshift_token = "openshfit-token"
verify = False

# HAPROXY vars
haproxy_cfg = "/etc/haproxy/haproxy.cfg"
service_name = "haproxy"

# Jinja2 template path 
template_env = Environment(loader=FileSystemLoader('.'))  

# Load Jinja2 template from an external file
haproxy_template = template_env.get_template('./haproxy.cfg.j2')

# Auth and get nodes
headers = {
    "Authorization": f"Bearer {openshift_token}"
}
response = requests.get(f"{openshift_api_url}/api/v1/nodes", headers=headers, verify=verify)

if response.status_code == 200:
    # Obtiene la lista de nodos
    nodes_data = response.json()

    # Filter control plane and non control plane nodes
    non_control_plane_nodes = [node for node in nodes_data["items"] if "node-role.kubernetes.io/master" not in node["metadata"]["labels"]]
    control_plane_nodes = [node for node in nodes_data["items"] if "node-role.kubernetes.io/master" in node["metadata"]["labels"]]

    # List containing the ips and names of the master nodes
    mnodes = []
    for node in control_plane_nodes:
        node_name = node["metadata"]["name"]
        node_address = node["status"]["addresses"][0]["address"]
        mnodes.append({"name": node_name, "ip": node_address})
    print(mnodes)

    # List with the IPs and hostnames of  workers and infra nodes
    wnodes = []
    for node in non_control_plane_nodes:
        node_name = node["metadata"]["name"]
        node_address = node["status"]["addresses"][0]["address"]
        wnodes.append({"name": node_name, "ip": node_address})
    print(wnodes)

    # Render HAProxy config
    haproxy_config = haproxy_template.render(local_ip = ip_address, master_nodes=mnodes, worker_nodes=wnodes)
    print(haproxy_config)

    # Save HAProxy config into a file
    with open(haproxy_config, "w") as haproxy_file:
        haproxy_file.write(haproxy_config)

    print("HAProxy config file has been modified.")

    # Reload HAProxy Service
    try:
        subprocess.run(["systemctl", "reload", service_name], check=True)
        print(f"Service {service_name} reloaded successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to reload service {service_name}. Error: {e}")

else:
    print(f"Error fetching OpenShift nodes. Error code: {response.status_code}")
