class Region:
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
    
    def __str__(self):
        # String representation, display as [x,y], (x,y), [x,y) or (x,y] based on inclusion
        left = '[' if self.lower_inclusive else '('
        right = ']' if self.upper_inclusive else ')'
        # If upper bound is infinity, use ∞ symbol
        upper_str = str(self.upper) if self.upper != float('inf') else '∞'
        return f"{left}{self.lower}, {upper_str}{right}"
    
    def __eq__(self, other):
        # Check if two regions are equal
        if not isinstance(other, Region):
            return False
        # Compare all attributes are identical
        return (self.lower == other.lower and 
                self.upper == other.upper and 
                self.lower_inclusive == other.lower_inclusive and 
                self.upper_inclusive == other.upper_inclusive)
    
    def __hash__(self):
        # Generate hash value for use as dictionary key or set element
        return hash((self.lower, self.upper, self.lower_inclusive, self.upper_inclusive))


class State:
    """State in TAPTA"""
    def __init__(self, state_id):
        # Unique identifier for state
        self.id = state_id
        # Whether it is accepting state (default: False)
        self.is_accepting = False
        # Whether it is rejecting state (default: False)
        self.is_rejecting = False
        # State transition dictionary, key is (symbol, region) pair, value is target state
        self.transitions = {}  # {(symbol, region): target_state}
    
    def add_transition(self, symbol, region, target_state):
        """Add transition from current state to target state"""
        # Add (symbol, region) pair as key and target state as value to transition dictionary
        self.transitions[(symbol, region)] = target_state
    
    def get_transition(self, symbol, region):
        """Get transition target state for given symbol and region"""
        # Iterate over all transitions
        for (sym, reg), target in self.transitions.items():
            # If matching symbol and region found, return corresponding target state
            if sym == symbol and reg == region:
                return target
        # If no matching transition found, return None
        return None
    
    def mark_as_accepting(self):
        """Mark state as accepting state"""
        # Set as accepting state
        self.is_accepting = True
        # Ensure not simultaneously rejecting
        self.is_rejecting = False
    
    def mark_as_rejecting(self):
        """Mark state as rejecting state"""
        # Set as rejecting state
        self.is_rejecting = True
        # Ensure not simultaneously accepting
        self.is_accepting = False


class TAPTA:
    """Timed Automaton with Pure Time Actions"""
    def __init__(self):
        # Dictionary storing all states, key is state ID, value is state object
        self.states = {}
        # Create and set initial state q0
        self.initial_state = self.create_state()
        
    def create_state(self):
        """Create new state and return"""
        # Use current state count as new state ID
        state_id = len(self.states)
        # Create new state object
        state = State(state_id)
        # Add new state to state dictionary
        self.states[state_id] = state
        # Return newly created state
        return state
    
    def delta(self, state, symbol_region_pair):
        """Transition function δ(q, (σ, I))"""
        # Unpack symbol and region from symbol-region pair
        symbol, region = symbol_region_pair
        # Call state's get_transition method to get target state
        return state.get_transition(symbol, region)
    
    def add_transition(self, source_state, symbol, region, target_state):
        """Add transition from source state to target state"""
        # Call source state's add_transition method to add transition
        source_state.add_transition(symbol, region, target_state)


def BuildTimedAPTA(S_positive, S_negative):
    """
    Build timed APTA automaton (matches pseudocode naming)
    
    Parameters:
    S_positive: Positive sample set, each sample is a timed trace, e.g. [(a,1), (b,2)]
    S_negative: Negative sample set, same format
    
    Returns:
    Built TAPTA automaton
    """
    # Combine positive and negative sample sets for calculating maximum constant and building automaton
    S = S_positive + S_negative
    
    # Determine maximum constant κ (round up to nearest integer)
    kappa = 0
    # Iterate over all traces
    for trace in S:
        # Iterate over each symbol-time pair in trace
        for _, tau in trace:
            # Calculate maximum value after rounding up time value
            kappa = max(kappa, int(tau) + (1 if tau > int(tau) else 0))
    
    # Output calculated maximum constant κ
    print(f"Calculated maximum constant κ: {kappa}")
    
    # Define time region list
    Regions = []
    # Add [0,0] region (exact time point 0)
    Regions.append(Region(0, 0, True, True))
    
    # Add (0,1), [1,1], ..., [kappa, kappa] regions
    for i in range(kappa):
        # Add (i, i+1) region (open interval)
        Regions.append(Region(i, i+1, False, False))
        # Add [i+1, i+1] region (exact time point i+1)
        Regions.append(Region(i+1, i+1, True, True))
    
    # Add (kappa, infinity) region (represents all time values greater than κ)
    Regions.append(Region(kappa, float('inf'), False, False))
    
    # Print all created time regions
    print("Created time regions:")
    for r in Regions:
        print(f"  {r}")
    
    # Initialize TAPTA automaton
    T = TAPTA()
    
    # Process each trace
    for omega in S:
        # Start from initial state q0
        q = T.initial_state
        
        # Iterate over each symbol-time pair in trace
        for i in range(len(omega)):
            # Unpack current symbol and time value
            sigma, tau = omega[i]
            
            # Find region I containing time value
            I = None
            # Iterate over all regions to find region containing current time value
            for region in Regions:
                if region.contains(tau):
                    I = region
                    break
            
            # Debug information, show which region time value maps to
            print(f"Time value {tau} maps to region {I}")
            
            # If no corresponding transition exists, create new state and transition
            if T.delta(q, (sigma, I)) is None:
                # Create new state
                q_new = T.create_state()
                # Add transition from current state to new state
                T.add_transition(q, sigma, I, q_new)
            
            # Move to next state (whether newly created or existing)
            q = T.delta(q, (sigma, I))
        
        # Mark final state
        if omega in S_positive:
            # If trace is positive sample, mark final state as accepting
            q.mark_as_accepting()
        else:
            # If trace is negative sample, mark final state as rejecting
            q.mark_as_rejecting()
    
    # Return built TAPTA automaton
    return T
