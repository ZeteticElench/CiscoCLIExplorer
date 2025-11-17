# Cisco CLI Explorer with PyATS

A Python tool that uses PyATS to perform a depth-first search (DFS) of Cisco CLI command trees. It discovers all available CLI commands by recursively using the `?` help feature and stores the results in a Trie data structure.

## Features

- **Depth-First Search**: Systematically explores the entire CLI command tree
- **Trie Data Structure**: Efficiently stores the command hierarchy with descriptions
- **PyATS Integration**: Leverages Cisco's PyATS framework for device connectivity
- **Configurable Exploration**: Control depth limits and command delays
- **JSON Export**: Save and reload command trees for analysis
- **Tree Visualization**: Print the discovered command structure

## Installation

### Prerequisites

- Python 3.7 or higher
- Access to a Cisco device (physical or virtual)
- Network connectivity to the device

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
