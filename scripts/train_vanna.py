import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.vanna_service import vanna_service
from app.core.config import settings

def train_vanna():
    print("Training Vanna with current schema...")
    
    # Path to schema SQL
    schema_path = os.path.join(os.getcwd(), "database/init/001_create_schema.sql")
    
    if not os.path.exists(schema_path):
        print(f"Schema file not found at {schema_path}")
        return

    with open(schema_path, "r") as f:
        sql_content = f.read()

    # Split into statements (basic split)
    statements = sql_content.split(";")
    ddl_statements = [s.strip() for s in statements if "CREATE TABLE" in s or "CREATE VIEW" in s]
    
    vanna_service.train_with_schema(ddl_statements)
    
    # Add some doc training
    vanna_service.vn.train(documentation="This is a retail database containing information about countries, customers, products, invoices, and sales items.")
    vanna_service.vn.train(documentation="The sales table contains line items for each invoice, including quantities and unit prices.")
    
    print("Vanna training completed.")

if __name__ == "__main__":
    train_vanna()
