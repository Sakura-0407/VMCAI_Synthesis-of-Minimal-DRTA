#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
batch_generate.py
Batch generate traces with different counts
"""

import os
import sys
import argparse
from generate_traces import *

def batch_generate_traces(json_file: str, trace_counts: List[int], output_dir: str = None):
    """Batch generate traces with different counts"""
    
    # Read JSON file
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found {json_file}")
        return
    except json.JSONDecodeError:
        print(f"Error: Unable to parse JSON file {json_file}")
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
        print("=" * 60)
    except Exception as e:
        print(f"Error: Failed to parse automaton - {e}")
        return
    
    # Create output directory
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    base_name = os.path.splitext(os.path.basename(json_file))[0]
    
    # Generate traces for each count
    for count in trace_counts:
        print(f"\nGenerating {count} traces...")
        
        # Set random seed for reproducibility
        random.seed(42 + count)
        
        # Generate traces
        positive_samples, negative_samples = generate_traces(automaton, count)
        
        print(f"Generation completed: {len(positive_samples)} positive, {len(negative_samples)} negative")
        
        # Determine output filename
        if output_dir:
            output_file = os.path.join(output_dir, f"{base_name}_{count}_traces.py")
        else:
            output_file = f"{base_name}_{count}_traces.py"
        
        # Generate output content
        result = format_output(positive_samples, negative_samples)
        
        # Add comment information
        header = f'''#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Auto-generated trace file
Source automaton: {json_file}
Automaton name: {automaton.name}
Total traces: {len(positive_samples) + len(negative_samples)}
Positive samples: {len(positive_samples)}
Negative samples: {len(negative_samples)}
Generation time: {time.strftime("%Y-%m-%d %H:%M:%S")}
"""

'''
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(header + result)
        
        print(f"Results saved to: {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Batch generate traces with different counts')
    parser.add_argument('json_file', help='JSON automaton file path')
    parser.add_argument('--counts', '-c', nargs='+', type=int, 
                       default=[50, 100, 200, 250, 500],
                       help='List of trace counts to generate (default: 50 100 200 250 500)')
    parser.add_argument('--output-dir', '-o', type=str, 
                       help='Output directory (optional)')
    
    args = parser.parse_args()
    
    print(f"Will generate traces with following counts for {args.json_file}: {args.counts}")
    
    batch_generate_traces(args.json_file, args.counts, args.output_dir)
    
    print(f"\nBatch generation completed!")

if __name__ == "__main__":
    import time
    main() 