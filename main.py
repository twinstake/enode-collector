import os
import json
import requests
from kubernetes import client, config

def main():
    # Load Kubernetes configuration
    config.load_incluster_config()

    # Create Kubernetes API client
    v1 = client.CoreV1Api()

    # Get the current namespace
    namespace = os.getenv("NAMESPACE", "default")

    # List services with the label "type: api"
    services = v1.list_namespaced_service(namespace, label_selector="type=api")

    enodes = []

    # Iterate over the services
    for service in services.items:
        # Get the service name
        service_name = service.metadata.name

        # Get the service endpoints
        endpoints = v1.list_namespaced_endpoints(namespace, field_selector=f"metadata.name={service_name}")
        # Iterate over the endpoints
        for endpoint in endpoints.items:
            # Iterate over the subsets
            for subset in endpoint.subsets:
                # Check if addresses is not None before iterating
                if subset.addresses is not None:
                    # Iterate over the addresses
                    for address in subset.addresses:
                        # Get the endpoint IP and port
                        endpoint_hostname = address.hostname
                        endpoint_port = 8545

                        # Construct the JSON-RPC request payload
                        payload = {
                            "jsonrpc": "2.0",
                            "method": "admin_nodeInfo",
                            "params": [],
                            "id": 1
                        }

                        try:
                            # Send the JSON-RPC request to the endpoint
                            response = requests.post(f"http://{endpoint_hostname}.{service_name}:{endpoint_port}", json=payload)

                            # Parse the response and extract the enode
                            result = response.json()["result"]
                            enode = result["enode"]

                            # Append the enode to the list
                            enodes.append(enode)
                        except requests.exceptions.RequestException as e:
                            print(f"Error occurred while sending request to {endpoint_hostname}.{service_name}:{endpoint_port}: {e}")
                        except (KeyError, IndexError) as e:
                            print(f"Error occurred while processing endpoint {endpoint_hostname}.{service_name}: {e}")

    # Print the array of enodes
    print(f"Fetched bootnodes: {json.dumps(enodes)}")

    # Fetch the chainspec file from GitHub
    # Determine the JSON file to fetch based on the namespace
    if namespace.lower() in ["mainnet", "ethereum"]:
        json_file = "foundation.json"
    else:
        json_file = f"{namespace.lower()}.json"
        
    url = f"https://raw.githubusercontent.com/NethermindEth/nethermind/master/src/Nethermind/Chains/{json_file}"
    response = requests.get(url)
    data = response.json()

    # Extract the bootnodes from the chainspec file
    bootnodes = data.get("nodes", [])

    print(f"Bootnodes from chainspec: {bootnodes}")

    # Append the bootnodes to the enodes list
    enodes.extend(bootnodes)

    # Write the enodes list to a file on the shared volume in the format BOOTNODES=enode,enode
    with open("/env/init-nodeport", "a") as f:
        f.write("BOOTNODES=" + ",".join(enodes).replace(" ", ""))
        
if __name__ == "__main__":
    main()
