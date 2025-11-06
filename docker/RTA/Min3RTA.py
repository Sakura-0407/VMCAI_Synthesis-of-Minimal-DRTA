#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Min3RTA.py
Implementation of Minimized 3RTA (Time-based Regional Tree Automaton)
Using incremental construction to implement Algorithm 1 functionality
Reference user-provided incremental DFA construction code structure
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
    print("And ensure Graphviz software is installed on system: https://graphviz.org/download/")
# Import networkx for building directed graphs
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    print("Note: networkx library not installed or cannot be imported.")
    print("To use networkx, run: pip install networkx")
# Import XML processing libraries
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from datetime import datetime

# Set Graphviz executable file path
GRAPHVIZ_DOT_PATH = "C:/Program Files/Graphviz/bin/dot.exe"
if os.path.exists(GRAPHVIZ_DOT_PATH) and GRAPHVIZ_AVAILABLE:
    # If exists, set environment variable
    os.environ["PATH"] += os.pathsep + os.path.dirname(GRAPHVIZ_DOT_PATH)
    # Set graphviz library dot command path
    graphviz.backend.dot_command = GRAPHVIZ_DOT_PATH

# Define sample type enumeration
class SampleType:
    """Sample type: accept or reject"""
    ACCEPT = True
    REJECT = False

class RegionTreeNode:
    """Region tree node, representing a state in Min-3RTA"""
    def __init__(self, state_id, is_accepting=False, is_rejecting=False):
        # Node identifier
        self.id = state_id
        # Accepting state flag
        self.is_accepting = is_accepting
        # Rejecting state flag
        self.is_rejecting = is_rejecting
        # Transition dictionary, format: {(symbol, region): target_node}
        self.transitions = {}
        # Children list, ordered by addition, stores RegionTreeNode objects
        self.children = []
        # Record registered equivalent nodes
        self.registered_equivalent = None
        # Record if merged
        self.is_merged = False
    
    def add_transition(self, symbol, region, target_node):
        """Add transition from current node to target node"""
        # Check if transition with same symbol but different time region exists
        for (sym, reg), target in list(self.transitions.items()):
            if sym == symbol and target == target_node:
                # Try to merge time regions
                merged_region = self._merge_regions(reg, region)
                merged_region = None
                # If regions cannot be merged (not adjacent or no overlap), skip
                if merged_region is None:
                    continue
                    
                # Region merge successful
                # Delete old transition
                del self.transitions[(sym, reg)]
                # Add new merged transition
                self.transitions[(sym, merged_region)] = target_node
                return
        
        # If no merge needed, directly add new transition
        self.transitions[(symbol, region)] = target_node
        
        # If target node not in children list, add it
        if target_node not in self.children:
            self.children.append(target_node)
    
    def _are_regions_adjacent_or_overlapping(self, region1, region2):
        """Determine if two regions are adjacent or overlapping"""
        # Case 1: Regions have overlap (lower bound of one region <= upper bound of another)
        has_overlap = (
            (region1.lower <= region2.upper and region1.upper >= region2.lower) or
            (region2.lower <= region1.upper and region2.upper >= region1.lower)
        )
        
        # Case 2: Regions are adjacent (upper bound of one equals lower bound of another)
        is_adjacent = (
            (region1.upper == region2.lower and (region1.upper_inclusive or region2.lower_inclusive)) or
            (region2.upper == region1.lower and (region2.upper_inclusive or region1.lower_inclusive))
        )
        
        return has_overlap or is_adjacent
    
    def _merge_regions(self, region1, region2):
        """Merge two time regions"""
        # Check if two regions are adjacent or overlapping
        if not self._are_regions_adjacent_or_overlapping(region1, region2):
            # print(f"Region merge failed: {region1} and {region2} are neither adjacent nor overlapping")
            return None
        
        # Get lower and upper bounds of two regions
        lower = min(region1.lower, region2.lower)
        upper = max(region1.upper, region2.upper)
        
        # Determine inclusion relationship after merge
        lower_inclusive = (region1.lower == lower and region1.lower_inclusive) or \
                          (region2.lower == lower and region2.lower_inclusive)
        
        upper_inclusive = (region1.upper == upper and region1.upper_inclusive) or \
                          (region2.upper == upper and region2.upper_inclusive)
        
        # Create new merged region
        merged = Region(lower, upper, lower_inclusive, upper_inclusive)
        # print(f"Region merge successful: {region1} + {region2} => {merged}")
        return merged
    
    def has_children(self):
        """Check if node has children"""
        return len(self.children) > 0
    
    def last_child(self):
        """Get last added child node"""
        if not self.has_children():
            return None
        return self.children[-1]
    
    def last_child_with_symbol(self, symbol, time_value=None):
        """Get last child node with specified symbol, if time value provided must contain that time value"""
        # Find the most specific matching transition for the given time value
        best_match = None
        best_region = None
        
        for (sym, region), target_node in self.transitions.items():
            if sym == symbol and (time_value is None or region.contains(time_value)):
                # If no best match yet, or if this region is more specific
                if best_match is None or self._is_more_specific_region(region, best_region):
                    best_match = target_node
                    best_region = region
        
        return best_match
    
    def _is_more_specific_region(self, region1, region2):
        """Check if region1 is more specific than region2"""
        if region1 is None or region2 is None:
            return region1 is not None
        
        # A region is more specific if it has a smaller range
        range1 = region1.upper - region1.lower
        range2 = region2.upper - region2.lower
        
        if range1 < range2:
            return True
        elif range1 > range2:
            return False
        else:
            # If ranges are equal, prefer exact point intervals over open intervals
            if region1.lower == region1.upper and region1.lower_inclusive and region1.upper_inclusive:
                if not (region2.lower == region2.upper and region2.lower_inclusive and region2.upper_inclusive):
                    return True
            return False
    
    def replace_last_child(self, new_target_node, rta):
        """Replace last child node with new target node"""
        if not self.has_children():
            return
        new_target_node.is_merged = True
        old_target_node = self.children[-1]       
        # Update transition dictionary
        for (symbol, region), target_node in list(self.transitions.items()):
            if target_node == old_target_node:
                self.transitions[(symbol, region)] = new_target_node
        
        # Update children list
        if old_target_node in self.children:
            index = self.children.index(old_target_node)
            self.children[index] = new_target_node
    
    def is_equivalent_to(self, other_node, rta):
        """Check if current node is equivalent to another node"""
        # Condition 1: Accept/reject states must be same
        if self.is_accepting != other_node.is_accepting or \
           self.is_rejecting != other_node.is_rejecting:
            return False
        
        # Get all symbol sets of both nodes
        self_symbols = set()
        other_symbols = set()
        
        for (sym, _) in self.transitions.keys():
            self_symbols.add(sym)
        
        for (sym, _) in other_node.transitions.keys():
            other_symbols.add(sym)
        
        # If symbol sets are different, nodes are not equivalent
        if self_symbols != other_symbols:
            return False
        
        # For each symbol, check if successor nodes are equivalent
        for symbol in self_symbols:
            # Get all possible successor states for current node and other node with corresponding symbol
            self_successors = set()
            other_successors = set()
            
            # Get successors of current node
            for (sym, region), target_node in self.transitions.items():
                if sym == symbol:
                    # Consider equivalent nodes
                    real_node = rta.get_real_node(target_node)
                    self_successors.add((real_node.id, str(region)))
            
            # Get successors of other node
            for (sym, region), target_node in other_node.transitions.items():
                if sym == symbol:
                    # Consider equivalent nodes
                    real_node = rta.get_real_node(target_node)
                    other_successors.add((real_node.id, str(region)))
            
            # Successor sets must be same (including time regions)
            if self_successors != other_successors:
                return False
        
        # Pass all checks, nodes are equivalent
        return True

