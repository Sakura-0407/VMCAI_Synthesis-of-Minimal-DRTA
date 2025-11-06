#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
generate_traces.py
Parse JSON automaton file and generate positive/negative traces conforming to the automaton
"""

import json
import random
import re
import argparse
import csv
from typing import List, Tuple, Dict, Any, Optional
from collections import deque

class TimeInterval:
    """Time interval class"""
    def __init__(self, interval_str: str):
        self.interval_str = interval_str
        self.parse_interval(interval_str)
    
    def parse_interval(self, interval_str: str):
        """Parse time interval string"""
        # Remove spaces
        interval_str = interval_str.replace(" ", "")
        
        # Parse left bracket
        if interval_str.startswith('['):
            self.left_closed = True
            left_bracket = '['
        elif interval_str.startswith('('):
            self.left_closed = False
            left_bracket = '('
        else:
            raise ValueError(f"Invalid interval format: {interval_str}")
        
        # Parse right bracket
        if interval_str.endswith(']'):
            self.right_closed = True
            right_bracket = ']'
        elif interval_str.endswith(')'):
            self.right_closed = False
            right_bracket = ')'
        else:
            raise ValueError(f"Invalid interval format: {interval_str}")
        
        # Extract interval content
        inner = interval_str[1:-1]
        parts = inner.split(',')
        if len(parts) != 2:
            raise ValueError(f"Invalid interval format: {interval_str}")
        
        # Parse left boundary
        left_str = parts[0].strip()
        if left_str == '-∞' or left_str == '-inf':
            self.left = float('-inf')
        else:
            self.left = float(left_str)
        
        # Parse right boundary
        right_str = parts[1].strip()
        if right_str == '∞' or right_str == 'inf' or right_str == '+' or right_str == '+)'.replace(')', ''):
            self.right = float('inf')
        else:
            self.right = float(right_str)
    
    def contains(self, value: float) -> bool:
        """Check if value is within interval"""
        if self.left_closed:
            left_ok = value >= self.left
        else:
            left_ok = value > self.left
        
        if self.right_closed:
            right_ok = value <= self.right
        else:
            right_ok = value < self.right
        
        return left_ok and right_ok
    
    def get_random_value(self) -> float:
        """Generate random value within interval"""
        if self.left == float('-inf') and self.right == float('inf'):
            return random.uniform(0, 100)  # Default range
        elif self.left == float('-inf'):
            return random.uniform(0, self.right - (0.1 if not self.right_closed else 0))
        elif self.right == float('inf'):
            return random.uniform(self.left + (0.1 if not self.left_closed else 0), self.left + 100)
        else:
            # Finite interval
            min_val = self.left + (0.1 if not self.left_closed else 0)
            max_val = self.right - (0.1 if not self.right_closed else 0)
            if min_val >= max_val:
                # If it's a point interval
                if self.left == self.right and self.left_closed and self.right_closed:
                    return self.left
                else:
                    raise ValueError(f"Invalid interval for random generation: {self.interval_str}")
            return random.uniform(min_val, max_val)

class Automaton:
    """Automaton class"""
    def __init__(self, json_data: Dict[str, Any]):
        self.name = json_data['name']
        self.states = json_data['s']
        self.alphabet = json_data['sigma']
        self.initial_state = json_data['init']
        self.accepting_states = set(json_data['accept'])
        self.rejecting_states = set(self.states) - self.accepting_states
        
        # Parse transition relations
        self.transitions = {}
        for trans_id, trans_data in json_data['tran'].items():
            source, symbol, interval_str, target = trans_data
            interval = TimeInterval(interval_str)
            
            if source not in self.transitions:
                self.transitions[source] = {}
            if symbol not in self.transitions[source]:
                self.transitions[source][symbol] = []
            
            self.transitions[source][symbol].append((interval, target))
    
    def get_possible_transitions(self, state: str, symbol: str, timestamp: float) -> List[str]:
        """Get possible transition targets at given timestamp"""
        if state not in self.transitions or symbol not in self.transitions[state]:
            return []
        
        possible_targets = []
        for interval, target in self.transitions[state][symbol]:
            if interval.contains(timestamp):
                possible_targets.append(target)
        
        return possible_targets
    
    def get_random_transition(self, state: str) -> Optional[Tuple[str, float, str]]:
        """Randomly select a transition from current state"""
        if state not in self.transitions:
            return None
        
        # Randomly select symbol
        available_symbols = list(self.transitions[state].keys())
        if not available_symbols:
            return None
        
        symbol = random.choice(available_symbols)
        
        # Randomly select a transition under this symbol
        available_transitions = self.transitions[state][symbol]
        interval, target = random.choice(available_transitions)
        
        # Generate random timestamp within time interval
        try:
            timestamp = interval.get_random_value()
            return symbol, timestamp, target
        except ValueError:
            return None

    def find_path_to_rejecting_state(self, max_depth: int = 10) -> Optional[List[Tuple[str, str]]]:
        """Use BFS to find path from initial state to any rejecting state"""
        if not self.rejecting_states:
            return None
            
        queue = deque([(self.initial_state, [])])
        visited = set()
        
        for _ in range(max_depth * len(self.states)):  # Limit search iterations
            if not queue:
                break
                
            current_state, path = queue.popleft()
            
            if current_state in visited:
                continue
            visited.add(current_state)
            
            # If reached rejecting state, return path
            if current_state in self.rejecting_states:
                return path
            
            # If path length reached limit, skip
            if len(path) >= max_depth:
                continue
            
            # Explore all possible transitions
            if current_state in self.transitions:
                for symbol in self.transitions[current_state]:
                    for interval, target in self.transitions[current_state][symbol]:
                        new_path = path + [(symbol, target)]
                        queue.append((target, new_path))
        
        return None

    def get_all_transitions_to_rejecting(self) -> List[Tuple[str, str, str]]:
        """Get all transitions pointing to rejecting states (source, symbol, target)"""
        rejecting_transitions = []
        
        for source_state in self.transitions:
            for symbol in self.transitions[source_state]:
                for interval, target in self.transitions[source_state][symbol]:
                    if target in self.rejecting_states:
                        rejecting_transitions.append((source_state, symbol, target))
        
        return rejecting_transitions

def generate_trace(automaton: Automaton, target_type: str, max_length: int = 20) -> List[Tuple[str, float]]:
    """Generate a trace"""
    trace = []
    current_state = automaton.initial_state
    min_steps = random.randint(1, 5)  # Execute at least 1-5 steps
    
    for step in range(max_length):
        # Force continuation in first few steps, then check if reached target state type
        if step >= min_steps:
            if target_type == "accepting" and current_state in automaton.accepting_states:
                break
            elif target_type == "rejecting" and current_state in automaton.rejecting_states:
                break
        
        # Try to make transition
        transition = automaton.get_random_transition(current_state)
        if transition is None:
            break
        
        symbol, timestamp, next_state = transition
        trace.append((symbol, timestamp))
        current_state = next_state
    
    # Check if final state meets requirements
    if target_type == "accepting" and current_state in automaton.accepting_states:
        return trace
    elif target_type == "rejecting" and current_state in automaton.rejecting_states:
        return trace
    else:
        return None

def generate_guided_rejecting_trace(automaton: Automaton, max_length: int = 20) -> Optional[List[Tuple[str, float]]]:
    """Generate rejecting trace using guided strategy"""
    # Strategy 1: Find a path to rejecting state
    path = automaton.find_path_to_rejecting_state(max_depth=max_length)
    if path:
        trace = []
        current_state = automaton.initial_state
        
        for symbol, target_state in path:
            # Find transition from current state through specified symbol to target state
            if (current_state in automaton.transitions and 
                symbol in automaton.transitions[current_state]):
                
                # Find correct transition
                for interval, trans_target in automaton.transitions[current_state][symbol]:
                    if trans_target == target_state:
                        try:
                            timestamp = interval.get_random_value()
                            trace.append((symbol, timestamp))
                            current_state = target_state
                            break
                        except ValueError:
                            continue
                else:
                    # If no valid transition found, fallback to random strategy
                    return None
            else:
                return None
        
        return trace
    
    # Strategy 2: Random walk biased toward rejecting states
    trace = []
    current_state = automaton.initial_state
    
    for step in range(max_length):
        if current_state in automaton.rejecting_states:
            break
            
        if current_state not in automaton.transitions:
            break
            
        # Prefer transitions pointing to rejecting states
        rejecting_transitions = []
        other_transitions = []
        
        for symbol in automaton.transitions[current_state]:
            for interval, target in automaton.transitions[current_state][symbol]:
                if target in automaton.rejecting_states:
                    rejecting_transitions.append((symbol, interval, target))
                else:
                    other_transitions.append((symbol, interval, target))
        
        # 70% probability to choose transition pointing to rejecting state (if exists)
        if rejecting_transitions and random.random() < 0.7:
            symbol, interval, target = random.choice(rejecting_transitions)
        elif other_transitions:
            symbol, interval, target = random.choice(other_transitions)
        else:
            break
            
        try:
            timestamp = interval.get_random_value()
            trace.append((symbol, timestamp))
            current_state = target
        except ValueError:
            break
    
    # Check if successfully reached rejecting state
    if current_state in automaton.rejecting_states:
        return trace
    else:
        return None

def generate_traces(automaton: Automaton, num_traces: int) -> Tuple[List[List[Tuple[str, float]]], List[List[Tuple[str, float]]]]:
    """Generate specified number of positive/negative traces"""
    positive_samples = []
    negative_samples = []
    
    num_positive = num_traces // 2
    num_negative = num_traces - num_positive
    
    print(f"Automaton information:")
    print(f"  Total states: {len(automaton.states)}")
    print(f"  Accepting states: {automaton.accepting_states}")
    print(f"  Rejecting states: {automaton.rejecting_states}")
    print(f"  Initial state: {automaton.initial_state}")
    
    # Check rejecting state reachability
    if not automaton.rejecting_states:
        print("Warning: No rejecting states, cannot generate negative samples")
    else:
        path_to_rejecting = automaton.find_path_to_rejecting_state()
        if path_to_rejecting:
            print(f"  Found path to rejecting state: {path_to_rejecting}")
        else:
            print("  Warning: Cannot reach any rejecting state from initial state")
    
    # Generate positive samples
    print(f"\nGenerating {num_positive} positive traces...")
    attempts = 0
    max_attempts = num_positive * 20  # Increase attempt count
    
    while len(positive_samples) < num_positive and attempts < max_attempts:
        trace = generate_trace(automaton, "accepting", max_length=random.randint(3, 15))
        if trace is not None and len(trace) > 0:
            positive_samples.append(trace)
        attempts += 1
    
    print(f"  Successfully generated {len(positive_samples)} positive traces")
    
    # Generate negative samples - using improved strategy
    print(f"\nGenerating {num_negative} negative traces...")
    attempts = 0
    max_attempts = num_negative * 50  # Significantly increase attempt count
    guided_attempts = 0
    random_attempts = 0
    
    while len(negative_samples) < num_negative and attempts < max_attempts:
        # First 50% attempts use guided strategy, last 50% use random strategy
        if attempts < max_attempts // 2:
            trace = generate_guided_rejecting_trace(automaton, max_length=random.randint(3, 15))
            guided_attempts += 1
        else:
            trace = generate_trace(automaton, "rejecting", max_length=random.randint(3, 15))
            random_attempts += 1
            
        if trace is not None and len(trace) > 0:
            negative_samples.append(trace)
        attempts += 1
    
    print(f"  Successfully generated {len(negative_samples)} negative traces")
    print(f"  Guided strategy attempts: {guided_attempts}, Random strategy attempts: {random_attempts}")
    
    if len(negative_samples) == 0:
        print("  Warning: Failed to generate any negative samples, possible reasons:")
        print("    1. Rejecting states are unreachable")
        print("    2. Paths to rejecting states are too complex")
        print("    3. Time constraints are too strict")
    
    return positive_samples, negative_samples

def format_csv_output(positive_samples: List[List[Tuple[str, float]]], 
                     negative_samples: List[List[Tuple[str, float]]],
                     automaton: Automaton,
                     output_file: str) -> str:
    """Format CSV output"""
    # Create symbol to number mapping
    symbol_to_num = {symbol: i for i, symbol in enumerate(automaton.alphabet)}
    
    csv_rows = []
    trace_counter = 1
    
    # Process positive traces
    for trace in positive_samples:
        trace_id = f"trace{trace_counter:03d}"
        for symbol, timestamp in trace:
            symbol_num = symbol_to_num[symbol]
            csv_rows.append([trace_id, symbol_num, f"{timestamp:.1f}", 1])
        trace_counter += 1
    
    # Process negative traces
    for trace in negative_samples:
        trace_id = f"trace{trace_counter:03d}"
        for symbol, timestamp in trace:
            symbol_num = symbol_to_num[symbol]
            csv_rows.append([trace_id, symbol_num, f"{timestamp:.1f}", 0])
        trace_counter += 1
    
    # Write to CSV file
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        # Write header
        writer.writerow(['id', 'symb', 'attr/f:duration', 'label'])
        # Write data
        writer.writerows(csv_rows)
    
    print(f"CSV results saved to: {output_file}")
    return f"CSV file contains {len(csv_rows)} rows of data"

def format_output(positive_samples: List[List[Tuple[str, float]]], 
                 negative_samples: List[List[Tuple[str, float]]],
                 output_file: str = None,
                 csv_output_file: str = None,
                 automaton: Automaton = None) -> str:
    """Format output"""
    output_lines = []
    
    # Format positive samples
    output_lines.append("positive_samples = [")
    for i, trace in enumerate(positive_samples):
        trace_str = "[" + ", ".join([f"('{symbol}', {timestamp:.1f})" for symbol, timestamp in trace]) + "]"
        if i < len(positive_samples) - 1:
            output_lines.append(f"    {trace_str},")
        else:
            output_lines.append(f"    {trace_str}")
    output_lines.append("]")
    output_lines.append("")
    
    # Format negative samples
    output_lines.append("negative_samples = [")
    for i, trace in enumerate(negative_samples):
        trace_str = "[" + ", ".join([f"('{symbol}', {timestamp:.1f})" for symbol, timestamp in trace]) + "]"
        if i < len(negative_samples) - 1:
            output_lines.append(f"    {trace_str},")
        else:
            output_lines.append(f"    {trace_str}")
    output_lines.append("]")
    
    result = "\n".join(output_lines)
    
    # If Python output file specified, write to file
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"Python format results saved to: {output_file}")
    
    # If CSV output file specified, generate CSV
    if csv_output_file and automaton:
        format_csv_output(positive_samples, negative_samples, automaton, csv_output_file)
    
    return result

def main():
    parser = argparse.ArgumentParser(description='Generate traces from JSON automaton file')
    parser.add_argument('json_file', help='JSON automaton file path')
    parser.add_argument('--num-traces', '-n', type=int, default=100, 
                       help='Total number of traces to generate (default: 100)')
    parser.add_argument('--output', '-o', type=str, 
                       help='Python format output file path (optional)')
    parser.add_argument('--csv-output', '-c', type=str,
                       help='CSV format output file path (optional)')
    parser.add_argument('--seed', type=int, default=None,
                       help='Random seed (default: different each run)')
    
    args = parser.parse_args()
    
    # Set random seed (only when user specifies)
    if args.seed is not None:
        random.seed(args.seed)
        print(f"Using fixed random seed: {args.seed}")
    else:
        print("Using random seed, results differ each run")
    
    # Read JSON file
    try:
        with open(args.json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found {args.json_file}")
        return
    except json.JSONDecodeError:
        print(f"Error: Unable to parse JSON file {args.json_file}")
        return
    
    # Create automaton
    try:
        automaton = Automaton(json_data)
        print(f"Successfully loaded automaton: {automaton.name}")
        print(f"States: {automaton.states}")
        print(f"Alphabet: {automaton.alphabet}")
        print(f"Initial state: {automaton.initial_state}")
        print(f"Accepting states: {list(automaton.accepting_states)}")
        print(f"Rejecting states: {list(automaton.rejecting_states)}")
        print()
    except Exception as e:
        print(f"Error: Failed to parse automaton - {e}")
        return
    
    # Generate traces
    positive_samples, negative_samples = generate_traces(automaton, args.num_traces)
    
    print(f"\nGeneration completed:")
    print(f"Positive samples: {len(positive_samples)}")
    print(f"Negative samples: {len(negative_samples)}")
    print(f"Total: {len(positive_samples) + len(negative_samples)}")
    
    # Format and output results
    result = format_output(positive_samples, negative_samples, args.output, args.csv_output, automaton)
    
    if not args.output and not args.csv_output:
        print("\nGenerated traces:")
        print("=" * 50)
        print(result)

if __name__ == "__main__":
    main() 