import os
from flask import Flask, render_template, redirect, url_for, session, request, flash
from auth import auth_bp
from decorators import login_required, role_required
import csv
from io import TextIOWrapper
from db import get_db
import pandas as pd

app = Flask(__name__)
app.secret_key = "dev-secret"

# register auth blueprint
app.register_blueprint(auth_bp)


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

        cur.close()
        conn.close()

        # แปลงเป็น dict
        products = [dict(zip(colnames, row)) for row in products]

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

        if len(files) > MAX_FILES:
            return {"ok": False, "error": "เลือกไฟล์ได้ไม่เกิน 2 ไฟล์"}, 400

        total_size = sum(
            (f.content_length or 0) for f in files
        )

        if total_size > MAX_TOTAL_SIZE:
            return {"ok": False, "error": "ขนาดไฟล์รวมเกิน 10MB"}, 400

        # ✅ แค่ผ่านเงื่อนไข
        return {
            "ok": True,
            "files": [f.filename for f in files]
        }

@app.route("/products/import/analyze", methods=["POST"])
@login_required
@role_required(["editor", "admin"])
def import_analyze():

    files = request.files.getlist("files[]")
    analyzed_data = []
    errors = []

    for file in files:
        name = file.filename.lower()

        if not any(name.endswith(ext) for ext in ALLOWED_EXT):
            errors.append(f"{file.filename} : นามสกุลไม่รองรับ")
            continue

        try:
            if name.endswith(".csv"):
                reader = csv.DictReader(
                    TextIOWrapper(file.stream, encoding="utf-8-sig")
                )
                headers = reader.fieldnames
                rows = list(reader)
            else:
                df = pd.read_excel(file)
                headers = list(df.columns)
                rows = df.to_dict(orient="records")

            if not REQUIRED_COLS.issubset(headers):
                raise Exception("Header ไม่ตรง")

            analyzed_data.append({
                "filename": file.filename,
                "rows": rows,
                "total": len(rows)
            })

        except Exception as e:
            errors.append(f"{file.filename} : {e}")

    if errors:
        return {"ok": False, "error": errors}, 400

    session["import_buffer"] = analyzed_data

    return {
        "ok": True,
        "summary": [
            {"filename": f["filename"], "total": f["total"]}
            for f in analyzed_data
        ]
    }


@app.route("/products/import/confirm", methods=["POST"])
@login_required
@role_required(["editor", "admin"])
def import_confirm():

    buffer = session.get("import_buffer")
    if not buffer:
        return {"ok": False, "error": "ไม่มีข้อมูลให้ import"}, 400

    conn = get_db()
    cur = conn.cursor()

    success = 0
    failed = 0
    errors = []

    try:
        for file in buffer:
            for row in file["rows"]:
                try:
                    cur.execute("""
                        INSERT INTO products (
                            company,business,product,code,product_type,
                            mit,mit_issue,mit_due,
                            factsheet,iso,test,tis,tisi,
                            productmodel,descrip,size,color
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (
                        row.get("company"),
                        row.get("business"),
                        row.get("product"),
                        row.get("code"),
                        row.get("product_type"),
                        row.get("mit"),
                        row.get("mit_issue") or None,
                        row.get("mit_due") or None,
                        row.get("factsheet"),
                        row.get("iso"),
                        row.get("test"),
                        row.get("tis"),
                        row.get("tisi"),
                        row.get("productmodel"),
                        row.get("descrip"),
                        row.get("size"),
                        row.get("color"),
                    ))
                    success += 1
                except Exception as e:
                    failed += 1
                    errors.append(str(e))

        conn.commit()

    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}, 500

    finally:
        cur.close()
        conn.close()
        session.pop("import_buffer", None)

    return {
        "ok": True,
        "success": success,
        "failed": failed,
        "errors": errors[:5]  # กัน error ยาว
    }




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
