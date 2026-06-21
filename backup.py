import psycopg2
import json

# Paste your External Connection String from Render inside the quotes below
DATABASE_URL = "postgresql://linklocker_db_user:biOWlQl7qb9QIRy6FjvKgCvy9nCLByqE@dpg-d89iudrbc2fs73f9c980-a.singapore-postgres.render.com/linklocker_db"

def backup_database():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Get all table names in the database
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = [row[0] for row in cur.fetchall()]
        
        backup_data = {}
        
        for table in tables:
            # Fetch column names
            cur.execute(f"SELECT * FROM {table} LIMIT 0")
            columns = [desc[0] for desc in cur.description]
            
            # Fetch all rows
            cur.execute(f"SELECT * FROM {table}")
            rows = cur.fetchall()
            
            # Convert rows to serializable format (strings for dates/UUIDs if necessary)
            serialized_rows = []
            for row in rows:
                serialized_rows.append([str(item) if item is not None else None for item in row])
                
            backup_data[table] = {
                "columns": columns,
                "rows": serialized_rows
            }
            print(f"Backed up table: {table} ({len(rows)} rows)")
            
        # Save to a local JSON file
        with open("aura_backup.json", "w") as f:
            json.dump(backup_data, f, indent=4)
            
        print("\n🎉 Success! Your data is safe inside 'aura_backup.json'")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error executing backup: {e}")

if __name__ == "__main__":
    backup_database()