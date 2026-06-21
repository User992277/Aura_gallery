import psycopg2
import json

# Paste your NEW Neon Connection String inside the quotes below
NEW_DATABASE_URL = "postgresql://neondb_owner:npg_DQSO0mXsgd4W@ep-square-bonus-aosuedpt.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

def restore_database():
    try:
        conn = psycopg2.connect(NEW_DATABASE_URL)
        cur = conn.cursor()
        
        # Load your backup file
        with open("aura_backup.json", "r") as f:
            backup_data = json.load(f)
            
        print("Starting data migration to Neon...")
        
        # Iterating through tables to insert records
        for table, data in backup_data.items():
            columns = data["columns"]
            rows = data["rows"]
            
            if not rows:
                print(f"Skipping empty table: {table}")
                continue
                
            # Construct a dynamic INSERT query
            cols_str = ", ".join(columns)
            placeholders = ", ".join(["%s"] * len(columns))
            insert_query = f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING;"
            
            # Execute inserts row by row
            inserted_count = 0
            for row in rows:
                # Replace back explicit 'None' string values into actual Python None/Nulls if needed
                processed_row = [None if item == 'None' else item for item in row]
                cur.execute(insert_query, processed_row)
                inserted_count += 1
                
            print(f"Successfully migrated {inserted_count} rows into table: {table}")
            
        conn.commit()
        print("\n🎉 Database Migration Complete! Your data is safe on Neon forever.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error during migration: {e}")

if __name__ == "__main__":
    restore_database()