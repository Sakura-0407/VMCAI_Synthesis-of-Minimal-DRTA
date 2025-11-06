#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Min3RTA Debug Tool

Features:
1. Load sample files
2. Build Min3RTA
3. Visualize Min3RTA graph
4. Verify all samples can pass through Min3RTA
5. Output detailed debug information

Usage:
python debug_min3rta.py traces_output/5_2_6-100.py
"""

import sys
import os
import time
from typing import List, Tuple, Any
import traceback

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def load_samples_from_file(file_path: str) -> Tuple[List[List[Tuple[str, float]]], List[List[Tuple[str, float]]]]:
    """
    Load positive and negative samples from Python file
    
    Args:
        file_path: Path to sample file
        
    Returns:
        (positive_samples, negative_samples)
    """
    print(f"Loading samples from: {file_path}")
    
    # Create temporary namespace
    namespace = {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            exec(f.read(), namespace)
        
        positive_samples = namespace.get('positive_samples', [])
        negative_samples = namespace.get('negative_samples', [])
        
        print(f"Loaded {len(positive_samples)} positive samples and {len(negative_samples)} negative samples")
        
        return positive_samples, negative_samples
        
    except Exception as e:
        print(f"Error loading samples from {file_path}: {e}")
        traceback.print_exc()
        return [], []

def print_sample_summary(positive_samples: List, negative_samples: List):
    """Print sample summary information"""
    print("\n" + "="*60)
    print("SAMPLE SUMMARY")
    print("="*60)
    
    print(f"Positive samples: {len(positive_samples)}")
    print(f"Negative samples: {len(negative_samples)}")
    
    # Count symbols and time range
    all_symbols = set()
    all_times = []
    
    for sample in positive_samples + negative_samples:
        for symbol, time_val in sample:
            all_symbols.add(symbol)
            all_times.append(time_val)
    
    print(f"Symbols used: {sorted(all_symbols)}")
    if all_times:
        print(f"Time range: [{min(all_times):.1f}, {max(all_times):.1f}]")
    
    # Display first few samples
    print(f"\nFirst 3 positive samples:")
    for i, sample in enumerate(positive_samples[:3]):
        print(f"  {i+1}: {sample}")
    
    print(f"\nFirst 3 negative samples:")
    for i, sample in enumerate(negative_samples[:3]):
        print(f"  {i+1}: {sample}")

def build_min3rta(positive_samples: List, negative_samples: List):
    """Build Min3RTA"""
    print("\n" + "="*60)
    print("BUILDING Min3RTA")
    print("="*60)
    
    try:
        from Min3RTA import build_min_3rta
        
        print("Building Min3RTA from samples...")
        start_time = time.time()
        
        min_3rta, drta = build_min_3rta(positive_samples, negative_samples)
        
        build_time = time.time() - start_time
        print(f"Min3RTA built successfully in {build_time:.2f} seconds")
        
        # Print Min3RTA information
        print(f"\nMin3RTA Statistics:")
        print(f"  Nodes: {len(min_3rta.nodes)}")
        print(f"  Root node: {min_3rta.root}")
        
        # Count accepting and rejecting nodes
        accepting_nodes = []
        rejecting_nodes = []
        for node_id, node in min_3rta.nodes.items():
            if node.is_accepting:
                accepting_nodes.append(node_id)
            if node.is_rejecting:
                rejecting_nodes.append(node_id)
        
        print(f"  Accepting nodes: {accepting_nodes}")
        print(f"  Rejecting nodes: {rejecting_nodes}")
        
        # Count edge labels
        edge_count = 0
        for node in min_3rta.nodes.values():
            edge_count += len(node.transitions)
        print(f"  Total transitions: {edge_count}")
        
        return min_3rta, drta
        
    except Exception as e:
        print(f"Error building Min3RTA: {e}")
        traceback.print_exc()
        return None, None

def visualize_min3rta(min_3rta, output_prefix: str):
    """Visualize Min3RTA"""
    print("\n" + "="*60)
    print("VISUALIZING Min3RTA")
    print("="*60)
    
    try:
        # Generate timestamp
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{output_prefix}_min3rta_{timestamp}"
        
        print(f"Saving Min3RTA visualization to: {filename}")
        
        # Save PNG image
        min_3rta.visualize_as_graphviz(filename)
        print(f"Min3RTA PNG saved: {filename}.png")
        
        # Save DOT file
        try:
            dot_content = min_3rta.generate_dot_content()
            dot_filename = f"{filename}.dot"
            with open(dot_filename, 'w', encoding='utf-8') as f:
                f.write(dot_content)
            print(f"Min3RTA DOT saved: {dot_filename}")
        except Exception as e:
            print(f"Failed to save DOT file: {e}")
            
    except Exception as e:
        print(f"Error visualizing Min3RTA: {e}")
        traceback.print_exc()

def verify_samples_with_min3rta(min_3rta, positive_samples: List, negative_samples: List):
    """Verify if samples can pass through Min3RTA"""
    print("\n" + "="*60)
    print("VERIFYING SAMPLES WITH Min3RTA")
    print("="*60)
    
    def simulate_sample(min_3rta, sample: List[Tuple[str, float]]) -> Tuple[bool, List[int], str]:
        """
        Simulate sample in Min3RTA
        
        Returns:
            (is_accepted, path, error_message)
        """
        try:
            current_node_id = min_3rta.root
            path = [current_node_id]
            
            for symbol, time_val in sample:
                # Find transition
                current_node = min_3rta.nodes[current_node_id]
                
                # Determine time region - use same logic as Min3RTA construction
                is_integer = time_val == int(time_val)
                
                # Need to get maximum time value to determine if it's the maximum
                max_time = 0
                for sample_list in [positive_samples, negative_samples]:
                    for sample in sample_list:
                        for _, t in sample:
                            max_time = max(max_time, t)
                
                is_max_time = abs(time_val - max_time) < 0.001
                
                if is_integer:
                    if is_max_time:
                        # Maximum time: map to [int(time), ∞) interval
                        region_str = f"[{int(time_val)}, ∞)"
                    else:
                        # Integer time value: map to exact point interval [t,t]
                        region_str = f"[{int(time_val)}, {int(time_val)}]"
                elif is_max_time:
                    # Maximum time: map to (int(time), ∞) interval
                    region_str = f"({int(time_val)}, ∞)"
                else:
                    # Decimal time value: map to open interval (t,t+1)
                    lower_bound = int(time_val)
                    upper_bound = lower_bound + 1
                    region_str = f"({lower_bound}, {upper_bound})"
                
                # Find matching transition
                found_transition = False
                for (sym, region), target_node in current_node.transitions.items():
                    if sym == symbol and str(region) == region_str:
                        current_node_id = target_node.id
                        path.append(current_node_id)
                        found_transition = True
                        break
                
                if not found_transition:
                    return False, path, f"No transition found for symbol {symbol} at time {time_val} (region {region_str})"
            
            # Check final state
            final_node = min_3rta.nodes[current_node_id]
            is_accepted = final_node.is_accepting
            
            return is_accepted, path, ""
            
        except Exception as e:
            return False, path, f"Simulation error: {e}"
    
    # Verify positive samples
    print("Verifying positive samples:")
    positive_errors = []
    for i, sample in enumerate(positive_samples):
        is_accepted, path, error = simulate_sample(min_3rta, sample)
        if not is_accepted:
            positive_errors.append((i, sample, path, error))
            print(f"  Sample {i+1}: {sample} -> REJECTED X (path: {path}, error: {error})")
        else:
            print(f"  Sample {i+1}: {sample} -> ACCEPTED OK (path: {path})")
        
        # Output detailed path analysis for each sample
        print(f"    Path analysis: {' -> '.join([f'q{node_id}' for node_id in path])}")
        
        # Special output for Sample 25 detailed information
        if i == 24:  # Sample 25 (index 24)
            print(f"\n=== DETAILED ANALYSIS FOR SAMPLE 25 ===")
            print(f"Sample: {sample}")
            print(f"Path: {path}")
            print(f"Error: {error}")
            
            # Analyze each step
            current_node_id = min_3rta.root
            for step_idx, (symbol, time_val) in enumerate(sample):
                current_node = min_3rta.nodes[current_node_id]
                print(f"\nStep {step_idx + 1}: Processing ('{symbol}', {time_val})")
                print(f"  Current node: {current_node_id}")
                print(f"  Node transitions: {[(sym, str(region)) for (sym, region), _ in current_node.transitions.items()]}")
                
                # Determine time region
                is_integer = time_val == int(time_val)
                max_time = 0
                for sample_list in [positive_samples, negative_samples]:
                    for sample in sample_list:
                        for _, t in sample:
                            max_time = max(max_time, t)
                is_max_time = abs(time_val - max_time) < 0.001
                
                if is_integer:
                    if is_max_time:
                        region_str = f"[{int(time_val)}, ∞)"
                    else:
                        region_str = f"[{int(time_val)}, {int(time_val)}]"
                elif is_max_time:
                    region_str = f"({int(time_val)}, ∞)"
                else:
                    lower_bound = int(time_val)
                    upper_bound = lower_bound + 1
                    region_str = f"({lower_bound}, {upper_bound})"
                
                print(f"  Expected region: {region_str}")
                
                # Find matching transition
                found_transition = False
                for (sym, region), target_node in current_node.transitions.items():
                    if sym == symbol and str(region) == region_str:
                        print(f"  Found transition: {sym}/{region} -> node {target_node.id}")
                        current_node_id = target_node.id
                        found_transition = True
                        break
                
                if not found_transition:
                    print(f"  NO TRANSITION FOUND!")
                    print(f"  Available transitions for symbol '{symbol}':")
                    for (sym, region), target_node in current_node.transitions.items():
                        if sym == symbol:
                            print(f"    {sym}/{region} -> node {target_node.id}")
                    break
            print(f"=== END DETAILED ANALYSIS ===\n")
    
    # Verify negative samples
    print(f"\nVerifying negative samples:")
    negative_errors = []
    for i, sample in enumerate(negative_samples):
        is_accepted, path, error = simulate_sample(min_3rta, sample)
        if is_accepted:
            negative_errors.append((i, sample, path, error))
            print(f"  Sample {i+1}: {sample} -> ACCEPTED X (path: {path}, error: should be rejected)")
        else:
            print(f"  Sample {i+1}: {sample} -> REJECTED OK (path: {path})")
        
        # Output detailed path analysis for each sample
        print(f"    Path analysis: {' -> '.join([f'q{node_id}' for node_id in path])}")
    
    # Summary
    print(f"\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    print(f"Positive samples: {len(positive_samples)} total, {len(positive_samples) - len(positive_errors)} correct, {len(positive_errors)} errors")
    print(f"Negative samples: {len(negative_samples)} total, {len(negative_samples) - len(negative_errors)} correct, {len(negative_errors)} errors")
    
    if positive_errors:
        print(f"\nPositive sample errors:")
        for i, sample, path, error in positive_errors[:5]:  # Only show first 5 errors
            print(f"  Sample {i+1}: {sample} -> {error}")
        if len(positive_errors) > 5:
            print(f"  ... and {len(positive_errors) - 5} more errors")
    
    if negative_errors:
        print(f"\nNegative sample errors:")
        for i, sample, path, error in negative_errors[:5]:  # Only show first 5 errors
            print(f"  Sample {i+1}: {sample} -> {error}")
        if len(negative_errors) > 5:
            print(f"  ... and {len(negative_errors) - 5} more errors")
    
    return len(positive_errors) == 0 and len(negative_errors) == 0

def analyze_time_regions(min_3rta, positive_samples: List, negative_samples: List):
    """Analyze time regions"""
    print("\n" + "="*60)
    print("ANALYZING TIME REGIONS")
    print("="*60)
    
    # Collect all time values and their regions
    time_region_mapping = {}
    all_samples = positive_samples + negative_samples
    
    for sample in all_samples:
        for symbol, time_val in sample:
            # Determine region
            is_integer = time_val == int(time_val)
            if is_integer:
                region_str = f"[{int(time_val)}, {int(time_val)}]"
            else:
                lower_bound = int(time_val)
                upper_bound = lower_bound + 1
                region_str = f"({lower_bound}, {upper_bound})"
            
            key = (symbol, region_str)
            if key not in time_region_mapping:
                time_region_mapping[key] = {'times': [], 'positive': [], 'negative': []}
            
            time_region_mapping[key]['times'].append(time_val)
            
            # Determine sample type
            is_positive = sample in positive_samples
            if is_positive:
                time_region_mapping[key]['positive'].append(time_val)
            else:
                time_region_mapping[key]['negative'].append(time_val)
    
    # Analyze mixed regions
    mixed_regions = []
    for (symbol, region_str), data in time_region_mapping.items():
        positive_times = data['positive']
        negative_times = data['negative']
        
        if positive_times and negative_times:
            mixed_regions.append((symbol, region_str, positive_times, negative_times))
    
    print(f"Total time regions: {len(time_region_mapping)}")
    print(f"Mixed regions (both positive and negative samples): {len(mixed_regions)}")
    
    if mixed_regions:
        print(f"\nMixed regions:")
        for symbol, region_str, pos_times, neg_times in mixed_regions[:10]:  # Only show first 10
            print(f"  {symbol}/{region_str}: positive={len(pos_times)}, negative={len(neg_times)}")
            print(f"    Positive times: {pos_times[:5]}{'...' if len(pos_times) > 5 else ''}")
            print(f"    Negative times: {neg_times[:5]}{'...' if len(neg_times) > 5 else ''}")
        if len(mixed_regions) > 10:
            print(f"  ... and {len(mixed_regions) - 10} more mixed regions")

def main():
    """Main function"""
    if len(sys.argv) != 2:
        print("Usage: python debug_min3rta.py <sample_file>")
        print("Example: python debug_min3rta.py traces_output/5_2_6-100.py")
        return
    
    sample_file = sys.argv[1]
    
    if not os.path.exists(sample_file):
        print(f"Error: File {sample_file} does not exist")
        return
    
    print("Min3RTA Debug Tool")
    print("="*60)
    print(f"Sample file: {sample_file}")
    print(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. Load samples
        positive_samples, negative_samples = load_samples_from_file(sample_file)
        
        if not positive_samples and not negative_samples:
            print("Error: No samples loaded")
            return
        
        # 2. Print sample summary
        print_sample_summary(positive_samples, negative_samples)
        
        # 3. Build Min3RTA
        min_3rta, drta = build_min3rta(positive_samples, negative_samples)
        
        if min_3rta is None:
            print("Error: Failed to build Min3RTA")
            return
        
        # 4. Visualize Min3RTA
        output_prefix = os.path.splitext(os.path.basename(sample_file))[0]
        visualize_min3rta(min_3rta, f"traces_output/{output_prefix}")
        
        # 5. Verify samples
        all_correct = verify_samples_with_min3rta(min_3rta, positive_samples, negative_samples)
        
        # 6. Analyze time regions
        analyze_time_regions(min_3rta, positive_samples, negative_samples)
        
        # 7. Summary
        print(f"\n" + "="*60)
        print("FINAL SUMMARY")
        print("="*60)
        print(f"Sample file: {sample_file}")
        print(f"Min3RTA nodes: {len(min_3rta.nodes)}")
        print(f"All samples correct: {'YES' if all_correct else 'NO'}")
        print(f"End time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if not all_correct:
            print(f"\nNote: Some samples failed verification. Check the error details above.")
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
