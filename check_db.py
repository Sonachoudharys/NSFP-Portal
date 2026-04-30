import mysql.connector
from mysql.connector import Error

try:
    conn = mysql.connector.connect(
        host='localhost', user='root', password='root@123', database='gov_ai_fraud', connection_timeout=10
    )
    cur = conn.cursor()
    cur.execute('SHOW TABLES')
    tables = [row[0] for row in cur.fetchall()]
    print('TABLES', tables)
    if 'admin_users' in tables:
        cur.execute('SELECT username, password_hash FROM admin_users LIMIT 5')
        print('ADMINS', cur.fetchall())
    if 'states' in tables:
        cur.execute('SELECT COUNT(*) FROM states')
        print('STATES COUNT', cur.fetchone()[0])
    if 'beneficiaries' in tables:
        cur.execute('SELECT COUNT(*) FROM beneficiaries')
        print('BENEFICIARIES COUNT', cur.fetchone()[0])
except Error as e:
    print('DB ERROR', e)
finally:
    if 'cur' in globals():
        cur.close()
    if 'conn' in globals() and conn.is_connected():
        conn.close()
