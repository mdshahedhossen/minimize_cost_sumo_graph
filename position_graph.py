import matplotlib.pyplot as plt
import traci
import sumolib
import networkx as nx
import random
import time
# from Ev_minimize_travel_cost import Vehicle, MTT
import scipy
import math

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points on the Earth using the Haversine formula.
    Input: latitudes and longitudes in decimal degrees.
    Returns: distance in kilometers.
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Differences in coordinates
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    # Haversine formula
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of Earth in kilometers
    r = 6371
    return c * r

def load_sumo_network_into_graph(net):
    """
    Convert SUMO network to a NetworkX graph.
    
    For each edge, attempt to compute distance using latitude and longitude if available.
    Otherwise, use edge.getLength() (with a conversion if the length is likely in meters).
    """
    G = nx.DiGraph()
    
    for edge in net.getEdges():
        u_node = edge.getFromNode()
        v_node = edge.getToNode()
        u = u_node.getID()
        v = v_node.getID()
        
        # Try to use geographic coordinates to compute the distance.
        try:
            # Attempt to get latitude and longitude attributes.
            # (Ensure your SUMO network file provides these attributes; otherwise, this will raise an exception.)
            lat1 = float(u_node.getAttribute("x"))
            lon1 = float(u_node.getAttribute("y"))
            lat2 = float(v_node.getAttribute("x"))
            lon2 = float(v_node.getAttribute("y"))
            distance = haversine_distance(lat1, lon1, lat2, lon2)
        except Exception as e:
            # If no geographic attributes are found, fallback to the SUMO edge length.
            distance = edge.getLength()/1000
            # If the length is greater than 80, assume it is in meters and convert to kilometers.
            # if distance > 80:
            #     distance = distance / 1000
        
        edge_data = {
            'angle': 0.86,      # Replace with actual angle if needed
            'air_density': 1.205  # Replace with real data if needed
        }
        G.add_edge(u, v, distance=distance, edge_data=edge_data)
    
    return G

if __name__ == "__main__":
    # Start SUMO with TraCI
    sumoBinary = "sumo-gui"  # Use "sumo" for the command-line version
    sumoCmd = [sumoBinary, "-c", "C:/Users/shahe/OneDrive/Desktop/Minimize_energy_Sumo/ottawa_data/network.sumocfg"]
    
    # Load the SUMO network
    net = sumolib.net.readNet("C:/Users/shahe/OneDrive/Desktop/Minimize_energy_Sumo/ottawa_data/network.net.xml")
    
    # Start TraCI to control SUMO
    traci.start(sumoCmd)
    
    # Load the SUMO network into a NetworkX graph
    G = load_sumo_network_into_graph(net)
    total_nodes = len(G.nodes())
    print("Total number of nodes in the graph:", total_nodes)
    print("Nodes in the graph:", list(G.nodes()))
    
    # Simulate initial traffic conditions on the edges
    
    # Initialize the MTT class with the graph and traffic info
    mtt = MTT(G)
    # Define vehicle data and add a vehicle
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
    
    # Add edges from the SUMO network to the MTT object
    for (u, v, data) in G.edges(data=True):
        edge_data = data['edge_data']
        mtt.add_edge(u, v, data['distance'], edge_data, vehicle_id=1)
    
    # Retrieve all junction IDs from SUMO and print them
    all_node_ids = traci.junction.getIDList()
    print("Available nodes in the SUMO network:", all_node_ids)
    total_nodes = len(all_node_ids)
    print("Total number of nodes in the SUMO network:", total_nodes)
    
    def get_valid_source_destination_connected(G):
        """Ensure source and destination are within the largest strongly connected component."""
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
    # source="9269003709"
    # destination="4642081946"
    print(f"Valid source: {source}")
    print(f"Valid destination: {destination}")
    initial_battery_level =90
    initial_charging_rate=0.5
    threshold=20
    
    # *****--------- Designate Charging Stations ---------*****
    # Set 45% of the available nodes as charging stations.
    num_charging_stations = int(0.38 * len(all_node_ids))
    charging_station_nodes = random.sample(all_node_ids, num_charging_stations)
    
    for node in charging_station_nodes:
        charging_speed = 100  # You can adjust this value as needed
        waiting_time = random.randint(0, 25)
        energy_rates=random.uniform(0.20, 0.60)
        mtt.chargingNodes(node, charging_speed=charging_speed, waiting_time=waiting_time,energy_rates=energy_rates)
        print(f"Node {node} set as a charging station with speed {charging_speed} waiting time {waiting_time} and energy rates {energy_rates}")
    
    # Main loop: simulate dynamic routing based on traffic updates
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
            
        
            mtt.write_output_to_file(source, destination, initial_battery_level, path, total_distance, total_time, charge_consumed, total_cost, execution_time, filename="th_20.txt")
            # Advance the simulation by one step
            traci.simulationStep()
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("Simulation interrupted")
    
    # Close the TraCI connection
    traci.close()
