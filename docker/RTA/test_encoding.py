#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_encoding.py
Test SMT encoding functionality of TDRTA
"""

import z3
from z3 import *
from Min3RTA import TDRTA, build_min_3rta
from Encoding import Encoding
import networkx as nx
import time
import sys
import os
import contextlib
import io

def generate_tapta_dot_content(tapta, positive_samples, negative_samples):
    """
    Generate DOT content for TAPTA automaton
    
    Args:
    tapta: TAPTA object
    positive_samples: List of positive samples
    negative_samples: List of negative samples
    
    Returns:
    DOT content as string
    """
    try:
        import graphviz
    except ImportError:
        return "// graphviz library not available"
    
    # Create directed graph
    dot = graphviz.Digraph('TAPTA', engine='dot', encoding='utf-8')
    dot.attr(rankdir='LR')  # Left-to-right layout
    
    # Get TAPTA states and transitions
    try:
        # Try different ways to access TAPTA structure
        if hasattr(tapta, 'states'):
            states = tapta.states
        elif hasattr(tapta, 'nodes'):
            states = tapta.nodes
        else:
            # Fallback: create basic structure
            states = set()
            for sample in positive_samples + negative_samples:
                states.add(0)  # At least initial state
                for i in range(len(sample)):
                    states.add(i + 1)
        
        # Create nodes
        for state_id in states:
            # Determine if state is accepting or rejecting
            is_accepting = False
            is_rejecting = False
            
            # Check if this state is final for any positive/negative sample
            for sample in positive_samples:
                if len(sample) == state_id:
                    is_accepting = True
            for sample in negative_samples:
                if len(sample) == state_id:
                    is_rejecting = True
            
            # Node attributes
            attrs = {
                'shape': 'circle',
                'style': 'filled',
                'fillcolor': 'white',
                'fontname': 'SimSun'
            }
            
            if state_id == 0:
                attrs['penwidth'] = '2'  # Initial state bold outline
            
            if is_accepting:
                attrs['shape'] = 'doublecircle'
                attrs['fillcolor'] = '#e6ffcc'  # Light green
            elif is_rejecting:
                attrs['fillcolor'] = '#ffcccc'  # Light red
            
            dot.node(str(state_id), f"q{state_id}", **attrs)
        
        # Add initial state indicator
        dot.node('start', label='', shape='none')
        dot.edge('start', '0', arrowhead='normal')
        
        # Add transitions based on samples
        transitions_added = set()
        for sample in positive_samples + negative_samples:
            current_state = 0
            for i, (symbol, timestamp) in enumerate(sample):
                next_state = i + 1
                
                # Create edge label
                edge_label = f"{symbol}/{timestamp}"
                
                # Avoid duplicate edges
                edge_key = (current_state, next_state, symbol, timestamp)
                if edge_key not in transitions_added:
                    dot.edge(str(current_state), str(next_state), label=edge_label, fontname='SimSun')
                    transitions_added.add(edge_key)
                
                current_state = next_state
        
        return dot.source
        
    except Exception as e:
        return f"// Error generating TAPTA DOT content: {e}"
    # positive_samples = [
    #     [('a', 1.0),('b', 1.0)], # trace2: 1-3 seconds
    #     [('a', 1.0)], # trace2: 1-3 seconds
    # ]

    # negative_samples = [
    #     [('b', 1.0),('a', 1.0)], # trace1: 1-3 seconds
    #     [('b', 1.0)], # trace2: 1-3 seconds
    # ]
def load_samples_from_file(filepath):
    """
    Load positive_samples and negative_samples from specified Python file
    
    Args:
    filepath: Python file path containing sample data
    
    Returns:
    tuple: (positive_samples, negative_samples)
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    
    # Read file content
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create namespace to execute file content
    namespace = {}
    try:
        exec(content, namespace)
    except Exception as e:
        raise ValueError(f"Error executing file {filepath}: {e}")
    
    # Extract positive_samples and negative_samples
    if 'positive_samples' not in namespace:
        raise ValueError(f"positive_samples not found in file {filepath}")
    if 'negative_samples' not in namespace:
        raise ValueError(f"negative_samples not found in file {filepath}")
    
    positive_samples = namespace['positive_samples']
    negative_samples = namespace['negative_samples']
    
    # Minimal output
    print(f"Successfully loaded sample data from {filepath}:")
    print(f"  Positive samples: {len(positive_samples)} traces")
    print(f"  Negative samples: {len(negative_samples)} traces")
    
    return positive_samples, negative_samples

def create_simple_tdrta(positive_samples, negative_samples, save_files=False, output_dir=None):
    """
    Create TDRTA using given samples
    
    Args:
    positive_samples: List of positive samples
    negative_samples: List of negative samples
    save_files: Whether to save visualization files
    output_dir: Output directory for saving files (if None, uses default)
    
    Returns:
    A TDRTA instance
    """
    # Create TDRTA using build_min_3rta (allow debug output)
    min_3rta, drta = build_min_3rta(positive_samples, negative_samples)
    
    # Generate unique filename based on sample count
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    pos_count = len(positive_samples)
    neg_count = len(negative_samples)
    
    # Save Min3RTA visualization (only if requested)
    if save_files and output_dir:
        os.makedirs(output_dir, exist_ok=True)
        min3rta_filename = os.path.join(output_dir, f"min3rta_{pos_count}p{neg_count}n_{timestamp}")
        try:
            # Allow debug output from visualization
            min_3rta.visualize_as_graphviz(min3rta_filename)
            
            # Also save DOT file separately
            try:
                import graphviz
                dot_content = min_3rta.generate_dot_content()
                dot_filename = f"{min3rta_filename}.dot"
                with open(dot_filename, 'w', encoding='utf-8') as f:
                    f.write(dot_content)
            except Exception:
                pass  # Silently ignore errors
                
        except Exception:
            pass  # Silently ignore errors
    
    # Save original TAPTA visualization if available (only if requested)
    if save_files and output_dir:
        try:
            from tAPTA import BuildTimedAPTA
            from drawFig import visualize_tapta
            
            # Allow debug output
            tapta = BuildTimedAPTA(positive_samples, negative_samples)
            
            tapta_filename = os.path.join(output_dir, f"original_tapta_{pos_count}p{neg_count}n_{timestamp}")
            
            # Try to visualize TAPTA with Unicode error handling
            try:
                visualize_tapta(tapta, positive_samples, negative_samples, tapta_filename)
                
                # Also try to save TAPTA DOT file
                try:
                    tapta_dot_content = generate_tapta_dot_content(tapta, positive_samples, negative_samples)
                    tapta_dot_filename = f"{tapta_filename}.dot"
                    with open(tapta_dot_filename, 'w', encoding='utf-8') as f:
                        f.write(tapta_dot_content)
                except Exception:
                    pass  # Silently ignore errors
                    
            except UnicodeEncodeError:
                # Try alternative approach: save without problematic Unicode characters
                try:
                    # Use matplotlib directly with basic settings
                    import matplotlib.pyplot as plt
                    plt.figure(figsize=(12, 8))
                    
                    # Try to get TAPTA state count, fallback to generic message
                    try:
                        state_count = len(tapta.states) if hasattr(tapta, 'states') else len(tapta.nodes) if hasattr(tapta, 'nodes') else "unknown"
                        state_info = f"TAPTA with {state_count} states"
                    except:
                        state_info = "TAPTA automaton"
                    
                    plt.text(0.5, 0.5, f"{state_info}\n(Unicode visualization failed)", 
                            ha='center', va='center', fontsize=14)
                    plt.title(f"Original TAPTA")
                    plt.axis('off')
                    plt.savefig(f"{tapta_filename}.png", dpi=300, bbox_inches='tight')
                    plt.close()
                    
                    # Still try to generate DOT file even if visualization failed
                    try:
                        tapta_dot_content = generate_tapta_dot_content(tapta, positive_samples, negative_samples)
                        tapta_dot_filename = f"{tapta_filename}.dot"
                        with open(tapta_dot_filename, 'w', encoding='utf-8') as f:
                            f.write(tapta_dot_content)
                    except Exception:
                        pass  # Silently ignore errors
                        
                except Exception:
                    pass  # Silently ignore errors
                    
        except Exception:
            pass  # Silently ignore errors
    
    # Print TDRTA information
    #print("\nCreated TDRTA information:")
    #print(f"Number of nodes: {len(drta.nodes)}")
    #print(f"Accepting states: {drta.accepting}")
    #print(f"Rejecting states: {drta.rejecting}")
    #print(f"Alphabet: {drta.alphabet}")
    
    # Print edge information
    #print("\nEdge information:")
    for (source, target, key), (symbol_id, region_str) in drta.edge_labels.items():
        symbol = [k for k, v in drta.alphabet.items() if v == symbol_id][0]
        #print(f"Edge ({source} -> {target}): symbol={symbol}, region={region_str}")
    
    return drta

