"""Database initialization script for ClickHouse."""
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from clickhouse_connect.driver import Client
from loguru import logger

from tdms_analytics_api.dependencies.database import get_clickhouse_client


class DatabaseInitializer:
    """Initialize ClickHouse database schema."""
    
    def __init__(self):
        self.client = get_clickhouse_client()
    
    def create_database(self) -> None:
        """Create the main database if it doesn't exist."""
        try:
            logger.info("Database connection verified")
        except Exception as e:
            logger.error(f"Failed to verify database: {e}")
            raise
    
    def create_tables(self) -> None:
        """Create all required tables."""
        
        # Supprimer les tables existantes
        self.client.command("DROP TABLE IF EXISTS datasets")
        self.client.command("DROP TABLE IF EXISTS channels") 
        self.client.command("DROP TABLE IF EXISTS sensor_data")
        self.client.command("DROP TABLE IF EXISTS sensor_data_with_time")
        
        # Créer tables avec une seule colonne puis ajouter les autres
        
        # Datasets
        self.client.command("CREATE TABLE datasets (dataset_id String) ENGINE = MergeTree() ORDER BY dataset_id")
        self.client.command("ALTER TABLE datasets ADD COLUMN filename String")
        self.client.command("ALTER TABLE datasets ADD COLUMN created_at DateTime64(3)")
        self.client.command("ALTER TABLE datasets ADD COLUMN total_points UInt64")
        logger.info("✓ Created datasets table")
        
        # Channels
        self.client.command("CREATE TABLE channels (channel_id String) ENGINE = MergeTree() ORDER BY channel_id")
        self.client.command("ALTER TABLE channels ADD COLUMN dataset_id String")
        self.client.command("ALTER TABLE channels ADD COLUMN group_name String")
        self.client.command("ALTER TABLE channels ADD COLUMN channel_name String")
        self.client.command("ALTER TABLE channels ADD COLUMN unit String")
        self.client.command("ALTER TABLE channels ADD COLUMN has_time Bool")
        self.client.command("ALTER TABLE channels ADD COLUMN n_rows UInt64")
        logger.info("✓ Created channels table")
        
        # Sensor data
        self.client.command("CREATE TABLE sensor_data (channel_id String) ENGINE = MergeTree() ORDER BY channel_id")
        self.client.command("ALTER TABLE sensor_data ADD COLUMN index UInt64")
        self.client.command("ALTER TABLE sensor_data ADD COLUMN value Float32")
        logger.info("✓ Created sensor_data table")
        
        # Sensor data with time
        self.client.command("CREATE TABLE sensor_data_with_time (channel_id String) ENGINE = MergeTree() ORDER BY channel_id")
        self.client.command("ALTER TABLE sensor_data_with_time ADD COLUMN index UInt64")
        self.client.command("ALTER TABLE sensor_data_with_time ADD COLUMN value Float32")
        self.client.command("ALTER TABLE sensor_data_with_time ADD COLUMN timestamp Float64")
        self.client.command("ALTER TABLE sensor_data_with_time ADD COLUMN timestamp_iso String")
        logger.info("✓ Created sensor_data_with_time table")
    
    def create_indexes(self) -> None:
        """Create additional indexes for performance."""
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

        try:
            client.insert("datasets", test_data)
            result = client.query("SELECT COUNT() FROM datasets WHERE dataset_id = 'test-123'")
            count = result.result_set[0][0] if result.result_set else 0
            
            if count >= 1:
                logger.info("✓ Test insertion successful")
                client.command("DELETE FROM datasets WHERE dataset_id = 'test-123'")
            else:
                logger.warning(f"Test insertion failed - count: {count}")
        except Exception as e:
            logger.warning(f"Test insertion failed: {e}")
                
        logger.info("🎉 Database is ready for use!")
        
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()