#!/usr/bin/env python3
"""
Load CLI command tree from JSON into Neo4j graph database.
"""
import argparse
import sys
import logging
from typing import Optional
from neo4j import GraphDatabase
from trie import CommandTrie, TrieNode


logger = logging.getLogger(__name__)


class Neo4jLoader:
    """Load command tree into Neo4j database."""

    def __init__(self, uri: str, username: str, password: str, database: str = "neo4j"):
        """
        Initialize Neo4j connection.

        Args:
            uri: Neo4j connection URI (e.g., bolt://localhost:7687)
            username: Neo4j username
            password: Neo4j password
            database: Database name (default: neo4j)
        """
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        self.database = database
        self.nodes_created = 0
        self.relationships_created = 0

    def close(self):
        """Close the Neo4j driver."""
        if self.driver:
            self.driver.close()

    def verify_connection(self) -> bool:
        """
        Verify connection to Neo4j.

        Returns:
            True if connected successfully
        """
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run("RETURN 1 AS test")
                return result.single()["test"] == 1
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            return False

    def clear_database(self):
        """Clear all nodes and relationships from the database."""
        with self.driver.session(database=self.database) as session:
            logger.info("Clearing existing data from Neo4j...")

            # Delete all relationships and nodes
            session.run("MATCH (n:Command) DETACH DELETE n")
            session.run("MATCH (n:Root) DETACH DELETE n")

            logger.info("Database cleared")

    def create_indexes(self):
        """Create indexes for better query performance."""
        with self.driver.session(database=self.database) as session:
            logger.info("Creating indexes...")

            # Create index on token for faster lookups
            try:
                session.run("CREATE INDEX command_token IF NOT EXISTS FOR (c:Command) ON (c.token)")
                logger.info("Created index on Command.token")
            except Exception as e:
                logger.warning(f"Index creation warning: {e}")

            # Create index on path for faster path queries
            try:
                session.run("CREATE INDEX command_path IF NOT EXISTS FOR (c:Command) ON (c.path)")
                logger.info("Created index on Command.path")
            except Exception as e:
                logger.warning(f"Index creation warning: {e}")

    def create_node(self, tx, node_id: str, token: str, description: str,
                   is_end: bool, depth: int, path: str, is_root: bool = False):
        """
        Create a command node in Neo4j.

        Args:
            tx: Neo4j transaction
            node_id: Unique node identifier
            token: Command token
            description: Command description
            is_end: Whether this is a complete command
            depth: Depth in the tree
            path: Full command path
            is_root: Whether this is the root node
        """
        if is_root:
            query = """
            CREATE (n:Root:Command {
                id: $id,
                token: $token,
                description: $description,
                is_end_of_command: $is_end,
                depth: $depth,
                path: $path
            })
            RETURN n
            """
        else:
            query = """
            CREATE (n:Command {
                id: $id,
                token: $token,
                description: $description,
                is_end_of_command: $is_end,
                depth: $depth,
                path: $path
            })
            RETURN n
            """

        tx.run(query,
               id=node_id,
               token=token,
               description=description,
               is_end=is_end,
               depth=depth,
               path=path)

        self.nodes_created += 1

    def create_relationship(self, tx, parent_id: str, child_id: str, order: int):
        """
        Create a HAS_CHILD relationship between nodes.

        Args:
            tx: Neo4j transaction
            parent_id: Parent node ID
            child_id: Child node ID
            order: Order of the child (for maintaining sequence)
        """
        query = """
        MATCH (parent:Command {id: $parent_id})
        MATCH (child:Command {id: $child_id})
        CREATE (parent)-[r:HAS_CHILD {order: $order}]->(child)
        RETURN r
        """

        tx.run(query, parent_id=parent_id, child_id=child_id, order=order)
        self.relationships_created += 1

    def load_trie_node(self, tx, node: TrieNode, parent_id: Optional[str] = None,
                      path: list = None, depth: int = 0):
        """
        Recursively load a Trie node and its children into Neo4j.

        Args:
            tx: Neo4j transaction
            node: TrieNode to load
            parent_id: ID of parent node
            path: Current command path
            depth: Current depth
        """
        if path is None:
            path = []

        # Generate unique node ID
        if parent_id is None:
            node_id = "ROOT"
            is_root = True
        else:
            node_id = "_".join(path) if path else node.token
            is_root = False

        # Create full path string
        path_str = " ".join(path) if path else "ROOT"

        # Create the node
        self.create_node(
            tx,
            node_id=node_id,
            token=node.token,
            description=node.description,
            is_end=node.is_end_of_command,
            depth=depth,
            path=path_str,
            is_root=is_root
        )

        # Create relationship from parent (if not root)
        if parent_id is not None:
            self.create_relationship(tx, parent_id, node_id, order=len(path) - 1)

        # Recursively process children
        for order, (token, child) in enumerate(sorted(node.children.items())):
            child_path = path + [child.token]
            self.load_trie_node(tx, child, node_id, child_path, depth + 1)

    def load_from_trie(self, trie: CommandTrie, clear_existing: bool = True):
        """
        Load entire Trie into Neo4j.

        Args:
            trie: CommandTrie to load
            clear_existing: Whether to clear existing data first
        """
        logger.info("Starting Neo4j data load...")

        if clear_existing:
            self.clear_database()

        with self.driver.session(database=self.database) as session:
            # Load the tree in a single transaction
            logger.info("Creating nodes and relationships...")
            session.execute_write(self.load_trie_node, trie.root)

        # Create indexes after loading
        self.create_indexes()

        logger.info(f"Load complete: {self.nodes_created} nodes, {self.relationships_created} relationships")

    def print_sample_queries(self):
        """Print useful Cypher queries for exploring the data."""
        print("\n" + "="*80)
        print("SAMPLE NEO4J CYPHER QUERIES")
        print("="*80)
        print("""
1. Count total commands:
   MATCH (c:Command) RETURN count(c) as total_commands

2. Count complete commands:
   MATCH (c:Command {is_end_of_command: true})
   RETURN count(c) as complete_commands

3. Find all commands at depth 2:
   MATCH (c:Command {depth: 2})
   RETURN c.path, c.description

4. Search for commands containing 'interface':
   MATCH (c:Command)
   WHERE c.token CONTAINS 'interface' OR c.description CONTAINS 'interface'
   RETURN c.path, c.description

5. Get command tree starting from 'show':
   MATCH path = (root:Command {token: 'show'})-[:HAS_CHILD*0..3]->(child)
   RETURN path

6. Find deepest commands:
   MATCH (c:Command)
   RETURN c.path, c.depth
   ORDER BY c.depth DESC
   LIMIT 10

7. Find commands with most children:
   MATCH (parent:Command)-[:HAS_CHILD]->(child)
   WITH parent, count(child) as child_count
   RETURN parent.path, child_count
   ORDER BY child_count DESC
   LIMIT 10

8. Get full path from root to a specific command:
   MATCH path = (root:Root)-[:HAS_CHILD*]->(target:Command)
   WHERE target.token = 'route'
   RETURN path
   LIMIT 5

9. Find all complete commands (endpoints):
   MATCH (c:Command {is_end_of_command: true})
   RETURN c.path, c.description
   ORDER BY c.path

10. Visualize command subtree:
    MATCH path = (root:Command {token: 'show'})-[:HAS_CHILD*0..2]->(child)
    RETURN path
        """)
        print("="*80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Load CLI command tree into Neo4j graph database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Load with default settings
  %(prog)s -i commands.json -u bolt://localhost:7687 --username neo4j --password password

  # Load without clearing existing data
  %(prog)s -i commands.json -u bolt://localhost:7687 --username neo4j --password password --no-clear

  # Show sample queries after loading
  %(prog)s -i commands.json -u bolt://localhost:7687 --username neo4j --password password --show-queries
        """
    )

    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input JSON file containing the command tree'
    )

    parser.add_argument(
        '-u', '--uri',
        default='bolt://localhost:7687',
        help='Neo4j connection URI (default: bolt://localhost:7687)'
    )

    parser.add_argument(
        '--username',
        default='neo4j',
        help='Neo4j username (default: neo4j)'
    )

    parser.add_argument(
        '--password',
        required=True,
        help='Neo4j password'
    )

    parser.add_argument(
        '--database',
        default='neo4j',
        help='Neo4j database name (default: neo4j)'
    )

    parser.add_argument(
        '--no-clear',
        action='store_true',
        help='Do not clear existing data before loading'
    )

    parser.add_argument(
        '--show-queries',
        action='store_true',
        help='Show sample Cypher queries after loading'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    loader = None
    try:
        # Load the command tree
        logger.info(f"Loading command tree from: {args.input}")
        trie = CommandTrie.load_from_file(args.input)
        logger.info(f"Loaded tree with {trie.total_commands} commands")

        # Connect to Neo4j
        logger.info(f"Connecting to Neo4j at {args.uri}")
        loader = Neo4jLoader(args.uri, args.username, args.password, args.database)

        # Verify connection
        if not loader.verify_connection():
            logger.error("Failed to connect to Neo4j. Please check connection settings.")
            return 1

        logger.info("Successfully connected to Neo4j")

        # Load data
        loader.load_from_trie(trie, clear_existing=not args.no_clear)

        logger.info("="*80)
        logger.info("LOAD COMPLETE")
        logger.info("="*80)
        logger.info(f"Nodes created: {loader.nodes_created}")
        logger.info(f"Relationships created: {loader.relationships_created}")
        logger.info("="*80)

        if args.show_queries:
            loader.print_sample_queries()

        return 0

    except FileNotFoundError:
        logger.error(f"File not found: {args.input}")
        return 1
    except Exception as e:
        logger.error(f"Error loading data into Neo4j: {e}", exc_info=True)
        return 1
    finally:
        if loader:
            loader.close()


if __name__ == '__main__':
    sys.exit(main())