def test_encoding(drta, positive_samples, negative_samples, save_files=False, output_dir=None):
    """
    Test SMT encoding of TDRTA
    
    Args:
    drta: TDRTA instance to encode
    positive_samples: List of positive samples
    negative_samples: List of negative samples
    save_files: Whether to save visualization files
    output_dir: Output directory for saving files (if None, uses default)
    """
    #print("\nStarting Encoding functionality test...")
    
    # Time statistics variables
    total_solver_time = 0
    successful_sizes = None
    
    # Iterative search starting from minimum state count
    sizes = 2
    max_sizes = 100  # Set maximum state count limit to avoid infinite loop
    
    while sizes <= max_sizes:
        #print(f"\nTrying to solve with {sizes} states...")
        
        # Create encoder instance (allow debug output)
        encoding = Encoding(drta, sizes, positive_samples=positive_samples)
        
        # Record solver start time
        solver_start_time = time.time()
        
        # Generate and solve constraints (allow debug output)
        result, model = encoding.generate_clauses()
        
        # Output constraint count information (minimal)
        #print(f"Hard constraint count: {len(encoding.hard_constraints)}")
        #print(f"Soft constraint count: {len(encoding.soft_constraints)}")
        #print(f"Total constraint count: {len(encoding.hard_constraints) + len(encoding.soft_constraints)}")
        #print(f"Total variable count: {len(encoding.variables)}")
        
        # Record solver end time
        solver_end_time = time.time()
        solver_duration = solver_end_time - solver_start_time
        total_solver_time += solver_duration
        
        #print(f"Solving time: {solver_duration:.3f} seconds")
        
        # Analyze results
        if result == z3.sat:
            #print(f"\n=== Solving successful! Found solution with {sizes} states:")
            successful_sizes = sizes
            
            # Output complete model (only True values) - disabled
            #print("\n=== Complete SMT Model (True values only) ===")
            #print(f"Total variable count: {len(encoding.variables)}")
            
            # Count True values
            true_count = 0
            for var_name, var in encoding.variables.items():
                if model[var] is not None and z3.is_true(model[var]):
                    true_count += 1
            
            #print(f"True variable count: {true_count}")
            #print("\nTrue variable assignments:")
            #for var_name, var in sorted(encoding.variables.items()):
            #    if model[var] is not None and z3.is_true(model[var]):
            #        print(f"  {var_name} = True")
            
            # Output all variable values
            #print("\n=== All variable values ===")
            #print(f"Total variable count: {len(encoding.variables)}")
            
            # Group output by variable type
            variable_groups = {
                'node_color': [],      # Node color variables
                'accepting': [],       # Accepting state variables
                'trans': [],          # Transition variables
                'trace': [],          # Trace variables
                'other': []           # Other variables
            }
            
            # Classify all variables
            for var_name, var in encoding.variables.items():
                var_value = model[var] if model[var] is not None else "undefined"
                var_info = f"{var_name} = {var_value}"
                
                if var_name.startswith("node_") and "_color_" in var_name:
                    variable_groups['node_color'].append(var_info)
                elif var_name.startswith("accepting_"):
                    variable_groups['accepting'].append(var_info)
                elif var_name.startswith("trans_"):
                    variable_groups['trans'].append(var_info)
                elif var_name.startswith("trace_") or var_name.startswith("x_") or var_name.startswith("z_"):
                    variable_groups['trace'].append(var_info)
                else:
                    variable_groups['other'].append(var_info)
            
            #print("\n3. Transition relation variables:")
            true_transitions = []
            false_transitions = []
            for var_info in sorted(variable_groups['trans']):
                if "= True" in var_info:
                    true_transitions.append(var_info)
                else:
                    false_transitions.append(var_info)
            
            # Debug: Specifically output trans_0_[5, ∞) transitions from state 0 - disabled
            #print("\nDebug: trans_1 transitions from state 0:")
            #for var_info in sorted(variable_groups['trans']):
            #    if "trans_5_" in var_info:
            #        print(f"     {var_info}")
            
            #print("\n4. Trace-related variables:")
            true_traces = []
            false_traces = []
            for var_info in sorted(variable_groups['trace']):
                if "= True" in var_info:
                    true_traces.append(var_info)
                else:
                    false_traces.append(var_info)
            
            #print(f"   Active trace variables ({len(true_traces)} count):")
            #for var_info in true_traces:
            #    print(f"     {var_info}")
            
            #print(f"   Inactive trace variables ({len(false_traces)} count):")
            #for var_info in false_traces[:10]:  # Only show first 10
            #    print(f"     {var_info}")
            #if len(false_traces) > 10:
            #    print(f"     ... {len(false_traces) - 10} more inactive trace variables")
            
            # Statistics summary - disabled
            #print(f"\n=== Variable statistics summary ===")
            #print(f"Transition relation variables: {len(variable_groups['trans'])} (active: {len(true_transitions)}, inactive: {len(false_transitions)})")
            #print(f"Trace-related variables: {len(variable_groups['trace'])} (active: {len(true_traces)}, inactive: {len(false_traces)})")
            
            # Analyze node color assignments
            for node_id in drta.nodes:
                assigned_colors = []
                for color in range(sizes):
                    var_name = f"node_{node_id}_color_{color}"
                    if var_name in encoding.variables:
                        var = encoding.variables[var_name]
                        if z3.is_true(model[var]):
                            assigned_colors.append(color)
            
            # Analyze color accepting states and collect accepting colors
            accepting_colors = []
            for color in range(sizes):
                var_name = f"accepting_{color}"
                if var_name in encoding.variables:
                    var = encoding.variables[var_name]
                    is_accepting = z3.is_true(model[var])
                    if is_accepting:
                        accepting_colors.append(color)
            
            # Collect transition relations
            transitions = []
            for var_name, var in encoding.variables.items():
                if var_name.startswith("trans_") and z3.is_true(model[var]):
                    transitions.append(var_name)
            
            # Output all edges before optimization - disabled
            #print("\n=== All Edges Before Optimization ===")
            edge_count_raw = 0
            raw_transitions_by_source = {}
            
            # Parse original transition relations
            for trans in transitions:
                parts = trans.split('_')
                if len(parts) >= 5:
                    symbol_id = parts[1]
                    # Region may contain underscores, need special handling
                    region_str = '_'.join(parts[2:-2])
                    color_from = int(parts[-2])
                    color_to = int(parts[-1])
                    
                    # Convert symbol ID to symbol name
                    symbol_name = symbol_id
                    if drta.alphabet is not None:
                        for sym, sym_id in drta.alphabet.items():
                            if str(sym_id) == str(symbol_id):
                                symbol_name = sym
                                break
                    
                    # Group by source state
                    if color_from not in raw_transitions_by_source:
                        raw_transitions_by_source[color_from] = []
                    
                    raw_transitions_by_source[color_from].append({
                        'symbol': symbol_name,
                        'region_str': region_str,
                        'color_to': color_to,
                        'trans': trans
                    })
            
            # Output original transition relations - disabled
            #for source_state in sorted(raw_transitions_by_source.keys()):
            #    print(f"\nFrom state q{source_state}:")
            #    
            #    for trans_info in raw_transitions_by_source[source_state]:
            #        edge_count_raw += 1
            #        print(f"  Edge {edge_count_raw}: q{source_state} --{trans_info['symbol']}/{trans_info['region_str']}--> q{trans_info['color_to']}")
            
            #print(f"\nTotal edges before optimization: {edge_count_raw}")
            #print("-" * 80)
            
            # Visualize raw transition relations before optimization (only if requested)
            if save_files and output_dir:
                raw_output_file = os.path.join(output_dir, "tdrta_raw_visualization")
                visualize_raw_transitions(transitions, accepting_colors, drta.alphabet, raw_output_file, save_files=save_files)
            
            # Optimize transition relations
            optimized_transitions = optimize_transitions_new(transitions)
            
            # Visualize optimized transition relations (only if requested)
            if save_files and output_dir:
                optimized_output_file = os.path.join(output_dir, "tdrta_optimized_visualization")
                visualize_transitions_with_graphviz(optimized_transitions, accepting_colors, optimized_output_file, drta.alphabet, save_files=save_files)
            
            # Verify generated DRTA (only output if errors)
            verify_drta_correctness(optimized_transitions, accepting_colors, positive_samples, negative_samples, drta.alphabet)
            break # Exit loop after finding solution
        else:
            #print(f"\nSolving failed, cannot find solution satisfying constraints: {result}")
            sizes += 1 # Increase state count and continue trying
    else:
        #print(f"\nTried maximum state count {max_sizes} times, still no solution found.")
        pass
    
    # Return time statistics
    return {
        'total_solver_time': total_solver_time,
        'successful_sizes': successful_sizes,
        'max_sizes_tried': min(sizes, max_sizes)
    }