class Min3RTA:
    """Minimized 3RTA (Time-based Regional Tree Automaton)"""
    def __init__(self):
        # Node map, from ID to node object
        self.nodes = {}
        # Register, stores representative node of each equivalence class {node_id: node_id}
        self.register = {}
        # Initial state ID, also root node
        self.root = None
        # Next available node ID
        self.next_node_id = 0
        # For tracking path
        self.previous_nodes = []
    
    def create_node(self, is_accepting=False, is_rejecting=False):
        """Create new node and return ID"""
        node_id = self.next_node_id
        self.nodes[node_id] = RegionTreeNode(node_id, is_accepting, is_rejecting)
        self.next_node_id += 1
        if self.root is None:
            self.root = node_id
        return node_id
    
    def get_real_node_id(self, node_id):
        """Get real ID of node (considering equivalent nodes)"""
        if node_id in self.register and self.register[node_id] != node_id:
            return self.register[node_id]
        return node_id
    
    def get_real_node(self, node):
        """Get real node object (considering equivalent nodes)"""
        real_id = self.get_real_node_id(node.id)
        return self.nodes[real_id]
    
    def set_previous(self, sample):
        """Set previous path for tracking"""
        self.previous_nodes = []
    
    def add(self, sample, is_positive, max_time):
        """Process single sample"""
        # Set previous path (similar to set_previous in reference code)
        self.set_previous(sample)
        
        # Ensure root node exists
        if self.root is None:
            self.root = self.create_node()
        
        pos = 0
        max_len = len(sample)
        current_id = self.root
        
        # Find common prefix
        while pos < max_len:
            symbol, time = sample[pos]
            # Find matching transition
            next_node = self.nodes[current_id].last_child_with_symbol(symbol, time)
            if next_node is None:
                break
            current_id = next_node.id
            pos += 1
        
        # If current node has children, first execute replace_or_register
        if self.nodes[current_id].has_children():
            self.replace_or_register(current_id)
        
        # Add remaining suffix
        self.add_suffix(current_id, sample, pos, is_positive, max_time)
    
    def add_suffix(self, current_id, sample, from_index, is_positive, max_time):
        """Add suffix of sample"""
        # Similar to add_suffix method in reference code
        for i in range(from_index, len(sample)):
            symbol, time = sample[i]
            
            # Determine if time value is an integer
            is_integer = time == int(time)
            
            # Determine if it's the maximum time value or close to it
            is_max_time = abs(time - max_time) < 0.001  # Use a small tolerance value
            if is_integer:
                if is_max_time:
                    # Maximum time value: map to [int(time), ∞) interval
                    lower_bound = int(time)
                    upper_bound = float('inf')
                    region = Region(lower_bound, upper_bound, True, False)  # [int(max), ∞) interval
                    # print(f"Mapping maximum time value {time} to unbounded interval {region}")
                else:
                    # Integer time value: map to exact point interval [t,t]
                    lower_bound = upper_bound = int(time)
                    region = Region(lower_bound, upper_bound, True, True)  # [t, t] interval
                    # print(f"Mapping integer time value {time} to exact interval {region}")
            
            elif is_max_time:
                # Maximum time value: map to (int(time), ∞) interval
                lower_bound = int(time)
                upper_bound = float('inf')
                region = Region(lower_bound, upper_bound, False, False)  # (int(max), ∞) interval
                # print(f"Mapping maximum time value {time} to unbounded interval {region}")
            else:
                # Decimal time value: map to open interval (t,t+1)
                lower_bound = int(time)
                upper_bound = lower_bound + 1
                region = Region(lower_bound, upper_bound, False, False)  # (t, t+1) interval
                # print(f"Mapping decimal time value {time} to open interval {region}")
            
            # Create new node
            new_id = self.create_node()
            
            # Add transition
            self.nodes[current_id].add_transition(symbol, region, self.nodes[new_id])
            
            # Update current node
            current_id = new_id
        
        # Mark final node type
        if is_positive:
            self.nodes[current_id].is_accepting = True
        else:
            self.nodes[current_id].is_rejecting = True
    
    def replace_or_register(self, state_id, visited=None, depth=0):
        """Execute replace_or_register algorithm, add recursive protection"""
        # Recursive depth protection
        MAX_DEPTH = 1000
        if depth > MAX_DEPTH:
            # print(f"Warning: replace_or_register recursion depth exceeded {MAX_DEPTH}, potential cycle structure")
            return
        
        # Visited node record
        if visited is None:
            visited = set()
        
        if state_id in visited:
            # print(f"Warning: Cycle detected, node {state_id} already visited")
            return
        
        visited.add(state_id)
        
        # Get last child node
        node = self.nodes[state_id]
        child_node = node.last_child()
        
        if child_node is None:
            visited.remove(state_id)
            return
        
        # If child node has its own children, recursively process
        if child_node.has_children():
            self.replace_or_register(child_node.id, visited, depth + 1)
        # if child_node.is_rejecting:
        #     return      
        # Check for registered equivalent nodes
        registered_id = None
        for reg_id in self.register:
            if child_node.is_equivalent_to(self.nodes[reg_id], self):
                registered_id = reg_id
                break
        
        if registered_id is not None:
            # If equivalent node found, replace last child node
            node.replace_last_child(self.nodes[registered_id], self)
            
            # Update register
            self.register[child_node.id] = registered_id
            
            # Important improvement: merge all transitions of the merged node to the target node
            merge_success = self._merge_node_transitions(child_node, self.nodes[registered_id])
            if not merge_success:
                # If merge failed due to state conflict, revert the registration
                print(f"Reverting merge due to state conflict. Node {child_node.id} will not be merged.")
                del self.register[child_node.id]
                # Restore the original child
                node.replace_last_child(child_node, self)
        else:
            # Otherwise, register current node as representative
            self.register[child_node.id] = child_node.id
        
        # Clean up visited record
        visited.remove(state_id)
    
    def _merge_node_transitions(self, source_node, target_node):
        """Merge all transitions of source node into target node"""
        
        # Check for state conflicts before merging
        if (source_node.is_accepting != target_node.is_accepting or 
            source_node.is_rejecting != target_node.is_rejecting):
            print(f"WARNING: Attempting to merge nodes with different states!")
            print(f"  Source node {source_node.id}: accepting={source_node.is_accepting}, rejecting={source_node.is_rejecting}")
            print(f"  Target node {target_node.id}: accepting={target_node.is_accepting}, rejecting={target_node.is_rejecting}")
            print(f"  This violates node equivalence! Skipping merge.")
            return False
        
        # Iterate through all transitions of source node
        for (symbol, region), next_node in list(source_node.transitions.items()):
            # Get actual target node (considering nodes that might have been merged)
            real_next_node = self.get_real_node(next_node)
            
            # Check if target node already has a transition with the same symbol
            has_transition = False
            for (t_sym, t_region), t_next in list(target_node.transitions.items()):
                # If a transition with the same symbol exists, and the target state is also the same
                if t_sym == symbol and self.get_real_node(t_next).id == real_next_node.id:
                    # Try to merge regions
                    merged_region = target_node._merge_regions(t_region, region)
                    merged_region = None
                    # If regions cannot be merged (not adjacent or no overlap), continue searching for other possible merges
                    if merged_region is None:
                        continue
                        
                    # Region merge successful
                    # Delete old transition
                    del target_node.transitions[(t_sym, t_region)]
                    # Add new merged transition
                    target_node.transitions[(t_sym, merged_region)] = t_next
                    has_transition = True
                    break
            
            # If no transition with the same symbol found, directly add
            if not has_transition:
                target_node.transitions[(symbol, region)] = real_next_node
                # Ensure target node is added to children list
                if real_next_node not in target_node.children:
                    target_node.children.append(real_next_node)
    
    def build_from_samples(self, positive_samples, negative_samples):
        """Build minimized automaton from sample set"""
        # Initialize root node
        if self.root is None:
            self.root = self.create_node()
        
        # Calculate maximum time value in all samples
        max_time = 0
        for sample_list in [positive_samples, negative_samples]:
            for sample in sample_list:
                for _, time in sample:
                    max_time = max(max_time, time)
        
        print(f"Maximum time value in all samples: {max_time}")
        
        # Combine positive and negative examples, and mark type for each sample
        all_samples = [(sample, SampleType.ACCEPT) for sample in positive_samples]
        all_samples.extend([(sample, SampleType.REJECT) for sample in negative_samples])
        
        # Sort samples by dictionary order
        # Note: Dictionary order comparison for samples is element-wise comparison (symbol, time) pairs
        all_samples.sort(key=lambda x: tuple((symbol, time) for symbol, time in x[0]))
        
        print("Samples sorted by dictionary order:")
        for sample, sample_type in all_samples:
            type_str = "Positive" if sample_type == SampleType.ACCEPT else "Negative"
            print(f"  {type_str}: {sample}")
        
        # Process all sorted samples
        for sample, sample_type in all_samples:
            self.add(sample, sample_type, max_time)
        
        # Finally, execute replace_or_register on root node to ensure minimization
        self.replace_or_register(self.root)
    
    
    def print_automaton(self):
        """Print automaton structure"""
        print("Minimized 3RTA Automaton:")
        print(f"Number of nodes: {len(self.nodes)}")
        print(f"Number of registered nodes: {len(self.register)}")
        
        # Print all nodes
        for node_id, node in self.nodes.items():
            state_type = "Initial state" if node_id == self.root else f"State {node_id}"
            
            if node.is_accepting:
                state_type += " (Accepting state)"
            if node.is_rejecting:
                state_type += " (Rejecting state)"
            
            registered = " [Registered]" if node_id in self.register and self.register[node_id] == node_id else ""
            equivalent = f" -> {self.register[node_id]}" if node_id in self.register and self.register[node_id] != node_id else ""
            
            print(f"{state_type}{registered}{equivalent}")
            
            # Print transitions
            for (symbol, region), target_node in node.transitions.items():
                # Get real ID of target node
                real_target_id = self.get_real_node_id(target_node.id)
                print(f"  --({symbol}/{region})--> {real_target_id}")
    
    def visualize_as_graphviz(self, output_file="min_3rta"):
        """Visualize minimized 3RTA automaton as image using Graphviz, only showing merged nodes"""
        if not GRAPHVIZ_AVAILABLE:
            print("graphviz library not available, cannot generate visualization image.")
            return None
        
        # Create directed graph
        dot = graphviz.Digraph('Min3RTA', filename=output_file, format='png', 
                              engine='dot', encoding='utf-8')
        dot.attr(rankdir='LR')  # Left-to-right layout
        
        # Find nodes that actually need to be displayed (representative of each equivalence class)
        active_nodes = set()
        for node_id in self.nodes:
            real_id = self.get_real_node_id(node_id)
            active_nodes.add(real_id)
        
        # Create nodes for states
        for node_id in active_nodes:
            node = self.nodes[node_id]
            
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
            if node_id == self.root:
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
        dot.edge('start', str(self.root), arrowhead='normal')
        
        # Add transition edges
        processed_edges = set()  # Avoid duplicate edges
        for node_id in active_nodes:
            node = self.nodes[node_id]
            
            # Process all transitions of the node
            for (symbol, region), target_node in node.transitions.items():
                # Use original target node ID for consistency with path tracing
                target_id = target_node.id
                
                # Create edge identifier to avoid duplicates
                edge_key = (node_id, target_id, symbol, str(region))
                if edge_key in processed_edges:
                    continue
                
                # Edge label
                edge_label = f"{symbol}/{region}"
                
                # Add edge
                dot.edge(str(node_id), str(target_id), label=edge_label, fontname='SimSun')
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

    def generate_dot_content(self):
        """Generate DOT content for Min3RTA automaton"""
        if not GRAPHVIZ_AVAILABLE:
            return "// graphviz library not available"
        
        # Create directed graph
        dot = graphviz.Digraph('Min3RTA', engine='dot', encoding='utf-8')
        dot.attr(rankdir='LR')  # Left-to-right layout
        
        # Find nodes that actually need to be displayed (representative of each equivalence class)
        active_nodes = set()
        for node_id in self.nodes:
            real_id = self.get_real_node_id(node_id)
            active_nodes.add(real_id)
        
        # Create nodes for states
        for node_id in active_nodes:
            node = self.nodes[node_id]
            
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
            if node_id == self.root:
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
        dot.edge('start', str(self.root), arrowhead='normal')
        
        # Add transition edges
        processed_edges = set()  # Avoid duplicate edges
        for node_id in active_nodes:
            node = self.nodes[node_id]
            
            # Process all transitions of the node
            for (symbol, region), target_node in node.transitions.items():
                # Use original target node ID for consistency with path tracing
                target_id = target_node.id
                
                # Create edge identifier to avoid duplicates
                edge_key = (node_id, target_id, symbol, str(region))
                if edge_key in processed_edges:
                    continue
                
                # Edge label
                edge_label = f"{symbol}/{region}"
                
                # Add edge
                dot.edge(str(node_id), str(target_id), label=edge_label, fontname='SimSun')
                processed_edges.add(edge_key)
        
        # Return DOT content as string
        return dot.source

