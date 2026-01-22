import os
from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify
from auth import auth_bp
from decorators import login_required, role_required
import csv
import io
from io import TextIOWrapper
from db import get_db
import pandas as pd
import tempfile
from uuid import uuid4


app = Flask(__name__)
app.secret_key = "dev-secret"


UPLOAD_DIR = "/tmp/mit_import"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# register auth blueprint
app.register_blueprint(auth_bp)

TEMP_DIR = os.path.join(tempfile.gettempdir(), "mit_import")

os.makedirs(TEMP_DIR, exist_ok=True)

@app.route("/")
@login_required
def home():
    return redirect(url_for("products"))



# ใช้ข้อมูลจาก postgerSQL
@app.route("/products")
@login_required
def products():
    try:

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM products")
        products = cur.fetchall()

        colnames = [desc[0] for desc in cur.description]
        products = [dict(zip(colnames, row)) for row in products]

        cur.close()
        conn.close()

        return render_template("products.html", products=products)
    except Exception as e:
        return f"""
        <h2>Internal Error</h2>
        <pre>{str(e)}</pre>
        """,500
        
    
REQUIRED_COLS = {
    "company","business","product","code","product_type",
    "mit","mit_issue","mit_due",
    "factsheet","iso","test","tis","tisi",
    "productmodel","descrip","size","color"
}


@app.route("/products/import/prepare", methods=["POST"])
@login_required
@role_required(["editor", "admin"])
def import_prepare():
    try:
        files = request.files.getlist("files[]")

        # 1. จำนวนไฟล์
        if not files:
            return jsonify(ok=False, error="กรุณาเลือกไฟล์"), 400

        if len(files) > 2:
            return jsonify(ok=False, error="เลือกไฟล์ได้ไม่เกิน 2 ไฟล์"), 400

        # 2. นามสกุล
        ALLOWED_EXT = (".csv", ".xlsx", ".xls")
        for f in files:
            if not f.filename.lower().endswith(ALLOWED_EXT):
                return jsonify(
                    ok=False,
                    error=f"ไฟล์ {f.filename} ไม่รองรับ"
                ), 400

        # 3. ขนาดรวม 
        total_size = 0
        for f in files:
            f.stream.seek(0, os.SEEK_END)
            total_size += f.stream.tell()
            f.stream.seek(0)

        if total_size > 10 * 1024 * 1024:
            return jsonify(ok=False, error="ขนาดไฟล์รวมเกิน 10MB"), 400

        saved_files = []

        for f in files:
            
            ext = os.path.splitext(f.filename)[1]
            filename = f"{uuid.uuid4()}{ext}"
            path = os.path.join(UPLOAD_DIR, filename)

        
            f.save(path)

            saved_files.append({
                "filename": f.filename,  
                "path": path          
            })

        # เก็บไฟล์ไว้ใช้ใน popup2 → /validate
        session["import_files"] = saved_files

        return jsonify(ok=True)


    except Exception as e:
        print("IMPORT PREPARE ERROR:", e)
        return jsonify(ok=False, error=str(e)), 500

def read_file_to_df(file):
    if file["filename"].lower().endswith(".csv"):
        return pd.read_csv(file["path"])
    else:
        return pd.read_excel(file["path"])



@app.route("/products/import/validate", methods=["POST"])
@login_required
@role_required(["editor", "admin"])
def import_validate():
    try:
        files = session.get("import_files")
        if not files:
            return jsonify(ok=False, error="ไม่พบไฟล์ใน session"), 400

        file = files[0]
        df = read_file_to_df(file)

        # 1. ตรวจ header
        missing = [c for c in REQUIRED_COLS if c not in df.columns]
        if missing:
            return jsonify(
                ok=False,
                error=f"ขาดคอลัมน์: {', '.join(missing)}"
            ), 400

        # 2. ตรวจข้อมูลว่าง
        if df["code"].isnull().any():
            return jsonify(ok=False, error="code ห้ามว่าง"), 400

        # 3. ตรวจซ้ำ DB
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT code FROM products")
        existing = {r[0] for r in cur.fetchall()}
        cur.close()
        conn.close()

        dup = df[df["code"].isin(existing)]
        if not dup.empty:
            return jsonify(
                ok=False,
                error=f"code ซ้ำ {dup.iloc[0]['code']}"
            ), 400

        # เก็บไว้รอ commit
        session["import_rows"] = df.to_dict("records")

        return jsonify(ok=True, rows=len(df))

    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500
    