def verify_drta_correctness(optimized_transitions, accepting_colors, positive_samples, negative_samples, alphabet):
    """
    Verify correctness of generated DRTA for all samples
    
    Args:
    optimized_transitions: Optimized transition relations
    accepting_colors: List of accepting colors
    positive_samples: List of positive samples
    negative_samples: List of negative samples
    alphabet: Alphabet mapping
    
    Returns:
    Verification result statistics
    """
    #print("Starting DRTA correctness verification...")
    
    # Statistics for verification results
    positive_correct = 0
    negative_correct = 0
    positive_total = len(positive_samples)
    negative_total = len(negative_samples)
    
    # Verify positive samples
    #print("\nVerifying positive samples:")
    for i, sample in enumerate(positive_samples):
        result = simulate_drta_execution(sample, optimized_transitions, accepting_colors, alphabet)
        if result['accepted']:
            positive_correct += 1
            #print(f"  Sample {i+1}: {sample} -> accepted OK (path: {result['path']})")
        else:
            print(f"  Sample {i+1}: {sample} -> rejected X (path: {result['path']}, reason: {result['reason']})")
    
    # Verify negative samples
    #print("\nVerifying negative samples:")
    for i, sample in enumerate(negative_samples):
        result = simulate_drta_execution(sample, optimized_transitions, accepting_colors, alphabet)
        if not result['accepted']:
            negative_correct += 1
            #print(f"  Sample {i+1}: {sample} -> rejected OK (path: {result['path']})")
        else:
            print(f"  Sample {i+1}: {sample} -> accepted X (path: {result['path']}, error: should be rejected)")
    
    # Output verification statistics - minimal output
    total_correct = positive_correct + negative_correct
    total_samples = positive_total + negative_total
    
    # Only print if there are errors
    if total_correct != total_samples:
        print("\n=== Verification result statistics ===")
        if positive_total > 0:
            print(f"Positive samples: {positive_correct}/{positive_total} correct ({100*positive_correct/positive_total:.1f}%)")
        if negative_total > 0:
            print(f"Negative samples: {negative_correct}/{negative_total} correct ({100*negative_correct/negative_total:.1f}%)")
        if total_samples > 0:
            print(f"Overall: {total_correct}/{total_samples} correct ({100*total_correct/total_samples:.1f}%)")
        print("=== Some samples failed verification, generated DRTA needs improvement.")
    
    return {
        'positive_correct': positive_correct,
        'positive_total': positive_total,
        'negative_correct': negative_correct,
        'negative_total': negative_total,
        'total_correct': total_correct,
        'total_samples': total_samples,
        'accuracy': total_correct / total_samples if total_samples > 0 else 0
    }