class TDRTA:
    """3DRTA (3-Deterministic Real-Time Automaton) data structure"""
    def __init__(self, tree, root, alphabet, accepting, rejecting, edge_labels, optimized=True, min_3rta=None):
        self.tree = tree  # DiGraph object
        self.root = root  # Root node index
        self.alphabet = alphabet  # Alphabet
        self.accepting = accepting  # Set of accepting nodes
        self.rejecting = rejecting  # Set of rejecting nodes
        self.nodes = tree.nodes  # Node view
        self.edge_labels = edge_labels  # Edge labels, format: {(source, target, key): (symbol_id, region)}
        self.optimized = optimized  # Whether optimized
        self.registered_nodes = []  # Array to record registered nodes

        # If min_3rta is provided, get merged node information from it
        if min_3rta is not None and hasattr(min_3rta, 'register'):
            for node_id, node in min_3rta.nodes.items():
                if node.is_merged:
                    self.registered_nodes.append(node_id)
            print(self.registered_nodes)
            print(self.accepting)
            print(self.rejecting)

def _sample_reaches_node(min_3rta, sample, target_node_id):
    """Check if a sample reaches a specific node"""
    try:
        current_node_id = min_3rta.root
        for symbol, time_val in sample:
            current_node = min_3rta.nodes[current_node_id]
            found_transition = False
            for (s, region), target_node in current_node.transitions.items():
                if s == symbol and region.contains(time_val):
                    current_node_id = target_node.id
                    found_transition = True
                    break
            if not found_transition:
                return False
        return current_node_id == target_node_id
    except Exception:
        return False

