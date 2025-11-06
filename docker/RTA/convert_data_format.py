#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data format conversion script
Convert advanced_test.dat format to format used in test_encoding.py

Input format:
- First line: total number of samples, number of symbols
- Each line: label(0/1) number_of_events symbol:timestamp ...

Output format:
- positive_samples = [[('symbol', timestamp), ...], ...]
- negative_samples = [[('symbol', timestamp), ...], ...]
"""

import sys
import argparse
from typing import List, Tuple, Dict

def parse_data_file(filename: str, symbol_mapping: Dict[int, str] = None) -> Tuple[List[List[Tuple[str, float]]], List[List[Tuple[str, float]]]]:
    """
    Parse data file
    
    Args:
        filename: Input filename
        symbol_mapping: Custom symbol mapping
        
    Returns:
        (positive_samples, negative_samples): Lists of positive and negative samples
    """
    positive_samples = []
    negative_samples = []
    
    # Default symbol mapping: number -> letter
    if symbol_mapping is None:
        # Use 26 English letters as symbol mapping
        symbol_mapping = {i: chr(ord('a') + i) for i in range(26)}
        # If more than 26 symbols, use numeric suffix
        for i in range(26, 100):
            symbol_mapping[i] = f'sym_{i}'
    
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Skip first line (metadata)
    for line_num, line in enumerate(lines[1:], 2):
        parts = line.strip().split()
        if len(parts) < 3:
            continue
            
        try:
            label = int(parts[0])  # 0=negative sample, 1=positive sample
            event_count = int(parts[1])  # Number of events
            
            # Parse event sequence
            trace = []
            for i in range(2, min(2 + event_count, len(parts))):
                symbol_time = parts[i].split(':')
                if len(symbol_time) == 2:
                    symbol_id = int(symbol_time[0])
                    timestamp = float(symbol_time[1])
                    symbol = symbol_mapping.get(symbol_id, f'sym_{symbol_id}')
                    trace.append((symbol, timestamp))
            
            # Sort by timestamp
            trace.sort(key=lambda x: x[1])
            
            # Add to corresponding sample set
            if label == 1:
                positive_samples.append(trace)
            else:
                negative_samples.append(trace)
                
        except (ValueError, IndexError) as e:
            print(f"Warning: Line {line_num} format error, skipping: {e}")
            continue
    
    return positive_samples, negative_samples

def format_output(positive_samples: List[List[Tuple[str, float]]], 
                 negative_samples: List[List[Tuple[str, float]]], 
                 max_samples: int = None,
                 compact: bool = False) -> str:
    """
    Format output as Python code
    
    Args:
        positive_samples: List of positive samples
        negative_samples: List of negative samples
        max_samples: Maximum number of samples limit
        compact: Whether to use compact format
        
    Returns:
        Formatted Python code string
    """
    # Limit number of samples
    if max_samples:
        positive_samples = positive_samples[:max_samples]
        negative_samples = negative_samples[:max_samples]
    
    output = []
    
    # Positive samples
    output.append("positive_samples = [")
    for i, trace in enumerate(positive_samples):
        if compact:
            trace_str = str(trace)
        else:
            trace_str = "[" + ", ".join([f"('{symbol}', {timestamp})" for symbol, timestamp in trace]) + "]"
        
        if not compact:
            time_range = f"{trace[0][1]:.1f}-{trace[-1][1]:.1f}s" if trace else "empty"
            comment = f"  # trace{i+1}: {time_range}, {len(trace)} events"
            output.append(f"    {trace_str},{comment}")
        else:
            output.append(f"    {trace_str},")
    output.append("]")
    output.append("")
    
    # Negative samples
    output.append("negative_samples = [")
    for i, trace in enumerate(negative_samples):
        if compact:
            trace_str = str(trace)
        else:
            trace_str = "[" + ", ".join([f"('{symbol}', {timestamp})" for symbol, timestamp in trace]) + "]"
        
        if not compact:
            time_range = f"{trace[0][1]:.1f}-{trace[-1][1]:.1f}s" if trace else "empty"
            comment = f"  # trace{i+1}: {time_range}, {len(trace)} events"
            output.append(f"    {trace_str},{comment}")
        else:
            output.append(f"    {trace_str},")
    output.append("]")
    
    return "\n".join(output)

def print_statistics(positive_samples: List[List[Tuple[str, float]]], 
                    negative_samples: List[List[Tuple[str, float]]]):
    """Print data statistics"""
    print(f"Data statistics:")
    print(f"  Positive samples: {len(positive_samples)}")
    print(f"  Negative samples: {len(negative_samples)}")
    print(f"  Total samples: {len(positive_samples) + len(negative_samples)}")
    
    # Statistics on symbol usage
    all_symbols = set()
    total_events = 0
    
    for trace in positive_samples + negative_samples:
        total_events += len(trace)
        for symbol, _ in trace:
            all_symbols.add(symbol)
    
    print(f"  Total events: {total_events}")
    print(f"  Symbols used: {sorted(all_symbols)}")
    
    # Statistics on time range
    all_timestamps = []
    for trace in positive_samples + negative_samples:
        for _, timestamp in trace:
            all_timestamps.append(timestamp)
    
    if all_timestamps:
        print(f"  Time range: {min(all_timestamps):.1f} - {max(all_timestamps):.1f}")
    
    # Statistics on trace length
    pos_lengths = [len(trace) for trace in positive_samples]
    neg_lengths = [len(trace) for trace in negative_samples]
    
    if pos_lengths:
        print(f"  Positive trace length: {min(pos_lengths)}-{max(pos_lengths)}, avg {sum(pos_lengths)/len(pos_lengths):.1f}")
    if neg_lengths:
        print(f"  Negative trace length: {min(neg_lengths)}-{max(neg_lengths)}, avg {sum(neg_lengths)/len(neg_lengths):.1f}")

def create_symbol_mapping(mapping_str: str) -> Dict[int, str]:
    """
    Create custom symbol mapping
    
    Args:
        mapping_str: Format like "0:a,1:b,2:c"
        
    Returns:
        Symbol mapping dictionary
    """
    mapping = {}
    for pair in mapping_str.split(','):
        if ':' in pair:
            num, symbol = pair.split(':', 1)
            mapping[int(num)] = symbol
    return mapping

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Convert advanced_test.dat format to test_encoding.py format')
    parser.add_argument('input_file', help='Input file path')
    parser.add_argument('-n', '--max-samples', type=int, help='Maximum number of samples limit')
    parser.add_argument('-o', '--output', help='Output file path (default: input_filename_formatted.py)')
    parser.add_argument('-c', '--compact', action='store_true', help='Use compact format output')
    parser.add_argument('-s', '--symbols', help='Custom symbol mapping, format: 0:a,1:b,2:c')
    parser.add_argument('-p', '--preview', type=int, default=3, help='Preview number of samples (default: 3)')
    parser.add_argument('--no-stats', action='store_true', help='Do not display statistics')
    
    args = parser.parse_args()
    
    try:
        # Create symbol mapping
        symbol_mapping = None
        if args.symbols:
            symbol_mapping = create_symbol_mapping(args.symbols)
        
        # Parse data
        positive_samples, negative_samples = parse_data_file(args.input_file, symbol_mapping)
        
        # Print statistics
        if not args.no_stats:
            print_statistics(positive_samples, negative_samples)
            print()
        
        # Format output
        formatted_output = format_output(positive_samples, negative_samples, args.max_samples, args.compact)
        
        # Determine output filename
        if args.output:
            output_file = args.output
        else:
            output_file = args.input_file.replace('.dat', '_formatted.py')
            if output_file == args.input_file:  # If no .dat extension
                output_file = args.input_file + '_formatted.py'
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# -*- coding: utf-8 -*-\n")
            f.write(f"# Converted from {args.input_file}\n")
            if args.symbols:
                f.write(f"# Symbol mapping: {args.symbols}\n")
            f.write("\n")
            f.write(formatted_output)
        
        print(f"Conversion completed! Output file: {output_file}")
        
        # Preview output
        if args.preview > 0:
            print(f"\nPreview first {args.preview} samples:")
            print("=" * 50)
            
            preview_positive = positive_samples[:args.preview] if len(positive_samples) >= args.preview else positive_samples
            preview_negative = negative_samples[:args.preview] if len(negative_samples) >= args.preview else negative_samples
            
            preview_output = format_output(preview_positive, preview_negative, compact=args.compact)
            print(preview_output)
        
    except Exception as e:
        print(f"Error occurred during conversion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 