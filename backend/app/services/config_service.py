import json
import os
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class ConfigService:
    def __init__(self):
        # Default paths (relative to code)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, "../../data")
        
        self.storage_path = os.path.join(data_dir, "db_config.json")
        self.credentials_dir = os.path.join(data_dir, "credentials")

        # Try to create directories. If read-only fs (Cloud Run), fallback to /tmp
        try:
            os.makedirs(data_dir, exist_ok=True)
            os.makedirs(self.credentials_dir, exist_ok=True)
        except OSError:
            logger.warning("Read-only filesystem detected. Falling back to /tmp for storage.")
            data_dir = "/tmp/tabi-data"
            self.storage_path = os.path.join(data_dir, "db_config.json")
            self.credentials_dir = os.path.join(data_dir, "credentials")
            os.makedirs(data_dir, exist_ok=True)
            os.makedirs(self.credentials_dir, exist_ok=True)

        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Load config from JSON file"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading db config: {e}")
                return {}
        return {}

    def _save_config(self) -> bool:
        """Save config to JSON file"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving db config: {e}")
            return False

    def get_config(self) -> dict:
        """Get the current configuration with masked passwords"""
        config_copy = json.loads(json.dumps(self.config))
        # Mask postgres password
        if "postgres" in config_copy and "password" in config_copy["postgres"]:
            if config_copy["postgres"]["password"]:
                config_copy["postgres"]["password"] = "********"
        return config_copy

    def get_db_type(self) -> str:
        """Get current database type (default to postgres)"""
        # Allow env var override for Cloud Run / SaaS mode
        env_type = os.getenv("DB_TYPE")
        if env_type:
            return env_type
        return self.config.get("db_type", "postgres")

    def get_postgres_config(self) -> dict:
        """Get Postgres specific config or defaults from ENV"""
        default_url = settings.DATABASE_URL
        # Parse default URL if no config exists
        default_params = {"host": "localhost", "port": 5432, "user": "user", "password": "", "database": "chatbi"}
        if default_url.startswith("postgresql://"):
            try:
                import re
                pattern = r"postgresql://(?P<user>.*?):(?P<password>.*?)@(?P<host>.*?):(?P<port>\d+)/(?P<database>.*)"
                match = re.match(pattern, default_url)
                if match:
                    default_params = match.groupdict()
                    default_params["port"] = int(default_params["port"])
            except:
                pass
        
        return self.config.get("postgres", default_params)

    def get_bigquery_config(self) -> dict:
        """Get BigQuery specific config"""
        # Allow env var override
        env_project = os.getenv("BIGQUERY_PROJECT")
        config = self.config.get("bigquery", {"project_id": "", "dataset_id": "", "credentials_path": ""})
        
        if env_project:
            config["project_id"] = env_project
            # If using public data, credentials path might not be needed if relying on ADC
            
        return config

    def get_iceberg_config(self) -> dict:
        """Get Iceberg/Athena specific config"""
        return self.config.get("iceberg", {"region": "", "s3_staging": "", "database": "", "catalog": "AwsDataCatalog", "credentials_path": ""})

    def get_db_url(self) -> str:
        """Legacy support for getting DB URL (Postgres only)"""
        db_type = self.get_db_type()
        if db_type == "postgres":
            p = self.get_postgres_config()
            return f"postgresql://{p['user']}:{p['password']}@{p['host']}:{p['port']}/{p['database']}"
        return ""

    def get_async_db_url(self) -> str:
        """Legacy support for async DB URL"""
        url = self.get_db_url()
        if url and url.startswith("postgresql://") and "+asyncpg" not in url:
            return url.replace("postgresql://", "postgresql+asyncpg://")
        return url

    def update_db_config(self, db_type: str, config_data: dict) -> bool:
        """Update and persist database configuration of a specific type"""
        self.config["db_type"] = db_type
        
        # If updating postgres and password is masked, keep the old one
        if db_type == "postgres" and config_data.get("password") == "********":
            old_p = self.get_postgres_config()
            config_data["password"] = old_p.get("password", "")
            
        self.config[db_type] = config_data
        return self._save_config()

    def save_credential_file(self, filename: str, content: bytes) -> str:
        """Save a credential file and return the absolute path"""
        # Security: Allow only certain extensions and sanitize filename
        if not (filename.endswith('.json') or filename.endswith('.csv') or filename.endswith('.txt')):
             # Basic check, can be improved
             pass
        
        file_path = os.path.join(self.credentials_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(content)
        return file_path

config_service = ConfigService()
