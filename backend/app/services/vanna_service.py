import logging
import os
import re
import traceback
from typing import Optional, Dict, Any, List
import pandas as pd
from vanna.chromadb import ChromaDB_VectorStore
from app.core.config import settings
from app.services.config_service import config_service

logger = logging.getLogger(__name__)



class VannaNoSQLError(Exception):
    """Raised when Vanna's LLM returns a text explanation instead of SQL."""
    pass


# Hardcoded DDL fallback for online_retail table (snake_case column names matching actual DB)
ONLINE_RETAIL_DDL = """
CREATE TABLE public.online_retail (
    id integer NOT NULL,
    invoice_no character varying(20),
    stock_code character varying(20),
    description text,
    quantity integer,
    invoice_date timestamp without time zone,
    unit_price double precision,
    customer_id double precision,
    country character varying(50)
);
"""

ONLINE_RETAIL_DOCS = [
    "The online_retail table contains transactional data from a UK-based online retail store. The table is in the public schema.",
    "invoice_no is the invoice number. Invoices starting with 'C' indicate cancellations.",
    "stock_code is the product code, a unique identifier for each product.",
    "description is the product name/description.",
    "quantity is the number of units purchased per transaction line.",
    "invoice_date is the date and time of the transaction.",
    "unit_price is the price per unit in GBP (British Pounds).",
    "customer_id is a unique identifier for each customer. It can be NULL for unregistered customers.",
    "country is the country where the customer is located.",
    "Total revenue per line can be calculated as quantity * unit_price.",
    "To analyze sales, use SUM(quantity * unit_price) as total revenue.",
    "Common analyses include: sales by country, top products, monthly trends, customer segmentation.",
    "All column names in the online_retail table are lowercase snake_case. No quoting is needed. For example: SELECT country, SUM(quantity * unit_price) FROM online_retail GROUP BY country",
]


