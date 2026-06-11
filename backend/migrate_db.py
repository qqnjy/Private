import sqlite3

def migrate():
    conn = sqlite3.connect('c:/Users/winniexue/.gemini/antigravity-ide/scratch/IGS/粉絲團數據追蹤/backend/data.db')
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE targets ADD COLUMN tags VARCHAR DEFAULT ''")
        print("Added tags")
    except Exception as e:
        print(e)
        
    try:
        cursor.execute("ALTER TABLE targets ADD COLUMN is_competitor INTEGER DEFAULT 0")
        print("Added is_competitor")
    except Exception as e:
        print(e)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
