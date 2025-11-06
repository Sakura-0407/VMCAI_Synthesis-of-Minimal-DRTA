This artifact provides the tools, files, logs, and additional packages needed to run the experiments presented in the VMCAI'26 submission "SAT-Based Synthesis of Minimal Deterministic Real-Time Automata via 3DRTA Representation".

The ZIP archive extracts its content inside the **vmcai26-artifact** directory, containing all benchmark files and scripts needed to run the experiments, including the source code of all tools evaluated in the paper.

The experiments are performed on an Ubuntu system with the help of benchexec (https://github.com/sosy-lab/benchexec/), a tool developed specifically for running benchmarks in a controlled setting and collecting statistics about the single executions.

Inside the **vmcai26-artifact** directory there is the following content:
- **docker**: a directory containing all material needed to generate the Docker image.
- **docker\*.sh**: multiple Bash script to generated and run the Docker image and perform multiple operations with it.
- **logs-submission**: the logs of the experiments performed for the submission.
- **plots** and **results**: two empty directories that are used for data exchange.


# Generating the Docker image in the host

The following instructions are given for a Linux operating system, where we assume Docker is already installed and the user is already configured to use it; 
on Windows or MacOS, please adapt them accordingly.

To generate the image, open a terminal, move to the **vmcai26-artifact** directory, and run the command
```bash
./dockerCreateImage.sh
```
On our machine, the image has been generated in about 15 minutes; 
the majority of the time is taken by the retrieval and installation of the required packages from the Ubuntu repositories.

Once completed, by running the command `docker images`, the output should be similar to
```
REPOSITORY   TAG        IMAGE ID       CREATED          SIZE
rta          latest     31f0121daae9   27 seconds ago   3.93GB
```


# Replicating the experiments

In a nutshell, the experiments reported in the paper can be replicated by running the following commands, inside the **vmcai26-artifact** directory:
```bash
./dockerPreparePlots.sh
./dockerRunFlexFringe.sh
./dockerRunRTA.sh
./dockerPreparePlots.sh
```

The `dockerPreparePlots.sh` command starts an rta Docker container that parses the log files of the experiments and generates the PDF files of the plots included in the paper; 
the generated files can be found inside the **plots** directory. 
Since every time the `dockerPreparePlots.sh` command is called, its content is overwritten, it is important to save the plots.

The plots are generated based on the TXT log files that are present in the **results** directory. 
The script first copies the original logs of our experiments and then it uses the most recent logs from FlexFringe (files starting with **rti**) and RTA (files starting with **rta**) contained in **results**.
BenchExec uses timestamps in the generated files, so logs are not overwritten.

The `dockerRunFlexFringe.sh` command starts an rta Docker container running FlexFringe on all the benchmarks files. 
On the machine we used for the experiments, the container terminated in about 20 minutes.

The `dockerRunRTA.sh` command is similar and it runs RTA on all the benchmarks files. 
On the machine we used for the experiments, the container terminated in about 11 hours.


# Sharing data between the Docker container and the host machine

The tools inside the Docker image, when run in a container, generate several files, like the tool's logs and the plots.
To make them available in the host machine, the scripts mentioned above to run the rta image bind the **plots** and **results** directories from the host machine to the container.
The user in the Docker image has the same UID as the user that created the image in the host. 
If the user in use in the host machine has a different UID (which can be found by running the command `id -u` in a terminal), then there may be some problem in managing the files to be created in **plots** and **results**, since Docker does not provide a general way to manage users with different IDs. 

The easiest solution for allowing users with different IDs to write in **plots** and **results** is to make them writable by everyone (through the command `chmod 777 tikz results`) and then use `sudo` when removing their content (as in `sudo rm -r tikz/* results/*`).
If `sudo` cannot be used, then it is better to extract the ZIP archive in **/tmp**, so that the operating system takes care of removing the created files during the periodical cleanup of **/tmp**.

Alternatively, files need to be copied manually with the rta container running in interactive mode, as explained below.


# Running the Docker container in interactive mode and transferring data with the host

To run the rta image in an interactive container, run the following command, inside the **vmcai26-artifact** directory:
```bash
./dockerRunInteractive.sh
```
This will start a container named `rta_container` and offer an interactive Bash shell.

To perform the experiments, simply call `./runExperimentDocker.sh rti.xml` or `./runExperimentDocker.sh rta.xml` for benchmarking FlexFringe or RTA, respectively. 
Additional options can be passed to the `runExperimentDocker.sh` script; see below for more details.

To generate the plots, simply call `./preparePlots.sh`.
This generates the plots, similarly to `dockerPreparePlots.sh`.

Once the operations with the container are completed, use the command `exit` to terminate the container and remove all associated information, including the generated data unless copied to the host before issuing the `exit` command.


## Transferring data from the container to the host

The data generated by the rta container run in interactive mode exists only inside the container. 
To make such data available in the host machine, Docker provides a command to copy data to and from the container.
To copy data generated by BenchExec and the plots, use the following two commands in the host machine while the `rta_container` is running, respectively:
```bash
docker container cp rta_container:/home/ubuntu/results .
docker container cp rta_container:/home/ubuntu/plots .
```

Transferring data to the running rta container is only needed in case one needs to provide the logs from a previous execution when generating the plots.
This can be achieved by one of the following commands:
```bash
docker container cp results rta_container:/home/ubuntu/
docker container cp results/* rta_container:/home/ubuntu/results
```
The first one copies the **results** directory and its content, while the second copies only its content.


# Speeding up the execution time needed by the experiments

To speed up the execution time of the experiments, it is possible to instruct BenchExec to run multiple benchmarks in parallel.
On the machine we used for our experiment, equipped with 12 cores and 16 GB of memory, we were able to run 6 benchmarks in parallel, without having a failure.
To run 6 experiments in parallel, use the option `--numOfThreads 6` when calling  `dockerRunFlexFringe.sh` or `dockerRunRTA.sh`.
Indicatively, the maximum number of benchmarks that can be run in parallel is the minimum between half the number of available CPU cores and the available GB of memory divided by 2.5.


# Running the experiments on machines with asymmetric CPU cores

Modern CPU sometimes have asymmetric CPU cores, where cores run at different maximum speed; 
this can happen for instance on gaming laptops.
When the host machine is equipped with an asymmetric CPU, BenchExec fails with the following message:
```
Asymmetric machine architecture not supported: CPU cores with different number of sibling cores.
```
To make BenchExec work, it needs to be restricted to use only a subset of the available cores.
To recognize them, run the command
```bash
lscpu -e
```
which generates an output similar to
```
CPU NODE SOCKET CORE L1d:L1i:L2:L3 ONLINE    MAXMHZ   MINMHZ       MHZ
  0    0      0    0 0:0:0:0          yes 4700.0000 800.0000 1290.1060
  1    0      0    0 0:0:0:0          yes 4700.0000 800.0000  800.0000
  2    0      0    1 4:4:1:0          yes 4700.0000 800.0000 1327.7280
  3    0      0    1 4:4:1:0          yes 4700.0000 800.0000  971.4940
  4    0      0    2 8:8:2:0          yes 4900.0000 800.0000 1262.1500
  5    0      0    2 8:8:2:0          yes 4900.0000 800.0000  800.0000
  6    0      0    3 12:12:3:0        yes 4900.0000 800.0000  800.0000
  7    0      0    3 12:12:3:0        yes 4900.0000 800.0000  800.0000
  8    0      0    4 16:16:4:0        yes 4700.0000 800.0000  800.0000
  9    0      0    4 16:16:4:0        yes 4700.0000 800.0000  800.0000
 10    0      0    5 20:20:5:0        yes 4700.0000 800.0000 1160.8530
 11    0      0    5 20:20:5:0        yes 4700.0000 800.0000  800.0000
 12    0      0    6 24:24:6:0        yes 3600.0000 800.0000 1494.4310
 13    0      0    7 25:25:6:0        yes 3600.0000 800.0000  913.1030
 14    0      0    8 26:26:6:0        yes 3600.0000 800.0000  800.0000
 15    0      0    9 27:27:6:0        yes 3600.0000 800.0000  800.0000
 16    0      0   10 28:28:7:0        yes 3600.0000 800.0000  800.0760
 17    0      0   11 29:29:7:0        yes 3600.0000 800.0000  800.0000
 18    0      0   12 30:30:7:0        yes 3600.0000 800.0000  800.0000
 19    0      0   13 31:31:7:0        yes 3600.0000 800.0000  800.0000
```
Then, when calling `dockerRunFlexFringe.sh` or `dockerRunRTA.sh`, use the option`--allowedCores` and specify the CPU IDs having the same MAXMHZ, e.g., `--allowedCores=0-3,8-11`.


# How to Use New Input Data for Experiments

Follow these steps to run experiments with your own data.

## Input Format

Create a Python file with your samples in this format:

```python
positive_samples = [
    [('a', 69.4)],                                    # Single event trace
    [('a', 57.2), ('b', 90.8), ('b', 11.7)],         # Multi-event trace
    [('a', 23.2)]
]

negative_samples = [
    [('a', 10.3), ('a', 7.1)],                       # Negative examples
    [('b', 5.2), ('a', 3.6)]
]
```
### Option: Automaton Model
If you have a JSON automaton model, generate samples from it:

```bash
# Generate traces from automaton model
python generate_traces.py your_automaton.json --num-traces 100 -o samples.py

# Generate both Python and CSV formats
python generate_traces.py your_automaton.json --num-traces 100 -o samples.py --csv-output data.csv
```

**JSON automaton format:**
```json
{
  "name": "example_automaton",
  "s": ["q0", "q1", "q2"],
  "sigma": ["a", "b"],
  "init": "q0",
  "accept": ["q2"],
  "tran": {
    "0": ["q0", "a", "[1,2]", "q1"],
    "1": ["q1", "b", "(2,5)", "q2"]
  }
}
```

**Format requirements:**
- Each trace is a list of `(symbol, timestamp)` tuples
- Symbols are strings (e.g., 'a', 'b', 'c', 'd')
- Timestamps are floats in ascending order
- Positive samples should be accepted, negative samples rejected

## Running Experiments

### 1. Basic RTA Construction
```bash
python debug_min3rta.py your_data.py
```
This will build the Min3RTA and verify all samples.

### 2. SMT Encoding and Solving
```bash
python test_encoding.py your_data.py
```
This performs complete SMT-based RTA learning with constraint generation.

## Expected Outputs

Each experiment produces:
- **Console output**: Detailed execution logs and statistics
- **Visualization files**: `.png` and `.dot` files showing automaton structure
- **Performance metrics**: Timing statistics and constraint counts

## Quick Start Example

1. Create `my_experiment.py`:
```python
positive_samples = [
    [('a', 0.2), ('b', 1.5), ('c', 3.2)],
    [('a', 0.5), ('b', 2.1), ('c', 4.0)]
]

negative_samples = [
    [('a', 0.5), ('d', 1.0)],
    [('b', 0.5), ('d', 2.0)]
]
```

2. Run experiment:
```bash
python test_encoding.py my_experiment.py
```

3. Check results in console output and generated visualization files.


# How to Extend RTA

This chapter provides a concise guide on how to extend the `RTA` system for different applications and research purposes. The RTA system is designed with modularity and extensibility in mind, offering multiple extension points.

## 1. System Architecture Overview

The RTA system is composed of several key components that can be extended independently:

- **Core Automaton Classes**: `Min3RTA`, `TDRTA`, `TAPTA`  
- **Encoding Framework**: Encoding class for constraint generation  
- **Visualization System**: Integration with Graphviz and NetworkX  
- **Data Processing Pipeline**: Sample handling, region refinement, optimization  
- **Import/Export Modules**: Export to UPPAAL-compatible XML  

## 2. Extending Core Automaton Classes

### 2.1 Custom Time Region Types
Developers can extend the `TimeRegion` beyond the basic intervals, e.g., adding probabilistic or cost-related properties.

### 2.2 Enhanced State Management
The `State` can be enriched with metadata, invariants, or urgency levels to capture domain-specific requirements.

## 3. Extending the Encoding Framework

### 3.1 Custom Constraint Generators
Additional constraints can be introduced in the `Encoding` to capture specialized requirements, such as timing restrictions.

### 3.2 Multi-Objective Optimization
The encoding can be adapted to support multiple objectives, such as minimizing states and transitions simultaneously.

## 4. Visualization Extensions

### 4.1 Custom Visualizers
New visualization methods can be added to generate interactive or domain-specific outputs, such as `D3.js` or HTML-based formats.

## 5. Data Processing Extensions

### 5.1 Custom Sample Processors
The system can be extended to load samples from additional data formats (e.g., `CSV` or `JSON`).

## 6. Integration Extensions

### 6.1 External Tool Integration
The `RTA` system can be integrated with external model checkers such as `UPPAAL` or `SPIN` for verification.

## 7. Performance Optimization Extensions

### 7.1 Parallel Processing
Large-scale problems can be addressed by extending the framework with multi-core parallelism.

### 7.2 Memory Optimization
Memory efficiency can be improved with caching strategies and batch processing of large datasets.

