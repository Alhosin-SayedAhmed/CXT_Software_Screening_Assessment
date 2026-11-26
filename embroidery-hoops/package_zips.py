"""Builds the Arabic-named zip bundles from ./stl (run make_hoops_v2.py first)."""
import zipfile, os, shutil, glob
STYLES = {
 "2side": ("طارة_مزخرفة_من_الناحيتين", "إطار_مزخرف_من_الناحيتين", """طارة تطريز وردة — مزخرفة من الناحيتين (من غير دعامات)
==========================================
قطعتين: إطار حتة واحدة + حلقة بتتقفل جواه بتكة.
- الزخرفة: وردة صغيرة على كل بتلة + ورقتين بين كل بتلتين + خط متموّج على الحافة.
- الوش: الحافة الدايرية بارزة، الأطراف مدوّرة، والزخرفة بارزة 0.4 مم.
- الضهر (الناحية اللي على البليتة): نفس الزخرفة بارزة 0.6 مم + إطار بارز حوالين البتلات والحافة،
  والأرضية اللي بينهم غاطسة. حرف البتلات مشطوف.
- ارتفاع الحافة 9 مم — تخانة البتلات 4 مم.

✅ من غير دعامات خالص — اقفل Support. الزخرفة البارزة في الضهر هي اللي قاعدة على البليتة،
   والطابعة بتعدّي (Bridge) فوق الأرضية الغاطسة اللي بينهم — أطول مسافة 8 مم بالكتير.
   الزخرفة بتطلع بملمس البليتة (Textured PEI).
"""),
 "1side": ("طارة_مزخرفة_من_ناحية_واحدة", "إطار_مزخرف_من_ناحية_واحدة", """طارة تطريز وردة — مزخرفة من ناحية واحدة
==========================================
قطعتين: إطار حتة واحدة + حلقة بتتقفل جواه بتكة.
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

التركيب:
1. افرد القماش على الحلقة البيضا.
2. اضغط الإطار عليها لحد ما تسمع "تكة": البروز اللي في نص الحلقة بيدخل في المجرى اللي جوه الإطار ويثبّتها.
   (بتشتغل من أي ناحية، والحلقة بتبقى على مستوى الإطار من الوش والضهر.)
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
            z.write("motif_map_80mm.png", f"{folder}/صورة_الزخرفة_الوش.png")
            if tag == "2side": z.write("back_map_80mm.png", f"{folder}/صورة_الزخرفة_الضهر.png")
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

HEART = {
 "2side": ("قلب_مجسم_مزخرف_من_الناحيتين", "إطار_قلب_مجسم_مزخرف_من_الناحيتين",
           "طارة تطريز قلب مجسّم (منفوخ) — مزخرفة من الناحيتين (من غير دعامات)\n==========================================\n"
           "قطعتين: إطار قلب مجسّم حتة واحدة + حلقة دايرية في النص بتتقفل جواه بتكة\n"
           "(نفس حلقة الطارة الوردة بالظبط — الحلقات تركب على الاتنين).\n"
           "- الوش: القلب منفوخ زي المخدة (1.6 مم عند الحرف وبيعلى لحد 13.5 مم، والفتحة الدايرية غاطسة في النص)، وعليه ورود بارزة 0.6 مم ماشية مع النفخة،\n"
           "  والحافة الدايرية بارزة وعليها خط متموّج.\n"
           "- الضهر (على البليتة): مستوي، وعليه نفس الورود بارزة 0.6 مم والأرضية بينها غاطسة. حرف القلب مشطوف.\n"
           "- خرم التعليق فوق في نقرة القلب.\n\n"
           "✅ من غير دعامات خالص — اقفل Support. أطول مسافة Bridge فوق الأرضية الغاطسة 8 مم.\n"
           "💡 علشان النفخة تطلع ناعمة: كليك يمين على الإطار ← Variable layer height ← Adaptive (أو Smooth).\n"),
 "1side": ("قلب_مجسم_مزخرف_من_ناحية_واحدة", "إطار_قلب_مجسم_مزخرف_من_ناحية_واحدة",
           "طارة تطريز قلب مجسّم (منفوخ) — مزخرفة من ناحية واحدة\n==========================================\n"
           "قطعتين: إطار قلب مجسّم حتة واحدة + حلقة دايرية في النص بتتقفل جواه بتكة (نفس حلقة الوردة).\n"
           "- الوش: القلب منفوخ وعليه ورود بارزة ماشية مع النفخة + خط متموّج على الحافة.\n"
           "- الضهر: مستوي.\n\n✅ من غير دعامات خالص.\n"
           "💡 علشان النفخة تطلع ناعمة: كليك يمين على الإطار ← Variable layer height ← Adaptive (أو Smooth).\n"),
}
HEART_PREFIX = "heartp"
HEART_SIZES = """
المقاسات (قطر فتحة القماش الدايرية):
- 60 مم  → القلب 143 × 134 مم  (الإطار + الحلقة على بليتة واحدة)
- 80 مم  → القلب 172 × 161 مم  (الإطار + الحلقة على بليتة واحدة)
- 100 مم → القلب 202 × 189 مم  (بليتتين: الإطار لوحده، والحلقة لوحدها)
"""

def heart():
    common = COMMON[:COMMON.index("المقاسات:")] + HEART_SIZES + COMMON[COMMON.index("جوه كل فولدر مقاس:") - 1:]
    with zipfile.ZipFile("طارات_تطريز_قلب_Bambu_A1.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for tag, (folder, _, intro) in HEART.items():
            z.writestr(f"{folder}/اقرأني_طريقة_الطباعة.txt", "\ufeff" + intro + common)
            z.write("heart_puffy_80mm.png", f"{folder}/صورة_الوش_والضهر.png")
            for D in SIZES:
                sub = f"{folder}/مقاس_{D}_مم"
                plates = sorted(glob.glob(f"stl/{HEART_PREFIX}_{D}mm_{tag}_plate*.3mf"))
                for pth in plates:
                    part = "" if len(plates) == 1 else ("_1_الإطار" if "1of2" in pth else "_2_الحلقة")
                    z.write(pth, f"{sub}/بليتة_جاهزة_للطباعة_{D}مم{part}.3mf")
                z.write(f"stl/{HEART_PREFIX}_{D}mm_{tag}_frame.stl", f"{sub}/الإطار_{D}مم.stl")
                z.write(f"stl/{HEART_PREFIX}_{D}mm_{tag}_ring.stl", f"{sub}/الحلقة_{D}مم.stl")
    shutil.rmtree("ملفات_STL_قلب", ignore_errors=True); os.makedirs("ملفات_STL_قلب")
    for tag, (_, fname, _) in HEART.items():
        for D in SIZES:
            shutil.copy(f"stl/{HEART_PREFIX}_{D}mm_{tag}_frame.stl", f"ملفات_STL_قلب/{fname}_{D}مم.stl")
    for D in SIZES:
        shutil.copy(f"stl/{HEART_PREFIX}_{D}mm_2side_ring.stl", f"ملفات_STL_قلب/حلقة_{D}مم.stl")
    with zipfile.ZipFile("ملفات_STL_طارة_القلب.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in sorted(glob.glob("ملفات_STL_قلب/*.stl")):
            z.write(f, f)
    for zp in ("طارات_تطريز_قلب_Bambu_A1.zip", "ملفات_STL_طارة_القلب.zip"):
        zz = zipfile.ZipFile(zp); print(zp, len(zz.namelist()), "files", round(os.path.getsize(zp) / 1e6, 1), "MB", "ok" if zz.testzip() is None else "BAD")

if __name__ == "__main__":
    import sys
    if "--heart" in sys.argv: heart()
    else: main()
