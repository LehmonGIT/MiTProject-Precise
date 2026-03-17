import os
import time
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_db(retries=3, delay=2):
    """
    เชื่อมต่อ DB พร้อม retry อัตโนมัติ
    - ถ้า SSL หลุด / connection ล้มเหลว → รอ delay วิ แล้วลองใหม่
    - retries=3  → ลองสูงสุด 3 ครั้ง
    - delay=2    → รอ 2 วิ ระหว่างแต่ละครั้ง
    """
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            conn = psycopg2.connect(
                DATABASE_URL,
                sslmode="require",
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5,
                connect_timeout=15,
            )
            # ทดสอบว่า connection ใช้งานได้จริงก่อน return
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            return conn

        except psycopg2.OperationalError as e:
            last_error = e
            print(f"[DB] connect attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(delay)

    raise Exception(
        f"ไม่สามารถเชื่อมต่อฐานข้อมูลได้หลังลอง {retries} ครั้ง: {last_error}"
    )