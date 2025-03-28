import networkx as nx
import math
import time
import matplotlib.pyplot as plt
from collections import deque
import random
import heapq


class Vehicle:
    def __init__(self, vehicle_id, mass, speed, mass_factor, rolling_resistance, drag_coefficient, cross_sectional_area, battery_capacity=100):
        self.vehicle_id = vehicle_id
        self.mass = mass
        self.speed = speed
        self.mass_factor = mass_factor
        self.rolling_resistance = rolling_resistance
        self.drag_coefficient = drag_coefficient
        self.cross_sectional_area = cross_sectional_area
        self.battery_capacity = battery_capacity

    def get_vehicle_data(self):
        return {
            "mass": self.mass,
            "speed": self.speed,
            "mass_factor": self.mass_factor,
            "rolling_resistance": self.rolling_resistance,
            "drag_coefficient": self.drag_coefficient,
            "cross_sectional_area": self.cross_sectional_area,
            "battery_capacity": self.battery_capacity
        }

class MTT:
    def __init__(self, nxGraph):
        self.charging_nodes = {}
        self.graph = nxGraph
        self.vehicles = {}
        self.energy_rates = {} 

    def add_vehicle(self, vehicle: Vehicle):
        self.vehicles[vehicle.vehicle_id] = vehicle

    def chargingNodes(self, node, charging_speed, waiting_time, energy_rates):
        # self.charging_nodes[node] = {'charging_speed': charging_speed, 'waiting_time': waiting_time, 'energy_rates': energy_rates, 'is_booked': False}
        self.charging_nodes[node] = {
            'charging_speed': charging_speed,
            'waiting_time': waiting_time,
            'energy_rates': energy_rates,
            'is_booked': False
    }
        self.energy_rates[node] = energy_rates


    def calculate_charging_time(self, battery_level, required_charge, charging_speed):
        remaining_capacity = battery_level
        charge_needed=required_charge - remaining_capacity
        # Charge needed (kWh) / Charger power (kW) = Hours of charging time
        charging_time = (charge_needed / charging_speed)*60 #convert hours to minutes
        charging_time = max(0, charging_time)
        return charging_time

    def charging_station_available(self, node):
        return not self.charging_nodes[node]['is_booked']

    def add_edge(self, from_node, to_node, distance, edge_data, vehicle_id):
        vehicle = self.vehicles[vehicle_id]
        vehicle_data = vehicle.get_vehicle_data()
        speed = edge_data.get("speed", vehicle_data["speed"])
        real_time_speed = self.get_real_time_speed(speed)
        energy_consumption = self.calculate_energy_consumption(vehicle_id, edge_data, distance)
        travel_time = (distance / real_time_speed) * 60  # Convert hours to minutes
        # self.graph.add_edge(from_node, to_node, distance=distance, energy_consumption=energy_consumption, travel_time=distance / real_time_speed)
        self.graph.add_edge(from_node,to_node, distance=distance,energy_consumption=energy_consumption, travel_time=travel_time, edge_data=edge_data)
        print(f"Edge ({from_node}, {to_node}) speed: {real_time_speed} km/h")

    def draw_graph(self):
        pos = nx.spring_layout(self.graph, seed=7)
        nx.draw(self.graph, pos, with_labels=True, node_size=1000)
        edge_labels = nx.get_edge_attributes(self.graph, 'distance')
        nx.draw_networkx_edge_labels(self.graph, pos, edge_labels=edge_labels)
        plt.show()

    def calculate_energy_consumption(self, vehicle_id, edge_data, distance):
        vehicle = self.vehicles[vehicle_id]
        vehicle_data = vehicle.get_vehicle_data()
        M = vehicle_data['mass']
        v0 = vehicle_data['speed']
        m = vehicle_data['mass_factor']
        f = vehicle_data['rolling_resistance']
        c = vehicle_data['drag_coefficient']
        A = vehicle_data['cross_sectional_area']

        alpha_deg = edge_data.get("angle", 0.86)
        p = edge_data.get("air_density", 1.225)
        d = distance
        cos_alpha = math.cos(math.radians(alpha_deg))
        sin_alpha = math.sin(math.radians(alpha_deg))
        dv_dt=0.3
 
        g = 9.8
        energy_consumption = (1 / 3600) * (M * g * (f * cos_alpha + sin_alpha) + 0.0386 * (p * c * A * v0**2) + (M + m) * dv_dt) * d
        return energy_consumption


    def get_real_time_speed(self, vehicle_speed, base_speed=None):
        return base_speed if base_speed else vehicle_speed  # Fixed speed without randomization

    def update_travel_times(self, vehicle_id):
        vehicle = self.vehicles[vehicle_id]
        vehicle_speed = vehicle.speed
        for u, v, data in self.graph.edges(data=True):
            base_speed = data['edge_data'].get("speed", vehicle_speed)
            real_time_speed = self.get_real_time_speed(vehicle_speed, base_speed)
            data['travel_time'] = data['distance'] / real_time_speed
            

    def battery_reduction(self, vehicle_id, energy_consumption, battery_level,distance):
        vehicle = self.vehicles[vehicle_id]
        battery_capacity = vehicle.battery_capacity
        energy_per_km = energy_consumption / distance
        reduction_per_km = (energy_per_km / battery_capacity) * 100  # Battery reduction as percentage
        total_reduction = reduction_per_km * distance # Total reduction based on distance
        new_battery_level = battery_level - total_reduction
        return max(new_battery_level, 0)
    
    def total_battery_reduction(self, source, destination, vehicle_id):
        try:
            path = nx.shortest_path(self.graph, source, destination, weight='travel_time')
            total_reduction = 0
            for i in range(len(path) - 1):
                from_node = path[i]
                to_node = path[i + 1]
                edge_data = self.graph.get_edge_data(from_node, to_node)
                
                if edge_data and 'distance' in edge_data:
                    distance = edge_data['distance']
                    energy_consumption = self.calculate_energy_consumption(vehicle_id, edge_data['edge_data'], distance)
                    total_reduction += energy_consumption
                else:
                    print(f"Edge data missing between {from_node} and {to_node}")
            
            return total_reduction
        except nx.NetworkXNoPath:
            print(f"No path found from {source} to {destination}.")
            return None
    
    def calculate_required_charge(self, current_node, destination, battery_level, graph, vehicle_id, threshold):
      
        print("Debugging calculate_required_charge")
        print("Type of graph:", type(graph))  
        print("Current Node:", current_node)  

        try:
            path = nx.dijkstra_path(graph, current_node, destination, weight='distance')
            print(f" Calculating required charge. Path: {path}")
        except nx.NetworkXNoPath:
            print(f" No path found from {current_node} to {destination}. Returning infinity.")
            return float('inf')

        try:
            total_energy_needed = sum([
                self.calculate_energy_consumption(vehicle_id, 
                                                graph[path[i]][path[i+1]].get('edge_data', {}), 
                                                graph[path[i]][path[i+1]].get('distance', 0))
                for i in range(len(path) - 1)
            ])
            print("total energy needed from requred charge",total_energy_needed)
        except KeyError as e:
            print(f"Missing data in graph at {e}. Returning infinity.")
            return float('inf')

        buffer_charge = total_energy_needed * 0.10  # 10% buffer
        # required_charge = max(0, total_energy_needed - battery_level + threshold + buffer_charge)
        required_charge = max(0, total_energy_needed + threshold+buffer_charge - battery_level)

        # print(f"Total Energy Needed: {total_energy_needed:.2f} kWh")
        print(f"Extra Buffer Charge (10%): {buffer_charge:.2f} kWh")
        print(f"Battery Level: {battery_level:.2f} kWh")
        print(f"Required Additional Charge: {required_charge:.2f} kWh")
        
        return required_charge

        
    def calculate_charging_rate(node, charging_stations, energy_rates):
        """
        Calculates the initial charging rate and current station charging rate.
        """
        if node in charging_stations:
            return charging_stations[node]['charging_speed']
        return energy_rates.get(node, 1)
   
    # def calculate_path_cost(self, graph, path, vehicle_id, energy_rates):
    #     total_cost = 0
    #     for i in range(len(path) - 1):
    #         from_node, to_node = path[i], path[i + 1]
    #         # edge_data = graph[from_node][to_node]
    #         distance = edge_data['distance']
    #         edge_data = graph[from_node][to_node]['edge_data']
            
    #         # Dynamically calculate energy consumed on this edge
    #         energy_consumed = self.calculate_energy_consumption(vehicle_id, edge_data, distance)
            
    #         # Get the energy rate at the start node
    #         energy_rate = energy_rates.get(from_node, 1)
            
    #         #  Calculate cost for this edge
    #         total_cost += energy_consumed * energy_rate
            
    #     return total_costy
    
    def calculate_travel_cost(self, from_node, to_node, battery_level, current_energy_rate, vehicle_id):
        # Step 1: If direct edge exists, use it
        if self.graph.has_edge(from_node, to_node):
            edge_data = self.graph[from_node][to_node]['edge_data']
            distance = self.graph[from_node][to_node]['distance']
            energy_consumed = self.calculate_energy_consumption(vehicle_id, edge_data, distance)
            travel_cost = energy_consumed * current_energy_rate

            # Deduct battery level
            battery_level -= energy_consumed
            if battery_level < 0:
                print(f"Battery depleted before reaching {to_node}!")
                return float('inf')

            print(f"Direct travel: {from_node} → {to_node} | Distance: {distance} km | Energy: {energy_consumed:.2f} kWh | Cost: {travel_cost:.2f}")
            return travel_cost  

        # Step 2: No direct edge → Use shortest path instead
        try:
            path = nx.dijkstra_path(self.graph, from_node, to_node, weight="distance")
            if not path or len(path) < 2:
                return float('inf')  # No valid path

            print("shahed", path)
            total_cost = 0

            print(f"Using alternative path: {path}")

            for i in range(len(path) - 1):
                u, v = path[i], path[i+1]

                # Validate Edge Exists Before Accessing
                if not self.graph.has_edge(u, v):
                    print(f"No valid edge found between {u} → {v}. Skipping...")
                    return float('inf')

                edge_data = self.graph[u][v]['edge_data']
                distance = self.graph[u][v]['distance']
                energy_consumed = self.calculate_energy_consumption(vehicle_id, edge_data, distance)

                cost = energy_consumed * current_energy_rate
                total_cost += cost  

                # Deduct battery level
                battery_level -= energy_consumed
                if battery_level < 0:
                    print(f"Battery depleted before reaching {v}!")
                    return float('inf')

                print(f"Alternative Path Travel: {u} → {v} | Distance: {distance} km | Energy: {energy_consumed:.2f} kWh | Battery:{battery_level:.2f} % | Rate: {current_energy_rate:.2f} | Cost: {cost:.2f}")

            return total_cost

        except nx.NetworkXNoPath:
            print(f"No valid path from {from_node} to {to_node}. Returning infinite cost.")
            return float('inf')

    
    # def calculate_travel_cost(self, from_node, to_node, battery_level, current_energy_rate, vehicle_id):

    #     # Step 1: If direct edge exists, use it
    #     if self.graph.has_edge(from_node, to_node):
    #         edge_data = self.graph[from_node][to_node]['edge_data']
    #         distance = self.graph[from_node][to_node]['distance']
    #         energy_consumed = self.calculate_energy_consumption(vehicle_id, edge_data, distance)
    #         travel_cost = energy_consumed * current_energy_rate

    #         print(f"Direct travel: {from_node} → {to_node} | Distance: {distance} km | Energy: {energy_consumed:.2f} kWh | Cost: {travel_cost:.2f}")
    #         return travel_cost  # Immediate return if direct path exists!

    #     # Step 2: No direct edge → Use shortest path instead
    #     try:
    #         path = nx.dijkstra_path(self.graph, from_node, to_node, weight="distance")
    #         print("shahed",path)
    #         total_cost = 0

    #         print(f"Using alternative path: {path}")

    #         for i in range(len(path) - 1):
    #             u, v = path[i], path[i+1]

    #             # Validate Edge Exists Before Accessing
    #             if not self.graph.has_edge(u, v):
    #                 print(f"No valid edge found between {u} → {v}. Skipping...")
    #                 return float('inf')  # No valid path

    #             edge_data = self.graph[u][v]['edge_data']
    #             distance = self.graph[u][v]['distance']
    #             energy_consumed = self.calculate_energy_consumption(vehicle_id, edge_data, distance)

    #             cost = energy_consumed * current_energy_rate  # Corrected Cost Calculation
    #             total_cost += cost  #  Accumulate cost

    #             print(f"Alternative Path Travel: {u} → {v} | Distance: {distance} km | Energy: {energy_consumed:.2f} kWh | Battery:{battery_level:.2f} % | Rate: {current_energy_rate:.2f} | Cost: {cost:.2f}")

    #         return total_cost

    #     except nx.NetworkXNoPath:
    #         print(f" No valid path from {from_node} to {to_node}. Returning infinite cost.")
    #         return float('inf')

    
    def update_charging_rate(self, initial_rate, initial_battery, charge_added, station_rate):
        """
        Updates the charging rate dynamically after charging at a station.
        """
        total_battery_after_charge = initial_battery + charge_added
        if total_battery_after_charge == 0:
            return initial_rate  # Avoid division by zero

        new_rate = ((initial_rate * initial_battery) + (station_rate * charge_added)) / total_battery_after_charge
        return new_rate
    

    def find_nearest_charging_station(self, current_node, graph, charging_costs):
        """Finds the closest charging station from the current node using shortest path distance."""
        
        if not charging_costs:
            print(" No charging stations available in the graph.")
            return None

        # Filter only reachable charging stations
        reachable_stations = [station for station in charging_costs.keys() if nx.has_path(graph, current_node, station)]

        if not reachable_stations:
            print(f"No reachable charging stations from {current_node}.")
            return None

        # Find the closest charging station based on shortest path distance
        min_distance = float('inf')
        closest_station = None

        for station in reachable_stations:
            try:
                distance = nx.shortest_path_length(graph, current_node, station, weight='distance')
                if distance < min_distance:
                    min_distance = distance
                    closest_station = station
            except nx.NetworkXNoPath:
                continue

        if closest_station is not None:
            print(f"Nearest Charging Station: {closest_station} | Distance: {min_distance} km")
        else:
            print("No valid charging station found.")

        return closest_station


    def bfs_reachable_nodes(self, graph, current_node, battery_level,destination, vehicle_id, threshold):
        """Finds all reachable charging stations and the destination based on current battery level."""
        
        queue = deque([(current_node, battery_level)])  # BFS Queue: (node, remaining battery)
        visited = set()
        reachable_stations = []

        print(f"BFS Started | Current Node: {current_node} | Battery Level: {battery_level:.2f}% | Destination: {destination}") 
        print("thersho form BFS",threshold)

        while queue:
            node, battery = queue.popleft()  # Dequeue node

            if node in visited:
                continue  # Skip already processed nodes

            visited.add(node)

            # Check if this node is a charging station or the destination
            if node == destination or (node in self.charging_nodes and nx.has_path(graph, node, destination)):
                print(f"Adding Reachable Node: {node} | Battery Left: {battery:.2f}%")
                reachable_stations.append(node)

            # Explore neighbors
            for neighbor in graph.neighbors(node):
                if not graph.has_edge(node, neighbor):
                    continue

                edge_data = graph[node][neighbor].get('edge_data', None)
                if edge_data is None:
                    print(f"Missing edge data between {node} → {neighbor}. Skipping...")
                    continue

                distance = graph[node][neighbor]['distance']

                try:
                    energy_required = self.calculate_energy_consumption(vehicle_id, edge_data, distance)
                except Exception as e:
                    print(f"Error calculating energy between {node} → {neighbor}: {e}")
                    continue

                new_battery = battery - energy_required  # Battery after reaching the neighbor
                new_battery = max(new_battery, 0)  # Ensure battery doesn't go below 0

                # Only add to queue if battery level is sufficient
                if new_battery >= threshold and neighbor not in visited:
                    queue.append((neighbor, new_battery))

        print(f"BFS Complete | Reachable Stations: {reachable_stations}")
        return reachable_stations

   # when current node not CS
    def CalCost(self, x, L, destination,battery_level,current_energy_rate,vehicle_id,threshold):
        """Calculates the best next node from x by minimizing total travel cost."""
        best_next_node = None
        min_cost = float('inf')
        best_energy_rate = None

        for l in L:
            if l == destination:
                # Case 1: `l` is the Destination
                travel_cost = self.calculate_travel_cost(x, l, battery_level,current_energy_rate,vehicle_id)
                Cl = travel_cost  # Total cost is just the travel cost
            else:
                # Case 2: `l` is a Charging Station
                travel_cost_xl = self.calculate_travel_cost(x, l, battery_level,current_energy_rate,vehicle_id)
                charging_cost = 0.01 * self.charging_nodes[l]['energy_rates']  # Assume 1% charge cost
                travel_cost_lD = self.calculate_travel_cost(l, destination, battery_level, self.charging_nodes[l]['energy_rates'],vehicle_id)
                
                Cl = travel_cost_xl + charging_cost + travel_cost_lD  # Total cost

            if Cl < min_cost:
                min_cost = Cl
                best_next_node = l
                best_energy_rate = self.charging_nodes.get(l, {}).get('energy_rates', None)

        return best_next_node, min_cost, best_energy_rate

    
   # When current node is CS
    def CalCostCharging(self, x, L, destination, battery_level, current_energy_rate, vehicle_id, threshold):
        cost_list = []

        print(f"\n DEBUG: Entering CalCostCharging | Current Node: {x} | Battery: {battery_level}% | Destination: {destination}")

        for l in L:
            #  Step 1: Prevent looping back to current node
            if l == x:
                continue  # Prevent selecting the current node again
            
            #  Step 2: Check if the destination is reachable directly
            energy_needed = self.calculate_required_charge(
                current_node=x, 
                destination=l, 
                battery_level=battery_level,  
                graph=self.graph,  
                vehicle_id=vehicle_id,  
                threshold=threshold  
            )

            print(f" Checking node {l} | Energy Needed: {energy_needed:.2f} kWh | Battery Available: {battery_level:.2f}%")

            if l == destination and battery_level >= energy_needed:
                print(f"Direct Destination Chosen: {destination} (No Charging Required)")
                return destination, self.calculate_travel_cost(x, destination, battery_level, current_energy_rate, vehicle_id), current_energy_rate
            
            # Step 3: If node `l` is a charging station
            energy_needed_to_l = self.calculate_required_charge(x, l, battery_level, self.graph, vehicle_id, threshold)
            energy_needed_to_d = self.calculate_required_charge(l, destination, battery_level, self.graph, vehicle_id, threshold)

            print(f"{l} → {destination} | Energy Needed: {energy_needed_to_d:.2f} kWh | Battery Left After {l}: {battery_level - energy_needed_to_l:.2f}%")

            # ✅ **NEW FIX: Ensure the EV has enough battery before moving**
            if battery_level < energy_needed_to_l + threshold:
                print(f"⚠️ Warning: Not enough battery to reach {l}. Need to charge at {x} first.")
                charge_needed = max(0, energy_needed_to_l - battery_level + threshold)
                charge_cost_x = charge_needed * self.charging_nodes[x]['energy_rates']
                travel_cost_xl = self.calculate_travel_cost(x, l, battery_level + charge_needed, current_energy_rate, vehicle_id)
                total_cost = charge_cost_x + travel_cost_xl
                print(f"Charging at {x} before moving to {l} | Charge Needed: {charge_needed:.2f} kWh | Total Cost: {total_cost:.2f}")
                return l, total_cost, current_energy_rate  # **Force charging first**

            # ✅ **Case: Can reach `l` without charging at `x`**
            travel_cost_xl = self.calculate_travel_cost(x, l, battery_level, current_energy_rate, vehicle_id)
            charge_cost = 0.01 * self.charging_nodes[l]['energy_rates']  # **1% charge cost at `l`**
            travel_cost_lD = self.calculate_travel_cost(l, destination, battery_level - energy_needed_to_l, self.charging_nodes[l]['energy_rates'], vehicle_id)
            Cl = travel_cost_xl + charge_cost + travel_cost_lD
            print(f"Choosing {l} without charging at {x} | Cost: {Cl:.2f}")

            heapq.heappush(cost_list, (Cl, l, self.charging_nodes.get(l, {}).get('energy_rates', current_energy_rate)))

        # ✅ **Choose the best next node (cheapest cost)**
        if cost_list:
            min_cost, best_next_node, best_energy_rate = heapq.heappop(cost_list)
            print(f"✅ Best Next Move: {best_next_node} | Cost: {min_cost:.2f} | Rate: {best_energy_rate}")
            return best_next_node, min_cost, best_energy_rate
        else:
            print("❌ No valid path found. Returning default values.")
            return None, float('inf'), current_energy_rate  # No valid path found

        
    def find_nearest_valid_node(self, current_node, graph, battery_level, vehicle_id):
       
        min_distance = float('inf')
        best_node = None

        print(f"Searching for nearest valid node from {current_node} | Battery: {battery_level:.2f}%")

        for neighbor in graph.neighbors(current_node):  # Iterate only over direct neighbors
            if not graph.has_edge(current_node, neighbor):
                continue

            edge_data = graph[current_node][neighbor].get('edge_data', None)
            if edge_data is None:
                print(f"Missing edge data for {current_node} → {neighbor}. Skipping...")
                continue

            distance = graph[current_node][neighbor]['distance']

            try:
                energy_required = self.calculate_energy_consumption(vehicle_id, edge_data, distance)
            except Exception as e:
                print(f" Error calculating energy for {current_node} → {neighbor}: {e}")
                continue

            if battery_level < energy_required:
                print(f"Cannot reach {neighbor}. Battery too low (Need: {energy_required:.2f}%). Skipping...")
                continue

            if distance < min_distance:
                min_distance = distance
                best_node = neighbor

        if best_node is None:
            print("No valid alternative node found. Vehicle is stuck.")
            return None

        print(f" Redirecting to closest reachable node: {best_node} (Distance: {min_distance} km)")
        return best_node
    
    
    def complete_logic_dynamic(self, source, destination, battery_level,current_charging_rate, vehicle_id, threshold):
      
        start_time = time.time()  # Start execution time tracking
        current_node=source
        path = [current_node]  # Stores the path taken
        total_time = 0
        total_cost = 0
        total_distance = 0
        total_energy_charged = 0
        total_charging_cost = 0
        charge_consumed = 0
        visited_charging_stations = []
        initial_battery_level = battery_level
        vehicle=self.vehicles[vehicle_id]
        threshold=10
        battery_level = min(max(battery_level, 0), 100)
        energy_rates = {}
        # energy_rates[source] = initial_charging_rate
        initial_charging_rate=current_charging_rate

        while current_node != destination:
            try:
                #  Step 1: Find the best path segment dynamically
                path_segment = nx.dijkstra_path(self.graph, current_node, destination, weight="distance")
                print(f"Found path segment: {path_segment}")
                
                # Step 2: Estimate energy required to reach the destination
                # estimated_energy = self.total_battery_reduction(current_node, destination, vehicle_id)
                estimated_energy = sum(self.total_battery_reduction(path_segment[i], path_segment[i+1], vehicle_id) for i in range(len(path_segment)-1))
                print(f"Estimated Energy Consumption: {estimated_energy:.2f}%")

                for i in range(len(path_segment) - 1):
                    next_node = path_segment[i + 1]
                    
                    # Step 3: If at a charging station, process charging decision
                    if current_node in self.charging_nodes:
                        print("shhh",type(self.charging_nodes))
                        print(f" Current node {current_node} is a charging station.")  
                        
                        charging_speed = self.charging_nodes[current_node]['charging_speed']
                        station_rate = self.charging_nodes[current_node]['energy_rates']
                        waiting_time = self.charging_nodes[current_node]['waiting_time']
                        estimated_energy_needed = self.total_battery_reduction(current_node, destination, vehicle_id)
                        print(f"Estimated Energy Consumption: {estimated_energy:.2f}%")
                        charge_needed = max(0, min(100 - battery_level, estimated_energy_needed+threshold))

                        if charge_needed > 0:  # **EV needs charging**
                            print(f"Charging at station {current_node} | Needed: {charge_needed:.2f} kWh")

                            total_time += waiting_time  # Account for queue time
                            charging_time = (charge_needed / charging_speed) * 60  # Convert to minutes
                            charging_cost = charge_needed * station_rate

                            total_charging_cost += charging_cost
                            total_energy_charged += charge_needed
                            battery_level = min(100, battery_level + charge_needed)
                            total_time += charging_time  # Update total time

                            # **Update charging rate dynamically**
                            prev_rate = current_charging_rate
                            prev_charge = battery_level - charge_needed  # Battery before charge
                           

                            # prev_charge = battery_level  # Battery before charge
                            new_charge = charge_needed  # Battery added
                            # current_charging_rate = ((prev_rate * prev_charge) + (station_rate * new_charge)) / (prev_charge + new_charge)
                            current_charging_rate = ((prev_rate * prev_charge) + (station_rate * new_charge)) / (battery_level)

                            print(f" Charging completed at {current_node}. Battery: {battery_level:.2f}% | New Rate: {current_charging_rate:.3f} cost/kWh")
                            visited_charging_stations.append((current_node, charge_needed, station_rate))

                        # Step 3.1: Find reachable charging stations and the destination
                        reachable_stations = self.bfs_reachable_nodes(self.graph, current_node,battery_level,destination, vehicle_id, threshold)
                        valid_stations = []
                        for station in reachable_stations:
                            if station == destination or (station in self.charging_nodes and station not in path):
                                current_to_dest = nx.shortest_path_length(self.graph, source=current_node, target=destination, weight="distance")
                                station_to_dest = nx.shortest_path_length(self.graph, source=station, target=destination, weight="distance")

                                if station_to_dest < current_to_dest:  # Ensure station brings us closer to destination
                                    valid_stations.append(station)

                        if valid_stations:
                            best_next_node, cost, rate = self.CalCostCharging(
                                current_node, valid_stations, destination, battery_level, current_charging_rate, vehicle_id, threshold
                            )
                            print(f"Choosing next station or destination: {best_next_node} (Cost: {cost}, Rate: {rate})")
                            # if self.graph.has_edge(current_node, destination):
                            #     distance = self.graph[current_node][destination]['distance']
                            #     edge_data = self.graph[current_node][destination].get('edge_data', {})
                            # else:
                            #     shortest_path = nx.shortest_path(self.graph, source=current_node, target=destination, weight="distance")
                            #     distance = sum(self.graph[shortest_path[i]][shortest_path[i + 1]]['distance'] for i in range(len(shortest_path) - 1))
                            #     edge_data = {}
                            # if best_next_node == destination or next_node==destination:
                            if best_next_node == destination or (self.graph.has_edge(current_node, destination) and best_next_node is None):
                                print(f"shahed please Directly moving to destination {destination}.")
                                shortest_path = nx.shortest_path(self.graph, source=current_node, target=destination, weight="distance")
                                print("shahed your path is",shortest_path )

                                for intermediate_node in shortest_path[1:]:  # Exclude the first node (current_node)
                                    if intermediate_node not in path:
                                        path.append(intermediate_node)

                                # **Ensure distance and cost updates correctly**
                                if self.graph.has_edge(current_node, destination):
                                    distance = self.graph[current_node][destination]['distance']
                                    edge_data = self.graph[current_node][destination].get('edge_data', {})
                                else:
                                    distance = sum(
                                        self.graph[shortest_path[i]][shortest_path[i + 1]]['distance'] for i in range(len(shortest_path) - 1)
                                    )
                                    edge_data = {}

                                total_distance += distance
                                total_cost += cost
                                speed = self.vehicles[vehicle_id].speed  # km/h
                                travel_time = (distance / speed) * 60  # Convert to minutes
                                total_time += travel_time

                                # **Calculate energy consumption safely**
                                charge_consumed += self.calculate_energy_consumption(vehicle_id, edge_data, distance)

                                if destination not in path:  # Prevent duplicate entries
                                    path.append(destination)

                                return (
                                    path, total_cost, total_distance, total_time, charge_consumed,
                                    total_energy_charged, total_charging_cost, time.time() - start_time
                                )
                            elif battery_level<15:
                                print(f"⚠️ Battery critically low ({battery_level:.2f}%). Must charge now at {current_node}.")
                                charge_needed = max(0, min(100 - battery_level, estimated_energy_needed + threshold))

                                # **Find cheaper station if possible**
                                cheaper_stations = [
                                    s for s in self.charging_nodes if self.charging_nodes[s]['energy_rates'] < rate
                                ]

                                if cheaper_stations:
                                    # **Pick the nearest cheaper station**
                                    closest_cheaper_station = min(
                                        cheaper_stations, key=lambda s: nx.shortest_path_length(self.graph, source=current_node, target=s, weight="distance")
                                    )
                                    energy_needed_to_cheaper = self.total_battery_reduction(current_node, closest_cheaper_station, vehicle_id)

                                    # **Charge only what’s needed to reach a cheaper station**
                                    charge_needed = max(0, min(energy_needed_to_cheaper + threshold, 100 - battery_level))
                                    print(f"⚠️ Taking **minimum** charge ({charge_needed:.2f}%) at {current_node} to reach cheaper station {closest_cheaper_station}.")
                                else:
                                    # No cheaper station available, charge fully
                                    print(f"⚠️ No cheaper station available. Taking full charge ({charge_needed:.2f}%).")

                                # **Charge at the current station**
                                charging_speed = self.charging_nodes[current_node]['charging_speed']
                                station_rate = self.charging_nodes[current_node]['energy_rates']
                                waiting_time = self.charging_nodes[current_node]['waiting_time']

                                total_time += waiting_time  # Account for queue time
                                charging_time = (charge_needed / charging_speed) * 60  # Convert to minutes
                                charging_cost = charge_needed * station_rate

                                total_charging_cost += charging_cost
                                total_energy_charged += charge_needed
                                battery_level = min(100, battery_level + charge_needed)
                                total_time += charging_time  # Update total time

                                # **Update charging rate dynamically**
                                prev_rate = current_charging_rate
                                prev_charge = battery_level - charge_needed  # Battery before charge
                                new_charge = charge_needed  # Battery added
                                current_charging_rate = ((prev_rate * prev_charge) + (station_rate * new_charge)) / (battery_level)

                                print(f"🔋 Charging completed at {current_node}. Battery: {battery_level:.2f}% | New Rate: {current_charging_rate:.3f} cost/kWh")
                                visited_charging_stations.append((current_node, charge_needed, station_rate))

                                return (
                                    path, total_cost, total_distance, total_time, charge_consumed,
                                    total_energy_charged, total_charging_cost, time.time() - start_time
                                )


                        else:
                            print("No reachable charging stations found, but destination might be reachable.")
                            # If destination is reachable, move to it
                            if destination in reachable_stations:
                                print(f" Moving directly to destination {destination}.")
                                distance = self.graph[current_node][destination]['distance']
                                edge_data = self.graph[current_node][destination].get('edge_data', {})
                                total_distance += distance
                                total_cost += cost
                                travel_time = (distance / self.vehicles[vehicle_id].speed) * 60  # Convert to minutes
                                total_time += travel_time
                                charge_consumed += self.calculate_energy_consumption(vehicle_id, edge_data, distance)
                                path.append(destination)
                                return (
                                    path, total_cost, total_distance, total_time, charge_consumed,
                                    total_energy_charged, total_charging_cost, time.time() - start_time
                                )

                            return (
                                path, total_cost, total_distance, total_time, charge_consumed,
                                total_energy_charged, total_charging_cost, time.time() - start_time
                            )
                    else:
                        # Step 4.1: Find all reachable nodes (charging stations + destination)
                        reachable_stations = self.bfs_reachable_nodes(self.graph, current_node, battery_level, destination, vehicle_id, threshold)
                        
                        # **Ensure valid_nodes includes the destination if reachable**
                        valid_nodes = []
                        for node in reachable_stations:
                            if self.graph.has_edge(current_node, node) and node not in path:
                                current_to_dest = nx.shortest_path_length(self.graph, source=current_node, target=destination, weight="distance")
                                node_to_dest = nx.shortest_path_length(self.graph, source=node, target=destination, weight="distance") 
                                if node_to_dest<current_to_dest:
                                    valid_nodes.append(node)

                        # Step 4.2: Choose the best next node using `CalCost()`
                        if valid_nodes:
                            best_next_node, cost, rate = self.CalCost(current_node, valid_nodes, destination, battery_level, current_charging_rate, vehicle_id, threshold)    
                            if best_next_node is None:
                                if self.graph.has_edge(current_node, destination):
                                    required_energy = self.calculate_energy_consumption(vehicle_id, self.graph[current_node][destination].get('edge_data', {}), self.graph[current_node][destination]['distance'])
                                    if required_energy <= battery_level:
                                        print(f"No valid next node found, but direct route {current_node} → {destination} is possible. Forcing direct movement.")
                                        return path + [destination], total_cost, total_distance, total_time, charge_consumed, total_energy_charged, total_charging_cost, time.time() - start_time
                                alternative_path = nx.shortest_path(self.graph, source=current_node, target=destination, weight="distance")
                                print("sha alt_p",alternative_path)
                                print("shh",alternative_path)
                                for node in alternative_path:
                                    if node not in path:
                                        best_next_node = node
                                        break  # Pick the first available forward move
                                # print("No valid best next move found. Checking alternatives...")
                                # return path, total_cost, total_distance, total_time, charge_consumed, total_energy_charged, total_charging_cost, time.time() - start_time
                        else:
                            print(" No valid next move found.")
                            alternative_path = nx.shortest_path(self.graph, source=current_node, target=destination, weight="distance")
                            for node in alternative_path:
                                if node not in path:
                                    best_next_node = node
                                    break 
                            # return path, total_cost, total_distance, total_time, charge_consumed, total_energy_charged, total_charging_cost, time.time() - start_time

                        # **Step 4.3: Move to the next node**
                        if best_next_node in path and best_next_node != destination:
                            print(f"Avoiding Infinite Loop | Node {best_next_node} already visited.")
                            # return path, total_cost, total_distance, total_time, charge_consumed, total_energy_charged, total_charging_cost, time.time() - start_time
                            alternative_path = nx.shortest_path(self.graph, source=current_node, target=destination, weight="distance")
                            for node in alternative_path:
                                if node not in path:
                                    best_next_node = node
                                    print(f"Forcing movement to alternative node: {best_next_node}")
                                    break  # Move forward
                        if self.graph.has_edge(current_node, best_next_node):
                            distance = self.graph[current_node][best_next_node]['distance']
                            edge_data = self.graph[current_node][best_next_node].get('edge_data', {})
                        else:
                            # **Handle missing edge by calculating the shortest path distance**
                            shortest_path = nx.shortest_path(self.graph, source=current_node, target=best_next_node, weight="distance")
                            distance = sum(self.graph[shortest_path[i]][shortest_path[i+1]]['distance'] for i in range(len(shortest_path) - 1))
                            edge_data = {}
                            print(f"No direct edge found! Using alternative shortest path {shortest_path}, Total Distance: {distance:.2f} km")

                        speed = self.vehicles[vehicle_id].speed  # km/h
                        travel_time = (distance / speed) * 60  # Convert to minutes
                        energy_consumed = self.calculate_energy_consumption(vehicle_id, edge_data, distance)
                        cost = energy_consumed * current_charging_rate

                        # **Update Metrics**
                        total_cost += cost
                        total_distance += distance
                        charge_consumed += energy_consumed
                        total_time += travel_time
                        battery_level = max(self.battery_reduction(vehicle_id, energy_consumed, battery_level, distance), 0)

                        print(f"Moving to {best_next_node} | Distance: {distance:.2f} km | Battery: {battery_level:.2f}% | Cost: {cost:.2f}")

                        if best_next_node not in path:
                            path.append(best_next_node)

                        current_node = best_next_node


            except nx.NetworkXNoPath:
                print(f"Error: No path from {current_node} to {destination}")
                return None  # Stop if no valid path exists

        # Compute execution time
        execution_time = time.time() - start_time
        return path, total_cost, total_distance, total_time, charge_consumed, total_energy_charged, total_charging_cost, execution_time
    

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

    
    
    

