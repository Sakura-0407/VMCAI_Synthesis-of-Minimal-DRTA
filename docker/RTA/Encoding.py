import z3
from z3 import *
from Min3RTA import TDRTA
from typing import List, Any, Dict, Set, Tuple

class Encoding:
    def __init__(self, min3drta:TDRTA, sizes, sym_mode="bfs", extra_clauses=None, positive_samples=None):
        """
        Initialize encoder
        
        Args:
        min3drta: TDRTA instance to encode
        sizes: Dictionary containing size information (color count, node count, etc.)
        sym_mode: Symmetry mode
        extra_clauses: Additional constraints
        positive_samples: List of positive samples (used for color 0 accepting constraint)
        """
        self.min3drta = min3drta  # Store TDRTA instance
        self.sizes = sizes  # Store size parameters
        self.sym_mode = sym_mode  # Store symmetry mode
        self.extra_clauses = extra_clauses  # Store additional constraints
        self.positive_samples = positive_samples  # Store positive samples
        
        # Use Z3 Solver
        self.solver = z3.Optimize()
        # Store all generated variables
        self.variables = {}
        # Get color count from sizes
        self.n_colors = self.sizes
        # Get node list instead of node count
        self.node_list = list(self.min3drta.nodes)
        self.clauses = []
        
        # Store hard and soft constraints separately
        self.hard_constraints = []  # Deterministic constraints and other key constraints
        self.soft_constraints = []  # Other constraints

        # Generate time region encoding
        self._generate_symbol_encoding()

    @classmethod
    def from_min3drta(cls, min3drta:TDRTA, sizes, sym_mode="bfs", extra_clauses=None, positive_samples=None):
        """
        Class method: Create Encoding instance from Min3RTA and return clauses
        
        Args:
        min3drta: Min3RTA instance
        sizes: Size parameters
        sym_mode: Symmetry mode
        extra_clauses: Additional clauses
        positive_samples: List of positive samples
        
        Returns:
        List of encoded clauses
        """
        # Create Encoding instance
        encoding = cls(min3drta, sizes, sym_mode, extra_clauses, positive_samples)
        # Return clauses directly
        return encoding.clauses()
    
    def _generate_symbol_encoding(self):
        print(f"Generating encoding")

    def color_accepting(self, color: int) -> int:
        """
        Create color encoding for accepting states
        Called z variables in the literature
        
        Args:
        color: Color number
        
        Returns:
        Corresponding variable ID
        """
        var_name = f"accepting_{color}"
        if var_name not in self.variables:
            self.variables[var_name] = Bool(var_name)
        return self.variables[var_name]
    
    def color_node(self, node: int, color: int) -> int:
        """
        Create color encoding for automaton nodes
        Called x variables in the literature
        
        Args:
        node: Node number
        color: Color number
        
        Returns:
        Corresponding variable ID
        """
        var_name = f"node_{node}_color_{color}"
        if var_name not in self.variables:
            self.variables[var_name] = Bool(var_name)
        return self.variables[var_name]
    
    def parent_relation(self, token: Any, region: Any, color1: int, color2: int) -> int:
        """
        Create encoding for transition relations
        Called y variables in the literature
        
        Args:
        token: Symbol or action of the transition
        region: Time region constraint
        color1: Source state color
        color2: Target state color
        
        Returns:
        Corresponding variable ID
        """
        # Variable name includes time region information
        var_name = f"trans_{token}_{region}_{color1}_{color2}"
        if var_name not in self.variables:
            self.variables[var_name] = Bool(var_name)
        return self.variables[var_name]
    
    def generate_onehot_color_clauses(self):
        """
        Generate OneHot encoding color constraints
        Ensure each node has at least one color and at most one color
        
        Returns:
        Z3 constraint list containing OneHot constraints
        """
        # Use SMT solver to add constraints
        for n in self.node_list:
            # Force initial node (node 0) to use color 0
            if n == 0:
                constraint = self.color_node(0, 0)
                self.add_hard_constraint(constraint, f"Node 0 must use color 0")
            else:
                # Other nodes have at least one color
                # Create boolean variables for nodes
                node_color_vars = []
                for c in range(self.n_colors):
                    node_color_vars.append(self.color_node(n, c))
                constraint = Or(*node_color_vars)
                self.add_hard_constraint(constraint, f"Node {n} has at least one color")
            
            # Each node has at most one color - this is a hard constraint
            if n not in self.min3drta.registered_nodes:  # Skip ignored rejection nodes
                for i in range(self.n_colors):
                    for j in range(i + 1, self.n_colors):  # i < j
                        # Two variables cannot both be true
                        var_i = self.color_node(n, i)
                        var_j = self.color_node(n, j)
                        constraint = Not(And(var_i, var_j))
                        self.add_hard_constraint(constraint, f"Colors {i} and {j} of node {n} are mutually exclusive")
    
    def generate_accept_reject_clauses(self):
        """
        Generate constraints for accepting and rejecting states
        
        Returns:
        Z3 constraint list containing accept/reject state constraints
        """
        # 1. Accepting node constraints: if node n has color c, then color c must be an accepting color
        for n in self.min3drta.accepting:
            for c in range(self.n_colors):
                color_var = self.color_node(n, c)
                accept_var = self.color_accepting(c)
                # Constraint: if node n has color c, then color c must be an accepting color
                # i.e., color_node(n, c) => color_accepting(c)
                # equivalent to Not(color_node(n, c)) OR color_accepting(c)
                constraint = Implies(color_var, accept_var)
                self.add_hard_constraint(constraint, f"Color {c} of accepting node {n} must be an accepting color")
        
        # 2. Rejecting node constraints: if node n has color c, then color c cannot be an accepting color
        for n in self.min3drta.rejecting:
            for c in range(self.n_colors):
                color_var = self.color_node(n, c)
                accept_var = self.color_accepting(c)
                # Constraint: if node n has color c, then color c cannot be an accepting color
                # i.e., color_node(n, c) => Not(color_accepting(c))
                # equivalent to Not(color_node(n, c)) OR Not(color_accepting(c))
                constraint = Implies(color_var, Not(accept_var))
                self.add_hard_constraint(constraint, f"Color {c} of rejecting node {n} cannot be an accepting color")

    def generate_color_zero_accepting_constraint(self):
        """
        Generate constraint: if positive samples exist, then color 0 must be an accepting state
        
        This constraint ensures that when there are positive samples, the initial state (color 0) 
        can accept empty traces or serve as a valid accepting state.
        """
        # Check if positive samples exist
        if self.positive_samples is not None and len(self.positive_samples) > 0:
            # If positive samples exist, color 0 must be an accepting state
            color_0_accepting_var = self.color_accepting(0)
            constraint = color_0_accepting_var
            self.add_hard_constraint(constraint, f"Color 0 must be accepting state when positive samples exist")
            print(f"Added constraint: Color 0 must be accepting state (positive samples: {len(self.positive_samples)})")
        else:
            print("No positive samples provided, skipping color 0 accepting constraint")

    def generate_transition_clauses(self):
        """
        Generate transition relation constraints
        Ensure that for each edge in the tree, if source node has color c1 and there exists a transition 
        from c1 through specific time region to c2, then target node has color c2
        
        Returns:
        Z3 constraint list containing transition constraints
        """
        # Traverse all transition edge labels
        for (source, target, key), (symbol, region_str) in self.min3drta.edge_labels.items():
            # Extract source and target nodes
            
            # Add constraints for all possible color combinations
            for color1 in range(self.n_colors):
                for color2 in range(self.n_colors):
                    source_var = self.color_node(source, color1)
                    target_var = self.color_node(target, color2)
                    # Create transition variable with time region
                    trans_var = self.parent_relation(symbol, region_str, color1, color2)
                    
                    # Constraint: if source node color is color1 and there exists symbol transition 
                    # with region constraint to color2, then target node must have color color2
                    # i.e., (source_var AND trans_var) => target_var
                    constraint = Implies(And(source_var, trans_var), target_var)
                    self.add_hard_constraint(constraint, f"Node {source} has color {color1} and transition from {color1} to {color2} with symbol {symbol} exists, then node {target} has color {color2}")
        
        # Add deterministic constraints: from same color state, same symbol, same or intersecting regions cannot reach multiple different color states
        self._add_deterministic_constraints()
        
        # Add constraint: at least one transition edge exists for each symbol/region combination
        self._add_symbol_region_existence_constraints()
    
    def _add_deterministic_constraints(self):
        """
        Add deterministic constraints to ensure from same color state, for same symbol and same/intersecting time regions,
        there cannot be multiple target color states
        
        This is the most important constraint, set as hard constraint (highest priority)
        """
        print("Adding deterministic constraints (highest priority)...")
        
        # Create dictionary to group all transition variables by (color1, symbol)
        transitions_by_source = {}
        
        # Collect all transition variables
        for var_name, var in self.variables.items():
            if var_name.startswith("trans_"):
                # Parse variable name trans_symbol_region_color1_color2
                parts = var_name.split('_')
                if len(parts) >= 5:  # Ensure variable name format is correct
                    symbol = parts[1]
                    region_str = '_'.join(parts[2:-2])  # Region may contain underscores
                    color1 = int(parts[-2])
                    color2 = int(parts[-1])
                    
                    # Group by (color1, symbol)
                    key = (color1, symbol)
                    if key not in transitions_by_source:
                        transitions_by_source[key] = []
                    
                    transitions_by_source[key].append((region_str, color2, var))
        
        # Add deterministic constraints for each group
        deterministic_count = 0
        for (color1, symbol), transitions in transitions_by_source.items():
            # Add constraints for each pair of possibly intersecting regions
            for i in range(len(transitions)):
                region1, color2_i, var_i = transitions[i]
                
                for j in range(i+1, len(transitions)):
                    region2, color2_j, var_j = transitions[j]
                    
                    # If different target colors and regions may intersect
                    if color2_i != color2_j and self._regions_may_intersect(region1, region2):
                        # Add constraint: these two transitions cannot both be true
                        constraint = Not(And(var_i, var_j))
                        
                        # Deterministic constraints are hard constraints (highest priority)
                        self.add_hard_constraint(constraint, 
                            f"Deterministic constraint: transitions from color {color1} through symbol {symbol} to region {region1}->color {color2_i} and {region2}->color {color2_j} cannot coexist")
                        deterministic_count += 1
        
        print(f"Added {deterministic_count} deterministic constraints (hard constraints)")
    
    def _regions_may_intersect(self, region1_str, region2_str):
        """
        Determine if two time regions may intersect
        
        Args:
        region1_str, region2_str: Strings representing time regions
        
        Returns:
        bool: True if regions may intersect, False otherwise
        """
        # Simple judgment: if region strings are exactly the same, they definitely intersect
        if region1_str == region2_str:
            return True
            
        # Parse interval strings while preserving interval open/closed properties
        def parse_region(region_str):
            # Remove spaces
            region_str = region_str.replace(" ", "")
            
            # Parse interval values and open/closed properties
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
                return (lower, upper, lower_closed, upper_closed)
            except ValueError:
                return None
        
        # Try to parse both regions
        region1 = parse_region(region1_str)
        region2 = parse_region(region2_str)
        
        # If cannot parse, conservatively assume they may intersect
        if region1 is None or region2 is None:
            return True
            
        # Check if intervals intersect, considering open/closed properties
        lower1, upper1, lower1_closed, upper1_closed = region1
        lower2, upper2, lower2_closed, upper2_closed = region2
        
        # Interval 1 is completely to the left of interval 2
        if upper1 < lower2 or (upper1 == lower2 and (not upper1_closed or not lower2_closed)):
            return False
            
        # Interval 1 is completely to the right of interval 2
        if lower1 > upper2 or (lower1 == upper2 and (not lower1_closed or not upper2_closed)):
            return False
            
        # Otherwise intervals intersect
        return True
    
    def _add_symbol_region_existence_constraints(self):
        """
        Add constraints to ensure at least one transition edge exists for each symbol/region combination
        """
        # Collect all unique symbol/region combinations
        symbol_region_pairs = set()
        for (source, target, key), (symbol, region_str) in self.min3drta.edge_labels.items():
            symbol_region_pairs.add((symbol, region_str))
        
        # Add constraints for each symbol/region combination
        for symbol, region_str in symbol_region_pairs:
            # Collect all possible transition variables for this symbol/region combination
            transition_vars = []
            for color1 in range(self.n_colors):
                for color2 in range(self.n_colors):
                    trans_var = self.parent_relation(symbol, region_str, color1, color2)
                    transition_vars.append(trans_var)
            
            # Constraint: at least one transition variable is true
            if transition_vars:
                constraint = Or(*transition_vars)
                self.add_hard_constraint(constraint, f"At least one transition edge exists for symbol {symbol} in region {region_str}")
    
    def _add_complete_coverage_constraints(self):
        """
        Add new constraints: for each state's each symbol/time combination, there must be a corresponding transition path
        
        This constraint ensures:
        1. For each edge (source, target, symbol, region) in original TDRTA, there must be a corresponding activated transition in SMT encoding
        2. Ensure no "isolated" edges, every symbol/time combination can find a transition path
        """
        # Collect all edge information from original TDRTA
        original_edges = []
        for (source, target, key), (symbol_id, region_str) in self.min3drta.edge_labels.items():
            original_edges.append({
                'source': source,
                'target': target, 
                'symbol_id': symbol_id,
                'region_str': region_str
            })
        
        print(f"Original TDRTA has {len(original_edges)} edges in total")
        
        # Add constraints for each original edge: must have corresponding activated transition
        for edge in original_edges:
            source = edge['source']
            target = edge['target']
            symbol_id = str(edge['symbol_id'])
            region_str = edge['region_str']
            
            # Find all possible transition variables matching this edge
            possible_transitions = []
            
            # Traverse all color combinations to find transitions that could implement this edge
            for source_color in range(self.n_colors):
                for target_color in range(self.n_colors):
                    # Check if source node can possibly have source_color
                    source_color_var = self.color_node(source, source_color)
                    # Check if target node can possibly have target_color  
                    target_color_var = self.color_node(target, target_color)
                    # Check if corresponding transition variable exists
                    trans_var = self.parent_relation(symbol_id, region_str, source_color, target_color)
                    
                    # Add triple: (source node color, transition, target node color)
                    possible_transitions.append(And(source_color_var, trans_var, target_color_var))
            
            if possible_transitions:
                # Constraint: for each edge in original TDRTA, at least one color combination must be able to implement it
                edge_coverage = Or(*possible_transitions)
                self.add_hard_constraint(edge_coverage, f"Original edge({source}->{target}, symbol{symbol_id}, region{region_str}) must have corresponding transition path")
        
        # Additional constraint: ensure each used color state has complete time coverage for each symbol
        self._add_temporal_coverage_constraints()
        
        # New constraint: ensure each state has transitions for every symbol_region combination
        self._add_state_symbol_region_coverage_constraints()
    
    def _add_state_symbol_region_coverage_constraints(self):
        """
        Add constraints: ensure each state has transitions for every symbol_region combination
        
        For example, if trans_4_(4, 5) exists, then not only should there be transitions from state 0 and state 2,
        but also transitions from state 1
        """
        # Collect all unique symbol_region combinations
        symbol_region_pairs = set()
        for (source, target, key), (symbol_id, region_str) in self.min3drta.edge_labels.items():
            symbol_region_pairs.add((str(symbol_id), region_str))
        
        print(f"Found {len(symbol_region_pairs)} symbol_region combinations")
        
        # Add constraints for each symbol_region combination and each color state
        for symbol_id, region_str in symbol_region_pairs:
            for source_color in range(self.n_colors):
                # Get variable representing whether this color is used
                color_used_var = self.variables.get(f"color_{source_color}_used")
                if color_used_var is None:
                    continue
                
                # Collect all possible transitions from this color state through this symbol_region
                transitions_from_color = []
                for target_color in range(self.n_colors):
                    trans_var = self.parent_relation(symbol_id, region_str, source_color, target_color)
                    transitions_from_color.append(trans_var)
                
                if transitions_from_color:
                    # Constraint: if color state is used, then must have transitions through this symbol_region
                    coverage_constraint = Implies(color_used_var, Or(*transitions_from_color))
                    self.add_hard_constraint(coverage_constraint, f"When color state {source_color} is used, must have transitions through symbol {symbol_id}_region {region_str}")

    def _add_temporal_coverage_constraints(self):
        """
        Add temporal coverage constraints: ensure each used color state has complete time axis coverage for each symbol
        """
        # Collect all symbols
        all_symbols = set()
        for (source, target, key), (symbol_id, region_str) in self.min3drta.edge_labels.items():
            all_symbols.add(str(symbol_id))
        
        # Add coverage constraints for each color state and each symbol
        for color in range(self.n_colors):
            color_used_var = self.variables.get(f"color_{color}_used")
            if color_used_var is None:
                continue
                
            for symbol in all_symbols:
                # Collect all transitions from this color state through this symbol
                transitions_for_color_symbol = []
                
                for target_color in range(self.n_colors):
                    # Collect all possible regions
                    regions_for_symbol = set()
                    for (source, target, key), (sym_id, region_str) in self.min3drta.edge_labels.items():
                        if str(sym_id) == symbol:
                            regions_for_symbol.add(region_str)
                    
                    # Create transition variables for each region
                    for region_str in regions_for_symbol:
                        trans_var = self.parent_relation(symbol, region_str, color, target_color)
                        transitions_for_color_symbol.append(trans_var)
                
                if transitions_for_color_symbol:
                    # Constraint: if color is used, then must have at least one transition through this symbol
                    coverage_constraint = Implies(color_used_var, Or(*transitions_for_color_symbol))
                    # self.solver.add(coverage_constraint)
                    # self.clauses.append(f"When color {color} is used, must have at least one transition through symbol {symbol}: {coverage_constraint}")

    def generate_min_colors_used_clauses(self):
        """
        Generate constraints to ensure at least specified number of colors are used, 
        and each color participates in at least one transition relation
        
        Returns:
        Z3 constraint list containing minimum color usage constraints
        """
        # Create a variable for each color indicating whether the color is used
        color_used_vars = []
        for c in range(self.n_colors):
            # Create variable indicating whether color c is used by at least one node
            vars_for_color = []
            for n in self.node_list:
                vars_for_color.append(self.color_node(n, c))
            
            # Color c is used if and only if at least one node uses this color
            color_used_var = Bool(f"color_{c}_used")
            self.variables[f"color_{c}_used"] = color_used_var
            
            # Add constraint: color_used_var <=> Or(node_0_color_c, node_1_color_c, ...)
            constraint = (color_used_var == Or(*vars_for_color))
            self.add_hard_constraint(constraint, f"Color {c} is used if and only if at least one node uses this color")
            
            color_used_vars.append(color_used_var)
        
        # Add constraint to ensure at least specified number of colors are used
        # From PbGe(color_used_vars, 1) we can get a constraint that at least 1 color is used
        # We need PbGe(color_used_vars, self.n_colors) to ensure all colors are used
        constraint = PbGe([(var, 1) for var in color_used_vars], self.n_colors)
        # self.add_hard_constraint(constraint)
        # self.clauses.append(f"At least {self.n_colors} colors are used: {constraint}")
        
        # Add new constraint: ensure each color participates in at least one transition relation (as source or target state)
        # self._add_color_transition_constraints()

    def _add_color_transition_constraints(self):
        """
        Add constraints to ensure each color participates in at least one transition relation (as source or target state)
        """
        # Collect all transition variables
        transition_vars_by_color = {}
        for c in range(self.n_colors):
            transition_vars_by_color[c] = {
                'as_source': [],  # Transition variables as source state
                'as_target': []   # Transition variables as target state
            }
        
        # Traverse all possible transition variables
        for var_name, var in self.variables.items():
            if var_name.startswith("trans_"):
                # Parse variable name, format: trans_symbol_region_color1_color2
                parts = var_name.split('_')
                if len(parts) >= 5:
                    color1 = int(parts[-2])  # Source state color
                    color2 = int(parts[-1])  # Target state color
                    
                    # Add to corresponding color lists
                    if color1 < self.n_colors:
                        transition_vars_by_color[color1]['as_source'].append(var)
                    if color2 < self.n_colors:
                        transition_vars_by_color[color2]['as_target'].append(var)
        
        # Add constraint: each color participates in at least one transition relation
        for c in range(self.n_colors):
            # if c == 0:
            #     continue
            # Get all transition variables where color c is source state
            source_vars = transition_vars_by_color[c]['as_source']
            # Get all transition variables where color c is target state
            target_vars = transition_vars_by_color[c]['as_target']
            
            # # Collect all transition variables related to color c
            # all_transition_vars = source_vars + target_vars
            
            # # If no transition variables related to this color, skip directly (theoretically shouldn't happen)
            # if not all_transition_vars:
            #     continue
            
            # Add constraint: if color c is used, then at least one related transition variable is true
            color_used_var = self.variables[f"color_{c}_used"]
            
            # # Color c is used => at least one related transition variable is true
            # # i.e.: Not(color_used_var) OR Or(transition_vars)
            # constraint = Implies(color_used_var, Or(*all_transition_vars))
            # self.solver.add(constraint)
            # self.clauses.append(f"When color {c} is used, participates in at least one transition relation: {constraint}")
            
        #     # To further strengthen constraint, ensure each color is at least source state of one transition
        #     if source_vars:
        #         # Create variable for color c indicating whether it serves as source state
        #         color_as_source_var = Bool(f"color_{c}_as_source")
        #         self.variables[f"color_{c}_as_source"] = color_as_source_var
                
        #         # color_as_source_var <=> Or(source_vars)
        #         source_constraint = (color_as_source_var == Or(*source_vars))
        #         self.solver.add(source_constraint)
                
        #         # If color c is used, then it should be source state of at least one transition
        #         source_implication = Implies(color_used_var, color_as_source_var)
        #         self.solver.add(source_implication)
        #         self.clauses.append(f"When color {c} is used, is at least source state of one transition: {source_implication}")
            
            # Ensure each color is at least target state of one transition
            if target_vars:
                if c == 0:
                    continue
                # Create variable for color c indicating whether it serves as target state
                color_as_target_var = Bool(f"color_{c}_as_target")
                self.variables[f"color_{c}_as_target"] = color_as_target_var
                
                # color_as_target_var <=> Or(target_vars)
                target_constraint = (color_as_target_var == Or(*target_vars))
                self.add_hard_constraint(target_constraint, f"Definition of color {c} as target state")

        # Add connectivity constraints for each color
        for c in range(self.n_colors):
            # if c == 0:  # Skip initial color
            #     continue
            
            # Add connection constraints with other colors
            other_colors_vars = []
            
            # Collect connection variables with other colors
            for var_name, var in self.variables.items():
                if var_name.startswith("trans_"):
                    parts = var_name.split('_')
                    if len(parts) >= 5:
                        color1 = int(parts[-2])
                        color2 = int(parts[-1])
                        
                        # If it's connection between current color and other colors
                        if (color1 == c and color2 != c) or (color2 == c and color1 != c):
                            other_colors_vars.append(var)
            
            # If there are possible connection variables
            if other_colors_vars:
                # When color c is used, must have connection with at least one other color
                connection_constraint = Implies(self.variables[f"color_{c}_used"], Or(*other_colors_vars))
                # self.solver.add(connection_constraint)
                # self.clauses.append(f"When color {c} is used, must have connection with at least one other color: {connection_constraint}")

    def generate_clauses(self):
        """
        Generate constraints for SMT solver and solve
        
        Returns:
        Solving result and model
        """
        # Clear existing constraint list
        self.clauses = []
        
        # 1. Generate and add OneHot color encoding constraints
        self.generate_onehot_color_clauses()
        
        # 2. Generate and add accept/reject state constraints
        self.generate_accept_reject_clauses()
        
        # 2.5. Generate color 0 accepting constraint (if positive samples exist)
        self.generate_color_zero_accepting_constraint()
        
        # 3. Generate and add transition constraints
        self.generate_transition_clauses()
        
        # 4. Add minimum color usage constraints
        self.generate_min_colors_used_clauses()
        
        # 5. Add complete coverage constraints (must be called after color_used variables are created)
        self._add_complete_coverage_constraints()
        
        # 6. Add debug constraints
        # debug_trans_var = self.parent_relation(0, "(4, 5)", 1, 0)
        # debug_constraint = debug_trans_var
        # self.solver.add(debug_constraint)
        # self.clauses.append(f"Debug constraint: force trans_0_(4, 5)_1_0 = True: {debug_constraint}")
        
        # Return solving result
        print(f"Added {len(self.clauses)} constraints to SMT solver")
        # for i, clause in enumerate(self.clauses):
        #     print(f"Constraint {i+1}: {clause}")
        
        # Try to solve
        result = self.solver.check()
        if result == sat:
            print("SMT solver found solution")
            model = self.solver.model()
            return (result, model)
        else:
            print(f"SMT solver result: {result}")
            return (result, None)
    
    def add_hard_constraint(self, constraint, description=""):
        """
        Add hard constraint (highest priority, must be satisfied)
        """
        self.solver.add(constraint)
        self.hard_constraints.append((constraint, description))
        self.clauses.append(f"Hard constraint: {description}: {constraint}")
    
    def add_soft_constraint(self, constraint, description="", weight=1):
        """
        Add soft constraint (treated as hard constraint since Solver doesn't support soft constraints)
        """
        self.solver.add(constraint)
        self.soft_constraints.append((constraint, description, weight))
        self.clauses.append(f"Soft constraint(weight{weight}): {description}: {constraint}")
    
    def solve(self):
        """
        Use Z3 solver to solve all constraints
        
        Returns:
        tuple: (result, model) where result is solving result, model is satisfied model
        """
        print("\n=== Solver Status ===")
        print(f"Hard constraint count: {len(self.hard_constraints)}")
        print(f"Soft constraint count: {len(self.soft_constraints)}")
        print(f"Total variable count: {len(self.variables)}")
        print("Solving...")
        
        result = self.solver.check()
        
        if result == sat:
            print("✓ Solving successful!")
            model = self.solver.model()
            return ("SAT", model)
        elif result == unsat:
            print("✗ No solution (UNSAT)")
            return ("UNSAT", None)
        else:
            print("? Unknown result")
            return ("UNKNOWN", None)
    
    