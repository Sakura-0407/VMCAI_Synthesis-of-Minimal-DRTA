#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Min-3RTA.py
Implementation of minimal 3RTA (Region Tree Automaton with Time)
Uses incremental construction to implement Algorithm 1 functionality
"""

from tAPTA import Region, State
import copy
# Import visualization related modules
import os
import matplotlib.pyplot as plt
try:
    import graphviz
    GRAPHVIZ_AVAILABLE = True
except ImportError:
    GRAPHVIZ_AVAILABLE = False
    print("Note: graphviz library not installed or cannot be imported.")
    print("To use graphviz, run: pip install graphviz")
    print("And ensure Graphviz software is installed: https://graphviz.org/download/")

# Set Graphviz executable path
GRAPHVIZ_DOT_PATH = "C:/Program Files/Graphviz/bin/dot.exe"
if os.path.exists(GRAPHVIZ_DOT_PATH) and GRAPHVIZ_AVAILABLE:
    # If exists, set environment variable
    os.environ["PATH"] += os.pathsep + os.path.dirname(GRAPHVIZ_DOT_PATH)
    # Set graphviz library dot command path
    graphviz.backend.dot_command = GRAPHVIZ_DOT_PATH

class RegionTreeNode:
    """Region tree node, represents a state in Min-3RTA"""
    def __init__(self, state_id, is_accepting=False, is_rejecting=False):
        # Node identifier
        self.id = state_id
        # Accepting state marker
        self.is_accepting = is_accepting
        # Rejecting state marker
        self.is_rejecting = is_rejecting
        # Transition dictionary, format: {(symbol, region): target_node_id}
        self.transitions = {}
        # Record registered equivalent nodes
        self.registered_equivalent = None
    
    def add_transition(self, symbol, region, target_node_id):
        """Add transition from current node to target node"""
        # Check if transition with same symbol but different time region exists
        for (sym, reg), target in list(self.transitions.items()):
            if sym == symbol and target == target_node_id:
                # Merge time regions
                merged_region = self._merge_regions(reg, region)
                # Delete old transition
                del self.transitions[(sym, reg)]
                # Add merged new transition
                self.transitions[(sym, merged_region)] = target_node_id
                return
        
        # If no merge needed, directly add new transition
        self.transitions[(symbol, region)] = target_node_id
    
    def _merge_regions(self, region1, region2):
        """Merge two time regions"""
        # Get lower and upper bounds of both regions
        lower = min(region1.lower, region2.lower)
        upper = max(region1.upper, region2.upper)
        
        # Determine inclusion relationship after merge
        lower_inclusive = (region1.lower == lower and region1.lower_inclusive) or \
                          (region2.lower == lower and region2.lower_inclusive)
        
        upper_inclusive = (region1.upper == upper and region1.upper_inclusive) or \
                          (region2.upper == upper and region2.upper_inclusive)
        
        # Create new merged region
        return Region(lower, upper, lower_inclusive, upper_inclusive)
    
    def has_children(self):
        """Check if node has children"""
        return len(self.transitions) > 0
    
    def get_last_child(self):
        """Get lexicographically largest child node ID"""
        if not self.has_children():
            return None
        
        # Sort by symbol and region, return lexicographically largest child node
        # Here we prioritize symbol, then region
        sorted_transitions = sorted(self.transitions.items(), 
                                   key=lambda x: (x[0][0], x[0][1].lower, x[0][1].upper))
        
        # Return target node ID of last transition
        return sorted_transitions[-1][1]
    
    def is_equivalent_to(self, other_node, node_map):
        """Check if current node is equivalent to another node"""
        # Condition 1: accepting/rejecting states must be the same
        if self.is_accepting != other_node.is_accepting or \
           self.is_rejecting != other_node.is_rejecting:
            return False
        
        # Get all symbol sets of both nodes
        self_symbols = {sym for (sym, _) in self.transitions.keys()}
        other_symbols = {sym for (sym, _) in other_node.transitions.keys()}
        
        # Merge symbol sets
        all_symbols = self_symbols.union(other_symbols)
        
        # Condition 2: for each symbol, either both have no successors or successors are equivalent
        for symbol in all_symbols:
            # Get all regions and targets for current node corresponding to this symbol
            self_regions_targets = [(reg, target) for (sym, reg), target in self.transitions.items() 
                                   if sym == symbol]
            
            # Get all regions and targets for other node corresponding to this symbol
            other_regions_targets = [(reg, target) for (sym, reg), target in other_node.transitions.items() 
                                    if sym == symbol]
            
            # If one has successors and the other doesn't, they are not equivalent
            if bool(self_regions_targets) != bool(other_regions_targets):
                return False
            
            # If both have successors, check if successors are equivalent
            if self_regions_targets and other_regions_targets:
                # To simplify comparison, we check if each target node is equivalent or is the same registered node
                for _, self_target in self_regions_targets:
                    self_target_node = node_map[self_target]
                    equivalent_found = False
                    
                    for _, other_target in other_regions_targets:
                        other_target_node = node_map[other_target]
                        
                        # If target nodes are the same or equivalent, mark as equivalent found
                        if self_target == other_target or \
                           (self_target_node.registered_equivalent is not None and 
                            self_target_node.registered_equivalent == other_target_node.registered_equivalent) or \
                           (other_target_node.registered_equivalent is not None and
                            other_target_node.registered_equivalent == self_target_node.registered_equivalent):
                            equivalent_found = True
                            break
                    
                    # If no equivalent target node found, they are not equivalent
                    if not equivalent_found:
                        return False
        
        # Passed all checks, nodes are equivalent
        return True

class Min3RTA:
    """Minimal 3RTA (Region Tree Automaton with Time)"""
    def __init__(self):
        # Node mapping, from ID to node object
        self.nodes = {}
        # Register, stores representative node for each equivalence class
        self.register = set()
        # Initial state ID
        self.initial_node_id = 0
        # Next available node ID
        self.next_node_id = 0
        # Used to track path of last added sample
        self.last_path = []
    
    def create_node(self, is_accepting=False, is_rejecting=False):
        """Create new node and return ID"""
        node_id = self.next_node_id
        self.nodes[node_id] = RegionTreeNode(node_id, is_accepting, is_rejecting)
        self.next_node_id += 1
        return node_id
    
    def process_sample(self, sample, is_positive):
        """Process a single sample"""
        if not sample:
            # If empty sample, only mark initial state
            if is_positive:
                self.nodes[self.initial_node_id].is_accepting = True
            else:
                self.nodes[self.initial_node_id].is_rejecting = True
            return
        
        # If first sample, need to create initial node
        if not self.nodes:
            self.initial_node_id = self.create_node()
        
        # Current node starts from initial node
        current_id = self.initial_node_id
        path = [current_id]  # Track path
        
        # Find common prefix
        i = 0
        while i < len(sample):
            symbol, time = sample[i]
            # Check if corresponding transition exists
            found = False
            
            for (sym, region), target_id in list(self.nodes[current_id].transitions.items()):
                if sym == symbol and region.contains(time):
                    current_id = target_id
                    path.append(current_id)
                    found = True
                    i += 1
                    break
            
            if not found:
                break
        
        # Add remaining suffix
        for j in range(i, len(sample)):
            symbol, time = sample[j]
            # Map time value to integer interval, e.g. 1.3 maps to [1,2]
            lower_bound = int(time)
            upper_bound = lower_bound + 1
            region = Region(lower_bound, upper_bound, True, False)  # [lower, upper) interval
            print(f"Mapping time value {time} to interval {region}")
            
            # Create new node
            new_id = self.create_node()
            
            # Add transition
            self.nodes[current_id].add_transition(symbol, region, new_id)
            
            current_id = new_id
            path.append(current_id)
        
        # Mark final state
        if is_positive:
            self.nodes[current_id].is_accepting = True
        else:
            self.nodes[current_id].is_rejecting = True
        
        # Save path for subsequent processing
        self.last_path = path
        
        # Execute replace_or_register starting from current node
        self.replace_or_register(current_id)
    
    def replace_or_register(self, node_id):
        """Execute replace_or_register algorithm"""
        # If node has no children, no processing needed
        if not self.nodes[node_id].has_children():
            # Check if equivalent node already in register
            self._check_and_register(node_id)
            return
        
        # Get lexicographically largest child node
        r_id = self.nodes[node_id].get_last_child()
        
        # Recursively process child node
        if self.nodes[r_id].has_children():
            self.replace_or_register(r_id)
        
        # Check if equivalent node already in register
        self._check_and_register(r_id)
    
    def _check_and_register(self, node_id):
        """Check if node has equivalent node in register, merge if exists, otherwise register"""
        node = self.nodes[node_id]
        
        # Check if equivalent node exists in register
        for reg_id in self.register:
            reg_node = self.nodes[reg_id]
            
            if node.is_equivalent_to(reg_node, self.nodes):
                # Found equivalent node, update reference
                node.registered_equivalent = reg_id
                
                # Update all transitions pointing to this node
                self._update_transitions(node_id, reg_id)
                
                return
        
        # If no equivalent node, add this node to register
        self.register.add(node_id)
    
    def _update_transitions(self, old_id, new_id):
        """Update all transitions pointing to old_id to point to new_id"""
        for node in self.nodes.values():
            for (symbol, region), target_id in list(node.transitions.items()):
                if target_id == old_id:
                    # Update transition
                    node.transitions[(symbol, region)] = new_id
    
    def build_from_samples(self, positive_samples, negative_samples):
        """Build minimal automaton from sample set"""
        # Sort all samples lexicographically
        all_samples = [(sample, True) for sample in positive_samples] + \
                     [(sample, False) for sample in negative_samples]
        
        # Sort lexicographically (ignoring time values)
        all_samples.sort(key=lambda x: [sym for sym, _ in x[0]])
        
        # Process samples one by one
        for sample, is_positive in all_samples:
            self.process_sample(sample, is_positive)
        
        # Final processing, ensure all nodes have gone through replace_or_register
        if self.last_path:
            for node_id in reversed(self.last_path):
                if node_id in self.nodes:  # Ensure node not deleted
                    self.replace_or_register(node_id)
    
    def print_automaton(self):
        """Print automaton structure"""
        print("Minimal 3RTA automaton:")
        print(f"Number of nodes: {len(self.nodes)}")
        print(f"Number of registered nodes: {len(self.register)}")
        
        # Print all nodes
        for node_id, node in self.nodes.items():
            state_type = "Initial state" if node_id == self.initial_node_id else f"State {node_id}"
            
            if node.is_accepting:
                state_type += " (Accepting state)"
            if node.is_rejecting:
                state_type += " (Rejecting state)"
            
            registered = " [Registered]" if node_id in self.register else ""
            equivalent = f" -> {node.registered_equivalent}" if node.registered_equivalent is not None else ""
            
            print(f"{state_type}{registered}{equivalent}")
            
            # Print transitions
            for (symbol, region), target_id in node.transitions.items():
                # Get real target node ID (considering equivalence relations)
                real_target_id = target_id
                target_node = self.nodes[target_id]
                if target_node.registered_equivalent is not None:
                    real_target_id = target_node.registered_equivalent
                
                print(f"  --({symbol}/{region})--> {real_target_id}")
    
    def visualize_as_graphviz(self, output_file="min_3rta"):
        """Visualize minimal 3RTA automaton as image using Graphviz, only showing merged nodes"""
        if not GRAPHVIZ_AVAILABLE:
            print("graphviz library unavailable, cannot generate visualization image.")
            return None
        
        # Create directed graph
        dot = graphviz.Digraph('Min3RTA', filename=output_file, format='png', 
                              engine='dot', encoding='utf-8')
        dot.attr(rankdir='LR')  # Left-to-right layout
        
        # Find nodes that actually need to be kept (nodes in register and nodes without equivalent nodes)
        active_nodes = set()
        for node_id, node in self.nodes.items():
            if node_id in self.register or node.registered_equivalent is None:
                active_nodes.add(node_id)
        
        # Create nodes for states
        for node_id in active_nodes:
            node = self.nodes[node_id]
            
            # If node has equivalent node but not in register, skip
            if node.registered_equivalent is not None and node_id not in self.register:
                continue
            
            # Node label
            label = f"q{node_id}"
            
            # Node attributes
            attrs = {
                'shape': 'circle',
                'style': 'filled',
                'fillcolor': 'white',
                'fontname': 'SimSun'  # Use Chinese font
            }
            
            # Special state styles
            if node_id == self.initial_node_id:
                attrs['penwidth'] = '2'  # Initial state bold outline
            
            if node.is_accepting:
                attrs['shape'] = 'doublecircle'  # Accepting state double circle
                attrs['fillcolor'] = '#e6ffcc'  # Light green
            elif node.is_rejecting:
                attrs['fillcolor'] = '#ffcccc'  # Light red
            
            # Add node
            dot.node(str(node_id), label, **attrs)
        
        # Initial state indicator arrow
        dot.node('start', label='', shape='none')
        dot.edge('start', str(self.initial_node_id), arrowhead='normal')
        
        # Add transition edges, only considering merged equivalent nodes
        processed_edges = set()  # Avoid duplicate edges
        for node_id in active_nodes:
            node = self.nodes[node_id]
            
            # If has equivalent node but not in register, skip
            if node.registered_equivalent is not None and node_id not in self.register:
                continue
            
            # Process all transitions of node
            for (symbol, region), target_id in node.transitions.items():
                # Get real target node ID (considering equivalence relations)
                real_target_id = target_id
                target_node = self.nodes[target_id]
                if target_node.registered_equivalent is not None:
                    real_target_id = target_node.registered_equivalent
                
                # Create edge identifier to avoid duplicates
                edge_key = (node_id, real_target_id, symbol, str(region))
                if edge_key in processed_edges:
                    continue
                
                # Edge label
                edge_label = f"{symbol}/{region}"
                
                # Add edge
                dot.edge(str(node_id), str(real_target_id), label=edge_label, fontname='SimSun')
                processed_edges.add(edge_key)
        
        # Save image
        try:
            dot.render(cleanup=True)  # Generate image and clean up dot file
            print(f"\nMin-3RTA graph saved to file: {output_file}.png")
            
            # Display absolute path
            abs_path = os.path.abspath(f"{output_file}.png")
            print(f"Absolute path: {abs_path}")
            return abs_path
        except Exception as e:
            print(f"Error generating image with graphviz: {e}")
            return None

def build_min_3rta(positive_samples, negative_samples):
    """Build and return minimal 3RTA"""
    min_3rta = Min3RTA()
    min_3rta.build_from_samples(positive_samples, negative_samples)
    return min_3rta

def main():
    """Main function demonstrating Min-3RTA usage"""
    from tAPTA import BuildTimedAPTA
    from drawFig import visualize_tapta
    
    # Example positive sample set
    S_positive = [
        [('a', 1)],
        [('a', 1.3), ('b', 5.2), ('b', 1)]
    ]
    
    # Example negative sample set
    S_negative = [
        [('a', 2.2), ('a', 1)],
        [('b', 1), ('a', 1.2)]
    ]
    
    # Build original TAPTA automaton
    print("Starting to build original TAPTA automaton...")
    tapta = BuildTimedAPTA(S_positive, S_negative)
    visualize_tapta(tapta, S_positive, S_negative, "original_tapta")
    
    # Build minimal 3RTA
    print("\nStarting to build minimal 3RTA automaton...")
    min_3rta = build_min_3rta(S_positive, S_negative)
    min_3rta.print_automaton()
    
    # Visualize minimal 3RTA
    print("\nStarting to visualize minimal 3RTA automaton...")
    min_3rta.visualize_as_graphviz("min_3rta_automaton")
    
    print("\nMinimal automaton construction completed!")

if __name__ == "__main__":
    main()
