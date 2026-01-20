import os
from flask import Flask, render_template, redirect, url_for, request, flash, session
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

MAX_FILES = 2
MAX_TOTAL_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXT = {".csv", ".xlsx", ".xls"}


@app.route("/products/import/prepare", methods=["POST"])
@login_required
@role_required(["editor", "admin"])
def import_prepare():

        files = request.files.getlist("files[]")

        if not files:
            return {"ok": False, "error": "กรุณาเลือกไฟล์"}, 400

        session["import_files"] = []

        if len(files) > MAX_FILES:
            return {"ok": False, "error": "เลือกไฟล์ได้ไม่เกิน 2 ไฟล์"}, 400

        total_size = sum((f.content_length or 0) for f in files)
        if total_size > MAX_TOTAL_SIZE:
            return {"OK" : False, "error ": "ขนาดไฟล์รวมเกิน 10 MB"}, 400

        for f in files:
            ext = os.path.splitext(f.filename)[1].lower()
            if ext not in ALLOWED_EXT:
                return {"ok": False, "error": f"{f.filename} นามสกุลไม่รองรับ"}, 400
    
            temp_id = str(uuid4())
            path = os.path.join(TEMP_DIR, temp_id + ext)
            f.save(path)
            
            session["import_files"].append({
                "temp_id" : temp_id,
                "filename": f.filename,
                "path" :path
            })

        return {
        "ok": True,
        "files": [f["filename"] for f in session["import_files"]]
    }

@app.route("/products/import/analyze", methods=["POST"])
@login_required
@role_required(["editor", "admin"])
def import_analyze():


    files = session.get("import_files")
    if not files:
        return {"ok": False, "error": "ไม่มีไฟล์"}, 400

        # เขียน DB 
    conn = get_db()
    cur = conn.cursor()
    

    success = 0
    failed = 0
    errors = []

    try: 
            for f in files:
                path = f["path"]
                filename = f["filename"].lower()

                if filename.endswith(".csv"):
                    with open(path, encoding="utf-8-sig") as fh:
                        reader = csv.DictReader(fh)
                        rows = list(reader)
                        headers = reader.fieldnames
                else:
                    df = pd.read_excel(path)
                    headers = list(df.columns)
                    rows = df.to_dict("records")

                if not REQUIRED_COLS.issubset(headers):
                    errors.append(f"{f['filename']} header ไม่ครบ")
                    continue


                for i , rows in enumerate(rows, start=1):
                    try:
                        values = [row.get(col) or None for col in REQUIRED_COLS]
                        cur.execute("""
                        INSERT INTO products (
                            company,business,product,code,product_type,
                            mit,mit_issue,mit_due,
                            factsheet,iso,test,tis,tisi,
                            productmodel,descrip,size,color
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """, values)
                        success +=1
                    except Exception as e:
                        failed +=1
                        errors.append(
                            f"{f.filename} แถว {i} :{e}"
                            )
            conn.commit()

    finally:
            cur.close()
            conn.close()
            session.pop("import_files", None)

    return {
        "ok": True,
        "success": success,
        "failed": failed,
        "errors": errors[:5]  
    }
    


# @app.route("/products/import/confirm", methods=["POST"])
# @login_required
# @role_required(["editor", "admin"])
# def import_confirm():

#     buffer = session.get("import_buffer")
    
#     print("BUFFER:", buffer)
#     if not buffer:
        
#         return {"ok": False, "error": "ไม่มีข้อมูลให้ import"}, 400

#     conn = get_db()
#     cur = conn.cursor()

#     success = 0
#     failed = 0
#     errors = []

#     try:
        
#         cur.execute("SELECT COUNT(*) FROM products")
#         print("BEFORE INSERT:", cur.fetchone())

#         for file in buffer:
#             for row in file["rows"]:
#                 try:
#                     cur.execute("""
#                         INSERT INTO products (
#                             company,business,product,code,product_type,
#                             mit,mit_issue,mit_due,
#                             factsheet,iso,test,tis,tisi,
#                             productmodel,descrip,size,color
#                         ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
#                     """, (
#                         row.get("company"),
#                         row.get("business"),
#                         row.get("product"),
#                         row.get("code"),
#                         row.get("product_type"),
#                         row.get("mit"),
#                         row.get("mit_issue") or None,
#                         row.get("mit_due") or None,
#                         row.get("factsheet"),
#                         row.get("iso"),
#                         row.get("test"),
#                         row.get("tis"),
#                         row.get("tisi"),
#                         row.get("productmodel"),
#                         row.get("descrip"),
#                         row.get("size"),
#                         row.get("color"),
#                     ))
#                     success += 1
#                 except Exception as e:
#                     failed += 1
#                     print("ROW ERROR:", row)
#                     print("ERROR:", e)
#                     errors.append(str(e))

#         conn.commit()

#         cur.execute("SELECT COUNT(*) FROM products")
#         after_count = cur.fetchone()[0]
#         print("AFTER INSERT:", after_count)


   

#     finally:
#         cur.close()
#         conn.close()
#         session.pop("import_buffer", None)
    
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
