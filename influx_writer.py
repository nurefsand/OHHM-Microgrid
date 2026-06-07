from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import datetime

url = "https://us-east-1-1.aws.cloud2.influxdata.com"
token = "LrtFjR88TGhkBWwQEhweG9uGSCJ7DMLB6b0ZUpfPizpF1Rd7iU_h3ZBpi_NDqe4KM6AJZpSMfTWsyQmJBwdTuA=="
org = "mqtt-project"
bucket = "mqtt"

client = InfluxDBClient(url=url, token=token, org=org)
write_api = client.write_api(write_options=SYNCHRONOUS)

def write_node_status(node_id, demand_power, min_power, status, grid_power):

    point = (
        Point("microgrid_nodes")
        .tag("node_id", node_id)
        .tag("status", status)
        .field("demand_power_kw", float(demand_power))
        .field("min_required_power_kw", float(min_power))
        .field("total_grid_power_kw", float(grid_power))
        .time(datetime.datetime.utcnow(), WritePrecision.NS)
    )
    write_api.write(bucket=bucket, org=org, record=point)