import matplotlib.pyplot as plt
import traci
import sumolib
import networkx as nx
import random
from Ev_minimize_travel_cost import Vehicle, MTT
import time
import numpy as np
from sklearn.cluster import KMeans

sumoBinary = "sumo-gui"  # Use "sumo" for the command-line version
sumoCmd = [sumoBinary, "-c", "C:/Users/shahe/OneDrive/Desktop/Minimize_energy_Sumo/ottawa_data/network.sumocfg"]
net = sumolib.net.readNet("C:/Users/shahe/OneDrive/Desktop/Minimize_energy_Sumo/ottawa_data/network.net.xml")


def load_sumo_network_into_graph(net):
    """Convert SUMO network to a NetworkX graph."""
    G = nx.DiGraph()
    for edge in net.getEdges():
        u = edge.getFromNode().getID()
        v = edge.getToNode().getID()
        length = edge.getLength()/1000  # Distance
        edge_data = {
            'angle': 0.86,  # Replace with actual angle if needed
            'air_density': 1.205  # Replace with real data if needed
        }
        G.add_edge(u, v, distance=length, edge_data=edge_data)
    return G


def place_charging_stations_by_distance(G, interval=1200):
    """Place charging stations at nodes approximately `interval` km apart."""
    charging_stations = []
    total_distance = 0

    for u, v, data in G.edges(data=True):
        distance = data.get('distance', 0)
        total_distance += distance
        if total_distance >= interval:
            charging_stations.append(v)
            total_distance = 0  # Reset after placing a charging station
    return list(set(charging_stations))
# num_stations = 750  #1000 1251 1501
num_stations = 1501  #1000 1251 1501

def place_charging_stations_by_clustering(G, num_stations=num_stations):
    """Place charging stations by clustering nodes into groups."""
    node_positions = np.array([[float(net.getNode(node).getCoord()[0]), float(net.getNode(node).getCoord()[1])] for node in G.nodes])
    kmeans = KMeans(n_clusters=num_stations)
    kmeans.fit(node_positions)
    cluster_centers = kmeans.cluster_centers_

    charging_stations = []
    for center in cluster_centers:
        closest_node = min(G.nodes, key=lambda node: np.linalg.norm(np.array(net.getNode(node).getCoord()) - center))
        charging_stations.append(closest_node)
    return charging_stations


def place_high_degree_nodes_as_stations(G, num_stations=num_stations):
    """Place charging stations at nodes with highest degree centrality."""
    degree_centrality = nx.degree_centrality(G)
    sorted_nodes = sorted(degree_centrality, key=degree_centrality.get, reverse=True)
    return sorted_nodes[:num_stations]

if __name__ == "__main__":
    traci.start(sumoCmd)
    G = load_sumo_network_into_graph(net)
    total_nodes = len(G.nodes())
    print("Total number of nodes in the graph:", total_nodes)

    mtt = MTT(G)

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

    vehicle_1 = Vehicle(**vehicle_data)
    mtt.add_vehicle(vehicle_1)

    all_node_ids = traci.junction.getIDList()
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

    # source='16874253'
    # destination='12475553343'
    # source='16874253'
    # destination='12475553343
    initial_battery_level = 75
    initial_charging_rate=0.5
    threshold=10

    # **Select placement strategy: Uncomment the desired approach**
    # Charging stations every 1000 meters
    charging_station_nodes = place_charging_stations_by_distance(G, interval=1300)
    
    # Clustering approach with 100 stations
    # charging_station_nodes = place_charging_stations_by_clustering(G, num_stations=100)
    
    # High-degree centrality nodes (key intersections)
    # charging_station_nodes = place_high_degree_nodes_as_stations(G, num_stations=100)

    valid_charging_station_nodes = [node for node in charging_station_nodes if node in all_node_ids]
    for node in valid_charging_station_nodes:
        charging_speed = 100
        waiting_time = random.randint(0, 25)
        energy_rates=random.uniform(0.20,0.60)
        mtt.chargingNodes(node, charging_speed=charging_speed, waiting_time=waiting_time,energy_rates=energy_rates)
        # print(f"Node {node} set as a charging station with speed {charging_speed} and waiting time {waiting_time}")

    try:
        while traci.simulation.getMinExpectedNumber() > 0:
            # Update traffic conditions on each iteration
            # Recalculate the optimal path with dynamic traffic conditions
            result=mtt.complete_logic_dynamic(source, destination, initial_battery_level, initial_charging_rate, vehicle_id=1, threshold=threshold)
            if result is None:
                print("No valid path found.")
            else:
                path, total_cost, total_distance, total_time, charge_consumed, total_energy_charged,total_charging_cost, execution_time = result
                print("-----------------------------------------------------")
                print(f"Optimal Path: {path}")
                print(f"Total Cost: {total_cost:.2f}")
                print(f"Total Distance: {total_distance:.2f} km")
                print(f"Total Travel Time: {total_time:.2f} minutes")
                print(f"Energy Consumed: {charge_consumed:.2f} kWh")
                print(f"Energy Charged: {total_energy_charged:.2f} kWh")
                print(f"Total Charging Cost: {total_charging_cost:.2f}")
                print(f"Execution Time: {execution_time:.4f} sec\n")
                print("-----------------------------------------------------")

            # Measure execution time
          
            # path, other_values = result
            path, total_cost, total_distance, total_time, charge_consumed, total_energy_charged, total_charging_cost, execution_time = result
            print(path)
            # print("Optimal Path with Dynamic Traffic Considerations:", other_values)
            mtt.write_output_to_file(source, destination, initial_battery_level, path, total_distance, total_time, charge_consumed, total_cost, execution_time, filename="cs_test.txt")
            # Advance the simulation by one step
            traci.simulationStep()
            time.sleep(1)
    except KeyboardInterrupt:
        print("Simulation interrupted")

    traci.close()
