import matplotlib.pyplot as plt
import traci
import sumolib
import networkx as nx
import random
import time
from ev_routing_update import Vehicle,MTT
import numpy as np
import math

# Start SUMO with TraCI
# Start SUMO with TraCI
sumoBinary = "sumo-gui"  # Use "sumo" for command-line version
sumoCmd = [sumoBinary, "-c", "C:/Users/shahe/OneDrive/Desktop/sumo_ottawa_output/ottawa_data/network.sumocfg"]
# Load the SUMO network
net = sumolib.net.readNet("C:/Users/shahe/OneDrive/Desktop/sumo_ottawa_output/ottawa_data/network.net.xml")


def load_sumo_network_into_graph(net):
    """Convert SUMO network to a NetworkX graph."""
    G = nx.DiGraph()
    for edge in net.getEdges():
        u = edge.getFromNode().getID()
        v = edge.getToNode().getID()
        length = edge.getLength()/1000 # Distance
            
        edge_data = {
            'angle': 0.86,  # Placeholder angle (adjust as needed)
            'air_density': 1.205  # Placeholder air density
        }
        G.add_edge(u, v, distance=length, edge_data=edge_data)
    return G

grid_size=(25,25)
percentage=0.02
def assign_charging_stations_by_grid(nodes, grid_size=grid_size, percentage=percentage):
    """Assign charging stations based on grid location."""
    charging_stations = []
    x_coords, y_coords = [], []

    # Get positions using TraCI
    for node in nodes:
        try:
            x, y = traci.junction.getPosition(node)
            x_coords.append(x)
            y_coords.append(y)
        except traci.TraCIException:
            continue  # Skip invalid nodes

    if not x_coords or not y_coords:
        raise ValueError("No valid node positions available for charging station assignment.")

    # Grid bins
    x_min, x_max = min(x_coords), max(x_coords)
    y_min, y_max = min(y_coords), max(y_coords)
    x_bins = np.linspace(x_min, x_max, grid_size[1] + 1)
    y_bins = np.linspace(y_min, y_max, grid_size[0] + 1)

    for i in range(grid_size[0]):
        for j in range(grid_size[1]):
            in_cell = [
                node for idx, node in enumerate(nodes)
                if x_bins[j] <= x_coords[idx] < x_bins[j + 1] and y_bins[i] <= y_coords[idx] < y_bins[i + 1]
            ]
            num_charging_stations = math.ceil(len(in_cell) * percentage)
            if num_charging_stations > 0:
                charging_stations += random.sample(in_cell, num_charging_stations)
    return charging_stations


def simulate_traffic_conditions(G):
    """Retrieve real-time traffic data from SUMO and update edge weights."""
    traffic_info = {}
    all_edge_ids = traci.edge.getIDList()

    for u, v in G.edges():
        edge_id = f"{u}_{v}"
        if edge_id in all_edge_ids:
            current_speed = traci.edge.getLastStepMeanSpeed(edge_id)
            allowed_speed = traci.edge.getSpeed(edge_id)
            traffic_factor = allowed_speed / current_speed if current_speed > 0 else 1.5
            traffic_factor = max(0.5, min(traffic_factor, 1.5))
            travel_time = G[u][v]['distance'] / (traffic_factor * 50)
            traffic_info[(u, v)] = {"traffic_factor": traffic_factor, "travel_time": travel_time}
            G[u][v]['distance'] *= traffic_factor
        else:
            traffic_factor = random.uniform(0.5, 1.5)
            travel_time = G[u][v]['distance'] / (traffic_factor * 50)
            traffic_info[(u, v)] = {"traffic_factor": traffic_factor, "travel_time": travel_time}
    return traffic_info

def choose_valid_source_and_destination(G):
    """
    Chooses a random source and destination from the graph G where a path exists.
    """
    nodes = list(G.nodes())
    while True:
        source = random.choice(nodes)
        destination = random.choice(nodes)
        if source != destination and nx.has_path(G, source, destination):
            return source, destination  # Return valid source and destination


