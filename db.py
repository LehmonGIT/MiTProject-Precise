import os
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    """
    สร้าง connection ใหม่ทุกครั้งที่เรียก
    - sslmode=require          → Render.com ต้องการ SSL
    - keepalives=1             → ส่ง TCP keepalive ป้องกัน idle timeout
    - keepalives_idle=30       → ส่ง keepalive ทุก 30 วิ ถ้าไม่มีข้อมูล
    - keepalives_interval=10   → retry keepalive ทุก 10 วิ
    - keepalives_count=5       → ลอง 5 ครั้งก่อนตัดสาย
    - connect_timeout=10       → timeout ถ้า connect ไม่ได้ใน 10 วิ
    """
    conn = psycopg2.connect(
        DATABASE_URL,
        sslmode="require",
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5,
        connect_timeout=10,
    )
    return conn