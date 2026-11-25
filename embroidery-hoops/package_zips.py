"""Builds the Arabic-named zip bundles from ./stl (run make_hoops_v2.py first)."""
import zipfile, os, shutil, glob
STYLES = {
 "2side": ("طارة_مزخرفة_من_الناحيتين", "إطار_مزخرف_من_الناحيتين", """طارة تطريز وردة — مزخرفة من الناحيتين (من غير دعامات)
==========================================
قطعتين: إطار حتة واحدة + حلقة بتتكبس من الوش وتزنق القماش وتقف على حافة في الضهر.
- الزخرفة: وردة صغيرة على كل بتلة + ورقتين بين كل بتلتين + خط متموّج على الحافة.
- الوش: الحافة الدايرية بارزة، الأطراف مدوّرة، والزخرفة بارزة 0.4 مم.
- الضهر (الناحية اللي على البليتة): مستوي، وعليه نفس الزخرفة محفورة 0.6 مم، وحرف البتلات مشطوف.
- ارتفاع الحافة 9 مم — تخانة البتلات 4 مم.

✅ من غير دعامات خالص — اقفل Support. الضهر قاعد على البليتة، والزخرفة المحفورة بتطلع
   بملمس البليتة (Textured PEI) والطبقة اللي فوقها بتعدّي عليها (Bridge) لوحدها.
"""),
 "1side": ("طارة_مزخرفة_من_ناحية_واحدة", "إطار_مزخرف_من_ناحية_واحدة", """طارة تطريز وردة — مزخرفة من ناحية واحدة
==========================================
قطعتين: إطار حتة واحدة + حلقة بتتكبس من الوش وتزنق القماش وتقف على حافة في الضهر.
- الوش: الحافة الدايرية بارزة، الأطراف مدوّرة، وزخرفة بارزة 0.4 مم
  (وردة صغيرة على كل بتلة + ورقتين بين كل بتلتين + خط متموّج على الحافة).
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
- Top surface pattern = Monotonic line (علشان الزخرفة تطلع نضيفة)
- Support = مقفول
- Ironing = مقفول (هيمسح الزخرفة)
- البليتة: Textured PEI
- ماتعملش Scale للموديل — هيبوّظ تركيب الحلقة في الإطار. لو محتاج مقاس تاني اطلبه.

لو الـ Slice وقف أو بطيء جدًا (عند Generating infill regions):
1. استنى دقيقتين — الإطار فيه نقشة كتير وأول Slice بياخد وقت على الأجهزة الضعيفة.
2. من Strength: خلّي Ensure vertical shell thickness = Moderate (أو Partial).
3. من Strength: اقفل Detect narrow internal solid infill.
4. خلّي Sparse infill pattern = Grid بدل Gyroid.
5. حدّث Bambu Studio لآخر نسخة.

التركيب (الحلقة بتدخل من الوش، وبتقف على حافة من ورا وماتطلعش من الضهر):
1. حط الإطار على ضهره (الزخرفة البارزة لفوق) على الترابيزة.
2. افرد القماش على فتحة الإطار من قدام، ووش التطريز لفوق.
3. دخّل الحلقة البيضا من قدام — الناحية المشطوفة (الأضيق) هي اللي تدخل الأول — واكبسها لحد
   ما تقف على الحافة اللي في ضهر الإطار، وتبقى على مستوى واحد مع وش الإطار زي الصورة.
   الحلقة والفتحة مخروطيين (Taper)، فكل ما تكبس أكتر القماش بيتزنق أكتر.
4. شد القماش من الأطراف وقصّ الزيادة من ورا، وعلّق من الخرم اللي في البتلة اللي فوق.
5. علشان تطلّع الحلقة: ادفعها من ورا لقدام (من نفس الناحية اللي دخلت منها).

الحلقة بتتطبع زي ما هي في الملف (الناحية العريضة على البليتة)، وبعدين تقلبها وتدخلها بالناحية الأضيق.
لو القماش رفيع والحلقة لسه مش زانقة كفاية → اطلب نسخة بخلوص أقل (FABRIC_GAP 0.25).
لو القماش تقيل والحلقة مش راضية تدخل للآخر → اطلب نسخة بخلوص أكبر (FABRIC_GAP 0.5).

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
            z.write("motif_map_80mm.png", f"{folder}/صورة_الزخرفة.png")
            z.write("section_compare_80mm.png", f"{folder}/صورة_المقطع.png")
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
        shutil.copy(f"stl/hoop_{D}mm_2side_ring.stl", f"ملفات_STL/حلقة_{D}مم.stl")
    with zipfile.ZipFile("ملفات_STL_طارات_التطريز.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in sorted(glob.glob("ملفات_STL/*.stl")):
            z.write(f, f)
    # backup: same hoops without decoration (if a slicer still struggles)
    with zipfile.ZipFile("نسخة_احتياطي_من_غير_زخرفة.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for tag, (_, fname, _) in STYLES.items():
            for D in SIZES:
                z.write(f"stl/hoop_{D}mm_{tag}_smooth_frame.stl", f"من_غير_زخرفة/{fname.replace('مزخرف', 'ناعم')}_{D}مم.stl")
        for D in SIZES:
            z.write(f"stl/hoop_{D}mm_2side_smooth_ring.stl", f"من_غير_زخرفة/حلقة_{D}مم.stl")
    for zp in ("طارات_تطريز_وردة_Bambu_A1.zip", "ملفات_STL_طارات_التطريز.zip", "نسخة_احتياطي_من_غير_زخرفة.zip"):
        zz = zipfile.ZipFile(zp); print(zp, len(zz.namelist()), "files", round(os.path.getsize(zp) / 1e6, 1), "MB", "ok" if zz.testzip() is None else "BAD")

if __name__ == "__main__":
    main()
