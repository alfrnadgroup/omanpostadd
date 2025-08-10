# address_gen.py
import psycopg2

def create_addresses(dsn):
    conn = psycopg2.connect(dsn)
    with conn.cursor() as cur:
        # Create addresses table if not exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS addresses (
                address_id SERIAL PRIMARY KEY,
                raw_id uuid UNIQUE,
                wilayat_code TEXT,
                canonical_code TEXT,
                geom geometry(Geometry,4326),
                created_at timestamptz DEFAULT now()
            );
        """)
        conn.commit()

        # For simplicity: assign dummy wilayat_code as 'WL001' and incremental code
        # In practice, join with admin boundaries to get wilayat_code
        cur.execute("SELECT raw_id, geom FROM raw_plots WHERE raw_id NOT IN (SELECT raw_id FROM addresses)")
        rows = cur.fetchall()
        seq = 1
        for raw_id, geom in rows:
            wilayat_code = "WL001"
            canonical_code = f"OM-{wilayat_code}-{seq:06d}"
            cur.execute("""
                INSERT INTO addresses (raw_id, wilayat_code, canonical_code, geom)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (raw_id) DO NOTHING
            """, (raw_id, wilayat_code, canonical_code, geom))
            seq += 1
        conn.commit()
    conn.close()
