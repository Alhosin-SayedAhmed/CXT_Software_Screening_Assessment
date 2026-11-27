"""
Builds ONE organised master folder (and zip) with every current hoop design:

طارات_التطريز_كل_الملفات/
  00_اقرأني_الأول.txt
  01_وردة_نصين_مزخرفة_من_الناحيتين/   مقاس_60_مم/ STL + 3MF_جاهز_للطباعة ...
  02_قلب_نصين_مزخرف_من_الناحيتين/
  03_وردة_حتة_واحدة/  أ_مزخرفة_من_الناحيتين / ب_مزخرفة_من_ناحية_واحدة
  04_قلب_مجسم_حتة_واحدة/  أ_... / ب_...
  05_احتياطي_وردة_من_غير_زخرفة/

Run the generators first (make_hoops_split.py, make_heart_split.py, make_hoops_v2.py [--smooth],
make_heart_puffy.py).
"""
import os, shutil, glob, zipfile

ROOT = "طارات_التطريز_كل_الملفات"
SIZES = (60, 80, 100)
BOM = "﻿"

SETTINGS = """
إعدادات Bambu Studio (Bambu Lab A1) — لكل الملفات:
  - PLA أو PLA Matte — فوهة 0.4 — 0.20mm Standard @BBL A1
  - Wall loops = 3 — Sparse infill = 15% Grid — البليتة Textured PEI
  - Support = مقفول (كل الملفات معمولة تتطبع من غير دعامات)
  - Top surface pattern = Monotonic line — Ironing = مقفول
  - ماتعملش Scale لأي قطعة (هيبوّظ تركيب الحلقة والمسامير).
  - لو الضهر فيه زخرفة بارزة على البليتة: Thick bridges = مقفول، Bridge flow = 0.85،
    سرعة الـ Bridge = 25–30، ومروحة الـ Bridges = 100%.
  - القلب المجسّم: كليك يمين على الإطار ← Variable layer height ← Adaptive علشان النفخة تطلع ناعمة.
"""

PINS = """
المسامير والتركيب:
  - المسامير منفصلة (ملف المسامير فيه 4: 3 + واحد احتياطي)، بتتطبع نايمة على البليتة.
  - كل نص فيه 3 خروم محفورة في الناحية المستوية. المسمار 2.5 مم والخرم 2.6 مم — مزنوق.
  1. دخّل المسامير التلاتة في خروم نص.
  2. اقلب النص التاني وحطه فوقه: المسامير بتدخل في خرومه، وخرم التعليق بيقابل بعضه.
  3. اضغطهم (ونقطة سوبر جلو في الخروم لو عايز تثبيت دايم).
  4. افرد القماش على الحلقة واضغط الإطار عليها لحد ما تسمع تكة.
  لو المسامير مش راضية تدخل → اطلب خرم 2.7 مم. لو سايبة → خرم 2.55 مم.
"""

SNAP = """
التركيب:
  1. افرد القماش على الحلقة البيضا.
  2. اضغط الإطار عليها لحد ما تسمع تكة (البروز اللي في نص الحلقة بيدخل في المجرى اللي جوه الإطار).
  3. شد القماش من الأطراف وقصّ الزيادة من ورا، وعلّق من خرم التعليق.
"""

# design key -> (folder, readme text, image(s), list of variants)
# variant = (sub-folder or "", file builder(D) -> list of (src, dst-name-in-STL-folder), plate globs)
def files_split(prefix):
    def f(D):
        return [(f"stl/{prefix}_{D}mm_half.stl", f"1_نص_الإطار_اطبعه_مرتين_{D}مم.stl"),
                (f"stl/{prefix}_{D}mm_ring.stl", f"2_الحلقة_{D}مم.stl"),
                ("stl/split_pins.stl", "3_المسامير_4_قطع.stl")]
    return f

def files_onepiece(prefix, tag):
    def f(D):
        return [(f"stl/{prefix}_{D}mm_{tag}_frame.stl", f"1_الإطار_{D}مم.stl"),
                (f"stl/{prefix}_{D}mm_{tag}_ring.stl", f"2_الحلقة_{D}مم.stl")]
    return f

