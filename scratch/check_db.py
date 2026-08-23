import sqlite3

try:
    conn = sqlite3.connect("trading.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Tables: {tables}")
    
    cursor.execute("SELECT COUNT(*) FROM signals;")
    count = cursor.fetchone()[0]
    print(f"Signals count: {count}")
    
    cursor.execute("SELECT * FROM signals LIMIT 5;")
    rows = cursor.fetchall()
    for row in rows:
        print(row)
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals():
        conn.close()
