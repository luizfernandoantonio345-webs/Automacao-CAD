import psycopg2
url = "postgresql://neondb_owner:npg_S2I4HkUGFgls@ep-bold-glade-ac4f72nf-pooler.sa-east-1.aws.neon.tech/neondb?channel_binding=require&sslmode=require"
conn = psycopg2.connect(url)
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
tables = [r[0] for r in cur.fetchall()]
print(f"Tabelas criadas ({len(tables)}):")
for t in tables:
    print(f"  - {t}")
conn.close()
