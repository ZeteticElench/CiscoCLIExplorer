#!/usr/bin/env python3
"""
Main script for exploring Cisco CLI command tree using PyATS.

This script performs a depth-first search of the CLI command tree,
starting with ? and building a Trie structure with all discovered commands.
"""
import argparse
import logging
import sys
from cli_explorer import TestbedCLIExplorer
from trie import CommandTrie


def setup_logging(verbose: bool = False):
    """
    Setup logging configuration.

    Args:
        verbose: Enable verbose (DEBUG) logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Explore Cisco CLI command tree using PyATS and build a Trie structure',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic exploration with default depth
  %(prog)s -t testbed.yaml -d router1 -o commands.json

  # Deep exploration with custom depth and delay
  %(prog)s -t testbed.yaml -d router1 -o commands.json --max-depth 15 --delay 1.0

  # Verbose logging
  %(prog)s -t testbed.yaml -d router1 -o commands.json -v

  # Print the tree after exploration
  %(prog)s -t testbed.yaml -d router1 -o commands.json --print-tree
        """
    )

    parser.add_argument(
        '-t', '--testbed',
        required=True,
        help='Path to PyATS testbed YAML file'
    )

    parser.add_argument(
        '-d', '--device',
        required=True,
        help='Device name from the testbed'
    )

    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output JSON file for the command tree'
    )

    parser.add_argument(
        '--max-depth',
        type=int,
        default=10,
        help='Maximum depth to explore (default: 10)'
    )

    parser.add_argument(
        '--delay',
        type=float,
        default=0.5,
        help='Delay between commands in seconds (default: 0.5)'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    parser.add_argument(
        '--print-tree',
        action='store_true',
        help='Print the tree structure after exploration'
    )

    parser.add_argument(
        '--load-only',
        type=str,
        metavar='FILE',
        help='Load and display a previously saved tree (skips exploration)'
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    try:
        if args.load_only:
            # Just load and display a saved tree
            logger.info(f"Loading tree from: {args.load_only}")
            trie = CommandTrie.load_from_file(args.load_only)
            logger.info(f"Loaded tree with {trie.total_commands} commands")

            if args.print_tree:
                print("\n" + "="*80)
                print("COMMAND TREE STRUCTURE")
                print("="*80)
                trie.print_tree()

        else:
            # Perform exploration
            logger.info("="*80)
            logger.info("Cisco CLI Explorer - PyATS DFS")
            logger.info("="*80)
            logger.info(f"Testbed: {args.testbed}")
            logger.info(f"Device: {args.device}")
            logger.info(f"Output: {args.output}")
            logger.info(f"Max Depth: {args.max_depth}")
            logger.info(f"Delay: {args.delay}s")
            logger.info("="*80)

            # Create explorer and run
            explorer = TestbedCLIExplorer(
                testbed_file=args.testbed,
                device_name=args.device,
                max_depth=args.max_depth,
                delay=args.delay
            )

            trie = explorer.explore(output_file=args.output)

            logger.info("="*80)
            logger.info("EXPLORATION COMPLETE")
            logger.info("="*80)
            logger.info(f"Total commands discovered: {trie.total_commands}")
            logger.info(f"Output saved to: {args.output}")

            if args.print_tree:
                print("\n" + "="*80)
                print("COMMAND TREE STRUCTURE")
                print("="*80)
                trie.print_tree()

        return 0

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    except KeyError as e:
        logger.error(f"Device not found in testbed: {e}")
        return 1
    except Exception as e:
        logger.error(f"Error during exploration: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