def plate_name(D, path, all_paths):
    if len(all_paths) == 1:
        return f"بليتة_جاهزة_{D}مم.3mf"
    k = all_paths.index(path) + 1
    return f"بليتة_{k}_من_{len(all_paths)}_{D}مم.3mf"

DESIGNS = [
 ("01_وردة_نصين_مزخرفة_من_الناحيتين",
  "طارة وردة — نصين متطابقين — مزخرفة من الناحيتين (من غير دعامات)\n"
  "==============================================================\n"
  "اطبع نص الإطار مرتين (الناحية المستوية على البليتة والزخرفة لفوق) + الحلقة + ملف المسامير.\n\n"
  "  مقاس 60 : الوردة 105 مم — الإطار ~16.6 جم + الحلقة ~5.1 جم\n"
  "  مقاس 80 : الوردة 130 مم — الإطار ~22.8 جم + الحلقة ~6.7 جم\n"
  "  مقاس 100: الوردة 154 مم — الإطار ~29.6 جم + الحلقة ~8.3 جم (بليتتين)\n" + PINS,
  ["split_hoop_80mm.png"], [("", files_split("split"), "split_{D}mm_plate*.3mf")]),
 ("02_قلب_نصين_مزخرف_من_الناحيتين",
  "طارة قلب مجسّم — نصين متطابقين — منفوخ ومزخرف بقلوب من الناحيتين (من غير دعامات)\n"
  "==============================================================\n"
  "اطبع نص القلب مرتين (الناحية المستوية على البليتة والنفخة لفوق) + الحلقة + ملف المسامير.\n"
  "الحلقة والمسامير نفس بتوع الوردة النصين بالظبط.\n\n"
  "  مقاس 60 : القلب 135 × 126 مم — الإطار ~37 جم + الحلقة ~5.1 جم\n"
  "  مقاس 80 : القلب 164 × 153 مم — الإطار ~52 جم + الحلقة ~6.7 جم\n"
  "  مقاس 100: القلب 193 × 181 مم — الإطار ~69 جم + الحلقة ~8.3 جم\n"
  "كل مقاس على بليتتين: (1) نص + حلقة + مسامير، (2) النص التاني.\n" + PINS,
  ["heart_split_80mm.png"], [("", files_split("hsplit"), "hsplit_{D}mm_plate_*.3mf")]),
 ("03_وردة_حتة_واحدة",
  "طارة وردة — الإطار حتة واحدة + حلقة بتكة (من غير دعامات)\n"
  "==============================================================\n"
  "أ: مزخرفة من الناحيتين — الضهر على البليتة وعليه الزخرفة بارزة والأرضية غاطسة.\n"
  "ب: مزخرفة من ناحية واحدة — الضهر مستوي.\n\n"
  "  مقاس 60: الوردة 113 مم — مقاس 80: 139 مم — مقاس 100: 165 مم (الإطار + الحلقة على بليتة واحدة)\n" + SNAP,
  ["motif_map_80mm.png", "back_map_80mm.png", "section_compare_80mm.png"],
  [("أ_مزخرفة_من_الناحيتين", files_onepiece("hoop", "2side"), "hoop_{D}mm_2side_plate*.3mf"),
   ("ب_مزخرفة_من_ناحية_واحدة", files_onepiece("hoop", "1side"), "hoop_{D}mm_1side_plate*.3mf")]),
 ("04_قلب_مجسم_حتة_واحدة",
  "طارة قلب مجسّم (منفوخ لحد 13.5 مم) — الإطار حتة واحدة + حلقة دايرية بتكة (من غير دعامات)\n"
  "==============================================================\n"
  "أ: مزخرف من الناحيتين (قلوب بارزة على النفخة + نفس القلوب بارزة على الضهر).\n"
  "ب: مزخرف من ناحية واحدة (الضهر مستوي).\n\n"
  "  مقاس 60 : القلب 143 × 134 مم — مقاس 80: 172 × 161 مم — مقاس 100: 202 × 189 مم (بليتتين)\n" + SNAP,
  ["heart_puffy_80mm.png", "heart_motif_map_80mm.png"],
  [("أ_مزخرف_من_الناحيتين", files_onepiece("heartp", "2side"), "heartp_{D}mm_2side_plate*.3mf"),
   ("ب_مزخرف_من_ناحية_واحدة", files_onepiece("heartp", "1side"), "heartp_{D}mm_1side_plate*.3mf")]),
 ("05_احتياطي_وردة_من_غير_زخرفة",
  "نسخة احتياطي: نفس طارة الوردة الحتة الواحدة بس من غير زخرفة (لو الـ Slicer علّق).\n"
  "==============================================================\n" + SNAP,
  [],
  [("أ_من_الناحيتين", files_onepiece("hoop", "2side_smooth"), "hoop_{D}mm_2side_smooth_plate*.3mf"),
   ("ب_من_ناحية_واحدة", files_onepiece("hoop", "1side_smooth"), "hoop_{D}mm_1side_smooth_plate*.3mf")]),
]