def simulate_drta_execution(sample, optimized_transitions, accepting_colors, alphabet):
    """
    Simulate DRTA execution of a sample trace
    
    Args:
    sample: Sample trace, format: [('symbol', timestamp), ...]
    optimized_transitions: Optimized transition relations
    accepting_colors: List of accepting colors
    alphabet: Alphabet mapping
    
    Returns:
    Execution result dictionary containing acceptance status, execution path, etc.
    """
    if not sample:
        # Empty sample at initial state 0, check if it's accepting
        return {
            'accepted': 0 in accepting_colors,
            'path': [0],
            'reason': 'empty sample' if 0 not in accepting_colors else 'empty sample in accepting state'
        }
    
    # Start from initial state 0
    current_state = 0
    path = [current_state]
    
    # Create reverse mapping from symbol to ID
    symbol_to_id = {}
    for sym, sym_id in alphabet.items():
        symbol_to_id[sym] = str(sym_id)
    
    # Process each event in sample sequentially
    for event_idx, (symbol, timestamp) in enumerate(sample):
        # Get symbol ID
        if symbol not in symbol_to_id:
            return {
                'accepted': False,
                'path': path,
                'reason': f'unknown symbol {symbol} in event {event_idx+1}'
            }
        
        symbol_id = symbol_to_id[symbol]
        
        # Find possible transitions from current state through this symbol
        possible_transitions = []
        
        for (state_from, sym), target_regions in optimized_transitions.items():
            if state_from == current_state and sym == symbol_id:
                for target_state, regions in target_regions.items():
                    for region in regions:
                        if is_timestamp_in_region(timestamp, region):
                            possible_transitions.append(target_state)
        
        # Check if there are valid transitions
        if not possible_transitions:
            return {
                'accepted': False,
                'path': path,
                'reason': f'no transition from state {current_state} through symbol {symbol}(time={timestamp})'
            }
        
        # If multiple possible transitions, choose first (should be only one in deterministic automaton)
        if len(possible_transitions) > 1:
            # This shouldn't happen in a correct deterministic automaton
            return {
                'accepted': False,
                'path': path,
                'reason': f'multiple possible transitions from state {current_state} through symbol {symbol}(time={timestamp}): {possible_transitions}'
            }
        
        # Execute transition
        current_state = possible_transitions[0]
        path.append(current_state)
    
    # Check if final state is accepting
    is_accepted = current_state in accepting_colors
    
    return {
        'accepted': is_accepted,
        'path': path,
        'reason': 'reached accepting state' if is_accepted else 'reached rejecting state'
    }

def is_timestamp_in_region(timestamp, region):
    """
    Check if timestamp is within specified region
    
    Args:
    timestamp: Timestamp (float)
    region: Region tuple (lower, upper, lower_closed, upper_closed)
    
    Returns:
    bool: True if timestamp is in region, False otherwise
    """
    lower, upper, lower_closed, upper_closed = region
    
    # Check lower bound
    if lower_closed:
        if timestamp < lower:
            return False
    else:
        if timestamp <= lower:
            return False
    
    # Check upper bound
    if upper_closed:
        if timestamp > upper:
            return False
    else:
        if timestamp >= upper:
            return False
    
    return True

def optimize_transitions_new(transitions):
    """
    Optimize transition relations: merge transitions with same source, symbol and target, 
    ensure different target regions don't intersect and cover entire positive real axis
    
    Args:
    transitions: List of transition variable names
    """
    #print("\nOptimizing transition relations:")
    
    # Parse transition variables
    parsed_transitions = []
    for trans in transitions:
        parts = trans.split('_')
        if len(parts) >= 5:
            symbol = parts[1]
            # Region may contain underscores, need special handling
            region_str = '_'.join(parts[2:-2])
            color_from = int(parts[-2])
            color_to = int(parts[-1])
            
            # Parse region
            region = parse_region(region_str)
            if region:
                parsed_transitions.append({
                    'symbol': symbol,
                    'region': region[0],  # Take first tuple since parse_region returns list
                    'region_str': region_str,
                    'color_from': color_from,
                    'color_to': color_to,
                    'orig_trans': trans
                })
    
    # Group by (color_from, symbol)
    transitions_by_source = {}
    for trans in parsed_transitions:
        key = (trans['color_from'], trans['symbol'])
        if key not in transitions_by_source:
            transitions_by_source[key] = []
        transitions_by_source[key].append(trans)
    
    # Store all optimized transition relations
    all_optimized_transitions = {}
    
    # Process each group
    for (color_from, symbol), trans_group in transitions_by_source.items():
        #print(f"\nTransitions from color{color_from} through symbol{symbol}:")
        
        # Print original transitions
        # for trans in trans_group:
            #print(f"  Original: {trans['orig_trans']}: region = {trans['region_str']}")
        
        # Group by target color
        by_target = {}
        for trans in trans_group:
            color_to = trans['color_to']
            if color_to not in by_target:
                by_target[color_to] = []
            by_target[color_to].append(trans)
        
        # Rule 1 and Rule 2: Handle maximum region and single transition cases
        if len(by_target) == 1:
            # Only one target color, extend directly to [0, ∞) (unless 0 is protected)
            color_to = list(by_target.keys())[0]
            
            # Check if 0 is a protected point for this color_from, symbol combination
            protected_points = {}
            for trans in parsed_transitions:
                if (trans['color_from'], trans['symbol']) == (color_from, symbol):
                    region = trans['region']
                    lower, upper, lower_closed, upper_closed = region
                    if lower == upper and lower_closed and upper_closed and lower == 0:
                        # This is an exact point interval at 0
                        protected_points[0] = trans['color_to']
            
            # Determine if 0 should be closed (protected by this color or no protection)
            zero_closed = (0 not in protected_points) or (protected_points.get(0) == color_to)
            
            # Create region extended to [0, ∞) or (0, ∞)
            extended_region = (0, float('inf'), zero_closed, False)
            bracket_type = "[0, ∞)" if zero_closed else "(0, ∞)"
            #print(f"  Rule 2: Single target color, extend region to {bracket_type}: {format_region(extended_region)}")
            
            # Save result
            optimized_regions = {color_to: [extended_region]}
        else:
            # Rule 3: Use solver to find optimal merging scheme
            #print("  Rule 3: Use solver to find optimal merging scheme")
            
            # First sort regions for each target color
            for color_to in by_target:
                by_target[color_to] = sorted([t['region'] for t in by_target[color_to]], 
                                            key=lambda r: (r[0], 0 if r[2] else 1))
            
            # Use solver to find optimal region division
            optimized_regions = optimize_regions_with_solver(by_target)
            
            # Output optimization results
            # for color_to, regions in optimized_regions.items():
                #print(f"  Target color {color_to} optimized regions: {format_regions(regions)}")
        
        # Check if requirements are met: regions don't intersect and cover entire positive real axis
        all_regions = []
        for regions in optimized_regions.values():
            all_regions.extend(regions)
        
        # Check if regions intersect
        has_overlap = False
        for i in range(len(all_regions)):
            for j in range(i+1, len(all_regions)):
                overlap = get_region_overlap(all_regions[i], all_regions[j])
                if overlap:
                    has_overlap = True
                    #print(f"  Warning: regions {format_region(all_regions[i])} and {format_region(all_regions[j])} intersect: {format_region(overlap)}")
        
        # if not has_overlap:
            #print("  Different regions don't intersect, satisfying determinism requirement")
        
        # Check if there are gaps between regions
        all_regions.sort(key=lambda r: (r[0], 0 if r[2] else 1))
        gaps = find_gaps(all_regions)
        
        # Filter out empty gaps
        valid_gaps = [gap for gap in gaps if not (gap[0] == gap[1] and (not gap[2] or not gap[3]))]
        
        # Collect protected point information
        protected_points = {}
        for trans in parsed_transitions:
            if (trans['color_from'], trans['symbol']) == (color_from, symbol):
                region = trans['region']
                lower, upper, lower_closed, upper_closed = region
                if lower == upper and lower_closed and upper_closed:
                    # This is an exact point interval
                    point_value = lower
                    target_color = trans['color_to']
                    protected_points[point_value] = target_color
        
        if valid_gaps:
            #print("  Union of regions doesn't cover entire positive real axis, following gaps exist:")
            # for gap in valid_gaps:
                #print(f"    {format_region(gap)}")
            
            # New: Fill detected gaps but protect exact points
            #print(f"  Filling {len(valid_gaps)} gaps to cover entire positive real axis...")
            fill_gaps_in_regions_protected(optimized_regions, valid_gaps, protected_points)
            
            # Check again if gaps have been filled
            all_regions = []
            for regions in optimized_regions.values():
                all_regions.extend(regions)
            all_regions.sort(key=lambda r: (r[0], 0 if r[2] else 1))
            remaining_gaps = find_gaps(all_regions)
            
            # Filter out empty gaps
            valid_remaining_gaps = [gap for gap in remaining_gaps if not (gap[0] == gap[1] and (not gap[2] or not gap[3]))]
            
            # if valid_remaining_gaps:
            #     #print("  Warning: uncovered regions still exist after gap filling:")
            #     for gap in valid_remaining_gaps:
            #         #print(f"    {format_region(gap)}")
        #     else:
        #         print("  Gaps successfully filled, union of regions covers entire positive real axis")
        # else:
        #     print("  Union of regions covers entire positive real axis, satisfying completeness requirement")
        
        # Store optimized transition relations
        key = (color_from, symbol)
        all_optimized_transitions[key] = optimized_regions
    
    return all_optimized_transitions

