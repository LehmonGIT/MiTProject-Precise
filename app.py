from flask import Flask, render_template, redirect, url_for, session, request
from auth import auth_bp
from decorators import login_required, role_required
import csv
import io
from db import get_db

app = Flask(__name__)
app.secret_key = "dev-secret"

# register auth blueprint
app.register_blueprint(auth_bp)

# -------- mock data --------
PRODUCTS = [
    {"id": 1, "company": "PEM", "business": "PEM101", "product": "Surge Arrester", "code": "HS-F-99-3303", "type": "39121700", "mit": "MiT6410002240", "mit_issue": "2025-12-18","mit_due": "2025-12-23", "factsheet": "-", "ISO" : "-" , "test": "✓","TIS": "✗", "TISI": "✓", "productmodel" : "✗","descrip":"กับดักเสิร์จออกไซต์โลหะไม่มีช่องว่าง สำหรับไฟฟ้ากระแสสลับ 30kV 10kA ชนิดฉนวนพอลิเมอร์ สำหรับใช้ในบริเวณที่มีมลภาวะ (PEA Material No. 1040000103)","size" : "กว้าง 675 mm x ยาว 420 mm x สูง 104 mm","color": "สีเทา"},
    {"id": 2, "company": "CI", "business": "CI101", "product": "1-Pole Disconnecting Switch (Vertical Break)", "code": "DS-F-99-0308", "type": "39121700", "mit": "MiT6404001344","mit_issue": "2025-01-18","mit_due": "2025-12-20", "factsheet": "-", "ISO" : "-" , "test": "✗","TIS": "-", "TISI": "✗", "productmodel" : "-" ,"descrip":"สวิตช์ใบมีดแรงสูงแบบใช้ภายนอกอาคาร ชนิด Single Pole พิกัดแรงดันไฟฟ้า 27 kV พิกัดกระแสไฟฟ้าต่อเนื่อง 630 A", "size" : "กว้าง 190 mm X ยาว 780 mm X สูง 573 mm","color": "สีน้ำตาล"},
    {"id": 3, "company": "CI", "business": "CI101", "product": "3-Pole Disconnecting Switch (Double-side Break)", "code": "DS-F-99-0105", "type": "39121700", "mit": "MiT6406002262", "mit_issue": "2025-12-15","mit_due": "2026-10-15","factsheet": "✓", "ISO" : "✗" , "test": "✗","TIS": "✓", "TISI": "✗", "productmodel" : "✗","descrip":"ใบมีดกราวด์ ชนิด 3-Pole พิกัดแรงดันไฟฟ้า 123 kV พิกัดกระแสลัดวงจร 40 kA" ,"size" : "กว้าง 246 mm X ยาว 6504 mm X สูง 1481 mm","color": "สีน้ำตาล"},
    {"id": 4, "company": "PEM", "business": "PEM101", "product": "LED Products and System", "code": "HS-F-99-3303", "type": "39111603", "mit": "MiT6410002240", "mit_issue": "2026-01-15","mit_due": "2026-03-23", "factsheet": "✓", "ISO" : "✗" , "test": "-","TIS": "-", "TISI": "✓", "productmodel" : "✗","descrip":"ดวงโคมไฟฟ้าสำหรับให้แสงสว่างบนถนน มีอุปกรณ์ขับหลอดอิเล็กทรอนิกส์ ใช้หลอด แอล อี ดี กำลังไฟฟ้า 60 วัตต์","size" : "กว้าง 675 mm x ยาว 420 mm x สูง 104 mm","color": "-"},
    {"id": 5, "company": "PEM", "business": "PEM101", "product": "Surge Arrester", "code": "HS-F-99-0212", "type": "39121700", "mit": "MiT6410002240", "mit_issue": "2025-01-15","mit_due": "2027-01-15", "factsheet": "✓", "ISO" : "✗" , "test": "-","TIS": "-", "TISI": "✓", "productmodel" : "✗","descrip":"กับดักเสิร์จออกไซต์โลหะไม่มีช่องว่าง สำหรับไฟฟ้ากระแสสลับ 21kV 5kA","size" : "กว้าง 520mm x ยาว 420mm x สูง 104mm","color": "สีเทา"},
    {"id": 6, "company": "PEM", "business": "PEM101", "product": "Surge Arrester", "code": "HS-F-99-3303", "type": "39121700", "mit": "MiT6410002240", "mit_issue": "3/23/2567","mit_due": "3/23/2569", "factsheet": "-", "ISO" : "-" , "test": "✓","TIS": "✗", "TISI": "✓", "productmodel" : "✗","descrip":"กับดักเสิร์จออกไซต์โลหะไม่มีช่องว่าง สำหรับไฟฟ้ากระแสสลับ 30kV 10kA ชนิดฉนวนพอลิเมอร์ สำหรับใช้ในบริเวณที่มีมลภาวะ (PEA Material No. 1040000103)","size" : "กว้าง 675 mm x ยาว 420 mm x สูง 104 mm","color": "สีเทา"},
    {"id": 7, "company": "CI", "business": "CI101", "product": "1-Pole Disconnecting Switch (Vertical Break)", "code": "DS-F-99-0308", "type": "39121700", "mit": "MiT6404001344", "mit_issue": "3/23/2567","mit_due": "3/23/2569", "factsheet": "-", "ISO" : "-" , "test": "✗","TIS": "-", "TISI": "✗", "productmodel" : "-" ,"descrip":"สวิตช์ใบมีดแรงสูงแบบใช้ภายนอกอาคาร ชนิด Single Pole พิกัดแรงดันไฟฟ้า 27 kV พิกัดกระแสไฟฟ้าต่อเนื่อง 630 A", "size" : "กว้าง 190 mm X ยาว 780 mm X สูง 573 mm","color": "สีน้ำตาล"},
    {"id": 8, "company": "CI", "business": "CI101", "product": "3-Pole Disconnecting Switch (Double-side Break)", "code": "DS-F-99-0105", "type": "39121700", "mit": "MiT6406002262", "mit_issue": "3/23/2567","mit_due": "3/23/2569", "factsheet": "✓", "ISO" : "✗" , "test": "✗","TIS": "✓", "TISI": "✗", "productmodel" : "✗","descrip":"ใบมีดกราวด์ ชนิด 3-Pole พิกัดแรงดันไฟฟ้า 123 kV พิกัดกระแสลัดวงจร 40 kA" ,"size" : "กว้าง 246 mm X ยาว 6504 mm X สูง 1481 mm","color": "สีน้ำตาล"},
    {"id": 9, "company": "PEM", "business": "PEM101", "product": "LED Products and System", "code": "HS-F-99-3303", "type": "39111603", "mit": "MiT6410002240", "mit_issue": "3/23/2567","mit_due": "3/23/2569","factsheet": "✓", "ISO" : "✗" , "test": "-","TIS": "-", "TISI": "✓", "productmodel" : "✗","descrip":"ดวงโคมไฟฟ้าสำหรับให้แสงสว่างบนถนน มีอุปกรณ์ขับหลอดอิเล็กทรอนิกส์ ใช้หลอด แอล อี ดี กำลังไฟฟ้า 60 วัตต์","size" : "กว้าง 675 mm x ยาว 420 mm x สูง 104 mm","color": "-"},
    {"id": 10, "company": "PEM", "business": "PEM101", "product": "Surge Arrester", "code": "HS-F-99-0212", "type": "39121700", "mit": "MiT6410002240", "mit_issue": "3/23/2567","mit_due": "3/23/2569", "factsheet": "✓", "ISO" : "✗" , "test": "-","TIS": "-", "TISI": "✓", "productmodel" : "✗","descrip":"กับดักเสิร์จออกไซต์โลหะไม่มีช่องว่าง สำหรับไฟฟ้ากระแสสลับ 21kV 5kA","size" : "กว้าง 520mm x ยาว 420mm x สูง 104mm","color": "สีเทา"},

]

