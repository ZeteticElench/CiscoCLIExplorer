"""
CLI Explorer using PyATS to perform depth-first search of CLI command tree.
"""
import re
import time
import logging
from typing import List, Dict, Optional, Tuple
from pyats.topology import loader
from unicon.core.errors import SubCommandFailure, TimeoutError as UniconTimeoutError
from trie import CommandTrie


logger = logging.getLogger(__name__)


class CLIExplorer:
    """Explores CLI command tree using depth-first search via PyATS."""

    def __init__(self, device, max_depth: int = 10, delay: float = 0.5):
        """
        Initialize the CLI Explorer.

        Args:
            device: PyATS device object
            max_depth: Maximum depth to explore in the command tree
            delay: Delay between commands in seconds
        """
        self.device = device
        self.max_depth = max_depth
        self.delay = delay
        self.trie = CommandTrie()
        self.visited_paths = set()
        self.command_count = 0

    def parse_help_output(self, output: str) -> Dict[str, str]:
        """
        Parse the output of the ? command to extract commands and descriptions.

        Args:
            output: Raw output from ? command

        Returns:
            Dictionary mapping command token to description
        """
        commands = {}

        # Remove ANSI escape sequences
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        output = ansi_escape.sub('', output)

        # Split into lines and process
        lines = output.split('\n')

        for line in lines:
            line = line.strip()

            # Skip empty lines and common prompts
            if not line or line.startswith('#') or line.startswith('?'):
                continue

            # Common patterns for Cisco help output:
            # 1. "command    Description text"
            # 2. "  command  Description text"
            # 3. "command"

            # Try to split by multiple spaces (common Cisco format)
            parts = re.split(r'\s{2,}', line, maxsplit=1)

            if len(parts) >= 2:
                command = parts[0].strip()
                description = parts[1].strip()
            elif len(parts) == 1:
                command = parts[0].strip()
                description = ""
            else:
                continue

            # Filter out invalid command tokens
            if command and not command.startswith('<') and command != '^':
                # Handle special characters and keywords
                if command in ['<cr>', 'CR', '|']:
                    continue
                commands[command] = description

        return commands

    def execute_help_command(self, command_path: List[str]) -> Optional[str]:
        """
        Execute a help command (command path + ?) on the device.

        Args:
            command_path: List of command tokens forming the path

        Returns:
            Output from the help command, or None if failed
        """
        # Build the command string
        if command_path:
            command = ' '.join(command_path) + ' ?'
        else:
            command = '?'

        try:
            logger.info(f"Executing: {command}")

            # Send the command
            output = self.device.execute(command, timeout=30)

            # Add delay to avoid overwhelming the device
            time.sleep(self.delay)

            return output

        except SubCommandFailure as e:
            logger.warning(f"Command failed: {command} - {str(e)}")
            return None
        except UniconTimeoutError as e:
            logger.warning(f"Command timeout: {command} - {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error executing {command}: {str(e)}")
            return None

    def dfs_explore(self, command_path: List[str] = None, depth: int = 0):
        """
        Perform depth-first search of the CLI command tree.

        Args:
            command_path: Current command path (list of tokens)
            depth: Current depth in the tree
        """
        if command_path is None:
            command_path = []

        # Check depth limit
        if depth > self.max_depth:
            logger.info(f"Max depth reached at: {' '.join(command_path)}")
            return

        # Create a hashable version of the path for visited tracking
        path_key = tuple(command_path)
        if path_key in self.visited_paths:
            logger.debug(f"Already visited: {' '.join(command_path)}")
            return

        self.visited_paths.add(path_key)

        # Execute help command
        output = self.execute_help_command(command_path)
        if output is None:
            return

        # Parse the help output
        commands = self.parse_help_output(output)

        if not commands:
            logger.debug(f"No commands found at: {' '.join(command_path)}")
            return

        logger.info(f"Found {len(commands)} options at depth {depth}: {' '.join(command_path)}")

        # Add current path to trie with descriptions
        descriptions = []
        for token in command_path:
            # We'll get the description from parent exploration
            descriptions.append("")

        if command_path:
            self.trie.add_command(command_path, descriptions)

        # Explore each child command (depth-first)
        for cmd_token, description in sorted(commands.items()):
            new_path = command_path + [cmd_token]

            # Add this node to trie with its description
            self.trie.add_command(new_path, descriptions + [description])
            self.command_count += 1

            logger.info(f"Exploring: {' '.join(new_path)}")

            # Recursively explore this branch
            self.dfs_explore(new_path, depth + 1)

    def explore(self) -> CommandTrie:
        """
        Start the exploration from the root.

        Returns:
            The populated CommandTrie
        """
        logger.info("Starting CLI exploration...")
        logger.info(f"Max depth: {self.max_depth}, Delay: {self.delay}s")

        start_time = time.time()

        # Start DFS from root
        self.dfs_explore([], 0)

        elapsed_time = time.time() - start_time

        logger.info(f"Exploration complete!")
        logger.info(f"Total unique command paths discovered: {self.command_count}")
        logger.info(f"Total paths in trie: {self.trie.total_commands}")
        logger.info(f"Time elapsed: {elapsed_time:.2f} seconds")

        return self.trie


class TestbedCLIExplorer:
    """High-level interface for exploring CLI using a PyATS testbed."""

    def __init__(self, testbed_file: str, device_name: str,
                 max_depth: int = 10, delay: float = 0.5):
        """
        Initialize the testbed-based CLI explorer.

        Args:
            testbed_file: Path to PyATS testbed YAML file
            device_name: Name of the device in the testbed
            max_depth: Maximum depth to explore
            delay: Delay between commands in seconds
        """
        self.testbed_file = testbed_file
        self.device_name = device_name
        self.max_depth = max_depth
        self.delay = delay
        self.testbed = None
        self.device = None

    def connect(self):
        """Connect to the device."""
        logger.info(f"Loading testbed from: {self.testbed_file}")
        self.testbed = loader.load(self.testbed_file)

        logger.info(f"Connecting to device: {self.device_name}")
        self.device = self.testbed.devices[self.device_name]
        self.device.connect(log_stdout=False)

        logger.info(f"Connected to {self.device_name}")

    def disconnect(self):
        """Disconnect from the device."""
        if self.device:
            logger.info(f"Disconnecting from {self.device_name}")
            self.device.disconnect()

    def explore(self, output_file: Optional[str] = None) -> CommandTrie:
        """
        Connect, explore, and optionally save results.

        Args:
            output_file: Optional path to save the trie JSON

        Returns:
            The populated CommandTrie
        """
        try:
            self.connect()

            explorer = CLIExplorer(self.device, self.max_depth, self.delay)
            trie = explorer.explore()

            if output_file:
                logger.info(f"Saving results to: {output_file}")
                trie.save_to_file(output_file)

            return trie

        finally:
            self.disconnect()
