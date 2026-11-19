"""Telegram-native menus; the user's Telegram theme controls bubble/button colors."""
LANGS=('uz','ru','en')
TEXT={
 'welcome':('👋 NAVBOT’ga xush kelibsiz!\nHEMIS ID raqamingizni kiriting.','👋 Добро пожаловать в NAVBOT!\nВведите свой HEMIS ID.','👋 Welcome to NAVBOT!\nEnter your HEMIS ID.'),
 'code':('Xodim shaxsingizni tekshirgach bergan bir martalik kodni kiriting.','Введите одноразовый код, выданный сотрудником после проверки личности.','Enter the one-time code issued by staff after checking your identity.'),
 'bad_id':('HEMIS ID formatini tekshiring. Qayta boshlash: /start','Проверьте формат HEMIS ID. Начать заново: /start','Check the HEMIS ID format. Start again: /start'),
 'bad_code':('ID yoki kod noto‘g‘ri, eskirgan yoki ishlatilgan. Qayta boshlash: /start','ID или код неверен, просрочен или использован. Начать заново: /start','The ID or code is invalid, expired or already used. Start again: /start'),
 'locked':('Urinishlar ko‘p bo‘ldi. 15 daqiqadan keyin qayta urinib ko‘ring.','Слишком много попыток. Повторите через 15 минут.','Too many attempts. Please try again in 15 minutes.'),
 'linked':('✅ Shaxsingiz tasdiqlandi. Telegram hisobingiz bog‘landi.','✅ Личность подтверждена. Telegram привязан.','✅ Identity confirmed. Your Telegram account is linked.'),
 'menu':('Asosiy menyu','Главное меню','Main menu'),
 'requests':('📋 Murojaatlarim','📋 Мои обращения','📋 My requests'),
 'track':('📍 Jarayonni kuzatish','📍 Отследить процесс','📍 Track progress'),
 'profile':('👤 Profilim','👤 Мой профиль','👤 My profile'),
 'help':('❓ Yordam','❓ Помощь','❓ Help'),
 'language':('🌐 Til','🌐 Язык','🌐 Language'),
 'help_text':('Murojaatingizni xodim kelganingizda yoki telefon orqali rasmiylashtiradi. Botda o‘z murojaatlaringiz holatini kuzatasiz. Javob va tanlangan fayllar faqat rahbar tasdig‘idan keyin yuboriladi. Bog‘lash yoki kod uchun xodimga murojaat qiling.','Сотрудник оформляет обращение лично или по телефону. В боте можно отслеживать свои обращения. Ответ и выбранные файлы отправляются только после утверждения руководителем. Для привязки и кода обратитесь к сотруднику.','Staff register your request in person or by phone. Track your own requests here. Answers and selected files are sent only after approval. Contact staff for verification and a linking code.'),
 'choose_language':('Tilni tanlang:','Выберите язык:','Choose your language:'),
 'choose_request':('Kuzatish uchun murojaatni tanlang:','Выберите обращение для отслеживания:','Choose a request to track:'),
 'your_requests':('Sizning murojaatlaringiz:','Ваши обращения:','Your requests:'),
 'none':('Hozircha murojaat yo‘q. Xodim uni sizning HEMIS ID bilan rasmiylashtiradi.','Обращений пока нет. Сотрудник зарегистрирует их с вашим HEMIS ID.','No requests yet. Staff will register them using your HEMIS ID.'),
 'missing':('Murojaat topilmadi yoki ko‘rish uchun ruxsat yo‘q.','Обращение не найдено или недоступно.','Request not found or access denied.'),
 'inactive':('Hisobingiz faol emas yoki talabalar bazasida yo‘q. Xodimga murojaat qiling.','Учётная запись неактивна или отсутствует в базе. Обратитесь к сотруднику.','Your student record is inactive or unavailable. Contact staff.'),
 'details':('Batafsil','Подробнее','Details'),
 'answer':('Javobni ko‘rish','Посмотреть ответ','View answer'),
 'back':('Ortga','Назад','Back'),
 'previous':('Oldingi','Предыдущая','Previous'),
 'next':('Keyingi','Следующая','Next'),
 'status':('Holat','Статус','Status'),
 'new':('Qabul qilindi','Принято','Received'),
 'in_progress':('Jarayonda','В работе','In progress'),
 'returned':('Qayta ko‘rib chiqilmoqda','На доработке','Under revision'),
 'pending_approval':('Rahbar tasdig‘i kutilmoqda','Ожидает утверждения','Awaiting approval'),
 'closed':('Yakunlangan','Завершено','Closed'),
 'approved':('Tasdiqlandi','Утверждено','Approved'),
 'assigned':('Bo‘limga yo‘naltirildi','Передано в отдел','Assigned to a department'),
 'prepared':('Javob tayyorlandi','Ответ подготовлен','Answer prepared'),
 'delivery':('Talabaga yuboriladi','Отправка студенту','Delivery to student'),
 'delivered':('Talabaga yuborildi','Отправлено студенту','Delivered to student'),
 'not_approved':('Yakuniy javob Telegram orqali yuborish uchun hali tasdiqlanmagan.','Итоговый ответ ещё не утверждён для отправки через Telegram.','The final answer has not been approved for Telegram delivery yet.'),
 'wait':('Tasdiqlangach, javob shu yerga keladi.','После утверждения ответ придёт сюда.','Your answer will arrive here after approval.'),
 'update':('Holatni yangilash','Обновить статус','Refresh status'),
 'phone':('Telefon orqali','По телефону','By phone'),
 'kiosk':('Kiosk orqali','Через киоск','Via kiosk'),
 'group':('Guruh','Группа','Group'),
 'faculty':('Fakultet','Факультет','Faculty'),
 'specialty':('Mutaxassislik shifri','Код специальности','Specialty code'),
 'course':('Kurs','Курс','Year'),
 'form':('Ta’lim shakli','Форма обучения','Mode of study'),
 'type':('Ta’lim turi','Уровень образования','Education level'),
 'verified':('Hisob: Tasdiqlangan','Аккаунт: Подтверждён','Account: Verified'),
 'deadline':('Muddat','Срок','Deadline'),
 'flood':('Iltimos, biroz kutib qayta bosing.','Подождите немного и повторите.','Please wait a little before trying again.'),
}


def uz(text):
    """Apply the same Uzbek alphabet used by the staff UI, to UI text only."""
    import re
    text=re.sub(r"([OoGg])[‘’ʻʼ'`]",lambda m:{'O':'Ö','o':'ö','G':'Ğ','g':'ğ'}[m[1]],text)
    for source,target in (('SH','Ş'),('Sh','Ş'),('sh','ş'),('CH','Ç'),('Ch','Ç'),('ch','ç')):
        text=text.replace(source,target)
    return text


def labels(key):
    # Accept buttons sent before the alphabet update as well as the new labels.
    return tuple(TEXT[key])+tuple(t(key,lang) for lang in LANGS)


def t(key,lang='uz'):
    index=LANGS.index(lang) if lang in LANGS else 0
    return uz(TEXT[key][index]) if index==0 else TEXT[key][index]


def main_keyboard(lang):
    return {'keyboard':[[{'text':t('requests',lang)},{'text':t('track',lang)}],[{'text':t('profile',lang)},{'text':t('help',lang)}],[{'text':t('language',lang)}]],'resize_keyboard':True,'is_persistent':True}


def languages():
    return {'inline_keyboard':[[{'text':'Özbekça','callback_data':'lang:uz'},{'text':'Русский','callback_data':'lang:ru'},{'text':'English','callback_data':'lang:en'}]]}