@app.route("/")
@login_required
def home():
    return redirect(url_for("products"))


# @app.route("/products")
# @login_required
# def products():
#     return render_template("products.html", products=PRODUCTS)

@app.route("/products")
@login_required
def products():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products ORDER BY id DESC")
    products = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("products.html", products=products)

@app.route("/products/import", methods=["POST"])
@login_required
@role_required(["editor", "admin"])
def import_csv():
    file = request.files.get("csv_file")
    if not file:
        return redirect(url_for("products"))

    stream = io.StringIO(file.stream.read().decode("utf-8"))
    reader = csv.DictReader(stream)

    for row in reader:
        new = {
            "id": len(PRODUCTS) + 1,
            "company": row.get("company"),
            "business": row.get("business"),
            "product": row.get("product"),
            "code": row.get("code"),
            "type": row.get("type"),
            "mit": row.get("mit"),
            "expdate": row.get("expdate"),
            "factsheet": row.get("factsheet"),
            "ISO": row.get("ISO"),
            "test": row.get("test"),
            "TIS": row.get("TIS"),
            "TISI": row.get("TISI"),
            "productmodel": row.get("productmodel"),
            "descrip": row.get("descrip"),
            "size": row.get("size"),
            "color": row.get("color"),
            "image_url": None
        }
        PRODUCTS.append(new)

    return redirect(url_for("products"))




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

@app.route("/product/add", methods=["GET", "POST"])
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
             factsheet,iso,test,tis,tisi,productmodel,
             descrip,size,color)
            VALUES (%s,%s,%s,%s,%s,
                    %s,%s,%s,
                    %s,%s,%s,%s,%s,%s,
                    %s,%s,%s)
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

# @app.route("/product/add", methods=["GET", "POST"])
# @login_required
# @role_required(["editor","admin"])
# def add():
#     if request.method == "POST":

#         new = {
#             "id": len(PRODUCTS) + 1,
#             "company": request.form["company"],
#             "business": request.form["business"],
#             "product": request.form["product"],
#             "code": request.form["code"],
#             "type": request.form["type"],
#             "descrip": request.form["descrip"],
#             "size": request.form["size"],
#             "color": request.form["color"],
#             "mit": request.form["mit"],
#             "expdate": request.form["expdate"],
#             "factsheet": request.form["factsheet"],
#             "ISO": request.form["ISO"],
#             "test": request.form["test"],
#             "TIS": request.form["TIS"],
#             "TISI": request.form["TISI"],
#             "productmodel": request.form["productmodel"],
#             "image_url": None
#         }

#         # รับไฟล์รูป
#         img = request.files.get("image")
#         if img:
#             path = f"static/uploads/{new['id']}.jpg"
#             img.save(path)
#             new["image_url"] = "/" + path

#         PRODUCTS.append(new)

#         return redirect(url_for("products"))

#     return render_template("add.html")

# @app.route("/product/<int:id>/delete")
# def delete_product(id):
#     if session.get("role") != "admin":
#         abort(403)

#     cursor = conn.cursor()
#     cursor.execute("DELETE FROM products WHERE id=?", (id,))
#     conn.commit()

#     return redirect("/products")

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    # app.run(debug=True)
