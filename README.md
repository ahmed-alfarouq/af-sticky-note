<div dir="rtl" align="right">

# 📌 Daily Sticky
### ملاحظتك اليومية الذكية على سطح المكتب

**الإصدار 0.5.0**

تطبيق سطح مكتب هادئ لا يفرض نفسه على مساحة عملك. تعيش الملاحظة خلف نوافذك، بلا ضجيج في شريط المهام، وتنظّم يومك بذكاء دون أن تطلب منك شيئًا.

---

<br>

## ✨ لماذا Daily Sticky؟

معظم تطبيقات الملاحظات تتصرف كأنها نافذة عادية: تظهر في شريط المهام، تقاطعك عند التبديل بين التطبيقات (Alt+Tab)، وتنسى ما فعلته بالأمس. Daily Sticky مبني على فكرة مختلفة: **ملاحظة تعيش على سطح المكتب نفسه**، كأنها جزء منه، لا نافذة تتنافس معه.

---

<br>

## 🧩 الميزات الأساسية

<table dir="rtl" style="width:100%;">
<tr><th style="text-align: right;">الميزة</th><th style="text-align: right;">الوصف</th></tr>
<tr ><td style="padding: 13px 0;"><b>Desktop Layer</b></td><td style="padding: 13px 0;">تبقى الملاحظة مثبّتة خلف النوافذ العادية، ومستبعدة تمامًا من شريط المهام (Taskbar) ومبدّل النوافذ (Alt+Tab)</td></tr>
<tr><td style="padding: 13px 0;"><b>Daily Rollover</b></td><td style="padding: 13px 0;">عند منتصف الليل، تُرحَّل المهام غير المنجزة تلقائيًا لليوم الجديد، بينما يبقى سجل الأيام السابقة محفوظًا وغير قابل للتعديل</td></tr>
<tr><td style="padding: 13px 0;"><b>حكمة اليوم والتقويم المزدوج</b></td><td style="padding: 13px 0;">عرض التاريخ بالتقويمين الهجري والميلادي معًا، مع اقتباس يومي متجدد</td></tr>
<tr><td style="padding: 13px 0;"><b>تفاعل غني مع المهام</b></td><td style="padding: 13px 0;">قائمة سياقية (Context Menu) بزر الفأرة الأيمن للتعديل والحذف وتنظيف المهام المنجزة، مع تمييز بصري واضح للأولويات</td></tr>
<tr><td style="padding: 13px 0;"><b>History</b></td><td style="padding: 13px 0;">نافذة مخصّصة لاستعراض أرشيف الأيام ونسب الإنجاز، للقراءة فقط وبدون تدخّل عرضي في البيانات القديمة</td></tr>
<tr><td style="padding: 13px 0;"><b>Geometry Persistence</b></td><td style="padding: 13px 0;">تتذكّر الملاحظة مكانها وأبعادها وتستعيدهما بأمان، حتى في إعدادات الشاشات المتعددة</td></tr>
<tr><td style="padding: 13px 0;"><b>System Tray</b></td><td style="padding: 13px 0;">تحكّم كامل بإظهار الملاحظة وإخفائها من الـ Tray، مع زر خروج علوي يسار لإنهاء التطبيق بالكامل</td></tr>
<tr><td style="padding: 13px 0;"><b>Windows Startup</b></td><td style="padding: 13px 0;">خيار اختياري لتشغيل التطبيق عند بدء ويندوز، عبر الـ Registry ودون الحاجة لصلاحيات Admin</td></tr>
</table>

<br clear="both">

---

## 💻 متطلبات التشغيل

- **نظام التشغيل:** Microsoft Windows 10 / 11 (64-bit)
- **بيئة التطوير:** Python 3.10 أو أحدث، مع مكتبة PySide6

---

<br>

## 🛠️ الإعداد لبيئة التطوير

اتبع الخطوات التالية لتشغيل المشروع محليًا:

**1. إنشاء البيئة الافتراضية وتفعيلها**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**2. تثبيت الحزم المطلوبة**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

**3. تشغيل التطبيق**
```bash
python run.py
```

**4. تشغيل الاختبارات**
```bash
python scripts/run_all_backend_tests.py
```

---

<br>

## 📦 بناء الحزمة والمثبّت

يعتمد المشروع على **PyInstaller** لإنتاج نسخة تنفيذية مستقلة (onedir)، وعلى **Inno Setup** لتوليد ملف تثبيت جاهز للتوزيع.

**لتشغيل سكربت البناء التلقائي (PowerShell):**
```powershell
powershell -ExecutionPolicy Bypass -File packaging/build_windows.ps1
```

**مخرجات البناء:**

<table dir="rtl" style="width:100%; margin: 16px 0;">
<tr><th align="right">العنصر</th><th align="right">المسار</th></tr>
<tr><td align="right">النسخة التنفيذية</td><td align="right"><code>dist/DailySticky/DailySticky.exe</code></td></tr>
<tr><td align="right">ملف التثبيت</td><td align="right"><code>dist/installer/DailySticky-Setup-0.5.0.exe</code></td></tr>
</table>

<br clear="both">

---

<br>


## 🗄️ تخزين بيانات المستخدم

تُحفظ قاعدة بيانات SQLite الخاصة بالمستخدم في مسار مستقل، بحيث لا تتأثر بتحديث التطبيق أو إزالته:

```
%LOCALAPPDATA%\DailySticky\daily_sticky.db
```

---

<br>

## ⚠️ قيود معروفة

- **اختصار إظهار سطح المكتب (Win+D):** يؤدي هذا الاختصار إلى إخفاء الملاحظة مؤقتًا خلف سطح مكتب Explorer (Progman). يمكن إعادة إظهارها بالنقر على أيقونة صينية النظام، أو بالنقر على سطح المكتب مباشرة. هذا السلوك معروف ومؤجَّل لإصدار لاحق.

---

<br>

<p align="center"><i>Daily Sticky — يبقى في مكانه، ليبقيك أنت في المسار الصحيح.</i></p>

</div>