# if __name__ == "__main__":
#     import networkx as nx
#     import time

#     # Create a new directed graph
#     G = nx.DiGraph()

#     # Add nodes (representing locations)
#         # Add nodes (some of these nodes will be charging stations)
#     G.add_node(1)
#     G.add_node(2)
#     G.add_node(3)
#     G.add_node(4)
#     G.add_node(5)
#     G.add_node(6)
#     G.add_node(7)
#     G.add_node(8)
#     G.add_node(9)
#     G.add_node(10)

#     # Add edges with distance and edge data
#     G.add_edge(1, 2, distance=60, edge_data={'angle': 0.5, 'air_density': 1.220})
#     G.add_edge(2, 3, distance=79, edge_data={'angle': 1.0, 'air_density': 1.200})
#     G.add_edge(3, 4, distance=49, edge_data={'angle': 0.8, 'air_density': 1.210})
#     G.add_edge(4, 5, distance=55, edge_data={'angle': 0.9, 'air_density': 1.205})
#     G.add_edge(5, 6, distance=55, edge_data={'angle': 1.2, 'air_density': 1.225})
#     G.add_edge(6, 7, distance=40, edge_data={'angle': 1.1, 'air_density': 1.215})
#     G.add_edge(7, 8, distance=32, edge_data={'angle': 0.6, 'air_density': 1.230})
#     G.add_edge(8, 9, distance=33, edge_data={'angle': 1.0, 'air_density': 1.205})
#     G.add_edge(9, 10, distance=37, edge_data={'angle': 0.5, 'air_density': 1.215})
#     G.add_edge(4, 8, distance=60, edge_data={'angle': 0.85, 'air_density': 1.195})
#     G.add_edge(3, 6, distance=36, edge_data={'angle': 0.95, 'air_density': 1.200})


