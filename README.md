# Cisco CLI Explorer with PyATS

A Python tool that uses PyATS to perform a depth-first search (DFS) of Cisco CLI command trees. It discovers all available CLI commands by recursively using the `?` help feature and stores the results in a Trie data structure.

## Features

- **Depth-First Search**: Systematically explores the entire CLI command tree
- **Trie Data Structure**: Efficiently stores the command hierarchy with descriptions
- **PyATS Integration**: Leverages Cisco's PyATS framework for device connectivity
- **Configurable Exploration**: Control depth limits and command delays
- **JSON Export**: Save and reload command trees for analysis
- **Tree Visualization**: Print the discovered command structure
- **Neo4j Integration**: Load command trees into Neo4j graph database for powerful queries and visualization

## Installation

### Prerequisites

- Python 3.7 or higher
- Access to a Cisco device (physical or virtual)
- Network connectivity to the device
- Neo4j database (optional, for graph database features)

### Setup

1. Clone this repository:
```bash
git clone <repository-url>
cd CiscoCLIExplorer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python explore_cli.py -t testbed.yaml -d router1 -o commands.json
```

### Command Line Options

```
-t, --testbed TESTBED      Path to PyATS testbed YAML file (required)
-d, --device DEVICE        Device name from the testbed (required)
-o, --output OUTPUT        Output JSON file for the command tree (required)
--max-depth DEPTH          Maximum depth to explore (default: 10)
--delay SECONDS            Delay between commands in seconds (default: 0.5)
-v, --verbose              Enable verbose logging
--print-tree               Print the tree structure after exploration
--load-only FILE           Load and display a previously saved tree
```

### Examples

#### Standard Exploration
```bash
python explore_cli.py -t testbed.yaml -d router1 -o commands.json
```

#### Deep Exploration with Custom Settings
```bash
python explore_cli.py -t testbed.yaml -d router1 -o commands.json \
  --max-depth 15 --delay 1.0 -v
```

#### Explore and Display Tree
```bash
python explore_cli.py -t testbed.yaml -d router1 -o commands.json \
  --print-tree
```

#### Load and Display Previously Saved Tree
```bash
python explore_cli.py --load-only commands.json --print-tree
```

## Testbed Configuration

Create a PyATS testbed YAML file to define your device connection. See `testbed_example.yaml` for a template.

### Example Testbed (testbed.yaml)

```yaml
devices:
  router1:
    os: iosxe
    type: router
    connections:
      cli:
        protocol: ssh
        ip: 192.168.1.1
        port: 22
    credentials:
      default:
        username: admin
        password: cisco123
      enable:
        password: enable123
```

### Supported Platforms

The tool should work with any Cisco platform supported by PyATS/Unicon:
- IOS
- IOS-XE
- IOS-XR
- NX-OS
- ASA

## How It Works

### Algorithm

1. **Initialize**: Connect to the device using PyATS
2. **Start DFS**: Begin at the root with the `?` command
3. **Parse Output**: Extract available commands and their descriptions
4. **Build Trie**: Add each command to the Trie structure
5. **Recurse**: For each discovered command, append it to the path and repeat
6. **Track State**: Avoid revisiting the same command paths
7. **Respect Limits**: Stop at the configured maximum depth
8. **Save Results**: Export the Trie to JSON format

### Trie Structure

The Trie (prefix tree) efficiently stores the command hierarchy:

```
ROOT
├── show - Show running system information
│   ├── interfaces - Interface status and configuration
│   │   └── status - Interface line status
│   ├── ip - IP information
│   │   └── route - IP routing table
│   └── version - System hardware and software status
├── configure - Enter configuration mode
│   └── terminal - Configuration from the terminal
└── ping - Send echo messages
```

### Output Format

The JSON output contains:
- **total_commands**: Count of unique command paths
- **tree**: Nested structure with:
  - `token`: The command word
  - `description`: Help text from `?` output
  - `is_end_of_command`: Whether this is a complete command
  - `children`: Nested child commands

## Architecture

### Components

1. **trie.py**: Trie data structure implementation
   - `TrieNode`: Individual node in the tree
   - `CommandTrie`: Complete Trie with save/load functionality

2. **cli_explorer.py**: Core exploration logic
   - `CLIExplorer`: DFS algorithm and command parsing
   - `TestbedCLIExplorer`: Testbed integration wrapper

3. **explore_cli.py**: Main entry point with CLI interface

4. **load_to_neo4j.py**: Neo4j database loader
   - Imports command tree into Neo4j graph database
   - Creates nodes and relationships for graph queries

5. **analyze_tree.py**: Analysis and query utilities
   - Statistics and tree visualization
   - Command search and filtering

## Neo4j Graph Database Integration

The command tree can be loaded into Neo4j for powerful graph-based queries and visualization.

### Prerequisites

