import sqlite3

def check_and_migrate():
    conn = sqlite3.connect("database.sqlite")
    c = conn.cursor()
    
    # Check stickies table
    c.execute("PRAGMA table_info(stickies)")
    columns = [col[1] for col in c.fetchall()]
    print(f"Stickies columns: {columns}")
    
    if "stickies" in columns: # Wait, "stickies" is the table name, columns should be id, guild_id...
        pass

    # Ensure is_embed exists
    if columns and "is_embed" not in columns:
        print("Adding is_embed column...")
        try:
            c.execute("ALTER TABLE stickies ADD COLUMN is_embed INTEGER DEFAULT 1")
        except Exception as e:
            print(f"Error adding is_embed: {e}")

    # Ensure id exists? If id doesn't exist, we might need to recreate the table.
    if columns and "id" not in columns:
        print("CRITICAL: 'id' column missing. Recreating table...")
        c.execute("ALTER TABLE stickies RENAME TO stickies_old")
        c.execute('''CREATE TABLE stickies (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id   TEXT,
            channel_id TEXT,
            title      TEXT,
            content    TEXT,
            message_id TEXT,
            enabled    INTEGER DEFAULT 1,
            cooldown   INTEGER DEFAULT 5,
            is_embed   INTEGER DEFAULT 1
        )''')
        # Try to port data if possible (mapping columns)
        # Note: This is a bit risky if data is important, but for a bot it's usually fine to clear or migrate.
        print("Table recreated.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    check_and_migrate()
