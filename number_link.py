import networkx as nx
import random
import matplotlib.pyplot as plt
from Ev_minimize_travel_cost import Vehicle,MTT
import math
from datetime import datetime
import time

class FixedSizeGraph:
    def __init__(self, width, height, num_nodes, num_links, distance_threshold, seed):
        self.width = width
        self.height = height
        self.num_nodes = num_nodes
        self.num_links = num_links
        self.distance_threshold = distance_threshold
        self.seed = seed
        self.G = nx.Graph()
        random.seed(self.seed)  # Set random seed for reproducibility
        self.charging_stations = []
        self.generate_graph()

    def generate_graph(self):
        # Step 1: Randomly place nodes in a 900x900 km area
        positions = {i: (random.uniform(0, self.width), random.uniform(0, self.height)) for i in range(self.num_nodes)}

        # Step 2: Add nodes
        for node in range(self.num_nodes):
            self.G.add_node(node, pos=positions[node])

        # Step 3: Add edges based on distance threshold
        possible_edges = [(i, j) for i in range(self.num_nodes) for j in range(i + 1, self.num_nodes)]
        random.shuffle(possible_edges)  # Shuffle to ensure randomness
        added_edges = 0

        for u, v in possible_edges:
            if added_edges >= self.num_links:
                break
            x1, y1 = positions[u]
            x2, y2 = positions[v]
            distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)  # Euclidean distance

            # Only add edge if within the distance threshold
            if distance <= self.distance_threshold:
                angle = 0.86  # Constant angle
                air_density = 1.205  # Constant air density
                self.G.add_edge(u, v, distance=distance, edge_data={'angle': angle, 'air_density': air_density})
                added_edges += 1

        # Step 4: Assign charging stations
        num_charging_stations = int(self.num_nodes * 0.45)  # 27% of nodes are charging stations
        self.charging_stations = random.sample(list(self.G.nodes), num_charging_stations)

        for station in self.charging_stations:
            self.G.nodes[station]['charging_station'] = True
            self.G.nodes[station]['charging_speed'] = 100  # Charging speed in kW
            self.G.nodes[station]['waiting_time'] = random.uniform(0, 25)
            self.G.nodes[station]['energy_rates'] = random.uniform(0.20, 0.60)

        # Ensure graph connectivity
        if not nx.is_connected(self.G):
            print("Warning: Graph is not fully connected. Some nodes may be unreachable.")
        else:
            print("Graph is connected.")
    def add_vehicle_and_run_mtt(self, mtt_class, vehicle_class):
        # Initialize your MTT class with the graph
        mtt = mtt_class(self.G)

        # Add vehicle to the system
        vehicle_data = {
            'vehicle_id': 1,
            'mass': 1800,                # kg
            'speed': 50,                 # km/h
            'mass_factor': 1.1,          # Dimensionless
            'rolling_resistance': 0.01,  # Coefficient
            'drag_coefficient': 0.6,     # Coefficient
            'cross_sectional_area': 3.5, # m^2
            'battery_capacity': 100      # kWh
        }

        vehicle_1 = vehicle_class(**vehicle_data)
        mtt.add_vehicle(vehicle_1)

        # Define charging stations in your MTT class
        for node in self.charging_stations:
            charging_speed = self.G.nodes[node]['charging_speed']
            waiting_time = self.G.nodes[node]['waiting_time']
            energy_rates = self.G.nodes[node]['energy_rates']
            # Add charging station details to the MTT class
            mtt.chargingNodes(node, charging_speed=charging_speed, waiting_time=waiting_time,energy_rates=energy_rates)

        # Add the edge details to the MTT graph
        for (u, v, data) in self.G.edges(data=True):
            edge_data = data['edge_data']
            distance = data['distance']
            # Add the edge details to the MTT graph for energy calculations
            mtt.add_edge(u, v, distance, edge_data, vehicle_id=1)

        # Define the source, destination, and initial battery level
        source = random.choice(list(self.G.nodes()))  # Pick a random source node
        destination = random.choice([node for node in self.G.nodes() if node != source])  # Pick a random destination node
        # source=239
        # destination = random.choice([node for node in self.G.nodes() if node != source])  # Pick a random destination node
        # destination=380
        initial_battery_level = 90  # Initial battery level between 50% and 100%
        initial_charging_rate=0.50
        threshold=5
        print(f"Source: {source}, Destination: {destination}, InitialBatteryLevel: {initial_battery_level}")

        # Start execution timer
        start_time = time.time()

        # Calculate the path using your algorithm
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

        end_time = time.time()
        execution_time = end_time - start_time  # Measure execution time
        print(execution_time)
        # path, other_values = result
        path, total_cost, total_distance, total_time, charge_consumed, total_energy_charged, total_charging_cost, execution_time = result
        print(path)
        
        end_time = time.time()
        execution_time = end_time - start_time  # Measure execution time
        print(execution_time)
        # print("Optimal Path with Dynamic Traffic Considerations:", other_values)
        filename="link_1400"
       
        self.write_output_to_file(source, destination, initial_battery_level, path, total_distance, total_time, charge_consumed, total_cost, execution_time, filename)
        
    def write_output_to_file(self, source, destination, initial_battery, path, total_distance, total_time, charge_consumed, total_cost, execution_time, filename):
        # Writing to .txt file
        with open(filename, "w") as file:
            file.write("-----------------------------------------------------\n")
            file.write(f"Source Node: {source}\n")
            file.write(f"Destination Node: {destination}\n")
            file.write(f"Initial Battery Level: {initial_battery}%\n")
            file.write(f"Optimal Path: {' -> '.join(map(str, path))}\n")
            file.write(f"Total Distance: {total_distance:.2f} km\n")
            file.write(f"Total Time: {total_time:.2f} minutes\n")
            file.write(f"Charge Consumed: {charge_consumed:.2f} kWh\n")
            file.write(f"Total Trip Cost: ${total_cost:.2f}\n")
            file.write(f"Execution Time: {execution_time:.4f} seconds\n")
            file.write("-----------------------------------------------------------\n")

        # Visualize the graph with the calculated path (if needed)
        # try:
        #     path = nx.shortest_path(mtt.graph, source, destination, weight='travel_time')
        #     self.visualize_path(source, destination, path)
        # except nx.NetworkXNoPath:
        #     print("No path found.")


    def visualize_graph(self):
        pos = nx.get_node_attributes(self.G, 'pos')

        if not pos:
            print("No node positions available. Ensure nodes have 'pos' attributes.")
            return

        plt.figure(figsize=(10, 10))
        charging_nodes = [node for node in self.charging_stations]
        non_charging_nodes = [node for node in self.G.nodes if node not in self.charging_stations]

        nx.draw_networkx_nodes(self.G, pos, nodelist=charging_nodes, node_color='red', label='Charging Stations', node_size=100)
        nx.draw_networkx_nodes(self.G, pos, nodelist=non_charging_nodes, node_color='blue', label='Regular Nodes', node_size=50)
        nx.draw_networkx_edges(self.G, pos, edge_color='gray')
        nx.draw_networkx_labels(self.G, pos, font_size=8)

        plt.title("Graph Visualization")
        plt.xlabel("X (km)")
        plt.ylabel("Y (km)")
        plt.legend()
        plt.show()

    def print_graph_info(self):
        print(f"Number of nodes: {self.num_nodes}")
        print(f"Number of edges (links): {self.G.number_of_edges()}")

        # total_distance = sum(data['distance'] for _, _, data in self.G.edges(data=True))
        # print(f"Total graph distance: {total_distance:.2f} km")

        print("\nEdge Details (Sample):")
        for u, v, data in list(self.G.edges(data=True))[:10]:  # Print first 10 edges as a sample
            print(f"Edge ({u} -> {v}): Distance = {data['distance']:.2f} km, Angle = {data['edge_data']['angle']:.2f}")

        print("\nCharging Station Details:")
        for station in self.charging_stations:
            print(f"Node {station}: Charging Speed = {self.G.nodes[station]['charging_speed']:.2f} kW")


# Example Usage with User Input
if __name__ == "__main__":
    width, height = 600, 600  # Area dimensions

    total_nodes = 500  # User input for nodes
    total_links = 1600  # User input for edges 1200,1400,1600
    distance_threshold =35  # User input for distance threshold
    seed =22 # Random seed for reproducibility

    ev_routing_system = FixedSizeGraph(width, height, total_nodes, total_links, distance_threshold, seed)

    # Print graph details
    ev_routing_system.print_graph_info()

    # Visualize the graph
    ev_routing_system.visualize_graph()
    ev_routing_system.add_vehicle_and_run_mtt(MTT, Vehicle)