class VannaService:
    def __init__(self):
        self._is_connected = False
        self.vn = None
        self._initialized = False

    def _ensure_initialized(self):
        """Initialize Vanna lazily to avoid startup blocking"""
        if self._initialized:
            return

        print("[VANNA] Starting initialization...")
        logger.info("VannaService: Starting initialization...")

        # Ensure storage directory exists
        base_dir = os.path.dirname(os.path.abspath(__file__))
        storage_path = os.path.join(base_dir, "../../vanna_storage")

        try:
            if not os.path.exists(storage_path):
                os.makedirs(storage_path)
        except OSError:
            print("[VANNA] Read-only filesystem, falling back to /tmp")
            logger.warning("Read-only filesystem detected for Vanna. Falling back to /tmp.")
            storage_path = "/tmp/vanna_storage"
            os.makedirs(storage_path, exist_ok=True)
        except Exception as e:
            print(f"[VANNA] Failed to create storage dir: {e}")
            logger.error(f"Failed to create vanna storage dir: {e}")
            storage_path = "/tmp/vanna_storage"
            os.makedirs(storage_path, exist_ok=True)

        print(f"[VANNA] storage_path={storage_path}, LLM_PROVIDER={settings.DEFAULT_LLM_PROVIDER}")

        if settings.DEFAULT_LLM_PROVIDER == "gemini":
            try:
                if not (settings.GOOGLE_CLOUD_PROJECT and settings.GOOGLE_CLOUD_LOCATION):
                     print("[VANNA] Missing GCP Project/Location, using fallback")
                     logger.warning("Vanna skipped Gemini init: Missing GCP Project/Location")
                     self._setup_fallback(storage_path)
                     self._initialized = True
                     return

                # Use custom VertexAIChat that supports ADC (no JSON file needed)
                from vanna.base import VannaBase
                import vertexai
                from vertexai.generative_models import GenerativeModel

                class VertexAIChat(VannaBase):
                    """Vertex AI Gemini chat with ADC support for Cloud Run"""
                    def __init__(self, config=None):
                        VannaBase.__init__(self, config=config)
                        self.temperature = config.get("temperature", 0.7)
                        model_name = config.get("model_name", config.get("model", "gemini-2.0-flash"))
                        vertexai.init(
                            project=config.get("project_id"),
                            location=config.get("location", "asia-northeast1")
                        )
                        self.chat_model = GenerativeModel(model_name)

                    def system_message(self, message: str) -> any:
                        return message

                    def user_message(self, message: str) -> any:
                        return message

                    def assistant_message(self, message: str) -> any:
                        return message

                    def submit_prompt(self, prompt, **kwargs) -> str:
                        response = self.chat_model.generate_content(
                            prompt,
                            generation_config={"temperature": self.temperature},
                        )
                        return response.text

                class TabiVanna(ChromaDB_VectorStore, VertexAIChat):
                    def __init__(self, config=None):
                        ChromaDB_VectorStore.__init__(self, config=config)
                        VertexAIChat.__init__(self, config=config)

                self.vn = TabiVanna(config={
                    'project_id': settings.GOOGLE_CLOUD_PROJECT,
                    'location': settings.GOOGLE_CLOUD_LOCATION,
                    'model': settings.GEMINI_MODEL,
                    'path': storage_path
                })
                print(f"[VANNA] Initialized with Vertex AI Gemini (ADC): {settings.GEMINI_MODEL}")
                logger.info(f"Vanna initialized with Vertex AI Gemini (ADC): {settings.GEMINI_MODEL}")
            except Exception as e:
                print(f"[VANNA] Gemini init FAILED: {e}\n{traceback.format_exc()}")
                logger.error(f"Failed to initialize Vanna with Vertex AI: {e}")
                self._setup_fallback(storage_path)
        else:
            print("[VANNA] Non-gemini provider, using fallback")
            self._setup_fallback(storage_path)

        self._initialized = True
        print(f"[VANNA] Initialized. vn={'set' if self.vn else 'None'}")

        # Auto-connect and auto-train on first initialization
        self._auto_setup()

    def _auto_setup(self):
        """Automatically connect to DB and train with schema if no training data exists."""
        print("[VANNA] _auto_setup: starting...")
        if not self.vn:
            print("[VANNA] _auto_setup: vn is None, skipping")
            logger.warning("Auto-setup: Vanna instance is None, skipping.")
            return

        try:
            self.connect_to_db()
        except Exception as e:
            print(f"[VANNA] _auto_setup: DB connection FAILED: {e}")
            logger.error(f"Auto-setup: DB connection failed: {e}\n{traceback.format_exc()}")
            return

        if not self._is_connected:
            print("[VANNA] _auto_setup: DB not connected, skipping training")
            logger.warning("Auto-setup: DB connection did not succeed, skipping training.")
            return

        print("[VANNA] _auto_setup: DB connected. Checking training data...")
        logger.info("Auto-setup: DB connected. Checking training data...")

        try:
            df = self.vn.get_training_data()
            if df is not None and not df.empty:
                print(f"[VANNA] _auto_setup: Training data exists ({len(df)} entries), skipping")
                logger.info(f"Auto-setup: Training data already exists ({len(df)} entries), skipping.")
                return
        except Exception as e:
            print(f"[VANNA] _auto_setup: Could not check training data: {e}")
            logger.warning(f"Auto-setup: Could not check training data: {e}")

        print("[VANNA] _auto_setup: No training data. Starting auto-train...")
        logger.info("Auto-setup: No training data found. Auto-training with DB schema...")
        self._auto_train_schema()

    def _auto_train_schema(self):
        """Fetch DDL from connected DB and train Vanna automatically."""
        ddl_trained = False

        # Try to get DDL from information_schema
        try:
            ddl_query = """
            SELECT
                'CREATE TABLE ' || table_schema || '.' || table_name || ' (' ||
                string_agg(
                    '"' || column_name || '" ' || data_type ||
                    CASE WHEN character_maximum_length IS NOT NULL
                         THEN '(' || character_maximum_length || ')'
                         ELSE '' END ||
                    CASE WHEN is_nullable = 'NO' THEN ' NOT NULL' ELSE '' END,
                    ', ' ORDER BY ordinal_position
                ) || ');' AS ddl
            FROM information_schema.columns
            WHERE table_schema = 'public'
            GROUP BY table_schema, table_name
            ORDER BY table_name;
            """
            df = self.vn.run_sql(ddl_query)
            row_count = len(df) if df is not None else 0
            print(f"[VANNA] _auto_train: information_schema returned {row_count} rows")
            logger.info(f"Auto-train: information_schema query returned {row_count} rows")

            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    ddl = row.iloc[0]
                    self.vn.train(ddl=ddl)
                    print(f"[VANNA] _auto_train: Trained DDL: {ddl[:80]}...")
                    logger.info(f"Auto-trained DDL from DB: {ddl[:100]}...")
                ddl_trained = True

        except Exception as e:
            print(f"[VANNA] _auto_train: information_schema FAILED: {e}")
            logger.warning(f"Auto-train: information_schema query failed: {e}")

        # Fallback: use hardcoded DDL if DB query failed
        if not ddl_trained:
            print("[VANNA] _auto_train: Using hardcoded DDL fallback")
            logger.info("Auto-train: Using hardcoded DDL fallback for online_retail table")
            try:
                self.vn.train(ddl=ONLINE_RETAIL_DDL)
                print("[VANNA] _auto_train: Hardcoded DDL trained OK")
                logger.info("Auto-trained with hardcoded online_retail DDL")
            except Exception as e:
                print(f"[VANNA] _auto_train: Hardcoded DDL FAILED: {e}")
                logger.error(f"Auto-train: Hardcoded DDL training failed: {e}")

        # Train with documentation
        try:
            for doc in ONLINE_RETAIL_DOCS:
                self.vn.train(documentation=doc)
            print(f"[VANNA] _auto_train: Trained {len(ONLINE_RETAIL_DOCS)} docs OK")
            logger.info(f"Auto-train: Trained with {len(ONLINE_RETAIL_DOCS)} documentation entries")
        except Exception as e:
            print(f"[VANNA] _auto_train: Documentation training FAILED: {e}")
            logger.error(f"Auto-train: Documentation training failed: {e}")

        print("[VANNA] _auto_train: Complete")
        logger.info("Auto-setup: Training complete.")

    def _setup_fallback(self, storage_path: str):
        try:
            from vanna.openai import OpenAI_Chat
            class TabiVannaLegacy(ChromaDB_VectorStore, OpenAI_Chat):
                def __init__(self, config=None):
                    ChromaDB_VectorStore.__init__(self, config=config)
                    OpenAI_Chat.__init__(self, config=config)

            if settings.OPENROUTER_API_KEY:
                self.vn = TabiVannaLegacy(config={
                    'api_key': settings.OPENROUTER_API_KEY,
                    'model': settings.OPENROUTER_MODEL,
                    'path': storage_path,
                    'base_url': "https://openrouter.ai/api/v1"
                })
                print(f"[VANNA] Fallback: OpenRouter ({settings.OPENROUTER_MODEL})")
                logger.info(f"Vanna initialized with OpenRouter fallback: {settings.OPENROUTER_MODEL}")
            else:
                self.vn = TabiVannaLegacy(config={
                    'api_key': settings.OPENAI_API_KEY or "dummy",
                    'model': 'gpt-4o',
                    'path': storage_path
                })
                print("[VANNA] Fallback: OpenAI (default)")
                logger.info("Vanna initialized with default OpenAI fallback")
        except Exception as e:
            print(f"[VANNA] Fallback FAILED: {e}")
            logger.error(f"Failed to setup Vanna fallback: {e}")
            self.vn = None
        self._is_connected = False

    def connect_to_db(self):
        if self._is_connected:
            return
        self._ensure_initialized()
        if not self.vn:
            print("[VANNA] connect_to_db: vn is None")
            logger.error("connect_to_db: Vanna instance is None")
            return

        try:
            db_type = config_service.get_db_type()
            print(f"[VANNA] connect_to_db: db_type={db_type}")
            logger.info(f"connect_to_db: db_type={db_type}")

            if db_type == "postgres":
                p = config_service.get_postgres_config()
                print(f"[VANNA] connect_to_db: host={p.get('host')}, port={p.get('port')}, db={p.get('database')}, user={p.get('user')}")
                logger.info(f"connect_to_db: Connecting to PostgreSQL host={p.get('host')}, port={p.get('port')}, dbname={p.get('database')}, user={p.get('user')}")
                self.vn.connect_to_postgres(
                    host=p.get("host"),
                    dbname=p.get("database"),
                    user=p.get("user"),
                    password=p.get("password"),
                    port=p.get("port", 5432)
                )
                self._is_connected = True
                print("[VANNA] connect_to_db: PostgreSQL connected OK")
                logger.info("Vanna connected to PostgreSQL successfully")

            elif db_type == "bigquery":
                c = config_service.get_bigquery_config()
                self.vn.connect_to_bigquery(
                    project_id=c.get("project_id"),
                    creds_path=c.get("credentials_path")
                )
                self._is_connected = True
                print(f"[VANNA] connect_to_db: BigQuery connected ({c.get('project_id')})")
                logger.info(f"Vanna connected to BigQuery (Project: {c.get('project_id')})")

            elif db_type == "iceberg":
                c = config_service.get_iceberg_config()
                self.vn.connect_to_athena(
                    region_name=c.get("region"),
                    s3_staging_dir=c.get("s3_staging"),
                    database=c.get("database"),
                    workgroup=c.get("workgroup", "primary")
                )
                self._is_connected = True
                print("[VANNA] connect_to_db: Athena/Iceberg connected")
                logger.info(f"Vanna connected to AWS Athena/Iceberg")
            else:
                print(f"[VANNA] connect_to_db: Unknown db_type: {db_type}")
                logger.warning(f"connect_to_db: Unknown db_type: {db_type}")

        except Exception as e:
            print(f"[VANNA] connect_to_db FAILED: {e}\n{traceback.format_exc()}")
            logger.error(f"Vanna connection error (db_type={config_service.get_db_type()}): {e}\n{traceback.format_exc()}")
            self._is_connected = False

    def generate_sql(self, question: str) -> Optional[str]:
        """Generate SQL from a natural-language question.

        Returns the SQL string on success.
        Raises ``VannaNoSQLError`` when the LLM responds with a text
        explanation instead of SQL (e.g. "insufficient context").
        Returns ``None`` for other failures.
        """
        self._ensure_initialized()
        if not self.vn:
            print("[VANNA] generate_sql: vn is None")
            logger.error("generate_sql: Vanna instance is None")
            return None

        if not self._is_connected:
            print("[VANNA] generate_sql: not connected, attempting connection...")
            logger.info("generate_sql: Not connected, attempting connection...")
            self.connect_to_db()

        if not self._is_connected:
            print("[VANNA] generate_sql: STILL not connected after connect_to_db()")
            logger.error("generate_sql: Still not connected after connect_to_db()")
            return None

        print(f"[VANNA] generate_sql: question='{question[:100]}'")
        logger.info(f"generate_sql: question='{question[:100]}'")

        # Log training data count for debugging
        try:
            td = self.vn.get_training_data()
            td_count = len(td) if td is not None else 0
            print(f"[VANNA] generate_sql: training_data_count={td_count}")
        except Exception:
            print("[VANNA] generate_sql: could not get training data count")

        try:
            sql = self.vn.generate_sql(question)
        except Exception as e:
            print(f"[VANNA] generate_sql: EXCEPTION: {e}\n{traceback.format_exc()}")
            logger.error(f"generate_sql: vn.generate_sql() raised exception: {e}\n{traceback.format_exc()}")
            return None

        print(f"[VANNA] generate_sql: raw result = {repr(sql)[:300]}")
        logger.info(f"generate_sql: raw result = {repr(sql[:300]) if sql else 'None/empty'}")

        if not sql:
            print("[VANNA] generate_sql: Vanna returned None/empty")
            logger.warning("generate_sql: Vanna returned None/empty")
            return None

        # Validate: SQL should start with common keywords
        if not any(sql.strip().upper().startswith(kw) for kw in ["SELECT", "WITH", "SHOW", "DESC", "DESCRIBE"]):
            print(f"[VANNA] generate_sql: non-SQL response: {sql[:200]}")
            logger.warning(f"generate_sql: Vanna returned non-SQL response: {sql[:200]}")
            # The LLM chose to explain why it can't generate SQL — surface
            # this to the user instead of a generic "failed" message.
            raise VannaNoSQLError(sql)

        print(f"[VANNA] generate_sql: SUCCESS sql={sql[:200]}")
        logger.info(f"generate_sql: SUCCESS sql={sql[:200]}")
        return sql

    def run_sql(self, sql: str) -> pd.DataFrame:
        self._ensure_initialized()
        if not self.vn: return pd.DataFrame()

        if not self._is_connected:
            self.connect_to_db()

        logger.info(f"run_sql: Executing SQL: {sql[:200]}")
        try:
            df = self.vn.run_sql(sql)
            logger.info(f"run_sql: SUCCESS rows={len(df)}, columns={list(df.columns)}")
            return df
        except Exception as e:
            logger.error(f"run_sql: FAILED: {e}\n{traceback.format_exc()}")
            raise

    def generate_plotly_figure(self, df: pd.DataFrame, question: str, sql: str) -> Any:
        self._ensure_initialized()
        if not self.vn: return None

        logger.info(f"generate_plotly_figure: df rows={len(df)}, question='{question[:60]}'")
        try:
            code = self.vn.generate_plotly_code(question=question, sql=sql, df=df)
            logger.info(f"generate_plotly_figure: plotly code generated ({len(code) if code else 0} chars)")
            fig = self.vn.get_plotly_figure(plotly_code=code, df=df)
            logger.info(f"generate_plotly_figure: figure generated OK")
            return fig
        except Exception as e:
            logger.error(f"generate_plotly_figure: FAILED: {e}\n{traceback.format_exc()}")
            return None

    def train_with_schema(self, ddl_list: List[str]):
        """Train Vanna with DDL statements"""
        self._ensure_initialized()
        if not self.vn: return

        for ddl in ddl_list:
            self.vn.train(ddl=ddl)
        logger.info(f"Vanna trained with {len(ddl_list)} DDL statements")

    def get_training_data(self) -> List[Dict[str, Any]]:
        """Get all training data from Vanna"""
        self._ensure_initialized()
        if not self.vn: return []

        try:
            df = self.vn.get_training_data()
            if df is not None and not df.empty:
                return df.to_dict(orient="records")
            return []
        except Exception as e:
            logger.error(f"Error getting training data: {e}")
            return []

    def train_documentation(self, documentation: str):
        """Train Vanna with documentation/metadata"""
        self._ensure_initialized()
        if not self.vn: return False

        try:
            self.vn.train(documentation=documentation)
            logger.info(f"Vanna trained with documentation: {documentation[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Error training documentation: {e}")
            return False

    def train_structured_metadata(self, metadata: List[Dict[str, Any]]):
        """Train Vanna with structured metadata (Cube, Measure, Dimension)"""
        self._ensure_initialized()
        if not self.vn: return False

        try:
            docs = []
            for item in metadata:
                name = item.get("name", "Unknown")
                m_type = item.get("type", "Unknown")
                desc = item.get("description", "").strip()
                polarity = item.get("polarity", "neutral")

                doc = f"The {m_type} '{name}'"
                if desc:
                    doc += f" is defined as: {desc}."

                if m_type == "measure":
                    if polarity == "positive":
                        doc += " Higher values are generally better/favorable for this metric."
                    elif polarity == "negative":
                        doc += " Lower values are generally better/favorable for this metric."

                docs.append(doc)

            if docs:
                combined_docs = "\n".join(docs)
                self.vn.train(documentation=combined_docs)
                logger.info(f"Vanna trained with {len(docs)} structured metadata entries.")
                return True
            return False
        except Exception as e:
            logger.error(f"Error training structured metadata: {e}")
            return False

    def remove_training_data(self, training_id: str):
        """Remove specific training data by ID"""
        self._ensure_initialized()
        if not self.vn: return False

        try:
            self.vn.remove_training_data(id=training_id)
            logger.info(f"Removed training data with ID: {training_id}")
            return True
        except Exception as e:
            logger.error(f"Error removing training data: {e}")
            return False

    def clear_all_training_data(self):
        """Clear all training data from Vanna"""
        self._ensure_initialized()
        if not self.vn: return False

        try:
            df = self.vn.get_training_data()
            if df is not None and not df.empty:
                for idx, row in df.iterrows():
                    self.vn.remove_training_data(id=row['id'])
                logger.info("Cleared all training data from Vanna")
            return True
        except Exception as e:
            logger.error(f"Error clearing all training data: {e}")
            return False

    def clear_documentation_training(self):
        """Clear documentation-type training data from Vanna"""
        self._ensure_initialized()
        if not self.vn: return False

        try:
            df = self.vn.get_training_data()
            if df is not None and not df.empty:
                doc_entries = df[df['training_data_type'] == 'documentation']
                for idx, row in doc_entries.iterrows():
                    self.vn.remove_training_data(id=row['id'])
                logger.info("Cleared documentation training data from Vanna")
            return True
        except Exception as e:
            logger.error(f"Error clearing documentation training: {e}")
            return False

vanna_service = VannaService()
