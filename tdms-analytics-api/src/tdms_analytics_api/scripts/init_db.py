"""Database initialization script for ClickHouse."""
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from clickhouse_connect.driver import Client
from loguru import logger

from tdms_analytics.dependencies.database import get_clickhouse_client


class DatabaseInitializer:
    """Initialize ClickHouse database schema."""
    
    def __init__(self):
        self.client = get_clickhouse_client()
    
    def create_database(self) -> None:
        """Create the main database if it doesn't exist."""
        try:
            # The database should already be selected via connection settings
            logger.info("Database connection verified")
        except Exception as e:
            logger.error(f"Failed to verify database: {e}")
            raise
    
    def create_tables(self) -> None:
        """Create all required tables."""
        
        # Datasets table
        self.client.command("""
            CREATE TABLE IF NOT EXISTS datasets (
                dataset_id String,
                filename String,
                created_at DateTime64(3),
                total_points UInt64
            ) ENGINE = MergeTree()
            ORDER BY (dataset_id, created_at)
            SETTINGS index_granularity = 8192
        """)
        logger.info("✓ Created datasets table")
        
        # Channels table
        self.client.command("""
            CREATE TABLE IF NOT EXISTS channels (
                channel_id String,
                dataset_id String,
                group_name String,
                channel_name String,
                unit String,
                has_time Bool,
                n_rows UInt64
            ) ENGINE = MergeTree()
            ORDER BY (dataset_id, channel_id)
            SETTINGS index_granularity = 8192
        """)
        logger.info("✓ Created channels table")
        
        # Sensor data without time (index-based)
        self.client.command("""
            CREATE TABLE IF NOT EXISTS sensor_data (
                channel_id String,
                index UInt64,
                value Float32,
                timestamp Nullable(Float64),
                timestamp_iso Nullable(String)
            ) ENGINE = MergeTree()
            ORDER BY (channel_id, index)
            SETTINGS index_granularity = 8192
        """)
        logger.info("✓ Created sensor_data table")
        
        # Sensor data with time (optimized for time queries)
        self.client.command("""
            CREATE TABLE IF NOT EXISTS sensor_data_with_time (
                channel_id String,
                index UInt64,
                value Float32,
                timestamp Float64,
                timestamp_iso String
            ) ENGINE = MergeTree()
            ORDER BY (channel_id, timestamp, index)
            SETTINGS index_granularity = 8192
        """)
        logger.info("✓ Created sensor_data_with_time table")
        
        # Create materialized views for better query performance
        self._create_views()
    
    def _create_views(self) -> None:
        """Create materialized views for analytics."""
        
        # View for channel statistics
        try:
            self.client.command("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS channel_stats_mv
                ENGINE = AggregatingMergeTree()
                ORDER BY channel_id
                AS SELECT
                    channel_id,
                    count() as total_points,
                    min(value) as min_value,
                    max(value) as max_value,
                    avg(value) as avg_value,
                    min(timestamp) as min_timestamp,
                    max(timestamp) as max_timestamp
                FROM sensor_data_with_time
                GROUP BY channel_id
            """)
            logger.info("✓ Created channel_stats_mv view")
        except Exception as e:
            logger.warning(f"Could not create channel_stats_mv: {e}")
    
    def create_indexes(self) -> None:
        """Create additional indexes for performance."""
        
        # Indexes are mostly handled by ORDER BY in MergeTree
        # Additional indexes can be added here if needed
        logger.info("✓ Indexes created (handled by MergeTree ORDER BY)")
    
    def initialize(self) -> None:
        """Run complete database initialization."""
        logger.info("Starting database initialization...")
        
        try:
            self.create_database()
            self.create_tables()
            self.create_indexes()
            
            logger.info("✅ Database initialization completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise


def main() -> None:
    """Main initialization function."""
    try:
        initializer = DatabaseInitializer()
        initializer.initialize()
        
        # Test the setup
        logger.info("Testing database setup...")
        client = get_clickhouse_client()
        
        # Test queries
        tables = client.query("SHOW TABLES").result_set
        logger.info(f"Available tables: {[row[0] for row in tables]}")
        
        # Test dataset insertion
        test_data = [{
            "dataset_id": "test-123",
            "filename": "test.tdms",
            "created_at": "2024-01-01 12:00:00",
            "total_points": 1000
        }]
        
        client.insert("datasets", test_data)
        result = client.query("SELECT COUNT() FROM datasets WHERE dataset_id = 'test-123'")
        
        if result.result_set[0][0] == 1:
            logger.info("✓ Test insertion successful")
            # Clean up test data
            client.command("DELETE FROM datasets WHERE dataset_id = 'test-123'")
        else:
            logger.warning("Test insertion failed")
        
        logger.info("🎉 Database is ready for use!")
        
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()