def _resolve_conflict_by_time_patterns(positive_samples, negative_samples):
    """
    Resolve conflicts based on time patterns in samples
    
    Strategy: If positive samples have significantly larger second time values,
    prioritize accepting state (longer delays indicate success).
    Otherwise, prioritize rejecting state.
    """
    if not positive_samples and not negative_samples:
        return 'rejecting'  # Default to rejecting if no samples
    
    if not positive_samples:
        return 'rejecting'
    if not negative_samples:
        return 'accepting'
    
    # Analyze second time values for length-2 samples
    pos_second_times = []
    neg_second_times = []
    
    for sample in positive_samples:
        if len(sample) == 2:
            pos_second_times.append(sample[1][1])
    
    for sample in negative_samples:
        if len(sample) == 2:
            neg_second_times.append(sample[1][1])
    
    if not pos_second_times or not neg_second_times:
        # Fallback to majority vote
        return 'accepting' if len(positive_samples) >= len(negative_samples) else 'rejecting'
    
    # Calculate averages
    pos_avg = sum(pos_second_times) / len(pos_second_times)
    neg_avg = sum(neg_second_times) / len(neg_second_times)
    
    # If positive samples have significantly larger second time values, prioritize accepting
    # This indicates that longer delays are associated with success
    if pos_avg > neg_avg * 1.5:  # 50% larger threshold
        return 'accepting'
    else:
        return 'rejecting'

