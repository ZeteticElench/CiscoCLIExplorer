"""
Trie data structure for storing CLI command tree.
"""
import json
from typing import Dict, Optional, List


class TrieNode:
    """Node in the Trie structure representing a CLI command or token."""

    def __init__(self, token: str = "", description: str = ""):
        """
        Initialize a Trie node.

        Args:
            token: The command token (word)
            description: Description from the ? help output
        """
        self.token = token
        self.description = description
        self.children: Dict[str, 'TrieNode'] = {}
        self.is_end_of_command = False

    def add_child(self, token: str, description: str = "") -> 'TrieNode':
        """
        Add a child node or return existing one.

        Args:
            token: The command token to add
            description: Description of the token

        Returns:
            The child TrieNode
        """
        if token not in self.children:
            self.children[token] = TrieNode(token, description)
        elif description and not self.children[token].description:
            # Update description if it was empty
            self.children[token].description = description
        return self.children[token]

    def to_dict(self) -> dict:
        """
        Convert the node and its children to a dictionary.

        Returns:
            Dictionary representation of the node
        """
        return {
            "token": self.token,
            "description": self.description,
            "is_end_of_command": self.is_end_of_command,
            "children": {k: v.to_dict() for k, v in self.children.items()}
        }


class CommandTrie:
    """Trie structure for storing and navigating CLI command trees."""

    def __init__(self):
        """Initialize an empty command Trie."""
        self.root = TrieNode("ROOT", "Root of command tree")
        self.total_commands = 0

    def add_command(self, command_path: List[str], descriptions: List[str]):
        """
        Add a command path to the Trie.

        Args:
            command_path: List of tokens forming the command path
            descriptions: List of descriptions for each token
        """
        current = self.root

        # Ensure descriptions list matches command_path length
        while len(descriptions) < len(command_path):
            descriptions.append("")

        for token, desc in zip(command_path, descriptions):
            current = current.add_child(token, desc)

        if not current.is_end_of_command:
            current.is_end_of_command = True
            self.total_commands += 1

    def get_node(self, command_path: List[str]) -> Optional[TrieNode]:
        """
        Get a node at a specific command path.

        Args:
            command_path: List of tokens forming the path

        Returns:
            The TrieNode at the path, or None if not found
        """
        current = self.root
        for token in command_path:
            if token not in current.children:
                return None
            current = current.children[token]
        return current

    def get_children_at_path(self, command_path: List[str]) -> Dict[str, str]:
        """
        Get all children tokens and descriptions at a given path.

        Args:
            command_path: List of tokens forming the path

        Returns:
            Dictionary mapping token to description
        """
        node = self.get_node(command_path)
        if node is None:
            return {}
        return {token: child.description for token, child in node.children.items()}

    def to_dict(self) -> dict:
        """
        Convert the entire Trie to a dictionary.

        Returns:
            Dictionary representation of the Trie
        """
        return {
            "total_commands": self.total_commands,
            "tree": self.root.to_dict()
        }

    def save_to_file(self, filename: str):
        """
        Save the Trie to a JSON file.

        Args:
            filename: Path to the output file
        """
        with open(filename, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_file(cls, filename: str) -> 'CommandTrie':
        """
        Load a Trie from a JSON file.

        Args:
            filename: Path to the input file

        Returns:
            CommandTrie instance
        """
        with open(filename, 'r') as f:
            data = json.load(f)

        trie = cls()
        trie.total_commands = data.get("total_commands", 0)
        trie.root = cls._dict_to_node(data["tree"])
        return trie

    @staticmethod
    def _dict_to_node(data: dict) -> TrieNode:
        """
        Convert a dictionary back to a TrieNode.

        Args:
            data: Dictionary representation of a node

        Returns:
            TrieNode instance
        """
        node = TrieNode(data["token"], data["description"])
        node.is_end_of_command = data["is_end_of_command"]
        node.children = {k: CommandTrie._dict_to_node(v)
                        for k, v in data["children"].items()}
        return node

    def print_tree(self, node: Optional[TrieNode] = None, prefix: str = "", is_last: bool = True):
        """
        Print the tree structure in a readable format.

        Args:
            node: Starting node (default: root)
            prefix: Prefix for tree drawing
            is_last: Whether this is the last child
        """
        if node is None:
            node = self.root

        if node != self.root:
            connector = "└── " if is_last else "├── "
            desc_text = f" - {node.description}" if node.description else ""
            end_marker = " [END]" if node.is_end_of_command else ""
            print(f"{prefix}{connector}{node.token}{desc_text}{end_marker}")

        children = list(node.children.values())
        for i, child in enumerate(children):
            is_last_child = (i == len(children) - 1)
            if node == self.root:
                new_prefix = prefix
            else:
                new_prefix = prefix + ("    " if is_last else "│   ")
            self.print_tree(child, new_prefix, is_last_child)