def fill_gaps_in_regions_protected(optimized_regions, gaps, protected_points):
    """
    Fill gaps in regions to ensure coverage of entire positive real axis, but protect exact point intervals
    
    Args:
    optimized_regions: Region dictionary grouped by target color
    gaps: List of gaps to fill
    protected_points: Protected exact point dictionary {point_value: target_color}
    """
    if not gaps:
        return  # No gaps to fill
    
    if not optimized_regions:
        return  # No regions to fill with
    
    # Target color list sorted by region count (fallback)
    target_colors = sorted(optimized_regions.keys(), key=lambda c: len(optimized_regions[c]))
    
    # Find most suitable target color for each gap
    for gap in gaps:
        gap_lower, gap_upper = gap[0], gap[1]
        gap_lower_closed, gap_upper_closed = gap[2], gap[3]
        
        # Skip only truly empty gaps (point gaps that are not closed intervals)
        if gap_lower == gap_upper and not (gap_lower_closed and gap_upper_closed):
            continue
        
        # Check if gap contains protected points
        conflicts = []
        for point_value, point_color in protected_points.items():
            # Check if point is within gap
            point_in_gap = False
            if gap_lower < point_value < gap_upper:
                point_in_gap = True
            elif gap_lower == point_value and gap_lower_closed:
                point_in_gap = True
            elif gap_upper == point_value and gap_upper_closed:
                point_in_gap = True
            
            if point_in_gap:
                conflicts.append(point_value)
        
        if conflicts:
            # Conflicts exist, need to split gap to avoid protected points
            sub_gaps = split_region_around_points(gap, conflicts)
            # Recursively handle each sub-gap
            fill_gaps_in_regions_protected(optimized_regions, sub_gaps, protected_points)
            continue
        
        # No conflicts, handle gap normally
        # Special handling for gaps starting from 0: prefer closed interval [0,...)
        if gap_lower == 0 and not gap_lower_closed:
            gap_lower_closed = True
            gap = (gap_lower, gap_upper, gap_lower_closed, gap_upper_closed)
        
        # Store best match information for each color
        color_matches = {}
        
        # Find regions adjacent to gap boundaries
        for color, regions in optimized_regions.items():
            for region in regions:
                region_lower, region_upper = region[0], region[1]
                region_lower_closed, region_upper_closed = region[2], region[3]
                
                # Check lower boundary adjacency
                lower_match = False
                if region_upper == gap_lower:
                    # Region upper boundary same as gap lower boundary, check if boundary point can connect
                    if region_upper_closed or gap_lower_closed:
                        lower_match = True
                
                # Check upper boundary adjacency
                upper_match = False
                if region_lower == gap_upper:
                    # Region lower boundary same as gap upper boundary, check if boundary point can connect
                    if region_lower_closed or gap_upper_closed:
                        upper_match = True
                
                # Calculate match score
                match_score = 0
                if lower_match:
                    match_score += 2  # Lower boundary match has higher weight
                if upper_match:
                    match_score += 1
                
                # If current region is adjacent to gap boundary, record highest score
                if match_score > 0:
                    if color not in color_matches or match_score > color_matches[color]:
                        color_matches[color] = match_score
        
        # Choose best matching color
        best_color = None
        best_score = -1
        
        for color, score in color_matches.items():
            if score > best_score:
                best_score = score
                best_color = color
            # If scores are equal, choose color with fewer regions
            elif score == best_score and len(optimized_regions[color]) < len(optimized_regions[best_color]):
                best_color = color
        
        # If no adjacent region found, fallback to calculating closest region distance
        if best_color is None:
            min_distance = float('inf')
            
            for color, regions in optimized_regions.items():
                for region in regions:
                    region_lower, region_upper = region[0], region[1]
                    
                    # Calculate distance between region and gap
                    if gap_upper <= region_lower:
                        # Gap is to the left of region
                        distance = region_lower - gap_upper
                    elif gap_lower >= region_upper:
                        # Gap is to the right of region
                        distance = gap_lower - region_upper
                    else:
                        # Gap intersects with region (shouldn't happen theoretically)
                        distance = 0
                    
                    if distance < min_distance:
                        min_distance = distance
                        best_color = color
            
            # If still no suitable color found, use color with fewest regions
            if best_color is None:
                best_color = target_colors[0]
        
        # Add gap to selected target color
        #print(f"    Assigning gap {format_region(gap)} to target color {best_color}")
        optimized_regions[best_color].append(gap)
        
        # Re-sort regions for this color
        optimized_regions[best_color] = sorted(optimized_regions[best_color], 
                                              key=lambda r: (r[0], 0 if r[2] else 1))
        
        # Try to merge adjacent regions, but protect exact points
        merge_adjacent_regions_protected(optimized_regions[best_color], protected_points, best_color)