def _sample_reaches_node(min_3rta, sample, target_node_id):
    """Check if a sample reaches a specific node"""
    try:
        current_node_id = min_3rta.root
        for symbol, time_val in sample:
            current_node = min_3rta.nodes[current_node_id]
            found_transition = False
            for (s, region), target_node in current_node.transitions.items():
                if s == symbol and region.contains(time_val):
                    current_node_id = target_node.id
                    found_transition = True
                    break
            if not found_transition:
                return False
        return current_node_id == target_node_id
    except Exception:
        return False

def _resolve_conflict_by_time_patterns(positive_samples, negative_samples):
    """
    Resolve conflicts based on time patterns in samples
    
    Strategy: If positive samples have significantly larger second time values,
    prioritize accepting state (longer delays indicate success).
    Otherwise, prioritize rejecting state.
    """
    if not positive_samples and not negative_samples:
        return 'rejecting'  # Default to rejecting if no samples
    
    if not positive_samples:
        return 'rejecting'
    if not negative_samples:
        return 'accepting'
    
    # Analyze second time values for length-2 samples
    pos_second_times = []
    neg_second_times = []
    
    for sample in positive_samples:
        if len(sample) == 2:
            pos_second_times.append(sample[1][1])
    
    for sample in negative_samples:
        if len(sample) == 2:
            neg_second_times.append(sample[1][1])
    
    if not pos_second_times or not neg_second_times:
        # Fallback to majority vote
        return 'accepting' if len(positive_samples) >= len(negative_samples) else 'rejecting'
    
    # Calculate averages
    pos_avg = sum(pos_second_times) / len(pos_second_times)
    neg_avg = sum(neg_second_times) / len(neg_second_times)
    
    # If positive samples have significantly larger second time values, prioritize accepting
    # This indicates that longer delays are associated with success
    if pos_avg > neg_avg * 1.5:  # 50% larger threshold
        return 'accepting'
    else:
        return 'rejecting'

