#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
DRTA.py
Implementation of Deterministic Real-Time Automaton (DRTA)
Contains data structure definitions and related functions
"""

import os
import copy
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional, Union, Any

# Import visualization related modules
try:
    import graphviz
    GRAPHVIZ_AVAILABLE = True
except ImportError:
    GRAPHVIZ_AVAILABLE = False
    print("Note: graphviz library not installed or cannot be imported.")
    print("To use graphviz, run: pip install graphviz")
    print("And ensure Graphviz software is installed: https://graphviz.org/download/")

# Import networkx
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    print("Note: networkx library not installed or cannot be imported.")
    print("To use networkx, run: pip install networkx")

# Set Graphviz executable path
GRAPHVIZ_DOT_PATH = "C:/Program Files/Graphviz/bin/dot.exe"
if os.path.exists(GRAPHVIZ_DOT_PATH) and GRAPHVIZ_AVAILABLE:
    # If exists, set environment variable
    os.environ["PATH"] += os.pathsep + os.path.dirname(GRAPHVIZ_DOT_PATH)
    # Set graphviz library dot command path
    graphviz.backend.dot_command = GRAPHVIZ_DOT_PATH
    print(f"Graphviz path set: {GRAPHVIZ_DOT_PATH}")
    print("Configured graphviz library to use system-installed Graphviz")

class TimeRegion:
    """Class representing time region, can be a point [t,t] or interval (t1,t2)"""
    def __init__(self, lower, upper, lower_inclusive=True, upper_inclusive=False):
        # Lower bound value
        self.lower = lower
        # Upper bound value
        self.upper = upper
        # Whether lower bound is included (closed interval)
        self.lower_inclusive = lower_inclusive
        # Whether upper bound is included (closed interval)
        self.upper_inclusive = upper_inclusive
    
    def contains(self, value):
        """Check if region contains given value"""
        # Check if value is greater than or equal to lower bound (closed) or strictly greater than lower bound (open)
        if self.lower_inclusive:
            lower_check = value >= self.lower
        else:
            lower_check = value > self.lower
        
        # Check if value is less than or equal to upper bound (closed) or strictly less than upper bound (open)
        if self.upper_inclusive:
            upper_check = value <= self.upper
        else:
            upper_check = value < self.upper
        
        # Only return True when both lower and upper conditions are satisfied
        return lower_check and upper_check
    
    def overlaps(self, other):
        """Check if two regions overlap"""
        # Check if two regions overlap (one region's lower bound is less than or equal to other's upper bound)
        has_overlap = (
            (self.lower <= other.upper and self.upper >= other.lower) or
            (other.lower <= self.upper and other.upper >= self.lower)
        )
        
        # Check if adjacent but non-overlapping
        if not has_overlap:
            # Two intervals are adjacent
            is_adjacent = (
                (self.upper == other.lower and (self.upper_inclusive or other.lower_inclusive)) or
                (other.upper == self.lower and (other.upper_inclusive or self.lower_inclusive))
            )
            return is_adjacent
        
        return has_overlap
    
    def __str__(self):
        # String representation, display as [x,y], (x,y), [x,y) or (x,y] based on inclusion
        left = '[' if self.lower_inclusive else '('
        right = ']' if self.upper_inclusive else ')'
        # If upper bound is infinity, use ∞ symbol
        upper_str = str(self.upper) if self.upper != float('inf') else '∞'
        return f"{left}{self.lower}, {upper_str}{right}"
    
    def __eq__(self, other):
        # Check if two regions are equal
        if not isinstance(other, TimeRegion):
            return False
        # Compare all attributes are identical
        return (self.lower == other.lower and 
                self.upper == other.upper and 
                self.lower_inclusive == other.lower_inclusive and 
                self.upper_inclusive == other.upper_inclusive)
    
    def __hash__(self):
        # Generate hash value for use as dictionary key or set element
        return hash((self.lower, self.upper, self.lower_inclusive, self.upper_inclusive))

class DRTA:
    """
    Deterministic Real-Time Automaton (DRTA)
    """
    def __init__(self):
        # Use networkx MultiDiGraph as base data structure
        if not NETWORKX_AVAILABLE:
            raise ImportError("networkx library required to create DRTA")
        
        self.graph = nx.MultiDiGraph()
        self.root = None  # Initial state
        self.accepting_states = set()  # Set of accepting states
        self.rejecting_states = set()  # Set of rejecting states
        self.alphabet = {}  # Alphabet mapping: symbol -> id
        self.next_symbol_id = 0  # Next available symbol ID
        self.next_state_id = 0  # Next available state ID
    
    def add_state(self, is_accepting=False, is_rejecting=False, is_initial=False):
        """Add new state and return its ID"""
        state_id = self.next_state_id
        self.next_state_id += 1
        
        # Add node, initialize attributes
        self.graph.add_node(state_id, 
                           sources=[], 
                           regions=[], 
                           from_states=[])
        
        # Set state type
        if is_accepting:
            self.accepting_states.add(state_id)
        if is_rejecting:
            self.rejecting_states.add(state_id)
        if is_initial or self.root is None:
            self.root = state_id
        
        return state_id
    
    def get_symbol_id(self, symbol):
        """Get symbol ID, add if not exists"""
        if symbol not in self.alphabet:
            self.alphabet[symbol] = self.next_symbol_id
            self.next_symbol_id += 1
        return self.alphabet[symbol]
    
    def add_transition(self, source_id, target_id, symbol, time_region):
        """
        Add a transition
        
        Parameters:
        source_id: Source state ID
        target_id: Target state ID
        symbol: Transition symbol
        time_region: TimeRegion object representing time constraint
        """
        # Ensure states exist
        if source_id not in self.graph:
            raise ValueError(f"Source state ID {source_id} does not exist")
        if target_id not in self.graph:
            raise ValueError(f"Target state ID {target_id} does not exist")
        
        # Get symbol ID
        symbol_id = self.get_symbol_id(symbol)
        
        # Check if identical transition already exists
        if self.graph.has_edge(source_id, target_id):
            for edge_key, edge_data in self.graph.get_edge_data(source_id, target_id).items():
                if edge_data.get('symbol_id') == symbol_id and edge_data.get('region') == str(time_region):
                    # Identical transition exists, don't add duplicate
                    return edge_key
        
        # Add new transition
        key = self.graph.add_edge(source_id, target_id)
        self.graph.edges[source_id, target_id, key].update({
            'symbol': symbol,
            'symbol_id': symbol_id,
            'region': str(time_region),
            'region_obj': time_region
        })
        
        # Update target state source information
        self.graph.nodes[target_id]['sources'].append(symbol)
        self.graph.nodes[target_id]['regions'].append(str(time_region))
        self.graph.nodes[target_id]['from_states'].append(source_id)
        
        return key

    def remove_transition(self, source_id, target_id, key=None):
        """
        Remove a transition
        
        Parameters:
        source_id: Source state ID
        target_id: Target state ID
        key: Optional edge key, if not provided remove all transitions from source to target
        """
        if key is not None:
            # Remove specific transition
            if self.graph.has_edge(source_id, target_id, key):
                self.graph.remove_edge(source_id, target_id, key)
        else:
            # Remove all transitions from source to target
            self.graph.remove_edges_from([(source_id, target_id, k) for k in self.graph[source_id][target_id]])
    
    def remove_state(self, state_id):
        """
        Remove a state and all its transitions
        
        Parameters:
        state_id: State ID to remove
        """
        if state_id not in self.graph:
            return
        
        # Remove state
        self.graph.remove_node(state_id)
        
        # Update accepting/rejecting state sets
        if state_id in self.accepting_states:
            self.accepting_states.remove(state_id)
        if state_id in self.rejecting_states:
            self.rejecting_states.remove(state_id)
        
        # If removed state is initial state, set initial state to None
        if state_id == self.root:
            if len(self.graph) > 0:
                self.root = list(self.graph.nodes)[0]  # Set any node as new initial state
            else:
                self.root = None
    
    def set_state_accepting(self, state_id, is_accepting=True):
        """Set state as accepting state"""
        if state_id not in self.graph:
            raise ValueError(f"State ID {state_id} does not exist")
        
        if is_accepting:
            self.accepting_states.add(state_id)
            # Ensure not simultaneously rejecting
            if state_id in self.rejecting_states:
                self.rejecting_states.remove(state_id)
        else:
            if state_id in self.accepting_states:
                self.accepting_states.remove(state_id)
    
    def set_state_rejecting(self, state_id, is_rejecting=True):
        """Set state as rejecting state"""
        if state_id not in self.graph:
            raise ValueError(f"State ID {state_id} does not exist")
        
        if is_rejecting:
            self.rejecting_states.add(state_id)
            # Ensure not simultaneously accepting
            if state_id in self.accepting_states:
                self.accepting_states.remove(state_id)
        else:
            if state_id in self.rejecting_states:
                self.rejecting_states.remove(state_id)
    
    def set_initial_state(self, state_id):
        """Set initial state"""
        if state_id not in self.graph:
            raise ValueError(f"State ID {state_id} does not exist")
        self.root = state_id
    
    def print_automaton(self):
        """Print automaton structure"""
        print("Deterministic Real-Time Automaton (DRTA):")
        print(f"Number of states: {len(self.graph.nodes)}")
        print(f"Number of accepting states: {len(self.accepting_states)}")
        print(f"Number of rejecting states: {len(self.rejecting_states)}")
        print(f"Alphabet: {self.alphabet}")
        
        # Print all states
        print("\nStates:")
        for state_id in self.graph.nodes:
            state_type = []
            if state_id == self.root:
                state_type.append("Initial state")
            if state_id in self.accepting_states:
                state_type.append("Accepting state")
            if state_id in self.rejecting_states:
                state_type.append("Rejecting state")
            
            state_type_str = " (".join(state_type) + ")" if state_type else ""
            print(f"  State {state_id}{state_type_str}")
        
        # Print all transitions
        print("\nTransitions:")
        # Iterate over all edges between node pairs
        for source in self.graph.nodes:
            for target in self.graph.successors(source):
                # Get all edges from source to target
                edge_data_dict = self.graph.get_edge_data(source, target)
                for key, data in edge_data_dict.items():
                    symbol = data.get('symbol', '?')
                    region = data.get('region', '?')
                    print(f"  {source} --({symbol}/{region})--> {target}")
    
    def visualize_as_graphviz(self, output_file="drta_automaton"):
        """
        Visualize DRTA automaton as image using Graphviz
        
        Parameters:
        output_file: Output filename (without extension)
        
        Returns:
        Generated image file path
        """
        if not GRAPHVIZ_AVAILABLE:
            print("graphviz library unavailable, cannot generate visualization image.")
            return None
        
        # Create directed graph
        dot = graphviz.Digraph('DRTA', filename=output_file, format='png', 
                              engine='dot', encoding='utf-8')
        dot.attr(rankdir='LR')  # Left-to-right layout
        
        # Create nodes for states
        for state_id in self.graph.nodes:
            # Node label
            label = f"q{state_id}"
            
            # Node attributes
            attrs = {
                'shape': 'circle',
                'style': 'filled',
                'fillcolor': 'white',
                'fontname': 'SimSun'  # Use Chinese font
            }
            
            # Special state styles
            if state_id == self.root:
                attrs['penwidth'] = '2'  # Initial state bold outline
            
            if state_id in self.accepting_states:
                attrs['shape'] = 'doublecircle'  # Accepting state double circle
                attrs['fillcolor'] = '#e6ffcc'  # Light green
            elif state_id in self.rejecting_states:
                attrs['fillcolor'] = '#ffcccc'  # Light red
            
            # Add node
            dot.node(str(state_id), label, **attrs)
        
        # Initial state indicator arrow
        if self.root is not None:
            dot.node('start', label='', shape='none')
            dot.edge('start', str(self.root), arrowhead='normal')
        
        # Add transition edges
        processed_edges = set()  # Avoid duplicate edges
        
        # Iterate over all edges between node pairs
        for source in self.graph.nodes:
            for target in self.graph.successors(source):
                # Get all edges from source to target
                edge_data_dict = self.graph.get_edge_data(source, target)
                for key, data in edge_data_dict.items():
                    symbol = data.get('symbol', '?')
                    region = data.get('region', '?')
                    
                    # Create edge identifier to avoid duplicates
                    edge_key = (source, target, symbol, region)
                    if edge_key in processed_edges:
                        continue
                    
                    # Edge label
                    edge_label = f"{symbol}/{region}"
                    
                    # Add edge
                    dot.edge(str(source), str(target), label=edge_label, fontname='SimSun')
                    processed_edges.add(edge_key)
        
        # Save image
        try:
            dot.render(cleanup=True)  # Generate image and clean up dot file
            print(f"\nDRTA graph saved to file: {output_file}.png")
            
            # Display absolute path
            abs_path = os.path.abspath(f"{output_file}.png")
            print(f"Absolute path: {abs_path}")
            return abs_path
        except Exception as e:
            print(f"Error generating image with graphviz: {e}")
            return None
    
    def export_to_uppaal(self, filename="drta_model.xml"):
        """
        Export DRTA structure to UPPAAL XML format
        
        Parameters:
        filename: Output XML filename
        
        Returns:
        Generated XML file path
        """
        # Create UPPAAL XML root element
        root = ET.Element("nta")
        
        # Add declaration section
        declaration = ET.SubElement(root, "declaration")
        declaration.text = "// Clock declaration\nclock x;\n\n// Constant declaration"
        
        # Create template element
        template = ET.SubElement(root, "template")
        
        # Add template name
        name = ET.SubElement(template, "name")
        name.text = "DRTA_Model"
        
        # Add local declaration
        local_declaration = ET.SubElement(template, "declaration")
        local_declaration.text = "// Local variable declaration"
        
        # Add all locations (nodes)
        for state_id in self.graph.nodes:
            location = ET.SubElement(template, "location")
            location.set("id", f"id{state_id}")
            
            # Add name label
            name_label = ET.SubElement(location, "name")
            name_label.text = f"q{state_id}"
            
            # Set location coordinates (simple layout)
            coordinate_x = (state_id % 5) * 150 + 100
            coordinate_y = (state_id // 5) * 150 + 100
            name_label.set("x", str(coordinate_x))
            name_label.set("y", str(coordinate_y - 30))
            
            # Set location attributes
            if state_id in self.accepting_states:
                # Accepting state uses committed location
                ET.SubElement(location, "committed")
            
            # Set invariant (if time constraints exist)
            if state_id in self.rejecting_states:
                # Rejecting state uses urgent location
                ET.SubElement(location, "urgent")
        
        # Add initial location
        if self.root is not None:
            init = ET.SubElement(template, "init")
            init.set("ref", f"id{self.root}")
        
        # Add all transitions (edges)
        # Iterate over all edges between node pairs
        for source in self.graph.nodes:
            for target in self.graph.successors(source):
                # Get all edges from source to target
                edge_data_dict = self.graph.get_edge_data(source, target)
                for key, data in edge_data_dict.items():
                    symbol = data.get('symbol', '?')
                    region_str = data.get('region', '(0, inf)')
                    
                    # Create transition element
                    transition = ET.SubElement(template, "transition")
                    
                    # Set source and target
                    source_elem = ET.SubElement(transition, "source")
                    source_elem.set("ref", f"id{source}")
                    
                    target_elem = ET.SubElement(transition, "target")
                    target_elem.set("ref", f"id{target}")
                    
                    # Set labels (synchronization, selection, guard, update)
                    # Parse region string, extract time constraints
                    region_text = region_str.replace("[", "").replace("]", "").replace("(", "").replace(")", "").replace(" ", "")
                    if ',' in region_text:
                        lower, upper = region_text.split(',')
                        if upper == "∞" or upper == "inf":
                            guard_text = f"x >= {lower}"
                        else:
                            if '[' in region_str:  # Closed interval lower bound
                                lower_op = ">="
                            else:  # Open interval lower bound
                                lower_op = ">"
                            
                            if ']' in region_str:  # Closed interval upper bound
                                upper_op = "<="
                            else:  # Open interval upper bound
                                upper_op = "<"
                            
                            guard_text = f"x {lower_op} {lower} && x {upper_op} {upper}"
                    else:
                        # Point interval
                        guard_text = f"x == {region_text}"
                    
                    # Add guard condition
                    guard = ET.SubElement(transition, "guard")
                    guard.text = guard_text
                    guard.set("x", str((source % 5) * 150 + 50))
                    guard.set("y", str((source // 5) * 150 + 50))
                    
                    # Add synchronization label
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
        system.text = "// Process instantiation\nsystem DRTA_Model;"
        
        # Add queries
        queries = ET.SubElement(root, "queries")
        query = ET.SubElement(queries, "query")
        formula = ET.SubElement(query, "formula")
        formula.text = "E<> true"  # Example query
        comment = ET.SubElement(query, "comment")
        comment.text = "Verify model reachability"
        
        # Beautify XML and write to file
        xml_str = ET.tostring(root, encoding='utf-8')
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent="  ")
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(pretty_xml)
        
        print(f"\nGenerated UPPAAL model file: {filename}")
        abs_path = os.path.abspath(filename)
        print(f"Absolute path: {abs_path}")
        
        return abs_path

def accepts(drta, word):
    """
    Check if DRTA accepts a timed word
    
    Parameters:
    drta: DRTA object
    word: Timed word, format: [(symbol1, time1), (symbol2, time2), ...]
    
    Returns:
    Boolean value indicating acceptance
    """
    if not word:
        # Empty word case, check if initial state is accepting
        return drta.root in drta.accepting_states
    
    current_state = drta.root
    
    for symbol, time in word:
        # Find matching transition
        found_transition = False
        
        # Check all edges from current state
        for target in drta.graph.successors(current_state):
            # Get all edges from current_state to target
            edge_data_dict = drta.graph.get_edge_data(current_state, target)
            for key, data in edge_data_dict.items():
                if data.get('symbol') == symbol:
                    region_obj = data.get('region_obj')
                    if region_obj and region_obj.contains(time):
                        current_state = target
                        found_transition = True
                        break
            if found_transition:
                break
        
        if not found_transition:
            # No matching transition found, reject
            return False
    
    # Check if final state is accepting
    return current_state in drta.accepting_states

def main():
    """Example code demonstrating DRTA usage"""
    # Create a DRTA object
    drta = DRTA()
    
    # Add states
    q0 = drta.add_state(is_initial=True)
    q1 = drta.add_state()
    q2 = drta.add_state(is_accepting=True)
    q3 = drta.add_state()
    q4 = drta.add_state(is_rejecting=True)
    
    # Add transitions
    drta.add_transition(q0, q1, 'a', TimeRegion(1, 2, False, False))  # (1,2)
    drta.add_transition(q0, q3, 'b', TimeRegion(1, 1, True, True))    # [1,1]
    drta.add_transition(q1, q2, 'a', TimeRegion(2, 3, False, False))  # (2,3)
    drta.add_transition(q3, q4, 'a', TimeRegion(3, float('inf'), False, False))  # (3,∞)
    
    # Print automaton structure
    drta.print_automaton()
    
    # Visualize automaton
    drta.visualize_as_graphviz("drta_example")
    
    # Export to UPPAAL format
    drta.export_to_uppaal("drta_example.xml")
    
    # Test accept/reject examples
    test_words = [
        [('a', 1.5), ('a', 2.5)],  # Should accept
        [('b', 1), ('a', 3.5)],    # Should reject
        [('a', 0.5)]               # Should reject (no matching transition)
    ]
    
    print("\nAccept/Reject tests:")
    for word in test_words:
        result = "Accept" if accepts(drta, word) else "Reject"
        print(f"  {word}: {result}")

if __name__ == "__main__":
    main()