def merge_adjacent_regions_protected(regions, protected_points, target_color):
    """
    Merge adjacent regions in region list, but protect exact point intervals
    
    Args:
    regions: List of regions to merge, sorted by lower bound
    protected_points: Protected exact point dictionary {point_value: target_color}
    target_color: Current target color
    """
    if len(regions) <= 1:
        return
    
    i = 0
    while i < len(regions) - 1:
        r1 = regions[i]
        r2 = regions[i + 1]
        
        # Deconstruct region information
        lower1, upper1, lower1_closed, upper1_closed = r1
        lower2, upper2, lower2_closed, upper2_closed = r2
        
        # Check if merged region would contain protected points (belonging to other target colors)
        can_merge = True
        
        # Check if protected points would be incorrectly included
        for point_value, point_color in protected_points.items():
            if point_color != target_color:
                # This point should belong to other color, check if merge would include it
                merged_lower = min(lower1, lower2)
                merged_upper = max(upper1, upper2)
                merged_lower_closed = lower1_closed if merged_lower == lower1 else lower2_closed
                merged_upper_closed = upper1_closed if merged_upper == upper1 else upper2_closed
                
                # Check if point is in merged interval
                point_in_merged = False
                if merged_lower < point_value < merged_upper:
                    point_in_merged = True
                elif merged_lower == point_value and merged_lower_closed:
                    point_in_merged = True
                elif merged_upper == point_value and merged_upper_closed:
                    point_in_merged = True
                
                # But point is not in either of the original two intervals
                point_in_r1 = ((lower1 < point_value < upper1) or 
                              (lower1 == point_value and lower1_closed) or 
                              (upper1 == point_value and upper1_closed))
                point_in_r2 = ((lower2 < point_value < upper2) or 
                              (lower2 == point_value and lower2_closed) or 
                              (upper2 == point_value and upper2_closed))
                
                if point_in_merged and not point_in_r1 and not point_in_r2:
                    # Merge would incorrectly include protected point
                    can_merge = False
                    break
        
        # If protection check passes, perform regular merge check
        if can_merge:
            # Check if two regions can be merged
            # Case 1: Overlap exists
            if lower2 < upper1:
                can_merge = True
            # Case 2: Boundary points are same and at least one is closed
            elif lower2 == upper1 and (upper1_closed or lower2_closed):
                can_merge = True
            # Case 3: Although no overlap, distance is minimal (numerical error)
            elif abs(lower2 - upper1) < 1e-10:
                can_merge = True
            else:
                can_merge = False
        
        if can_merge:
            # Merge regions
            new_lower = min(lower1, lower2)
            new_upper = max(upper1, upper2)
            
            # Determine closure of new region boundaries
            new_lower_closed = lower1_closed if new_lower == lower1 else lower2_closed
            new_upper_closed = upper1_closed if new_upper == upper1 else upper2_closed
            
            # If lower bounds of two regions are same, merged lower bound is closed if either is closed
            if lower1 == lower2:
                new_lower_closed = lower1_closed or lower2_closed
            
            # If upper bounds of two regions are same, merged upper bound is closed if either is closed
            if upper1 == upper2:
                new_upper_closed = upper1_closed or upper2_closed
            
            # Replace original two regions with merged region
            merged = (new_lower, new_upper, new_lower_closed, new_upper_closed)
            regions[i] = merged
            regions.pop(i + 1)
        else:
            i += 1

def optimize_regions_with_solver(by_target):
    """
    Use Z3 solver to find optimal merging scheme with minimum number of regions
    
    Args:
    by_target: Region dictionary grouped by target color
    
    Returns:
    Optimized region dictionary
    """
    # Create copy to avoid modifying original data
    optimized = {}
    
    # First check if there are exact point intervals, handle these specially
    point_intervals = {}  # {point_value: [target_colors]}
    
    for color_to, regions in by_target.items():
        for region in regions:
            lower, upper, lower_closed, upper_closed = region
            # Check if it's exact point interval
            if lower == upper and lower_closed and upper_closed:
                point_value = lower
                if point_value not in point_intervals:
                    point_intervals[point_value] = []
                point_intervals[point_value].append(color_to)
    
    # For exact point intervals, ensure determinism: each point can only correspond to one target color
    protected_points = {}  # {point_value: target_color}
    for point_value, target_colors in point_intervals.items():
        if len(target_colors) > 1:
            # Multiple target colors have same point, choose first (maintain determinism)
            chosen_color = min(target_colors)  # Choose smallest color ID
            protected_points[point_value] = chosen_color
            #print(f"Warning: Point {point_value} has multiple target colors {target_colors}, choosing color {chosen_color}")
        else:
            protected_points[point_value] = target_colors[0]
    
    # Process regions for each target color
    for color_to, regions in by_target.items():
        processed_regions = []
        
        for region in regions:
            lower, upper, lower_closed, upper_closed = region
            
            # Check if it's protected exact point interval
            if lower == upper and lower_closed and upper_closed:
                point_value = lower
                if protected_points.get(point_value) == color_to:
                    # This is protected point interval, keep unchanged
                    processed_regions.append(region)
                # Otherwise ignore this interval (occupied by other color)
            else:
                # Non-point interval, need to check for conflicts with protected points
                conflicts = []
                for point_value, point_color in protected_points.items():
                    if point_color != color_to:
                        # Check if interval contains this protected point
                        point_in_interval = False
                        if lower < point_value < upper:
                            point_in_interval = True
                        elif lower == point_value and lower_closed:
                            point_in_interval = True
                        elif upper == point_value and upper_closed:
                            point_in_interval = True
                        
                        if point_in_interval:
                            conflicts.append(point_value)
                
                if not conflicts:
                    # No conflicts, keep original interval
                    processed_regions.append(region)
                else:
                    # Conflicts exist, need to split interval to avoid protected points
                    split_regions = split_region_around_points(region, conflicts)
                    processed_regions.extend(split_regions)
        
        optimized[color_to] = processed_regions
    
    # Perform merge optimization for each color's regions, but protect exact points
    for color_to in optimized:
        if len(optimized[color_to]) > 1:
            # Sort by lower bound
            optimized[color_to].sort(key=lambda r: (r[0], 0 if r[2] else 1))
            # Use protected merge function
            merge_adjacent_regions_protected(optimized[color_to], protected_points, color_to)
    
    return optimized