def convert_to_3DRTA(min_3rta):
    """
    Convert Min3RTA data structure to 3DRTA data structure
    
    Parameters:
    min_3rta: Built Min3RTA object
    
    Returns:
    APTA object, representing the converted 3DRTA structure
    """
    if not NETWORKX_AVAILABLE:
        print("Warning: Cannot convert to 3DRTA structure, networkx library is missing")
        return None
    
    # Create directed graph
    tree = nx.MultiDiGraph()  # Use MultiDiGraph to support multiple parallel edges
    
    # Collect alphabet
    alphabet = set()
    for node_id, node in min_3rta.nodes.items():
        for (symbol, _), _ in node.transitions.items():
            alphabet.add(symbol)
    
    # Convert alphabet to mapping table
    alphabet_map = {sym: i for i, sym in enumerate(sorted(alphabet))}
    
    # Process nodes
    accepting = set()
    rejecting = set()
    edge_labels = {}  # Format: {(source, target, key): (symbol_id, region)}
    
    # For tracking edges already added to avoid duplicate additions
    # Format: {(source_id, target_id, symbol, region_str): edge_key}
    added_edges = {}
    
    # Add all nodes
    for node_id, node in min_3rta.nodes.items():
        # Get real node ID (considering merged nodes)
        real_id = min_3rta.get_real_node_id(node_id)
        
        # If it's a new node, add it to the graph
        if real_id not in tree.nodes:
            # Initial node has no source and region
            if real_id == min_3rta.root:
                tree.add_node(real_id, sources=[], regions=[], from_nodes=[])
            else:
                tree.add_node(real_id, sources=[], regions=[], from_nodes=[])
        
        # Record accepting/rejecting states (always check, not just for new nodes)
        if node.is_accepting:
            accepting.add(real_id)
        if node.is_rejecting:
            rejecting.add(real_id)
    
    # Add all edges (transitions)
    for node_id, node in min_3rta.nodes.items():
        real_source_id = min_3rta.get_real_node_id(node_id)
        
        for (symbol, region), target_node in node.transitions.items():
            real_target_id = min_3rta.get_real_node_id(target_node.id)
            region_str = str(region)
            
            # Check if the same edge has already been added
            edge_key = added_edges.get((real_source_id, real_target_id, symbol, region_str))
            
            if edge_key is None:
                # If it's a new edge, add it and record
                edge_key = tree.add_edge(real_source_id, real_target_id)
                edge_labels[(real_source_id, real_target_id, edge_key)] = (alphabet_map[symbol], region_str)
                added_edges[(real_source_id, real_target_id, symbol, region_str)] = edge_key
                
                # Update source information of target node
                tree.nodes[real_target_id]['sources'].append(symbol)
                tree.nodes[real_target_id]['regions'].append(region_str)
                tree.nodes[real_target_id]['from_nodes'].append(real_source_id)
    
    # Resolve conflicts between accepting and rejecting states
    conflicts = accepting & rejecting
    if conflicts:
        print(f"Found {len(conflicts)} conflicting nodes: {conflicts}")
        
        # Get positive and negative samples for analysis
        positive_samples = getattr(min_3rta, 'positive_samples', [])
        negative_samples = getattr(min_3rta, 'negative_samples', [])
        
        for conflict_node in conflicts:
            # Analyze samples reaching this node
            positive_reaching = []
            negative_reaching = []
            
            # Check positive samples
            for i, sample in enumerate(positive_samples):
                if _sample_reaches_node(min_3rta, sample, conflict_node):
                    positive_reaching.append(sample)
            
            # Check negative samples  
            for i, sample in enumerate(negative_samples):
                if _sample_reaches_node(min_3rta, sample, conflict_node):
                    negative_reaching.append(sample)
            
            # Apply time-based conflict resolution
            resolution = _resolve_conflict_by_time_patterns(positive_reaching, negative_reaching)
            
            if resolution == 'accepting':
                rejecting.discard(conflict_node)
                print(f"Resolved conflict for node {conflict_node}: prioritizing accepting state (time-based analysis)")
            else:
                accepting.discard(conflict_node)
                print(f"Resolved conflict for node {conflict_node}: prioritizing rejecting state (time-based analysis)")
    
    # Resolve conflicts between accepting and rejecting states
    conflicts = accepting & rejecting
    if conflicts:
        print(f"Found {len(conflicts)} conflicting nodes: {conflicts}")
        
        # Get positive and negative samples for analysis
        positive_samples = getattr(min_3rta, 'positive_samples', [])
        negative_samples = getattr(min_3rta, 'negative_samples', [])
        
        for conflict_node in conflicts:
            # Analyze samples reaching this node
            positive_reaching = []
            negative_reaching = []
            
            # Check positive samples
            for i, sample in enumerate(positive_samples):
                if _sample_reaches_node(min_3rta, sample, conflict_node):
                    positive_reaching.append(sample)
            
            # Check negative samples  
            for i, sample in enumerate(negative_samples):
                if _sample_reaches_node(min_3rta, sample, conflict_node):
                    negative_reaching.append(sample)
            
            # Apply time-based conflict resolution
            resolution = _resolve_conflict_by_time_patterns(positive_reaching, negative_reaching)
            
            if resolution == 'accepting':
                rejecting.discard(conflict_node)
                print(f"Resolved conflict for node {conflict_node}: prioritizing accepting state (time-based analysis)")
            else:
                accepting.discard(conflict_node)
                print(f"Resolved conflict for node {conflict_node}: prioritizing rejecting state (time-based analysis)")
    
    # Create and return APTA object
    return TDRTA(
        tree=tree,
        root=min_3rta.root,
        alphabet=alphabet_map,
        accepting=accepting,
        rejecting=rejecting,
        edge_labels=edge_labels,
        optimized=True,  # Assume Min3RTA is already optimized
        min_3rta=min_3rta  # Pass min_3rta to collect merged nodes
    )

def build_min_3rta(positive_samples, negative_samples):
    """Build and return minimized 3RTA and corresponding 3DRTA"""
    min_3rta = Min3RTA()
    min_3rta.build_from_samples(positive_samples, negative_samples)
    
    # Store samples for conflict resolution
    min_3rta.positive_samples = positive_samples
    min_3rta.negative_samples = negative_samples
    
    # Convert Min3RTA to 3DRTA structure
    drta = convert_to_3DRTA(min_3rta)
    
    return min_3rta, drta

