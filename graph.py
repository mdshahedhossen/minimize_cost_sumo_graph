import matplotlib.pyplot as plt
import traci
import sumolib
import networkx as nx
import random
import time
from Ev_minimize_travel_cost import Vehicle, MTT
import scipy


# Start SUMO with TraCI
sumoBinary = "sumo-gui"  # Use "sumo" for the command-line version
sumoCmd = [sumoBinary, "-c", "C:/Users/shahe/OneDrive/Desktop/Minimize_energy_Sumo/ottawa_data/network.sumocfg"]
net = sumolib.net.readNet("C:/Users/shahe/OneDrive/Desktop/Minimize_energy_Sumo/ottawa_data/network.net.xml")


def load_sumo_network_into_graph(net):
    """Convert SUMO network to a NetworkX graph."""
    G = nx.DiGraph()
    
    for edge in net.getEdges():
        u = edge.getFromNode().getID()
        v = edge.getToNode().getID()
        length = edge.getLength()# Distance
        if length > 80:
            length = length / 1000
        edge_data = {
            'angle': 0.86,  # Replace with actual angle if needed
            'air_density': 1.205  # Replace with real data if needed
        }
        G.add_edge(u, v, distance=length, edge_data=edge_data)
    
    return G


if __name__ == "__main__":
    # Start TraCI to control SUMO
    traci.start(sumoCmd)
    
    # Load SUMO network into NetworkX graph
    G = load_sumo_network_into_graph(net)
    total_nodes = len(G.nodes())
    print("Total number of nodes in the graph:", total_nodes)
    print("Nodes in the graph:", list(G.nodes()))
    
    # Simulate initial traffic conditions on edges
    
    # Initialize MTT class with the graph and traffic info
    mtt = MTT(G)

    # Define vehicle data
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

    # Add vehicle
    vehicle_1 = Vehicle(**vehicle_data)
    mtt.add_vehicle(vehicle_1)



    # Add edges from SUMO network to MTT
    for (u, v, data) in G.edges(data=True):
        edge_data = data['edge_data']
        mtt.add_edge(u, v, data['distance'], edge_data, vehicle_id=1)  # veh2
       

    # Define source, destination, and initial battery level
    # Get a list of all node IDs in the SUMO network
    all_node_ids = traci.junction.getIDList()
    print("Available nodes in the SUMO network:", all_node_ids)
    total_nodes = len(all_node_ids)
    print("Total number of nodes in the SUMO network:", total_nodes)

    # Select a source and destination node from the list
    source = all_node_ids[0] 
    destination = all_node_ids[-1] 
    # source = random.choice(all_node_ids)
    
    # destination = random.choice(all_node_ids)

    # # Ensure source != destination
    # while source == destination:
    #     destination = random.choice(all_node_ids)

    # def get_valid_source_destination_connected(G):
    #     """ Ensure source and destination are in the largest connected component """
    #     if not nx.is_strongly_connected(G):
    #         largest_cc = max(nx.strongly_connected_components(G), key=len)
    #         subgraph = G.subgraph(largest_cc).copy()
    #     else:
    #         subgraph = G

    #     all_node_ids = list(subgraph.nodes())

    #     while True:
    #         source = random.choice(all_node_ids)
    #         destination = random.choice(all_node_ids)

    #         if source != destination:
    #             return source, destination

    # source, destination = get_valid_source_destination_connected(G)
    print(f"Valid source: {source}")
    print(f"Valid destination: {destination}")
    # source='2063153795'
    # destination='1404013521'
    initial_battery_level = 90 
    initial_charging_rate=0.5
    threshold=5
        

    #*****---------make a charging_station 30% of the total nodes--******---------
    
    num_charging_stations = int(0.45* len(all_node_ids))
    
    # Randomly select nodes to be charging stations
    charging_station_nodes = random.sample(all_node_ids, num_charging_stations)

    # Define properties for each charging station and add them using the charging_nodes function
    for node in charging_station_nodes:
        # charging_speed = random.randint(45, 55)  # Random charging speed between 45 and 55
        charging_speed=100
        waiting_time = random.randint(0, 25)  # Random waiting time between 5 and 10
        energy_rates=random.uniform(0.20, 0.60)
        mtt.chargingNodes(node, charging_speed=charging_speed, waiting_time=waiting_time,energy_rates=energy_rates)
        print(f"Node {node} set as a charging station with speed {charging_speed} waiting time {waiting_time} and energy_rates {energy_rates}")

    # Read charging station IDs from a text file
    # charging_station_file = "C:/Users/shahe/OneDrive/Desktop/Sumo_Toronto_output/charging_station.txt"

    # # Load fixed charging station IDs
    # with open(charging_station_file, 'r') as file:
    #     fixed_charging_station_nodes = [line.strip() for line in file.readlines()]

    # # Assign properties to fixed charging stations
    # for node in fixed_charging_station_nodes:
    #     if node in all_node_ids:  # Ensure the node exists in the SUMO network
    #         charging_speed = random.randint(45, 55)  # Random charging speed between 45 and 55
    #         waiting_time = random.randint(0, 25)  # Random waiting time between 0 and 25
    #         mtt.charging_nodes(node, charging_speed=charging_speed, waiting_time=waiting_time)
    #         print(f"Node {node} set as a charging station with speed {charging_speed} and waiting time {waiting_time}")
    #     else:
    #         print(f"Warning: Node {node} from the file does not exist in the SUMO network.")


    # Main loop to simulate dynamic routing based on traffic updates

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