def split_region_around_points(region, conflict_points):
    """
    Split interval around conflict points to avoid these points
    
    Args:
    region: Interval to split (lower, upper, lower_closed, upper_closed)
    conflict_points: List of points to avoid
    
    Returns:
    List of split intervals
    """
    lower, upper, lower_closed, upper_closed = region
    
    if not conflict_points:
        return [region]
    
    # Only handle conflict points within interval
    internal_points = []
    for point in conflict_points:
        if lower < point < upper:
            internal_points.append(point)
        elif point == lower and lower_closed:
            # Point on left boundary, need to exclude
            lower_closed = False
        elif point == upper and upper_closed:
            # Point on right boundary, need to exclude
            upper_closed = False
    
    if not internal_points:
        # Only boundary point conflicts, return adjusted interval
        if lower < upper or (lower == upper and lower_closed and upper_closed):
            return [(lower, upper, lower_closed, upper_closed)]
        else:
            return []  # Interval becomes empty set
    
    # Sort points by value
    internal_points.sort()
    
    # Split interval
    result = []
    current_lower = lower
    current_lower_closed = lower_closed
    
    for point in internal_points:
        # Add interval to the left of point
        if current_lower < point or (current_lower == point and current_lower_closed):
            result.append((current_lower, point, current_lower_closed, False))
        
        # Prepare to handle interval to the right of point
        current_lower = point
        current_lower_closed = False
    
    # Add last interval
    if current_lower < upper or (current_lower == upper and current_lower_closed and upper_closed):
        result.append((current_lower, upper, current_lower_closed, upper_closed))
    
    # Filter out empty intervals
    return [r for r in result if r[0] < r[1] or (r[0] == r[1] and r[2] and r[3])]

def parse_region(region_str):
    """
    Parse region string to tuple list
    
    Args:
    region_str: Region string like "[1, 2)", "(3, ∞)"
    
    Returns:
    Parsed region list, each element is (lower, upper, lower_closed, upper_closed)
    """
    # Remove spaces
    region_str = region_str.replace(" ", "")
    
    # Parse interval
    lower_closed = region_str.startswith("[")
    upper_closed = region_str.endswith("]")
    
    # Extract interval values
    inner_str = region_str[1:-1]  # Remove brackets from both ends
    parts = inner_str.split(",")
    if len(parts) != 2:
        return None
    
    try:
        lower = float(parts[0]) if parts[0] != "∞" and parts[0] != "inf" else float('-inf')
        upper = float(parts[1]) if parts[1] != "∞" and parts[1] != "inf" else float('inf')
        return [(lower, upper, lower_closed, upper_closed)]
    except ValueError:
        return None

def get_region_overlap(r1, r2):
    """
    Calculate intersection of two regions
    
    Args:
    r1, r2: Region tuples (lower, upper, lower_closed, upper_closed)
    
    Returns:
    Intersection region or None
    """
    # Calculate intersection lower and upper bounds
    lower = max(r1[0], r2[0])
    upper = min(r1[1], r2[1])
    
    # Determine if boundaries are closed
    lower_closed = (r1[2] if lower == r1[0] else False) and (r2[2] if lower == r2[0] else False)
    upper_closed = (r1[3] if upper == r1[1] else False) and (r2[3] if upper == r2[1] else False)
    
    # Check if interval is valid
    if lower < upper or (lower == upper and lower_closed and upper_closed):
        return (lower, upper, lower_closed, upper_closed)
    else:
        return None

def find_gaps(regions):
    """
    Find gaps in region list
    
    Args:
    regions: Sorted region list
    
    Returns:
    Gap region list
    """
    if not regions:
        return [(0, float('inf'), True, False)]  # Entire positive real axis
    
    gaps = []
    
    # Check if starting from 0
    if regions[0][0] > 0:
        gaps.append((0, regions[0][0], True, not regions[0][2]))
    elif regions[0][0] == 0 and not regions[0][2]:
        # First region starts at 0 but is open, no gap needed as we prefer [0,...)
        pass
    
    # Check gaps in between
    for i in range(len(regions) - 1):
        current_upper = regions[i][1]
        next_lower = regions[i+1][0]
        current_upper_closed = regions[i][3]
        next_lower_closed = regions[i+1][2]
        
        if current_upper < next_lower:
            # Clear gap between regions
            gaps.append((current_upper, next_lower, not current_upper_closed, not next_lower_closed))
        elif current_upper == next_lower and not (current_upper_closed and next_lower_closed):
            # Boundary point gap: point is not covered by either region
            if not current_upper_closed and not next_lower_closed:
                # Both regions exclude the boundary point, create a point gap [point, point]
                gaps.append((current_upper, current_upper, True, True))
            # If one region includes the point, no gap needed
    
    # Check if extending to infinity
    if regions[-1][1] != float('inf'):
        gaps.append((regions[-1][1], float('inf'), not regions[-1][3], False))
    
    return gaps

def format_regions(regions):
    """
    Format region list to readable string
    
    Args:
    regions: Region list
    
    Returns:
    Formatted string
    """
    if not regions:
        return "∅"
    
    return " ∪ ".join(format_region(r) for r in regions)

def format_region(region):
    """
    Format single region to readable string
    
    Args:
    region: Region tuple (lower, upper, lower_closed, upper_closed)
    
    Returns:
    Formatted string
    """
    lower, upper, lower_closed, upper_closed = region
    # Remove the forced open interval at 0, allow closed intervals when appropriate
    # Handle single point intervals
    if lower == upper:
        return f"[{lower}]" if lower_closed and upper_closed else "∅"
    
    # Construct interval string
    left_bracket = "[" if lower_closed else "("
    right_bracket = "]" if upper_closed else ")"
    
    lower_str = str(lower) if lower != float('-inf') else "-∞"
    upper_str = str(upper) if upper != float('inf') else "∞"
    
    return f"{left_bracket}{lower_str}, {upper_str}{right_bracket}"



def visualize_transitions_with_graphviz(optimized_transitions, accepting_colors, output_file="tdrta_visualization", alphabet=None, save_files=False):
    """
    Visualize optimized transition relations using Graphviz
    
    Args:
    optimized_transitions: Optimized transition relations dictionary, format: {(color_from, symbol): {color_to: [regions]}}
    accepting_colors: List of accepting colors
    output_file: Output filename (without extension)
    alphabet: Alphabet mapping for converting numbers to symbols
    save_files: Whether to save files (default: False)
    
    Returns:
    None, directly generates image file
    """
    if not save_files:
        return
    
    try:
        import graphviz
    except ImportError:
        return
    
    # Create directed graph
    dot = graphviz.Digraph(comment='Optimized TDRTA', format='png')
    dot.attr(rankdir='LR')  # Left to right layout
    
    # Collect all states (colors)
    all_states = set()
    for (color_from, _), target_dict in optimized_transitions.items():
        all_states.add(color_from)
        for color_to in target_dict.keys():
            all_states.add(color_to)
    
    # Add nodes
    for state in sorted(all_states):
        # Set node attributes
        node_attrs = {
            'shape': 'circle',
            'style': 'filled',
            'fillcolor': 'white',
            'fontname': 'SimHei'  # Use SimHei font for Chinese display
        }
        
        # Accepting states use double circle
        if state in accepting_colors:
            node_attrs['shape'] = 'doublecircle'
            node_attrs['fillcolor'] = 'lightgreen'
        
        dot.node(f'q{state}', f'q{state}', **node_attrs)
    
    # Add edges
    for (color_from, symbol), target_dict in sorted(optimized_transitions.items()):
        # Convert number to symbol (if alphabet is provided)
        symbol_str = symbol
        if alphabet is not None:
            # Reverse lookup alphabet to get symbol corresponding to symbol
            for sym, sym_id in alphabet.items():
                if str(sym_id) == str(symbol):
                    symbol_str = sym
                    break
        
        for color_to, regions in sorted(target_dict.items()):
            # Format regions
            region_strs = []
            for region in regions:
                region_str = format_region(region)
                region_strs.append(region_str)
            
            # Multiple regions connected with union symbol
            region_label = " ∪ ".join(region_strs)
            
            # Edge label
            edge_label = f"{symbol_str}/{region_label}"
            
            # Add edge
            dot.edge(f'q{color_from}', f'q{color_to}', label=edge_label, fontname='SimHei')
    
    # Render image (without viewing)
    try:
        dot.render(output_file, view=False)
    except Exception as e:
        # Try to save as DOT file
        try:
            dot.save(f"{output_file}.dot")
        except:
            pass  # Silently ignore errors

