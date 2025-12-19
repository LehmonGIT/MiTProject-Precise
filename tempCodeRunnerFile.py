from flask import Flask, render_template, redirect, url_for, session, request
from auth import auth_bp
from decorators import login_required, role_required

app = Flask(__name__)
app.secret_key = "dev-secret"

# register auth blueprint
app.register_blueprint(auth_bp)

# -------- mock data --------
PRODUCTS = [
    {"id": 1, "company": "PEM", "business": "PEM101", "product": "Surge Arrester", "code": "HS-F-99-3303", "type": "39121700", "mit": "MiT6410002240", "expdate": "xx/xx/xx", "factsheet": "xxx", "ISO" : "xxx" , "test": "xxx","TIS": "xxx", "TISI": "xxx", "productmodel" : "xxx","descrip":"กับดักเสิร์จออกไซต์โลหะไม่มีช่องว่าง สำหรับไฟฟ้ากระแสสลับ 30kV 10kA ชนิดฉนวนพอลิเมอร์ สำหรับใช้ในบริเวณที่มีมลภาวะ (PEA Material No. 1040000103)","size" : "กว้าง 675 mm x ยาว 420 mm x สูง 104 mm","color": "สีเทา"},
    {"id": 2, "company": "CI", "business": "CI101", "product": "1-Pole Disconnecting Switch (Vertical Break)", "code": "DS-F-99-0308", "type": "39121700", "mit": "MiT6404001344", "expdate": "xx/xx/xx", "factsheet": "xxx", "ISO" : "xxx" , "test": "xxx","TIS": "xxx", "TISI": "xxx", "productmodel" : "xxx" ,"descrip":"สวิตช์ใบมีดแรงสูงแบบใช้ภายนอกอาคาร ชนิด Single Pole พิกัดแรงดันไฟฟ้า 27 kV พิกัดกระแสไฟฟ้าต่อเนื่อง 630 A", "size" : "กว้าง 190 mm X ยาว 780 mm X สูง 573 mm","color": "สีน้ำตาล"},
    {"id": 3, "company": "CI", "business": "CI101", "product": "3-Pole Disconnecting Switch (Double-side Break)", "code": "DS-F-99-0105", "type": "39121700", "mit": "MiT6406002262", "expdate": "xx/xx/xx", "factsheet": "xxx", "ISO" : "xxx" , "test": "xxx","TIS": "xxx", "TISI": "xxx", "productmodel" : "xxx","descrip":"ใบมีดกราวด์ ชนิด 3-Pole พิกัดแรงดันไฟฟ้า 123 kV พิกัดกระแสลัดวงจร 40 kA" ,"size" : "กว้าง 246 mm X ยาว 6504 mm X สูง 1481 mm","color": "สีน้ำตาล"},
    {"id": 4, "company": "PEM", "business": "PEM101", "product": "LED Products and System", "code": "HS-F-99-3303", "type": "39111603", "mit": "MiT6410002240", "expdate": "xx/xx/xx", "factsheet": "xxx", "ISO" : "xxx" , "test": "xxx","TIS": "xxx", "TISI": "xxx", "productmodel" : "xxx","descrip":"ดวงโคมไฟฟ้าสำหรับให้แสงสว่างบนถนน มีอุปกรณ์ขับหลอดอิเล็กทรอนิกส์ ใช้หลอด แอล อี ดี กำลังไฟฟ้า 60 วัตต์","size" : "กว้าง 675 mm x ยาว 420 mm x สูง 104 mm","color": "-"},
    {"id": 5, "company": "PEM", "business": "PEM101", "product": "Surge Arrester", "code": "HS-F-99-0212", "type": "39121700", "mit": "MiT6410002240", "expdate": "xx/xx/xx", "factsheet": "xxx", "ISO" : "xxx" , "test": "xxx","TIS": "xxx", "TISI": "xxx", "productmodel" : "xxx","descrip":"กับดักเสิร์จออกไซต์โลหะไม่มีช่องว่าง สำหรับไฟฟ้ากระแสสลับ 21kV 5kA","size" : "กว้าง 520mm x ยาว 420mm x สูง 104mm","color": "สีเทา"},
    {"id": 6, "company": "PEM", "business": "PEM101", "product": "Surge Arrester", "code": "HS-F-99-3303", "type": "39121700", "mit": "MiT6410002240", "expdate": "xx/xx/xx", "factsheet": "xxx", "ISO" : "xxx" , "test": "xxx","TIS": "xxx", "TISI": "xxx", "productmodel" : "xxx","descrip":"กับดักเสิร์จออกไซต์โลหะไม่มีช่องว่าง สำหรับไฟฟ้ากระแสสลับ 30kV 10kA ชนิดฉนวนพอลิเมอร์ สำหรับใช้ในบริเวณที่มีมลภาวะ (PEA Material No. 1040000103)","size" : "กว้าง 675 mm x ยาว 420 mm x สูง 104 mm","color": "สีเทา"},
    {"id": 7, "company": "CI", "business": "CI101", "product": "1-Pole Disconnecting Switch (Vertical Break)", "code": "DS-F-99-0308", "type": "39121700", "mit": "MiT6404001344", "expdate": "xx/xx/xx", "factsheet": "xxx", "ISO" : "xxx" , "test": "xxx","TIS": "xxx", "TISI": "xxx", "productmodel" : "xxx" ,"descrip":"สวิตช์ใบมีดแรงสูงแบบใช้ภายนอกอาคาร ชนิด Single Pole พิกัดแรงดันไฟฟ้า 27 kV พิกัดกระแสไฟฟ้าต่อเนื่อง 630 A", "size" : "กว้าง 190 mm X ยาว 780 mm X สูง 573 mm","color": "สีน้ำตาล"},
    {"id": 8, "company": "CI", "business": "CI101", "product": "3-Pole Disconnecting Switch (Double-side Break)", "code": "DS-F-99-0105", "type": "39121700", "mit": "MiT6406002262", "expdate": "xx/xx/xx", "factsheet": "xxx", "ISO" : "xxx" , "test": "xxx","TIS": "xxx", "TISI": "xxx", "productmodel" : "xxx","descrip":"ใบมีดกราวด์ ชนิด 3-Pole พิกัดแรงดันไฟฟ้า 123 kV พิกัดกระแสลัดวงจร 40 kA" ,"size" : "กว้าง 246 mm X ยาว 6504 mm X สูง 1481 mm","color": "สีน้ำตาล"},
    {"id": 9, "company": "PEM", "business": "PEM101", "product": "LED Products and System", "code": "HS-F-99-3303", "type": "39111603", "mit": "MiT6410002240", "expdate": "xx/xx/xx", "factsheet": "xxx", "ISO" : "xxx" , "test": "xxx","TIS": "xxx", "TISI": "xxx", "productmodel" : "xxx","descrip":"ดวงโคมไฟฟ้าสำหรับให้แสงสว่างบนถนน มีอุปกรณ์ขับหลอดอิเล็กทรอนิกส์ ใช้หลอด แอล อี ดี กำลังไฟฟ้า 60 วัตต์","size" : "กว้าง 675 mm x ยาว 420 mm x สูง 104 mm","color": "-"},
    {"id": 10, "company": "PEM", "business": "PEM101", "product": "Surge Arrester", "code": "HS-F-99-0212", "type": "39121700", "mit": "MiT6410002240", "expdate": "xx/xx/xx", "factsheet": "xxx", "ISO" : "xxx" , "test": "xxx","TIS": "xxx", "TISI": "xxx", "productmodel" : "xxx","descrip":"กับดักเสิร์จออกไซต์โลหะไม่มีช่องว่าง สำหรับไฟฟ้ากระแสสลับ 21kV 5kA","size" : "กว้าง 520mm x ยาว 420mm x สูง 104mm","color": "สีเทา"},


]

@app.route("/")
@login_required
def home():
    return redirect(url_for("products"))


@app.route("/products")
@login_required
def products():
    return render_template("products.html", products=PRODUCTS)

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

        new = {
            "id": len(PRODUCTS) + 1,
            "company": request.form["company"],
            "business": request.form["business"],
            "product": request.form["product"],
            "code": request.form["code"],
            "type": request.form["type"],
            "descrip": request.form["descrip"],
            "size": request.form["size"],
            "color": request.form["color"],
            "mit": request.form["mit"],
            "expdate": request.form["expdate"],
            "factsheet": request.form["factsheet"],
            "ISO": request.form["ISO"],
            "test": request.form["test"],
            "TIS": request.form["TIS"],
            "TISI": request.form["TISI"],
            "productmodel": request.form["productmodel"],
            "image_url": None
        }

        # รับไฟล์รูป
        img = request.files.get("image")
        if img:
            path = f"static/uploads/{new['id']}.jpg"
            img.save(path)
            new["image_url"] = "/" + path

        PRODUCTS.append(new)

        return redirect(url_for("products"))

    return render_template("add.html")


if __name__ == "__main__":
    app.run(debug=True)
