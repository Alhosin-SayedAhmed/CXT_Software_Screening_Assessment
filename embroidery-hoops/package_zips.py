"""Builds the Arabic-named zip bundles from ./stl (run make_hoops_v2.py first)."""
import zipfile, os, shutil, glob
STYLES = {
 "2part": ("طارة_مزخرفة_من_الناحيتين", "إطار_مزخرف_من_الناحيتين", """طارة تطريز وردة — مزخرفة من الناحيتين
==========================================
قطعتين: إطار حتة واحدة + حلقة بتتقفل جواه بتكة.
- الحافة الدايرية بارزة من الوش ومن الضهر، والأطراف مدوّرة.
- الوش: نقشة ورق بارزة 0.4 مم.  الضهر: نفس النقشة محفورة (غايرة) 0.4 مم.
- ارتفاع الحافة 9 مم — تخانة البتلات 4 مم.

⚠️ الإطار محتاج دعامات صغيرة (البتلات مرفوعة 2.5 مم فوق البليتة):
   Support: Enable ✔ — Type: tree(auto) — On build plate only ✔ — Top Z distance 0.2
   الحلقة من غير دعامات.
"""),
 "1side": ("طارة_مزخرفة_من_ناحية_واحدة", "إطار_مزخرف_من_ناحية_واحدة", """طارة تطريز وردة — مزخرفة من ناحية واحدة
==========================================
قطعتين: إطار حتة واحدة + حلقة بتتقفل جواه بتكة.
- الوش: الحافة الدايرية بارزة، الأطراف مدوّرة، ونقشة ورق بارزة 0.4 مم.
- الضهر: مستوي تمامًا (مش بارز ومن غير نقشة).
- ارتفاع الحافة 9 مم — تخانة البتلات 4 مم.

✅ من غير دعامات خالص — الضهر المستوي قاعد على البليتة.
"""),
}
COMMON = """
إعدادات Bambu Studio للطابعة Bambu Lab A1:
- الخامة: PLA أو PLA Matte — فوهة 0.4
- البروفايل: 0.20mm Standard @BBL A1
- Wall loops = 3 — Sparse infill = 15% (Grid أو Gyroid)
- Top surface pattern = Monotonic line (علشان النقشة تطلع نضيفة)
- Ironing = مقفول (هيمسح النقشة)
- البليتة: Textured PEI
- ماتعملش Scale للموديل — هيبوّظ تركيب الحلقة في الإطار. لو محتاج مقاس تاني اطلبه.

لو الـ Slice وقف أو بطيء جدًا (عند Generating infill regions):
1. استنى دقيقتين — الإطار فيه نقشة كتير وأول Slice بياخد وقت على الأجهزة الضعيفة.
2. من Strength: خلّي Ensure vertical shell thickness = Moderate (أو Partial).
3. من Strength: اقفل Detect narrow internal solid infill.
4. خلّي Sparse infill pattern = Grid بدل Gyroid.
5. حدّث Bambu Studio لآخر نسخة.

التركيب:
1. افرد القماش على الحلقة البيضا.
2. اضغط الإطار عليها لحد ما تسمع "تكة": البروز اللي في نص الحلقة بيدخل في المجرى اللي جوه الإطار ويثبّتها.
3. شد القماش من الأطراف وقصّ الزيادة من ورا، وعلّق من الخرم اللي في البتلة اللي فوق.

لو التكة ناشفة أوي أو القماش تقيل → محتاج بروز أصغر (0.4 مم). لو الحلقة سايبة → بروز أكبر (0.6 مم).

المقاسات:
- 60 مم  → قطر الوردة 113 مم
- 80 مم  → قطر الوردة 139 مم
- 100 مم → قطر الوردة 165 مم
(كل مقاس: الإطار + الحلقة بيدخلوا على بليتة A1 واحدة)

جوه كل فولدر مقاس:
- بليتة_جاهزة_للطباعة_XXمم.3mf  ← افتحه في Bambu Studio واطبع على طول (الإطار + الحلقة)
- الإطار_XXمم.stl و الحلقة_XXمم.stl  ← نفس القطع لوحدها لو حابب ترتبهم بنفسك
"""
SIZES = (60, 80, 100)

def main():
    with zipfile.ZipFile("طارات_تطريز_وردة_Bambu_A1.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for tag, (folder, _, intro) in STYLES.items():
            z.writestr(f"{folder}/اقرأني_طريقة_الطباعة.txt", "﻿" + intro + COMMON)
            z.write("preview_v2.png", f"{folder}/صورة_المقطع_والوش_والضهر.png")
            for D in SIZES:
                sub = f"{folder}/مقاس_{D}_مم"
                z.write(f"stl/hoop_{D}mm_{tag}_plate.3mf", f"{sub}/بليتة_جاهزة_للطباعة_{D}مم.3mf")
                z.write(f"stl/hoop_{D}mm_{tag}_frame.stl", f"{sub}/الإطار_{D}مم.stl")
                z.write(f"stl/hoop_{D}mm_{tag}_ring.stl", f"{sub}/الحلقة_{D}مم.stl")
    shutil.rmtree("ملفات_STL", ignore_errors=True); os.makedirs("ملفات_STL")
    for tag, (_, fname, _) in STYLES.items():
        for D in SIZES:
            shutil.copy(f"stl/hoop_{D}mm_{tag}_frame.stl", f"ملفات_STL/{fname}_{D}مم.stl")
    for D in SIZES:
        shutil.copy(f"stl/hoop_{D}mm_2part_ring.stl", f"ملفات_STL/حلقة_{D}مم.stl")
    with zipfile.ZipFile("ملفات_STL_طارات_التطريز.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in sorted(glob.glob("ملفات_STL/*.stl")):
            z.write(f, f)
    for zp in ("طارات_تطريز_وردة_Bambu_A1.zip", "ملفات_STL_طارات_التطريز.zip"):
        zz = zipfile.ZipFile(zp); print(zp, len(zz.namelist()), "files", round(os.path.getsize(zp) / 1e6, 1), "MB", "ok" if zz.testzip() is None else "BAD")

if __name__ == "__main__":
    main()