- Neo4j database (version 5.0+)
- Running Neo4j instance (local or remote)

### Setup Neo4j

#### Option 1: Docker (Recommended)

```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

#### Option 2: Local Installation

Download and install from [neo4j.com/download](https://neo4j.com/download/)

### Loading Data into Neo4j

```bash
# Basic load
python load_to_neo4j.py -i commands.json --password your_password

# Custom Neo4j instance
python load_to_neo4j.py -i commands.json \
  -u bolt://localhost:7687 \
  --username neo4j \
  --password your_password \
  --database neo4j

# Load without clearing existing data
python load_to_neo4j.py -i commands.json --password your_password --no-clear

# Show sample Cypher queries
python load_to_neo4j.py -i commands.json --password your_password --show-queries
```

### Graph Structure

The Neo4j graph represents the command tree with:

- **Nodes**: Each command token is a node with properties:
  - `token`: The command word
  - `description`: Help text from `?` output
  - `is_end_of_command`: Boolean indicating complete command
  - `depth`: Depth level in the tree
  - `path`: Full command path as string
  - `id`: Unique identifier

- **Relationships**: `HAS_CHILD` relationships connect parent to child commands
  - `order`: Maintains the sequence of children

- **Labels**:
  - `Root`: The root node
  - `Command`: All command nodes (including root)

### Sample Cypher Queries

#### Count all commands
```cypher
MATCH (c:Command)
RETURN count(c) as total_commands
```

#### Find complete commands (executable)
```cypher
MATCH (c:Command {is_end_of_command: true})
RETURN c.path, c.description
ORDER BY c.path
```

#### Search for specific commands
```cypher
MATCH (c:Command)
WHERE c.token CONTAINS 'interface' OR c.description CONTAINS 'interface'
RETURN c.path, c.description
```

#### Get command subtree (e.g., all 'show' commands)
```cypher
MATCH path = (root:Command {token: 'show'})-[:HAS_CHILD*0..3]->(child)
RETURN path
```

#### Find commands at specific depth
```cypher
MATCH (c:Command {depth: 2})
RETURN c.path, c.description
ORDER BY c.path
```

#### Find commands with most children
```cypher
MATCH (parent:Command)-[:HAS_CHILD]->(child)
WITH parent, count(child) as child_count
RETURN parent.path, child_count
ORDER BY child_count DESC
LIMIT 10
```

#### Get full path from root to target command
```cypher
MATCH path = (root:Root)-[:HAS_CHILD*]->(target:Command)
WHERE target.token = 'route'
RETURN path
LIMIT 5
```

#### Find deepest commands
```cypher
MATCH (c:Command)
RETURN c.path, c.depth
ORDER BY c.depth DESC
LIMIT 10
```

### Neo4j Browser

Access the Neo4j Browser at `http://localhost:7474` to:
- Visualize the command graph
- Run Cypher queries interactively
- Explore relationships visually

### Benefits of Neo4j Integration

- **Visual Exploration**: See command relationships graphically
- **Complex Queries**: Use Cypher for advanced pattern matching
- **Relationship Analysis**: Understand command hierarchies
- **Performance**: Indexed queries for fast lookups
- **Integration**: Connect with other graph-based tools

## Configuration Tips

### Max Depth

- **Default (10)**: Suitable for most explorations
- **Shallow (5-7)**: Quick overview, less comprehensive
- **Deep (15-20)**: Thorough exploration, takes longer

### Delay

- **Default (0.5s)**: Balanced speed and device load
- **Fast (0.1-0.3s)**: Quicker exploration, may stress device
- **Slow (1.0-2.0s)**: Gentle on device, takes longer

## Troubleshooting

### Connection Issues

```
Error: Device not found in testbed
```
- Verify device name matches testbed YAML
- Check testbed file path is correct

### Timeout Errors

```
Command timeout: show ?
```
- Increase delay with `--delay 1.0`
- Check network connectivity
- Verify device is responsive

### Incomplete Exploration

- Increase `--max-depth` if commands are truncated
- Some commands may require privileged exec mode
- Check device logs for errors

## Performance Considerations

- Exploration time depends on:
  - CLI complexity (number of commands)
  - Maximum depth setting
  - Delay between commands
  - Network latency

- Typical exploration:
  - **Shallow (depth 5)**: 1-5 minutes
  - **Medium (depth 10)**: 5-15 minutes
  - **Deep (depth 15+)**: 15-60+ minutes

## Use Cases

- **Documentation**: Auto-generate CLI command references
- **Training**: Understand available commands on new platforms
- **Automation**: Discover commands for scripting
- **Comparison**: Compare CLI across different OS versions
- **Validation**: Verify command availability after upgrades

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please submit pull requests or open issues for bugs and feature requests.

## Acknowledgments

Built with [Cisco PyATS](https://developer.cisco.com/pyats/) framework.
