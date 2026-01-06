import os
from flask import Flask, render_template, redirect, url_for, session, request, flash
from auth import auth_bp
from decorators import login_required, role_required
import csv
from io import textIOwrapper
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
        <h2>Tnternal Error</h2>
        <pre>{str(e)}</pre>
        """,500
        
    
# กลับมาแก้พรุ่งนี้
@app.route("/products/import-csv", methods=["POST"])
@login_required   
@role_required(["editor", "admin"])
def import_csv():
    file = request.files.get("csv_file")

    if not file or file.filename =="":
        flash("No CSV file selected")
        return redirect(url_for("add"))

    if not file.filename.lower().endswith(".csv"):
        flash("File must be CSV")
        return redirect(url_for("add"))
     
    conn = get_db()
    cur = conn.cursor()

    reader = csv.DictReader(textIOwrapper(file, encoding= "utf-8-sig"))
    # stream = io.StringIO(file.stream.read().decode("utf-8-sig"))
    # reader = csv.DictReader(stream)

    # REQUIRED_COLS = { 
    #     "company","business","product","code","type",
    #     "mit","mit_issue","mit_due",
    #     "factsheet","iso","test","tis","tisi",
    #     "productmodel","descrip","size","color"
    # }

    # if not REQUIRED_COLS.issubset(reader.fieldnames):
    #     return "CSV header ไม่ตรงกับระบบ", 400



    for row in reader:
        cur.execute("""
            INSERT INTO products
            (company,business,product,code,type,
             mit,mit_issue,mit_due,
             factsheet,iso,test,tis,tisi,
             productmodel,descrip,size,color)
            VALUES (%s,%s,%s,%s,%s,
                    %s,%s,%s,
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,%s)
        """, (
            row["company"],
            row["business"],
            row["product"],
            row["code"],
            row["type"],
            row["mit"],
            row["mit_issue"] or None,
            row["mit_due"] or None,
            row["factsheet"],
            row["iso"],
            row["test"],
            row["tis"],
            row["tisi"],
            row["productmodel"],
            row["descrip"],
            row["size"],
            row["color"],
        ))

    conn.commit()
    cur.close()
    conn.close()

    flash("csv imported successfully")
    return redirect(url_for("products"))
    print("csv row:", row)


@app.route("/product/<int:pid>")
@login_required
def view(pid):
    product = next(p for p in PRODUCTS if p["id"] == pid)
    return render_template("view.html", product=product)

@app.route("/product/<int:pid>/edit", methods=["GET","POST"])
@login_required
@role_required(["editor","admin"])
def edit(pid):

    print("CURRENT ROLE:", session.get("role"))
    product = next(p for p in PRODUCTS if p["id"] == pid)

    if request.method == "POST":
        product["company"] = request.form["company"]
        product["business"] = request.form["business"]
        product["product"] = request.form["product"]
        product["code"] = request.form["code"]
        product["type"] = request.form["type"]
        product["descrip"] = request.form["descrip"]
        product["size"] = request.form["size"]
        product["color"] = request.form["color"]
        product["mit"] = request.form["mit"]
        product["expdate"] = request.form["expdate"]
        product["factsheet"] = request.form["factsheet"]
        product["ISO"] = request.form["ISO"]
        product["test"] = request.form["test"]
        product["TIS"] = request.form["TIS"]
        product["TISI"] = request.form["TISI"]
        product["productmodel"] = request.form["productmodel"]

        return redirect(url_for("view", pid=pid))
    return render_template("edit.html", product=product)

@app.route("/product/add", methods=["GET","POST"])
@login_required
@role_required(["editor","admin"])
def add():
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO products
            (company,business,product,code,type,
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
            request.form["type"],
            request.form["mit"],
            request.form["mit_issue"] or None,
            request.form["mit_due"] or None,
            request.form["factsheet"],
            request.form["ISO"],
            request.form["test"],
            request.form["TIS"],
            request.form["TISI"],
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

    # app.run(debug=True)
