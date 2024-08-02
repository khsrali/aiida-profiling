"""
Note: at the moment, to run this script, you need sudo privileges to restart apache2 service.
use at your own risk.
"""

import requests
import time

import json
import pandas as pd
import os


class EndpointNotAvailable(Exception):
    """raised when response status code is not 200"""


class logger:
    """
    This class logs the time taken to call an endpoint
    later it can be more generalized to be used for other purposes. (e.g. to log the response time of a function, maybe using cprofile)
    """

    def __init__(self, base_url, success_code=200):
        self.log_timing = {}
        self.base_url = base_url
        self.success_code = success_code

    def log_endpoint(self, url, id=None):
        """
        Log the endpoint and return the data
        """

        if url not in self.log_timing:
            self.log_timing[url] = {
                "ncalls": 0,
                "ave_time_per_call(ms)": 0.0,
                "total_time(s)": 0.0,
                "Error: EndpointNotAvailable": 0,
            }

        start_time = time.time()
        response = requests.get(self.base_url + url.replace("<id>", str(id)))
        end_time = time.time()
        duration = end_time - start_time

        if response.status_code == self.success_code:
            if response.content:
                try:
                    data = response.json()
                except json.decoder.JSONDecodeError:
                    data = response.content
            else:
                data = None
        else:
            # raise EndpointNotAvailable
            self.log_timing[url]["Error: EndpointNotAvailable"] += 1
            return None

        # Update the log data for this URL
        self.log_timing[url]["ncalls"] += 1
        self.log_timing[url]["total_time(s)"] += duration
        self.log_timing[url]["ave_time_per_call(ms)"] = (
            self.log_timing[url]["total_time(s)"] / (self.log_timing[url]["ncalls"])
        ) * 1000

        return data


class Performance:

    def __init__(self, config_file, endpoints_file):
        """
        Initialize the Performance class

        Parameters:
        config_file (str): Path to the configuration file (*json)
        endpoints_file (str): Path to the endpoints file (*json)
        """

        with open(config_file) as f:
            config = json.load(f)

        self.base_url = config["base_url"]
        self.id_limit = config["id_limit"]
        self.data_base_type = config["data_base_type"]
        self.wsgi_path = config["wsgi_path"]
        self.wsgi_template = config["wsgi_template"]

        with open(endpoints_file) as f:
            endpoints = json.load(f)

        self.general_endpoints = endpoints["general_endpoints"]
        self.node_specific_endpoints = endpoints["node_specific_endpoints"]

    def measure_performance(self):
        """
        Measure the performance of the AiiDA REST API
        """
        # Get all node IDs
        l = logger(base_url=self.base_url)
        nodes_data = l.log_endpoint("/api/v4/nodes")
        node_ids = [node["uuid"] for node in nodes_data["data"]["nodes"]]
        node_ids = node_ids[: self.id_limit]
        ## Get download formats
        download_formats = l.log_endpoint("/api/v4/nodes/download_formats")["data"]

        # call general_endpoints multiple times
        for i in range(10):
            for endpoint in self.general_endpoints:
                response = l.log_endpoint(endpoint)

        # call node_specific_endpoints['all'] for all nodes
        for endpoint in self.node_specific_endpoints["all"]:
            for id in node_ids:
                response = l.log_endpoint(endpoint, id)

        # node_specific_endpoints['download']
        for id in node_ids:
            nodes = l.log_endpoint("/api/v4/nodes/<id>", id)["data"]["nodes"]
            for junior_node in nodes:
                node_type = junior_node["full_type"]
                # print(f"Node type: {node_type}")
                for my_endpoint in self.node_specific_endpoints["download"]:
                    for download_format in download_formats[node_type]:
                        response = l.log_endpoint(
                            my_endpoint.replace("<download_format>", download_format),
                            id,
                        )
                        # print(f"Downloaded node with format {download_format}")#: {response.text}")

        df = pd.DataFrame(l.log_timing).T

        return df

    def compare_performance(self, print_results=False):
        """
        Compare the performance of the AiiDA REST API for different databases (e.g. sqlite, postgresql)
        """
        results = {}
        for data_base in self.data_base_type:

            with open(self.wsgi_template, "r") as f:
                wsgi_content = f.read()
            with open(self.wsgi_path, "w") as f:
                f.write(
                    wsgi_content.replace(
                        'load_profile("")', f"load_profile('{data_base}')"
                    )
                )
            os.system("sudo systemctl restart apache2.service")

            results[data_base] = self.measure_performance()

            if print_results:
                print(f"### Performance for {data_base}")
                print(results[data_base].round(3).to_string())
                print("\n\n\n")

        return results

    def write_performance_to_file(self, results_):
        """
        Write the performance data to a file
        """
        with open(f"results/restapi.txt", "w") as f:
            for data_base in self.data_base_type:
                f.write(f"### Performance for {data_base}\n")
                f.write(results_[data_base].round(3).to_string())
                f.write("\n\n\n")

        for data_base in self.data_base_type:
            results_[data_base].round(3).to_csv(f"results/restapi_{data_base}.csv")


"""
Main function
"""
p = Performance(
    config_file="restapi/config.json", endpoints_file="restapi/endpoints.json"
)

results = p.compare_performance(print_results=True)
p.write_performance_to_file(results)
