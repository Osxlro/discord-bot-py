import sqlite3

def main():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE test (id INTEGER, coins INTEGER)")
    cursor.execute("INSERT INTO test (id, coins) VALUES (1, 100)")
    row = cursor.execute("SELECT * FROM test").fetchone()
    
    print("row['coins']:", row['coins'])
    print("'coins' in row:", 'coins' in row)
    print("list(row.keys()):", list(row.keys()))
    
    conn.close()

if __name__ == "__main__":
    main()
