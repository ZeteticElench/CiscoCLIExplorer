#!/usr/bin/env python3
"""
Utility script to analyze and query saved CLI command trees.
"""
import argparse
import sys
from trie import CommandTrie


def print_statistics(trie: CommandTrie):
    """Print statistics about the command tree."""
    print("\n" + "="*80)
    print("COMMAND TREE STATISTICS")
    print("="*80)
    print(f"Total commands: {trie.total_commands}")

    # Calculate depth
    max_depth = calculate_max_depth(trie.root)
    print(f"Maximum depth: {max_depth}")

    # Count nodes
    total_nodes = count_nodes(trie.root)
    print(f"Total nodes: {total_nodes}")

    # Average children per node
    avg_children = calculate_avg_children(trie.root)
    print(f"Average children per node: {avg_children:.2f}")

    print("="*80)


def calculate_max_depth(node, depth=0):
    """Calculate the maximum depth of the tree."""
    if not node.children:
        return depth

    return max(calculate_max_depth(child, depth + 1)
               for child in node.children.values())


def count_nodes(node):
    """Count total number of nodes in the tree."""
    count = 1
    for child in node.children.values():
        count += count_nodes(child)
    return count


def calculate_avg_children(node):
    """Calculate average number of children per node."""
    total_children = 0
    total_nodes = 0

    def traverse(n):
        nonlocal total_children, total_nodes
        total_nodes += 1
        total_children += len(n.children)
        for child in n.children.values():
            traverse(child)

    traverse(node)

    return total_children / total_nodes if total_nodes > 0 else 0


def search_commands(trie: CommandTrie, query: str):
    """Search for commands matching a query."""
    query_lower = query.lower()
    matches = []

    def traverse(node, path):
        # Check if current token matches
        if query_lower in node.token.lower():
            matches.append((path + [node.token], node.description))

        # Traverse children
        for child in node.children.values():
            traverse(child, path + [node.token] if node.token else path)

    traverse(trie.root, [])

    if matches:
        print("\n" + "="*80)
        print(f"SEARCH RESULTS FOR: '{query}'")
        print("="*80)
        for path, desc in matches:
            command = ' '.join(path)
            if desc:
                print(f"{command}")
                print(f"  Description: {desc}")
            else:
                print(f"{command}")
        print(f"\nFound {len(matches)} matching commands")
        print("="*80)
    else:
        print(f"\nNo commands found matching '{query}'")


def list_commands_at_depth(trie: CommandTrie, depth: int):
    """List all commands at a specific depth."""
    commands = []

    def traverse(node, path, current_depth):
        if current_depth == depth:
            commands.append((path, node.description))
            return

        for child in node.children.values():
            new_path = path + [child.token]
            traverse(child, new_path, current_depth + 1)

    traverse(trie.root, [], 0)

    if commands:
        print("\n" + "="*80)
        print(f"COMMANDS AT DEPTH {depth}")
        print("="*80)
        for path, desc in sorted(commands):
            command = ' '.join(path)
            if desc:
                print(f"{command}")
                print(f"  Description: {desc}")
            else:
                print(f"{command}")
        print(f"\nTotal: {len(commands)} commands at depth {depth}")
        print("="*80)
    else:
        print(f"\nNo commands found at depth {depth}")


def get_command_path(trie: CommandTrie, command: str):
    """Get details about a specific command path."""
    tokens = command.split()
    node = trie.get_node(tokens)

    if node:
        print("\n" + "="*80)
        print(f"COMMAND DETAILS: {command}")
        print("="*80)
        print(f"Token: {node.token}")
        print(f"Description: {node.description}")
        print(f"Is complete command: {node.is_end_of_command}")
        print(f"Number of children: {len(node.children)}")

        if node.children:
            print("\nAvailable sub-commands:")
            for token, child in sorted(node.children.items()):
                if child.description:
                    print(f"  {token} - {child.description}")
                else:
                    print(f"  {token}")
        print("="*80)
    else:
        print(f"\nCommand path '{command}' not found in tree")


def export_text(trie: CommandTrie, output_file: str):
    """Export all commands to a text file."""
    commands = []

    def traverse(node, path):
        if node.is_end_of_command and path:
            command = ' '.join(path)
            commands.append((command, node.description))

        for child in node.children.values():
            new_path = path + [child.token]
            traverse(child, new_path)

    traverse(trie.root, [])

    with open(output_file, 'w') as f:
        f.write("CLI Command Reference\n")
        f.write("=" * 80 + "\n\n")

        for command, desc in sorted(commands):
            f.write(f"{command}\n")
            if desc:
                f.write(f"  {desc}\n")
            f.write("\n")

    print(f"\nExported {len(commands)} commands to {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Analyze and query CLI command trees',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show statistics
  %(prog)s commands.json --stats

  # Print the tree
  %(prog)s commands.json --print-tree

  # Search for commands
  %(prog)s commands.json --search interface

  # List commands at specific depth
  %(prog)s commands.json --depth 3

  # Get details about a command
  %(prog)s commands.json --command "show ip route"

  # Export to text file
  %(prog)s commands.json --export-text commands.txt
        """
    )

    parser.add_argument(
        'input_file',
        help='Input JSON file containing the command tree'
    )

    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show statistics about the tree'
    )

    parser.add_argument(
        '--print-tree',
        action='store_true',
        help='Print the entire tree structure'
    )

    parser.add_argument(
        '--search',
        metavar='QUERY',
        help='Search for commands containing the query string'
    )

    parser.add_argument(
        '--depth',
        type=int,
        metavar='N',
        help='List all commands at depth N'
    )

    parser.add_argument(
        '--command',
        metavar='CMD',
        help='Get details about a specific command path'
    )

    parser.add_argument(
        '--export-text',
        metavar='FILE',
        help='Export all commands to a text file'
    )

    args = parser.parse_args()

    # Load the tree
    try:
        print(f"Loading command tree from: {args.input_file}")
        trie = CommandTrie.load_from_file(args.input_file)
        print(f"Loaded tree with {trie.total_commands} commands\n")

        # Execute requested operations
        if args.stats:
            print_statistics(trie)

        if args.print_tree:
            print("\n" + "="*80)
            print("COMMAND TREE STRUCTURE")
            print("="*80)
            trie.print_tree()

        if args.search:
            search_commands(trie, args.search)

        if args.depth is not None:
            list_commands_at_depth(trie, args.depth)

        if args.command:
            get_command_path(trie, args.command)

        if args.export_text:
            export_text(trie, args.export_text)

        # If no operation specified, show stats
        if not any([args.stats, args.print_tree, args.search,
                   args.depth is not None, args.command, args.export_text]):
            print_statistics(trie)

        return 0

    except FileNotFoundError:
        print(f"Error: File '{args.input_file}' not found")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
