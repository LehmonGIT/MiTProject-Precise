import os
from flask import Flask, render_template, redirect, url_for, session, request, flash
from auth import auth_bp
from decorators import login_required, role_required
import csv
from io import TextIOWrapper
from db import get_db

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
        
    
@app.route("/products/import-csv", methods=["POST"])
@login_required
@role_required(["editor", "admin"])
def import_csv():

    print("IMPORT CSV CALLED")
    print("METHOD =", request.method)

    file = request.files.get("csv_file")

    if not file or file.filename == "":
        flash("กรุณาเลือกไฟล์")
        return redirect(url_for("add"))

    if not file.filename.lower().endswith(".csv,.xlsx"):
        flash("รอบรับไฟล์ CSV, xlsx")
        return redirect(url_for("add"))

        # สร้าง reader ก่อน
    reader = csv.DictReader(TextIOWrapper(file, encoding="utf-8-sig"))

        # ✅ debug header
    print("CSV HEADERS:", reader.fieldnames)

    REQUIRED_COLS = {
        "company","business","product","code","product_type",
        "mit","mit_issue","mit_due",
        "factsheet","iso","test","tis","tisi",
        "productmodel","descrip","size","color"
        }

    if not REQUIRED_COLS.issubset(reader.fieldnames):
        return f"""
        <h3>CSV header ไม่ตรง</h3>
        <pre>{reader.fieldnames}</pre>
        """, 400

    conn = get_db()
    cur = conn.cursor()

    for row in reader:
        print("ROW:", row)

        cur.execute("""
            INSERT INTO products (company,business,product,code,product_type,mit,mit_issue,mit_due,
                factsheet,iso,test,tis,tisi,productmodel,descrip,size,color)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
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

    conn.commit()
    cur.close()
    conn.close()

    flash("แนบไฟล์สำเร็จ")
    return redirect(url_for("products"))
    

@app.errorhandler(500)
def internal_error(e):
    import traceback
    return "<pre>" + traceback.format_exc() + "</pre>", 500


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