#     # Simulate traffic conditions (optional)
    
    
#     # Initialize the MTT class with the graph 
#     mtt = MTT(G)

#     # Define and add a vehicle to the system
   
#     vehicle_data = {
#         'vehicle_id': 1,
#         'mass': 1800,
#         'speed': 50,         
#         'mass_factor': 1.1,
#         'rolling_resistance': 0.01,
#         'drag_coefficient': 0.6,
#         'cross_sectional_area': 3.5,
#         'battery_capacity': 100
#     }

#     vehicle_1 = Vehicle(**vehicle_data)
#     mtt.add_vehicle(vehicle_1)

#     # Define charging stations (with charging speed & waiting time)
#     mtt.chargingNodes(4, charging_speed=50, waiting_time=5,energy_rates=0.20)
#     mtt.chargingNodes(8, charging_speed=51, waiting_time=8,energy_rates=0.25)

#     # Add edge details to the graph
#     for (u, v, data) in G.edges(data=True):
#         edge_data = data['edge_data']
#         mtt.add_edge(u, v, data['distance'], edge_data, vehicle_id=1)

#     # Define the source, destination, and initial battery level
#     source = 1
#     destination = 10
#     initial_battery_level = 90  # Start at 80% battery
#     initial_charging_rate=0.5
#     # Run the EV Routing Algorithm
#     result = mtt.complete_logic_dynamic(source, destination, initial_battery_level, initial_charging_rate, vehicle_id=1, threshold=5)
    

#     # Unpack the result
#     (path, total_cost, total_distance, total_time, 
#      charge_consumed, total_energy_charged, 
#      total_charging_cost, execution_time) = result

#     # Print the output
#     print("-----------------------------------------------------")
#     print(f"Optimal Path: {path}")
#     print(f"Total Cost: {total_cost:.2f}")
#     print(f"Total Distance: {total_distance:.2f} km")
#     print(f"Total Travel Time: {total_time:.2f} minutes")
#     print(f"Energy Consumed: {charge_consumed:.2f} kWh")
#     print(f"Energy Charged: {total_energy_charged:.2f} kWh")
#     print(f"Total Charging Cost: {total_charging_cost:.2f}")
#     print(f"Execution Time: {execution_time:.4f} sec\n")
#     print("-----------------------------------------------------")

     
    



    

    