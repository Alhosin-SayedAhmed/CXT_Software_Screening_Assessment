// مراحل تجهيز الطلب بالترتيب.
// تقدر تعدّل الأسماء أو تزوّد/تشيل مراحل من هنا براحتك.
// key: اسم ثابت بالإنجليزي (ماتغيّروش بعد ما يبقى عندك طلبات)
// label: اللي العميل بيشوفه
// description: سطر توضيحي تحت المرحلة
// icon: شكل الأيقونة المتحركة. المتاح: clipboard, box, gear, shield, package, truck, home, check
const STAGES = [
  { key: 'received', icon: 'clipboard', label: 'تم استلام الطلب', description: 'وصلنا طلبك وتم تأكيده' },
  { key: 'preparing', icon: 'box', label: 'جاري التجهيز', description: 'بنجهز الخامات والمكونات' },
  { key: 'manufacturing', icon: 'gear', label: 'جاري التصنيع', description: 'طلبك على خط التصنيع دلوقتي' },
  { key: 'quality', icon: 'shield', label: 'فحص الجودة', description: 'بنختبر المنتج قبل التغليف' },
  { key: 'completed', icon: 'package', label: 'تم الانتهاء', description: 'المنتج جاهز ومتغلف' },
  { key: 'shipping', icon: 'truck', label: 'جاري الشحن', description: 'الطلب مع شركة الشحن' },
  { key: 'delivered', icon: 'home', label: 'تم التوصيل', description: 'وصل الطلب للعميل' },
];

const STAGE_KEYS = STAGES.map((s) => s.key);

function isValidStage(key) {
  return STAGE_KEYS.includes(key);
}

module.exports = { STAGES, STAGE_KEYS, isValidStage };