def export_to_uppaal(drta, filename="rta_model.xml"):
    """
    Export 3DRTA structure to UPPAAL XML format
    
    Parameters:
    drta: APTA object, representing 3DRTA structure
    filename: Name of the output XML file
    
    Returns:
    Path of the generated XML file
    """
    if drta is None:
        print("Warning: Cannot export to UPPAAL format, DRTA structure is empty")
        return None
    
    # Create UPPAAL XML root element
    root = ET.Element("nta")
    
    # Add declaration section
    declaration = ET.SubElement(root, "declaration")
    declaration.text = "// Clock declarations\nclock x;\n\n// Constant declarations"
    
    # Invert alphabet map for easier lookup
    inv_alphabet = {v: k for k, v in drta.alphabet.items()}
    
    # Create template element
    template = ET.SubElement(root, "template")
    
    # Add template name
    name = ET.SubElement(template, "name")
    name.text = "RTA_Model"
    
    # Add local declaration
    local_declaration = ET.SubElement(template, "declaration")
    local_declaration.text = "// Local variable declarations"
    
    # Add all locations (nodes)
    for node_id in drta.nodes:
        location = ET.SubElement(template, "location")
        location.set("id", f"id{node_id}")
        
        # Add name label
        name_label = ET.SubElement(location, "name")
        name_label.text = f"q{node_id}"
        
        # Set location coordinates (simple layout)
        coordinate_x = (node_id % 5) * 150 + 100
        coordinate_y = (node_id // 5) * 150 + 100
        name_label.set("x", str(coordinate_x))
        name_label.set("y", str(coordinate_y - 30))
        
        # Set location attributes
        if node_id in drta.accepting:
            # Accepting state uses committed location
            ET.SubElement(location, "committed")
        
        # Set invariants (if time constraints)
        if node_id in drta.rejecting:
            # Rejecting state uses urgent location
            ET.SubElement(location, "urgent")
    
    # Add initial location
    init = ET.SubElement(template, "init")
    init.set("ref", f"id{drta.root}")
    
    # Add all transitions (edges)
    edge_keys = list(drta.edge_labels.keys())
    for edge_key in edge_keys:
        source, target, key = edge_key
        symbol_id, region_str = drta.edge_labels[edge_key]
        symbol = inv_alphabet[symbol_id]
        
        # Create transition element
        transition = ET.SubElement(template, "transition")
        
        # Set source and target
        source_elem = ET.SubElement(transition, "source")
        source_elem.set("ref", f"id{source}")
        
        target_elem = ET.SubElement(transition, "target")
        target_elem.set("ref", f"id{target}")
        
        # Set label (synchronisation, choice, guard, update)
        # Parse region string to extract time constraints
        region_text = region_str.replace("[", "").replace("]", "").replace("(", "").replace(")", "").replace(" ", "")
        if ',' in region_text:
            lower, upper = region_text.split(',')
            if upper == "∞" or upper == "inf":
                guard_text = f"x >= {lower}"
            else:
                if '[' in region_str:  # Closed lower bound
                    lower_op = ">="
                else:  # Open lower bound
                    lower_op = ">"
                
                if ']' in region_str:  # Closed upper bound
                    upper_op = "<="
                else:  # Open upper bound
                    upper_op = "<"
                
                guard_text = f"x {lower_op} {lower} && x {upper_op} {upper}"
        else:
            # Single point interval
            guard_text = f"x == {region_text}"
        
        # Add guard condition
        guard = ET.SubElement(transition, "guard")
        guard.text = guard_text
        guard.set("x", str((source % 5) * 150 + 50))
        guard.set("y", str((source // 5) * 150 + 50))
        
        # Add synchronisation label
        sync = ET.SubElement(transition, "synchronisation")
        sync.text = f"{symbol}!"
        sync.set("x", str((source % 5) * 150 + 50))
        sync.set("y", str((source // 5) * 150 + 70))
        
        # Add update label (reset clock)
        update = ET.SubElement(transition, "assignment")
        update.text = "x = 0"
        update.set("x", str((source % 5) * 150 + 50))
        update.set("y", str((source // 5) * 150 + 90))
        
        # Add comment
        nail = ET.SubElement(transition, "nail")
        mid_x = ((source % 5) + (target % 5)) * 75 + 100
        mid_y = ((source // 5) + (target // 5)) * 75 + 100
        nail.set("x", str(mid_x))
        nail.set("y", str(mid_y))
    
    # Add system declaration
    system = ET.SubElement(root, "system")
    system.text = "// Process instantiation\nsystem RTA_Model;"
    
    # Add queries
    queries = ET.SubElement(root, "queries")
    query = ET.SubElement(queries, "query")
    formula = ET.SubElement(query, "formula")
    formula.text = "E<> true"  # Example query
    comment = ET.SubElement(query, "comment")
    comment.text = "Verify model reachability"
    
    # Pretty print XML and write to file
    xml_str = ET.tostring(root, encoding='utf-8')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent="  ")
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(pretty_xml)
    
    print(f"\nUPPAAL model file generated: {filename}")
    abs_path = os.path.abspath(filename)
    print(f"Absolute path: {abs_path}")
    
    return abs_path

def main():
    """Main function, demonstrating Min-3RTA usage"""
    from tAPTA import BuildTimedAPTA
    from drawFig import visualize_tapta
    # S_positive = [
    #     [('a', 1)],                     # Accept a/1
    #     [('a', 2.5), ('b', 2)]          # Accept a/1.5 -> b/2
    # ]
    
    # S_negative = [
    #     [('b', 1)],                     # Reject b/1
    #     [('a', 3)]                      # Reject a/3
    # ]
    # Example positive sample set
    S_positive = [
        [('b', 2), ('b', 1)]
        # [('a', 1)],
        # [('a', 1.3), ('b', 5.2), ('b', 1)],
        # [('a', 2.7), ('c', 2.4)],
    ]
    
    # Example negative sample set
    S_negative = [
        # [('a', 2.2), ('a', 2.4)],
        [('b', 1), ('b', 1)]
    ]
    # S_positive = [
    #     [('a', 0.3), ('b', 1.2), ('f', 1.5), ('c', 1.6), ('d', 1.6), ('a', 2.7), ('d', 3.8), ('a', 4.2), ('f', 4.3), ('e', 4.4), ('a', 4.5)],  # trace80: 0.3-4.5 seconds, 11 events
    # ]
    # S_negative = [
    #     [('c', 0.9), ('b', 1.0), ('a', 2.1), ('a', 2.2), ('c', 2.5), ('a', 2.8), ('f', 3.3), ('c', 3.5), ('a', 3.7), ('d', 4.2), ('a', 4.6), ('e', 4.9)],  # trace1: 0.9-4.9 seconds, 12 events
    #     [('a', 0.8), ('e', 1.5), ('b', 1.9), ('a', 3.1)],  # trace2: 0.8-3.1 seconds, 4 events
    #     [('e', 1.0), ('f', 1.5), ('b', 1.6), ('f', 2.4), ('d', 3.0), ('b', 3.0), ('c', 3.5), ('c', 3.6), ('f', 4.1), ('b', 4.1), ('d', 4.1), ('f', 4.5)],  # trace3: 1.0-4.5 seconds, 12 events
    #  ]
    
    S_positive = [
        [('a', 0.2)],
        [('a', 1.3)]
    ]
    S_negative = []

    S_positive = [
        [('a', 1)],
        [('a', 1), ('b', 2), ('b', 1)],
        [('b', 2), ('b', 1)]
        
        # [('a', 1.3), ('b', 5.2), ('b', 1)],
        # [('a', 2.7), ('c', 2.4)],
    ]
    
    # Example negative sample set
    S_negative = [
        [('a', 1), ('b', 1), ('a', 1)],
        [('b', 2)],
        [('b', 1), ('b', 1)]
    ]
    # Build original TAPTA automaton
    print("Starting to build original TAPTA automaton...")
    tapta = BuildTimedAPTA(S_positive, S_negative)
    visualize_tapta(tapta, S_positive, S_negative, "original_tapta")
    
    # Build minimized 3RTA
    print("\nStarting to build minimized 3RTA automaton...")
    min_3rta, drta = build_min_3rta(S_positive, S_negative)
    min_3rta.print_automaton()
    
    # Visualize minimized 3RTA
    print("\nStarting to visualize minimized 3RTA automaton...")
    min_3rta.visualize_as_graphviz("min_3rta_automaton")
    
    # Print 3DRTA structure
    if drta is not None:
        print("\n3DRTA structure information:")
        print(f"Number of nodes: {len(drta.nodes)}")
        print(f"Number of accepting states: {len(drta.accepting)}")
        print(f"Number of rejecting states: {len(drta.rejecting)}")
        print(f"Alphabet map: {drta.alphabet}")
        
        print("\nNode attributes:")
        for node_id, attrs in drta.nodes.items():
            state_type = []
            if node_id in drta.accepting:
                state_type.append("Accepting state")
            if node_id in drta.rejecting:
                state_type.append("Rejecting state")
            if node_id == drta.root:
                state_type.append("Initial state")
            
            state_type_str = " (".join(state_type) + ")" if state_type else ""
            
            # Get sources, regions, and from_nodes arrays
            sources = attrs.get('sources', [])
            regions = attrs.get('regions', [])
            from_nodes = attrs.get('from_nodes', [])
            
            # Combine sources, regions, and from_nodes into path information, using set to remove duplicates
            path_tuples = set()
            for i in range(len(sources)):
                if i < len(regions) and i < len(from_nodes):
                    path_tuples.add((from_nodes[i], sources[i], regions[i]))
            
            # Convert to list of path string
            paths = [f"From node {src} via {sym}/{reg}" for src, sym, reg in path_tuples]
            
            # Print node information
            path_info = ", ".join(paths) if paths else "No incoming paths"
            print(f"   Node {node_id}{state_type_str}: {path_info}")
        
        print("\nEdges and labels:")
        # Print edges grouped by source and target nodes
        edges_by_nodes = {}
        for (source, target, key), (symbol_id, region) in drta.edge_labels.items():
            if (source, target) not in edges_by_nodes:
                edges_by_nodes[(source, target)] = []
            symbol = [k for k, v in drta.alphabet.items() if v == symbol_id][0]
            edges_by_nodes[(source, target)].append(f"{symbol}/{region}")
        
        # Print all edges
        for (source, target), labels in edges_by_nodes.items():
            labels_str = ", ".join(labels)
            print(f"  {source} --({labels_str})--> {target}")
        
        # Export to UPPAAL format
        print("\nStarting to export to UPPAAL format...")
        uppaal_file = export_to_uppaal(drta, "rta_model.xml")
        if uppaal_file:
            print(f"Can open file with UPPAAL: {uppaal_file} for further verification and analysis")
    else:
        print("\nWarning: Cannot generate 3DRTA structure, networkx library is required")
    
    print("\nMinimized automaton construction complete!")

if __name__ == "__main__":
    main()
