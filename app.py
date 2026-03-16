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
import uuid
import math
import traceback

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
    "company","business","fgcode","core_product","product_descrip",
    "mit","mit_issue","mit_due", "iso","iso_issue","iso_due","tis","tis_issue","tis_due",
    "tisi","tisi_issue","tisi_due","cfp","cfp_issue","cfp_due",
    "cfo","cfo_issue","cfo_due","factsheet","factsheet_issue","factsheet_due",
    "technicaldata","tech_issue","tech_due","outline","outline_issue","outline_due",
    "typetest1","typetest1_issue","typetest1_due","typetest2","typetest2_issue","typetest2_due",
    "typetest3","typetest3_issue","typetest3_due","typetest4","typetest4_issue","typetest4_due",
    "typetest5","typetest5_issue","typetest5_due","details","size","color","weight"
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

        return jsonify(
        ok=True,
        files=[f["filename"] for f in saved_files]
        )


    except Exception as e:
        print("IMPORT PREPARE ERROR:", e)
        return jsonify(ok=False, error=str(e)), 500

def read_file_to_df(file):
    if file["filename"].lower().endswith(".csv"):
        return pd.read_csv(file["path"], encoding="utf-8-sig")
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
        missing = REQUIRED_COLS - set(df.columns)
        if missing:
            return jsonify(
                ok=False,
                error=f"ขาดคอลัมน์: {', '.join(missing)}"
            ), 400

        # 2. ตรวจข้อมูลว่าง
        if df["fgcode"].isnull().any():
            return jsonify(ok=False, error="fgcode ห้ามว่าง"), 400

        # 3. ตรวจซ้ำ DB
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT fgcode FROM products")
        existing = {r[0] for r in cur.fetchall()}
        cur.close()
        conn.close()

        dup = df[df["fgcode"].isin(existing)]
        if not dup.empty:
            return jsonify(
                ok=False,
                error=f"fgcode ซ้ำ {dup.iloc[0]['fgcode']}"
            ), 400

        # เก็บไว้รอ commit
        # session["import_rows"] = df.to_dict(orient="records")
        session["import_file"] = file["path"]

        return jsonify(ok=True, rows=len(df))
 
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500
    
def clean(v):
    try:
        if v is None:
            return None
        if isinstance(v, float) and math.isnan(v):
            return None
        s = str(v).strip()
        if s in ("", "-", "nan", "NaN"):
            return None
        return s
    except:
        return None

def to_mark(v):
    try:
        if v is None:
            return "X"
        if isinstance(v, float) and math.isnan(v):
            return "X"
        s = str(v).strip().lower()
        if s in ("✓", "yes", "y", "true", "1"):
            return "✓"
        return "X"
    except:
        return "X"

