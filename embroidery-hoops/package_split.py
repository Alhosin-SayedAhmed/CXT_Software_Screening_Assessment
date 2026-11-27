"""Builds the organised zip for the two-half flower hoop (run make_hoops_split.py first)."""
import zipfile, os, glob
SIZES = (60, 80, 100)
W = {60: (16.6, 5.1), 80: (22.8, 6.7), 100: (29.6, 8.3)}      # frame (2 halves), ring - grams, estimated
README = """﻿طارة تطريز وردة — مزخرفة من الناحيتين — بتتطبع نصين
=====================================================
الطارة بتتطبع نصين متطابقين (متقسمة بالعرض من النص) + حلقة + مسامير منفصلة.
كل حاجة بتتطبع نايمة على البليتة **من غير أي دعامات**.

جوه كل فولدر مقاس:
  1_نص_الإطار_اطبعه_مرتين_XXمم.stl   ← اطبعه مرتين (وش وضهر). الناحية المستوية على البليتة والزخرفة لفوق.
  2_الحلقة_XXمم.stl                  ← مرة واحدة، واقفة زي ما هي في الملف.
  3_المسامير_4_قطع.stl                ← 4 مسامير (3 + واحد احتياطي)، نايمين على البليتة.
  بليتة_جاهزة_XXمم.3mf               ← كل القطع مترتبة على بليتة A1 (مقاس 100 على بليتتين).

الأوزان (تقريبية — الوزن الحقيقي يظهر في Bambu Studio بعد الـ Slice):
  60 مم : الإطار (النصين) ~16.6 جم + الحلقة ~5.1 جم   — الوردة 105 مم
  80 مم : الإطار (النصين) ~22.8 جم + الحلقة ~6.7 جم   — الوردة 130 مم
  100 مم: الإطار (النصين) ~29.6 جم + الحلقة ~8.3 جم   — الوردة 154 مم

إعدادات Bambu Studio (Bambu Lab A1):
  - PLA أو PLA Matte — فوهة 0.4 — 0.20mm Standard @BBL A1
  - Wall loops = 3 — Sparse infill = 15% Grid
  - Support = مقفول — البليتة Textured PEI
  - Top surface pattern = Monotonic line — Ironing = مقفول
  - المسامير صغيرة: لو اتحركت، شغّل Brim للمسامير بس (كليك يمين على المسامير ← Brim).
  - ماتعملش Scale لأي قطعة.

التركيب:
  1. حط نقطة سوبر جلو في كل خرم من الخروم التلاتة اللي في الناحية المستوية لنص من النصين، ودخّل المسامير.
  2. اقلب النص التاني (الزخرفة لتحت) وحطه فوقه — المسامير بتدخل في الخروم، وخرم التعليق بيقابل بعضه.
  3. اضغط دقيقة لحد ما الغرا يمسك.
  4. استخدم الطارة زي العادة: افرد القماش على الحلقة واضغط الإطار عليها لحد ما تسمع تكة
     (المجرى اللي الحلقة بتقفل فيه متقسم بين النصين في النص بالظبط).
"""
out = "طارة_الوردة_نصين_STL.zip"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    z.writestr("اقرأني_طريقة_الطباعة_والتركيب.txt", README)
    z.write("split_hoop_80mm.png", "صورة_الطارة_مقاس_80.png")
    for D in SIZES:
        sub = f"مقاس_{D}_مم"
        z.write(f"stl/split_{D}mm_half.stl", f"{sub}/1_نص_الإطار_اطبعه_مرتين_{D}مم.stl")
        z.write(f"stl/split_{D}mm_ring.stl", f"{sub}/2_الحلقة_{D}مم.stl")
        z.write("stl/split_pins.stl", f"{sub}/3_المسامير_4_قطع.stl")
        plates = sorted(glob.glob(f"stl/split_{D}mm_plate*.3mf"))
        for p in plates:
            tag = "" if len(plates) == 1 else ("_1_نص_وحلقة_ومسامير" if "1of2" in p else "_2_النص_التاني")
            z.write(p, f"{sub}/بليتة_جاهزة_{D}مم{tag}.3mf")
zz = zipfile.ZipFile(out)
print(out, len(zz.namelist()), "files", round(os.path.getsize(out) / 1e6, 1), "MB", "ok" if zz.testzip() is None else "BAD")
for n in zz.namelist(): print("  ", n)