if __name__ == "__main__":
    traci.start(sumoCmd)

    G = load_sumo_network_into_graph(net)
    all_node_ids = traci.junction.getIDList()

    print("Total nodes:", len(G.nodes()))
    print("SUMO nodes:", list(G.nodes()))

    # Vehicle data
    vehicle_data = {
        'vehicle_id': 1,
        'mass': 1800,
        'speed': 50,
        'mass_factor': 1.1,
        'rolling_resistance': 0.01,
        'drag_coefficient': 0.6,
        'cross_sectional_area': 3.5,
        'battery_capacity': 100
    }

    # Initialize MTT and add vehicle
    mtt = MTT(G, traffic_info={})
    vehicle_1 = Vehicle(**vehicle_data)
    mtt.add_vehicle(vehicle_1)

    # Assign charging stations
    charging_station_nodes = assign_charging_stations_by_grid(all_node_ids, grid_size=grid_size, percentage=percentage)
    print(f"Charging stations (1% by grid): {len(charging_station_nodes)}")

    for node in charging_station_nodes:
        # charging_speed = random.randint(45, 55)
        charging_speed=100
        waiting_time = random.randint(0, 25)
        mtt.charging_nodes(node, charging_speed=charging_speed, waiting_time=waiting_time)
        print(f"Node {node}: Charging speed {charging_speed}, waiting time {waiting_time}")

        # Select a source and destination node from the list
    # source = all_node_ids[0] 
    # destination = all_node_ids[-1] 
    

    def get_valid_source_destination_connected(G):
        """ Ensure source and destination are in the largest connected component """
        if not nx.is_strongly_connected(G):
            largest_cc = max(nx.strongly_connected_components(G), key=len)
            subgraph = G.subgraph(largest_cc).copy()
        else:
            subgraph = G

        all_node_ids = list(subgraph.nodes())

        while True:
            source = random.choice(all_node_ids)
            destination = random.choice(all_node_ids)

            if source != destination:
                return source, destination

    source, destination = get_valid_source_destination_connected(G)
    print(f"Valid source: {source}")
    print(f"Valid destination: {destination}")

    # source='2063153795'
    # destination='1404013521'
    # source='16874253'
    # destination='12475553343'
    # source ='8630521039'
    # destination='1999586977'
   
    initial_battery_level = 90
    # Get all node IDs from the SUMO network
    
    
   # Ensure you have the NetworkX graph (G) loaded
    # G = load_sumo_network_into_graph(net)

    # # Choose valid source and destination
    # source, destination = choose_valid_source_and_destination(G)
    # print(f"Valid Source: {source}, Valid Destination: {destination}")

    # initial_battery_level = 90

    try:
        while traci.simulation.getMinExpectedNumber() > 0:
            traffic_info = simulate_traffic_conditions(G)
            mtt.update_traffic_info(traffic_info)

            # result = mtt.compelete_Logic_dynamic(source, destination, initial_battery_level, vehicle_id=1)
            # path, other_values = result
            # print("Optimal Path:", path)
            # print("Details:", other_values)
            # mtt.write_output_to_file(source, destination, initial_battery_level, path, other_values)
            result= mtt.compelete_Logic_dynamic(source, destination, initial_battery_level, vehicle_id=1)
            print(result)
            path, other_values = result
            print(path)
            print("Optimal Path with Dynamic Traffic Considerations:",other_values)
            mtt.write_output_to_file(source, destination, initial_battery_level, path, other_values)

            try:
                path = nx.shortest_path(mtt.graph, source, destination, weight='travel_time')
            except nx.NetworkXNoPath:
                path = None
            mtt.draw_graph_with_path(source, destination, path=path)

            traci.simulationStep(5)
            time.sleep(1)
    except KeyboardInterrupt:
        print("Simulation interrupted")
    finally:
        traci.close()