@app.route("/products/import/commit", methods=["POST"])
@login_required
def import_commit():
    print("SESSION AT COMMIT:", dict(session))
    try: 
        
        file_path = session.get("import_file")

        if not file_path:
            return jsonify(ok=False, error="ไม่พบไฟล์สำหรับ import"), 400
        
        df = pd.read_csv(file_path, encoding="utf-8-sig")
       
        df.columns = df.columns.str.strip().str.lower()
        rows = df.to_dict(orient="records")


        if not rows:
            return jsonify(ok=False, error="ไม่มีข้อมูลให้บันทึก"), 400

        conn = get_db()
        print("DB INFO:", conn.get_dsn_parameters())
    
        cur = conn.cursor()

        success = 0
        failed = 0
        errors = []

        print("ROWS COUNT:", len(rows))
        print("FIRST ROW:", rows[0])
        
        for i, r in enumerate(rows, start=1):
            try:

                print("INSERT ROW", i, r)
                cur.execute("""
                        INSERT INTO products (
                            company,business,fgcode,core_product,product_descrip,
                            mit,mit_issue,mit_due,iso,iso_issue,iso_due,

                            tis,tis_issue,tis_due,
                            tisi,tisi_issue,tisi_due,

                            cfp,cfp_issue,cfp_due,
                            cfo,cfo_issue,cfo_due,

                            factsheet,factsheet_issue,factsheet_due,

                            technicaldata,tech_issue,tech_due,

                            outline,outline_issue,outline_due,

                            typetest1,typetest1_issue,typetest1_due,
                            typetest2,typetest2_issue,typetest2_due,
                            typetest3,typetest3_issue,typetest3_due,
                            typetest4,typetest4_issue,typetest4_due,
                            typetest5,typetest5_issue,typetest5_due,

                            details,size,color,weight
                        ) VALUES (
                            %s,%s,%s,%s,%s,
                            %s,%s,%s,%s,%s,%s,

                            %s,%s,%s,
                            %s,%s,%s,

                            %s,%s,%s,
                            %s,%s,%s,

                            %s,%s,%s,

                            %s,%s,%s,

                            %s,%s,%s,

                            %s,%s,%s,
                            %s,%s,%s,
                            %s,%s,%s,
                            %s,%s,%s,
                            %s,%s,%s,

                            %s,%s,%s,%s
                        )
                    """, (
                        clean(r.get("company")),
                        clean(r.get("business")),
                        clean(r.get("fgcode")),
                        clean(r.get("core_product")),
                        clean(r.get("product_descrip")),

                        clean(r.get("mit")),
                        clean(r.get("mit_issue")),
                        clean(r.get("mit_due")),

                        to_mark(r.get("iso")),
                        clean(r.get("iso_issue")),
                        clean(r.get("iso_due")),

                        to_mark(r.get("tis")),
                        clean(r.get("tis_issue")),
                        clean(r.get("tis_due")),

                        to_mark(r.get("tisi")),
                        clean(r.get("tisi_issue")),
                        clean(r.get("tisi_due")),

                        to_mark(r.get("cfp")),
                        clean(r.get("cfp_issue")),
                        clean(r.get("cfp_due")),

                        to_mark(r.get("cfo")),
                        clean(r.get("cfo_issue")),
                        clean(r.get("cfo_due")),

                        to_mark(r.get("factsheet")),
                        clean(r.get("factsheet_issue")),
                        clean(r.get("factsheet_due")),

                        to_mark(r.get("technicaldata")),
                        clean(r.get("tech_issue")),
                        clean(r.get("tech_due")),

                        to_mark(r.get("outline")),
                        clean(r.get("outline_issue")),
                        clean(r.get("outline_due")),

                        to_mark(r.get("typetest1")),
                        clean(r.get("typetest1_issue")),
                        clean(r.get("typetest1_due")),

                        to_mark(r.get("typetest2")),
                        clean(r.get("typetest2_issue")),
                        clean(r.get("typetest2_due")),

                        to_mark(r.get("typetest3")),
                        clean(r.get("typetest3_issue")),
                        clean(r.get("typetest3_due")),

                        to_mark(r.get("typetest4")),
                        clean(r.get("typetest4_issue")),
                        clean(r.get("typetest4_due")),

                        to_mark(r.get("typetest5")),
                        clean(r.get("typetest5_issue")),
                        clean(r.get("typetest5_due")),

                        clean(r.get("details")),
                        clean(r.get("size")),
                        clean(r.get("color")), 
                        clean(r.get("weight")),
                    ))
                print("ROWCOUNT:", cur.rowcount) 
                success += 1
            except Exception as e:
                print("❌ INSERT ERROR ROW", i, traceback.format_exc())  # ← full stack trace
                failed += 1
                errors.append(f"แถว {i}: {str(e)}")


        conn.commit()
        cur.close()
        conn.close()


        if success == 0:
            return jsonify(ok=False, error="บันทึกไม่สำเร็จ", errors=errors), 400

        return jsonify(ok=True, success=success, failed=failed, errors=errors)

    except Exception as e:  # ← try-except ชั้นนอกสุด อันเดียว
        print("IMPORT COMMIT ERROR:", traceback.format_exc())
        return jsonify(ok=False, error=str(e)), 500
    
   
    