def visualize_raw_transitions(transitions, accepting_colors, alphabet, output_file="tdrta_raw_visualization", save_files=False):
    """
    Visualize raw transition relations before optimization using Graphviz
    
    Args:
    transitions: Transition relation list, each element is transition variable name (like "trans_0_[1, 2)_1_2")
    accepting_colors: List of accepting colors
    alphabet: Alphabet mapping for converting numbers to symbols
    output_file: Output filename (without extension)
    save_files: Whether to save files (default: False)
    
    Returns:
    None, directly generates image file
    """
    if not save_files:
        return
    
    try:
        import graphviz
    except ImportError:
        return
    
    # Create directed graph
    dot = graphviz.Digraph(comment='Raw TDRTA transition relations', format='png')
    dot.attr(rankdir='LR')  # Left to right layout
    
    # Parse transition relations
    parsed_transitions = []
    for trans in transitions:
        parts = trans.split('_')
        if len(parts) >= 5:
            symbol_id = parts[1]
            # Region may contain underscores, need special handling
            region_str = '_'.join(parts[2:-2])
            color_from = int(parts[-2])
            color_to = int(parts[-1])
            
            # Convert number to symbol (if possible)
            symbol_str = symbol_id
            for sym, sym_id in alphabet.items():
                if str(sym_id) == str(symbol_id):
                    symbol_str = sym
                    break
            
            parsed_transitions.append({
                'symbol': symbol_str,
                'region_str': region_str,
                'color_from': color_from,
                'color_to': color_to,
                'orig_trans': trans
            })
    
    # Collect all states (colors)
    all_states = set()
    for trans in parsed_transitions:
        all_states.add(trans['color_from'])
        all_states.add(trans['color_to'])
    
    # Add nodes
    for state in sorted(all_states):
        # Set node attributes
        node_attrs = {
            'shape': 'circle',
            'style': 'filled',
            'fillcolor': 'white',
            'fontname': 'SimHei'  # Use SimHei font for Chinese display
        }
        
        # Accepting states use double circle
        if state in accepting_colors:
            node_attrs['shape'] = 'doublecircle'
            node_attrs['fillcolor'] = 'lightgreen'
        
        dot.node(f'q{state}', f'q{state}', **node_attrs)
    
    # Add edges
    # Create dictionary for multiple transitions between same source and target
    edge_labels = {}
    for trans in parsed_transitions:
        key = (trans['color_from'], trans['color_to'])
        if key not in edge_labels:
            edge_labels[key] = []
        
        edge_label = f"{trans['symbol']}/{trans['region_str']}"
        edge_labels[key].append(edge_label)
    
    # Add edges, merge multiple labels for same source and target pair
    for (from_state, to_state), labels in edge_labels.items():
        combined_label = "\n".join(labels)
        dot.edge(f'q{from_state}', f'q{to_state}', label=combined_label, fontname='SimHei')
    
    # Render image (without viewing)
    try:
        dot.render(output_file, view=False)
    except Exception as e:
        # Try to save as DOT file
        try:
            dot.save(f"{output_file}.dot")
        except:
            pass  # Silently ignore errors

if __name__ == "__main__":
    # Process command line arguments
    if len(sys.argv) < 2:
        print("Usage: python test_encoding.py <traces_file> [--save-files]")
        print("Example: python test_encoding.py traces_output/traces_20.py")
        print("         python test_encoding.py traces_output/traces_20.py --save-files")
        sys.exit(1)
    
    traces_file = sys.argv[1]
    save_files = "--save-files" in sys.argv
    
    # Record program start time
    program_start_time = time.time()
    
    # Determine output directory based on input filename
    output_dir = None
    if save_files:
        # Get base filename without extension (e.g., "4_5_5-5" from "4_5_5-5.py")
        base_name = os.path.splitext(os.path.basename(traces_file))[0]
        # Create output directory in traces_output
        output_dir = os.path.join("traces_output", base_name)
        # Create directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
    # Output information
    print("=== TDRTA SMT Encoding Test Program ===")
    print(f"Program start time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(program_start_time))}")
    print(f"Input file: {traces_file}")
    
    # Load sample data
    print("\n1. Loading sample data...")
    try:
        positive_samples, negative_samples = load_samples_from_file(traces_file)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Create simple TDRTA
    print("\n2. Creating TDRTA...")
    drta_start_time = time.time()
    drta = create_simple_tdrta(positive_samples, negative_samples, save_files=save_files, output_dir=output_dir)
    drta_end_time = time.time()
    drta_creation_time = drta_end_time - drta_start_time
    print(f"TDRTA creation time: {drta_creation_time:.3f} seconds")
    
    # Test encoding functionality
    print("\n3. Starting SMT encoding and solving...")
    encoding_start_time = time.time()
    time_stats = test_encoding(drta, positive_samples, negative_samples, save_files=save_files, output_dir=output_dir)
    encoding_end_time = time.time()
    encoding_total_time = encoding_end_time - encoding_start_time
    
    # Record program end time
    program_end_time = time.time()
    program_total_time = program_end_time - program_start_time
    
    # Output time statistics
    print("\n" + "="*60)
    print("=== Time Statistics Report ===")
    print("="*60)
    print(f"Program start time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(program_start_time))}")
    print(f"Program end time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(program_end_time))}")
    print(f"Input file: {traces_file}")
    print(f"Sample statistics: {len(positive_samples)} positive, {len(negative_samples)} negative")
    print("-" * 60)
    print(f"Sample loading and TDRTA creation time: {drta_creation_time:.3f} seconds")
    print(f"SMT solver total time:                  {time_stats['total_solver_time']:.3f} seconds")
    print(f"Encoding and optimization total time:   {encoding_total_time:.3f} seconds")
    print(f"Program total runtime:                  {program_total_time:.3f} seconds")
    print("-" * 60)
    
    if time_stats['successful_sizes']:
        print(f"Successfully solved with state count:  {time_stats['successful_sizes']}")
    else:
        print(f"Tried state count range:               2 to {time_stats['max_sizes_tried']}")
        print("Solving status:                        No solution found satisfying constraints")
    
    print(f"Solver time percentage:                 {100 * time_stats['total_solver_time'] / program_total_time:.1f}%")
    print("="*60)
    print("Test completed!")
    