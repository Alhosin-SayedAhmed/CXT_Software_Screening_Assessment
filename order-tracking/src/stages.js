// مراحل تجهيز الطلب بالترتيب.
// تقدر تعدّل الأسماء أو تزوّد/تشيل مراحل من هنا براحتك.
// key: اسم ثابت بالإنجليزي (ماتغيّروش بعد ما يبقى عندك طلبات)
// label: اللي العميل بيشوفه
// description: سطر توضيحي تحت المرحلة
const STAGES = [
  { key: 'received', label: 'تم استلام الطلب', description: 'وصلنا طلبك وتم تأكيده' },
  { key: 'preparing', label: 'جاري التجهيز', description: 'بنجهز الخامات والمكونات' },
  { key: 'manufacturing', label: 'جاري التصنيع', description: 'طلبك على خط التصنيع دلوقتي' },
  { key: 'quality', label: 'فحص الجودة', description: 'بنختبر المنتج قبل التغليف' },
  { key: 'completed', label: 'تم الانتهاء', description: 'المنتج جاهز ومتغلف' },
  { key: 'shipping', label: 'جاري الشحن', description: 'الطلب مع شركة الشحن' },
  { key: 'delivered', label: 'تم التوصيل', description: 'وصل الطلب للعميل' },
];

const STAGE_KEYS = STAGES.map((s) => s.key);

function isValidStage(key) {
  return STAGE_KEYS.includes(key);
}

module.exports = { STAGES, STAGE_KEYS, isValidStage };