@app.route("/debug-import")
def debug_import():
    import math
    
    # ทดสอบ to_mark และ clean กับค่าจาก CSV จริง
    test_vals = ["✓", "✗", "-", " - ", "", None, float("nan"), "2025-01-18"]
    results = {}
    for v in test_vals:
        results[repr(v)] = {
            "to_mark": to_mark(v),
            "clean": clean(v)
        }
    
    # ทดสอบ DB insert 1 row
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO products (company, business, fgcode, core_product, product_descrip,
                mit, mit_issue, mit_due, iso, iso_issue, iso_due,
                tis, tis_issue, tis_due, tisi, tisi_issue, tisi_due,
                cfp, cfp_issue, cfp_due, cfo, cfo_issue, cfo_due,
                factsheet, factsheet_issue, factsheet_due,
                technicaldata, tech_issue, tech_due,
                outline, outline_issue, outline_due,
                typetest1, typetest1_issue, typetest1_due,
                typetest2, typetest2_issue, typetest2_due,
                typetest3, typetest3_issue, typetest3_due,
                typetest4, typetest4_issue, typetest4_due,
                typetest5, typetest5_issue, typetest5_due,
                details, size, color, weight)
            VALUES (%s,%s,%s,%s,%s, %s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s, %s,%s,%s,%s,%s,%s,
                    %s,%s,%s, %s,%s,%s, %s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s)
        """, (
            "TEST_CO", "TEST_BIZ", "TEST-FGCODE-DEBUG", "TestProduct", "desc",
            "MiT001", "2025-01-01", "2025-12-31", "✓", "2025-01-01", "2025-12-31",
            "✓", "2025-01-01", "2025-12-31", "X", None, None,
            "✓", "2025-01-01", "2025-12-31", "X", None, None,
            "✓", "2025-01-01", "2025-12-31",
            "X", None, None,
            "X", None, None,
            "X", None, None,
            "X", None, None,
            "X", None, None,
            "X", None, None,
            "X", None, None,
            "X", None, None,
            "debug details", "100x200", "black", "5kg"
        ))
        conn.commit()
        cur.close()
        conn.close()
        db_result = "✅ INSERT สำเร็จ"
    except Exception as e:
        import traceback
        db_result = "❌ INSERT ERROR: " + traceback.format_exc()

    return f"<pre>to_mark/clean tests:\n{results}\n\nDB test:\n{db_result}</pre>"


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
            INSERT INTO products (
                company,business,fgcode,core_product,product_descrip,
                mit,mit_issue,mit_due,iso,iso_issue,iso_due,

                tis,tis_issue,tis_due,
                tisi,tisi_issue,tisi_due,

                cfp,cfp_issue,cfp_due,
                cfo,cfo_issue,cfo_due,

                factsheet,factsheet_issue,factsheet_due,

                technicaldata,tech_issue,tech_due,

                outline,outline_issue,outline_due,

                typetest1,typetest1_issue,typetest1_due,
                typetest2,typetest2_issue,typetest2_due,
                typetest3,typetest3_issue,typetest3_due,
                typetest4,typetest4_issue,typetest4_due,
                typetest5,typetest5_issue,typetest5_due,

                details,size,color,weight,
            )
            VALUES (
                %s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,

                %s,%s,%s,
                %s,%s,%s,

                %s,%s,%s,
                %s,%s,%s,

                %s,%s,%s,

                %s,%s,%s,

                %s,%s,%s,

                %s,%s,%s,
                %s,%s,%s,
                %s,%s,%s,
                %s,%s,%s,
                %s,%s,%s,

                %s,%s,%s,%s
            )
        """, (
            request.form["company"],
            request.form["business"],
            request.form["fgcode"],
            request.form["core_product"],     
            request.form["product_descrip"],

            request.form["mit"],
            request.form["mit_issue"] or None,
            request.form["mit_due"] or None,

            request.form["iso"],
            request.form["iso_issue"] or None,
            request.form["iso_due"] or None,

            request.form.get("tis"),
            request.form.get("tis_issue") or None,
            request.form.get("tis_due") or None,

            request.form.get("tisi"),
            request.form.get("tisi_issue") or None,
            request.form.get("tisi_due") or None,

            request.form.get("cfp"),
            request.form.get("cfp_issue") or None,
            request.form.get("cfp_due") or None,

            request.form.get("cfo"),
            request.form.get("cfo_issue") or None,
            request.form.get("cfo_due") or None,

            request.form.get("factsheet"),
            request.form.get("factsheet_issue") or None,
            request.form.get("factsheet_due") or None,

            request.form.get("technicaldata"),
            request.form.get("tech_issue") or None,
            request.form.get("tech_due") or None,

            request.form.get("outline"),
            request.form.get("outline_issue") or None,
            request.form.get("outline_due") or None,

            request.form.get("typetest1"),
            request.form.get("typetest1_issue") or None,
            request.form.get("typetest1_due") or None,

            request.form.get("typetest2"),
            request.form.get("typetest2_issue") or None,
            request.form.get("typetest2_due") or None,

            request.form.get("typetest3"),
            request.form.get("typetest3_issue") or None,
            request.form.get("typetest3_due") or None,

            request.form.get("typetest4"),
            request.form.get("typetest4_issue") or None,
            request.form.get("typetest4_due") or None,

            request.form.get("typetest5"),
            request.form.get("typetest5_issue") or None,
            request.form.get("typetest5_due") or None,

            request.form.get("details"),
            request.form.get("size"),
            request.form.get("color"),
            request.form.get("weight"),
        ))
        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for("products"))

    return render_template("add.html")


@app.route("/product/<int:pid>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_product(pid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id=%s", (pid,))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"ok": True})

port = int(os.environ.get("PORT", 5000))

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=port, 
        debug=True
    )
    # app.run(debug=True)