INDEX = BOM + """طارات التطريز — كل الملفات (Bambu Lab A1)
==========================================
كل تصميم في فولدر لوحده، وجوه كل تصميم فولدر لكل مقاس (60 / 80 / 100 مم = قطر فتحة القماش)،
وجوه كل مقاس:
   STL/                    ← القطع لوحدها، مترقّمة بالترتيب (اطبع كل واحدة على حسب اسمها)
   3MF_جاهز_للطباعة/       ← نفس القطع مترتبة على بليتة A1 — افتحه في Bambu Studio واطبع على طول

01_وردة_نصين_مزخرفة_من_الناحيتين   ← الأخف: نصين متطابقين + حلقة + مسامير منفصلة
02_قلب_نصين_مزخرف_من_الناحيتين     ← قلب منفوخ من الناحيتين: نصين + حلقة + مسامير
03_وردة_حتة_واحدة                  ← إطار حتة واحدة + حلقة بتكة (أ: من الناحيتين، ب: من ناحية واحدة)
04_قلب_مجسم_حتة_واحدة              ← قلب منفوخ حتة واحدة + حلقة دايرية (أ / ب)
05_احتياطي_وردة_من_غير_زخرفة        ← نفس 03 من غير زخرفة

الحلقات: حلقة الوردة والقلب في نفس المقاس واحدة (01 و 02 نفس الحلقة، 03 و 04 نفس الحلقة).
""" + SETTINGS

def build():
    shutil.rmtree(ROOT, ignore_errors=True)
    os.makedirs(ROOT)
    with open(os.path.join(ROOT, "00_اقرأني_الأول.txt"), "w", encoding="utf-8") as fh:
        fh.write(INDEX)
    for folder, text, images, variants in DESIGNS:
        dpath = os.path.join(ROOT, folder); os.makedirs(dpath)
        with open(os.path.join(dpath, "اقرأني.txt"), "w", encoding="utf-8") as fh:
            fh.write(BOM + text + SETTINGS)
        if images:
            ipath = os.path.join(dpath, "صور"); os.makedirs(ipath)
            for k, img in enumerate(images, 1):
                shutil.copy(img, os.path.join(ipath, f"صورة_{k}.png"))
        for sub, files, plate_glob in variants:
            vpath = os.path.join(dpath, sub) if sub else dpath
            for D in SIZES:
                spath = os.path.join(vpath, f"مقاس_{D}_مم")
                os.makedirs(os.path.join(spath, "STL")); os.makedirs(os.path.join(spath, "3MF_جاهز_للطباعة"))
                for src, name in files(D):
                    shutil.copy(src, os.path.join(spath, "STL", name))
                plates = sorted(glob.glob(os.path.join("stl", plate_glob.format(D=D))))
                assert plates, (folder, sub, D)
                for p in plates:
                    shutil.copy(p, os.path.join(spath, "3MF_جاهز_للطباعة", plate_name(D, p, plates)))
    # zips: everything, and STL only
    def zipdir(out, only_stl=False):
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for base, _, names in sorted(os.walk(ROOT)):
                for n in sorted(names):
                    full = os.path.join(base, n)
                    if only_stl and n.endswith(".3mf"): continue
                    z.write(full, full)
        zz = zipfile.ZipFile(out)
        print(out, len(zz.namelist()), "files", round(os.path.getsize(out) / 1e6, 1), "MB", "ok" if zz.testzip() is None else "BAD")
    zipdir(ROOT + ".zip")
    zipdir(ROOT + "_STL_بس.zip", only_stl=True)

if __name__ == "__main__":
    build()