@app.route("/products/import/commit", methods=["POST"])
@login_required
def import_commit():

    rows = session.get("import_rows")
    if not rows:
        return jsonify(ok=False, error="ไม่มีข้อมูลให้บันทึก"), 400

    conn = get_db()
    cur = conn.cursor()

    success = 0
    failed = 0

    for r in rows:
        try:

            cur.execute("""
                        INSERT INTO products (
                            company,business,product,code,product_type,
                            mit,mit_issue,mit_due,
                            factsheet,iso,test,tis,tisi,
                            productmodel,descrip,size,color
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (
                            rows.get("company"),
                            rows.get("business"),
                            rows.get("product"),
                            rows.get("code"),
                            rows.get("product_type"),
                            rows.get("mit"),
                            rows.get("mit_issue") or None,
                            rows.get("mit_due") or None,
                            rows.get("factsheet"),
                            rows.get("iso"),
                            rows.get("test"),
                            rows.get("tis"),
                            rows.get("tisi"),
                            rows.get("productmodel"),
                            rows.get("descrip"),
                            rows.get("size"),
                            rows.get("color"),
                        ))
            success +=1
        except Exception as e:
            failed +=1
            errors.append(f"{f.filename} แถว {i} :{e}")

    conn.commit()
    cur.close()
    conn.close()

    session.pop("import_rows", None)

    return {
        "ok": True,
        "success": success,
        "failed": failed
    }





    
@app.route("/db-test")
def db_test():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        conn.close()
        return "DB CONNECT OK"
    except Exception as e:
        return str(e), 500






@app.route("/product/<int:pid>")
@login_required
def view(pid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE id=%s", (pid,))
    row = cur.fetchone()

    if not row:
        return "Product not found", 404

    colnames = [desc[0] for desc in cur.description]
    product = dict(zip(colnames, row))

    cur.close()
    conn.close()

    return render_template("view.html", product=product)


@app.route("/product/<int:pid>/edit", methods=["GET","POST"])
@login_required
@role_required(["editor","admin"])
def edit(pid):

    return "Edit page not implemented yet", 501
    # print("CURRENT ROLE:", session.get("role"))

    # product = next(p for p in PRODUCTS if p["id"] == pid)

    # if request.method == "POST":
    #     product["company"] = request.form["company"]
    #     product["business"] = request.form["business"]
    #     product["product"] = request.form["product"]
    #     product["code"] = request.form["code"]
    #     product["type"] = request.form["type"]
    #     product["descrip"] = request.form["descrip"]
    #     product["size"] = request.form["size"]
    #     product["color"] = request.form["color"]
    #     product["mit"] = request.form["mit"]
    #     product["expdate"] = request.form["expdate"]
    #     product["factsheet"] = request.form["factsheet"]
    #     product["ISO"] = request.form["ISO"]
    #     product["test"] = request.form["test"]
    #     product["TIS"] = request.form["TIS"]
    #     product["TISI"] = request.form["TISI"]
    #     product["productmodel"] = request.form["productmodel"]

    #     return redirect(url_for("view", pid=pid))
    # return render_template("edit.html", product=product)


@app.route("/product/add", methods=["GET","POST"])
@login_required
@role_required(["editor","admin"])
def add():
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO products
            (company,business,product,code,product_type,
             mit,mit_issue,mit_due,
             factsheet,iso,test,tis,tisi,
             productmodel,descrip,size,color)
            VALUES (%s,%s,%s,%s,%s,
                    %s,%s,%s,
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,%s)
        """, (
            request.form["company"],
            request.form["business"],
            request.form["product"],
            request.form["code"],
            request.form["product_type"],
            request.form["mit"],
            request.form["mit_issue"] or None,
            request.form["mit_due"] or None,
            request.form["factsheet"],
            request.form["iso"],
            request.form["test"],
            request.form["tis"],
            request.form["tisi"],
            request.form["productmodel"],
            request.form["descrip"],
            request.form["size"],
            request.form["color"]
        ))

        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for("products"))

    return render_template("add.html")


@app.route("/product/<int:id>/delete", methods=["POST"])
@login_required
@role_required(["admin"])
def delete_product(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id=%s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("products"))


# @app.route("/env-test")
# def env_test():
#     return {
#         "DATABASE_URL": bool(os.environ.get("DATABASE_URL"))
#     }

    
port = int(os.environ.get("PORT", 5000))

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )
    # app.run(debug=True)
