/* UI-only translation catalog. User-provided names, notes, answers and content never pass through this helper. */
'use strict';
window.NavI18n=(()=>{
const rows=`
Xodimlar faolligi, kiriş urinishlari va xavfsizlik hodisalari.|Активность сотрудников, попытки входа и события безопасности.|Staff activity, sign-in attempts and security events.
Xodim / login|Сотрудник / логин|Staff / username
IP manzil|IP-адрес|IP address
Xavf darajasi|Уровень риска|Risk level
Hodisa turi|Тип события|Event type
Muvaffaqiyatli|Успешно|Successful
Rad etilgan / xato|Отказ / ошибка|Rejected / failed
Filtrlaş|Применить фильтр|Apply filters
Filtrni tozalaş|Сбросить фильтр|Clear filters
Brauzer xabarlari|Уведомления браузера|Browser notifications
Oddiy|Обычный|Normal
Ogohlantiriş|Предупреждение|Warning
Şubhali|Подозрительный|Suspicious
Jiddiy|Критический|Critical
Iş amali|Рабочая операция|Business action
Faollik|Активность|Activity
Avtomatik sörovlar|Автоматические запросы|Automatic requests
Kiriş|Вход|Sign-in
Yuklaş|Загрузка|Upload
Yuklab oliş|Скачивание|Download
Xavfsizlik|Безопасность|Security
Bloklangan|Заблокировано|Blocked
Tekşiruv|Проверка|Validation
Vaqtincha bloklangan IP manzillar|Временно заблокированные IP-адреса|Temporarily blocked IP addresses
Blokdan çiqariş|Разблокировать|Unblock
IP blokdan çiqarildi|IP разблокирован|IP unblocked
Usul / manzil|Метод / адрес|Method / path
Fayl / hajm|Файл / размер|File / size
Sörovlar soni|Число запросов|Request count
Audit sahifalari|Страницы аудита|Audit pages
Auditni oçiş|Открыть аудит|Open audit
Sörov: {size} KB|Запрос: {size} КБ|Request: {size} KB
Javob: {size} KB|Ответ: {size} КБ|Response: {size} KB
Brauzer xabarlari uçun HTTPS kerak|Для уведомлений браузера нужен HTTPS|Browser notifications require HTTPS
Brauzer xabarlari yoqildi|Уведомления браузера включены|Browser notifications enabled
Brauzer xabarlari rad etildi|Уведомления браузера отклонены|Browser notifications denied
Brauzer xabarlari qöllanmaydi|Уведомления браузера не поддерживаются|Browser notifications are not supported
Parol, sessiya kaliti va fayl mazmuni yozilmaydi. Takroriy avtomatik sörovlar daqiqalik hisoblagichda jamlanadi.|Пароли, ключи сеансов и содержимое файлов не записываются. Повторные автоматические запросы учитываются поминутно.|Passwords, session keys and file contents are not logged. Repeated automatic requests are counted per minute.
Muvaffaqiyatsiz kiriş|Неудачный вход|Failed sign-in
Vakolat rad etildi|Доступ запрещён|Permission denied
Maxfiy manzilni qidiriş|Поиск закрытых адресов|Sensitive path probe
IP bloklandi|IP заблокирован|IP blocked
Bloklangan IP sörovi|Запрос заблокированного IP|Blocked IP request
Yangi IPdan kiriş|Вход с нового IP|Sign-in from a new IP
Sörov rad etildi|Запрос отклонён|Request rejected
Server xatosi|Ошибка сервера|Server error
Fayl yuklandi|Файл загружен|File uploaded
Fayl yuklab olindi|Файл скачан|File downloaded
Tizimdan foydalaniş|Использование системы|System activity
Rol almaştirildi|Роль переключена|Role switched
Ruxsat etilgan rollar|Разрешённые роли|Allowed roles
Rolni almaştiriş|Переключение роли|Switch role
Faol rol|Активная роль|Active role
Rolga ötiş|Переключиться|Switch role
Bo‘lim boshlig‘i faqat belgilangan rollarga öta oladi. Superadmin barcha rollarga ega.|Начальник отдела может выбирать только назначенные роли. Суперадмин имеет все роли.|Department heads can only switch to assigned roles. Superadmins have all roles.
Tanlangan rolning menyusi va vakolatlari qöllanadi. Hisob egasi özgarmaydi.|Применяются меню и права выбранной роли. Владелец учётной записи не меняется.|The selected role’s menu and permissions apply. The account owner stays the same.
Mutaxassislik şifri|Код специальности|Specialty code
Yangi talabalar qöşiladi. 8 ustunli faylda mavjud talabaning faqat böş mutaxassislik şifri va guruhi töldiriladi.|Добавляются новые студенты. В файле с 8 столбцами у существующих студентов заполняются только пустые код специальности и группа.|Adds new students. For 8-column files, only empty specialty code and group fields of existing students are filled.
Qöşildi: {added}. Mavjud: {skipped}. Tö‘ldirildi: {updated}.|Добавлено: {added}. Уже есть: {skipped}. Дополнено: {updated}.|Added: {added}. Existing: {skipped}. Enriched: {updated}.
Boshqariş|Управление|Manage
Yönaliş|Направление|Programme
Har sahifada 50 ta|По 50 на странице|50 per page
Talabalar sahifalari|Страницы студентов|Student pages
Oldingi|Предыдущая|Previous
Keyingi|Следующая|Next
Filtrdagi talabalarni öçiriş|Удалить студентов по фильтру|Delete filtered students
Barcha talabalarni öçiriş|Удалить всех студентов|Delete all students
Talabalarni öçirişni tasdiqlaş|Подтвердите удаление студентов|Confirm student deletion
Öçiriladigan talabalar: {count}|Студентов к удалению: {count}|Students to delete: {count}
Tasdiq uçun talabalar sonini kiriting|Для подтверждения введите число студентов|Enter the student count to confirm
Öçirildi: {count} ta talaba|Удалено студентов: {count}|Deleted {count} students
Eski murojaatlardagi talaba ma’lumotlari saqlanadi. Xodimlar, navbatlar, audio va sozlamalar öçirilmaydi. Davom etişdan oldin zaxira nusxa oling.|Данные студентов в прежних обращениях сохранятся. Сотрудники, очередь, аудио и настройки не удаляются. Перед продолжением сделайте резервную копию.|Student details in previous requests are retained. Staff, queues, audio and settings are retained. Make a backup before continuing.
O‘quv bo‘limi|Учебный отдел|Academic affairs office
Xalqaro aloqalar bo‘limi|Отдел международных связей|International relations office
Xodimlar bo‘limi|Отдел кадров|Human resources office
Ma’lumotlar bazasi menejeri|Менеджер базы данных|Database manager
Xodim raqami|Номер сотрудника|Staff number
Parolni körsatiş|Показать пароль|Show password
Parolni yashiriş|Скрыть пароль|Hide password
Xodimlar röyxati|Список сотрудников|Staff directory
Tahrirlaş|Редактировать|Edit
Nofaol qiliş|Деактивировать|Deactivate
Faollaştiriş|Активировать|Activate
Xodimni tahrirlaş|Редактировать сотрудника|Edit staff member
Xodimni öçiriş|Удалить сотрудника|Delete staff member
Xodimni nofaol qiliş|Деактивировать сотрудника|Deactivate staff member
Xodimni faollaştiriş|Активировать сотрудника|Activate staff member
Tasdiq uçun xodim loginini kiriting|Для подтверждения введите логин сотрудника|Enter the staff username to confirm
Hisobga kiriş yopiladi. Avvalgi murojaatlar va audit saqlanadi.|Доступ к учётной записи закрывается. История обращений и аудит сохраняются.|Account access is removed. Previous requests and audit history are retained.
Hisobga kiriş töxtatiladi va sessiyalar yopiladi. Murojaatlar saqlanadi.|Вход блокируется, сеансы завершаются. Обращения сохраняются.|Login is blocked and sessions are revoked. Requests are retained.
Xodim yana tizimga kirişi va yangi murojaatlar olişi mumkin.|Сотрудник снова сможет входить и получать обращения.|The staff member can sign in and receive new requests again.
Murojaat amallari|Действия с обращениями|Request actions
Faol murojaatlar|Активные обращения|Active requests
Dashboard|Обзор|Dashboard
Butun tizim böyiça umumiy körsatiçlar|Общие показатели системы|System overview
Vakolatingiz doirasidagi murojaatlar|Обращения в пределах ваших полномочий|Requests within your access
Bugungi murojaatlar|Обращения сегодня|Requests today
Oxirgi 7 kun|Последние 7 дней|Last 7 days
Sönggi murojaatlar|Последние обращения|Recent requests
Murojaatlar holati|Статусы обращений|Request statuses
Murojaat kanallari|Каналы обращений|Request channels
Barça murojaatlar|Все обращения|All requests
Toşkent vaqti|Ташкентское время|Tashkent time
Rasm faylini tanlang|Выберите файл изображения|Choose an image file
Rasm öçirildi|Изображение удалено|Image deleted
Profil rasmi|Фото профиля|Profile photo
Rasmni saqlaş|Сохранить фото|Save photo
Rasmni öçiriş|Удалить фото|Delete photo
Logotipni öçiriş|Удалить логотип|Delete logo
PNG yoki JPEG, eng köpi 2 MB.|PNG или JPEG, не более 2 МБ.|PNG or JPEG, up to 2 MB.
Ma’lumot va xizmat ko‘rsatish tizimi|Информационно-сервисная система|Information and service system
Registrator ofisi|Офис регистратора|Registrar’s Office
Murojaatlar|Обращения|Requests
Yangi murojaat|Новое обращение|New request
Hisobot|Отчёт|Report
Talabalar bazasi|База студентов|Student database
Arxiv|Архив|Archive
Bildirişnomalar|Уведомления|Notifications
Mening profilim|Мой профиль|My profile
Xodimlar va loginlar|Сотрудники и учётные записи|Staff and accounts
Tizim sozlamalari|Настройки системы|System settings
Audit jurnali|Журнал аудита|Audit log
Integratsiyalar|Интеграции|Integrations
Kiosk, TV va tablo|Киоск, ТВ и табло|Kiosk, TV and displays
Kiosk, TV va tablolar|Киоск, ТВ и табло|Kiosk, TV and displays
Superadmin|Суперадминистратор|Superadmin
Menejer|Менеджер|Manager
Ijroçi|Исполнитель|Assignee
Bölim boşliği|Руководитель отдела|Department head
Direktor|Директор|Director
Yangi|Новое|New
Jarayonda|В работе|In progress
Qaytarilgan|Возвращено|Returned
Tasdiq kutilmoqda|Ожидает утверждения|Awaiting approval
Yakunlangan|Завершено|Completed
Yakunlandi|Завершено|Completed
Faol|Активен|Active
active|Активен|Active
inactive|Неактивен|Inactive
academic_leave|Академический отпуск|Academic leave
Kunduzgi|Очная|Full-time
Sirtqi|Заочная|Part-time
Kechki|Вечерняя|Evening
Murojaat röyxatga olindi|Обращение зарегистрировано|Request registered
Qabul boşlandi|Приём начат|Service started
Qabul tugadi|Приём завершён|Service finished
Qayta çaqirildi|Повторный вызов|Called again
Röyxatga olindi|Зарегистрировано|Registered
Ma’lumotlar yangilandi|Данные обновлены|Details updated
Mas’ulga yönaltirildi|Назначен исполнитель|Assigned
Menejerga qaytarildi|Возвращено менеджеру|Returned to manager
Tasdiqqa yuborildi|Отправлено на утверждение|Submitted for approval
Tasdiqlandi va yopildi|Утверждено и закрыто|Approved and closed
Tuzatişga qaytarildi|Возвращено на доработку|Returned for correction
Joyida hal qilindi|Решено на месте|Resolved on site
Muddat özgardi|Срок изменён|Deadline changed
Çaqirildi|Вызвано|Called
Çiqiş|Выйти|Sign out
iş oynasi|рабочее окно|workspace
NAVBOT · 0.5 lokal sinov|NAVBOT · 0.5 локальное тестирование|NAVBOT · 0.5 local testing
Talaba ma’lumotlari faqat vakolatli kabinetda.|Данные студентов доступны только уполномоченным сотрудникам.|Student information is available only to authorized staff.
Navbat, talaba profili va ariza ijrosi|Очередь, профиль студента и исполнение обращения|Queue, student profile and request progress
Tizimga kiriş|Вход в систему|Sign in
Foydalanuvçi nomi|Имя пользователя|Username
Parol|Пароль|Password
Yagona raqamli qabul|Единая цифровая приёмная|Unified digital reception
Murojaatdan|От обращения|From request
natijagaça.|до результата.|to resolution.
Navbat, talaba ma’lumotlari, mas’ul ijroçi va javob — bitta tizimda.|Очередь, данные студента, исполнитель и ответ — в одной системе.|Queue, student details, assignee and response in one system.
Xodimning şaxsiy kabineti|Личный кабинет сотрудника|Staff account
Lokal sinov akkauntlari|Учётные записи для локального теста|Local test accounts
Demo baza yoqilgan bölsa:|Если включена демонстрационная база:|When the demo database is enabled:
Demo parol:|Демонстрационный пароль:|Demo password:
Haqiqiy serverda demo akkauntlardan foydalanmang.|Не используйте демонстрационные учётные записи на рабочем сервере.|Do not use demo accounts on a production server.
Kiosk|Киоск|Kiosk
TV ekran|Экран ТВ|TV screen
1-oyna tablosi|Табло окна 1|Counter 1 display
Barcha|Все|All
Barçasi|Все|All
Menga biriktirilgan|Назначенные мне|Assigned to me
Men yuborgan|Отправленные мной|Sent by me
Muddati yaqin|Срок близок|Due soon
Muddati ötgan|Просрочено|Overdue
Tasdiqqa yuborilgan|Отправленные на утверждение|Submitted for approval
Murojaatlar arxivi|Архив обращений|Request archive
Murojaatni qidiriş|Поиск обращения|Search requests
Raqam, talaba yoki xizmat…|Номер, студент или услуга…|Number, student or service…
Talaba biriktirilmagan|Студент не привязан|Student not linked
Bu röyxatda murojaat yöq.|В этом списке нет обращений.|No requests in this list.
Murojaatni tanlang|Выберите обращение|Select a request
Çapdagi röyxatdan ariza kartasini oçing.|Откройте карточку обращения из списка слева.|Open a request from the list on the left.
Keyingi raqamni çaqiriş|Вызвать следующий номер|Call next ticket
Navbat raqami|Номер очереди|Queue number
Ariza raqami|Номер обращения|Request number
Xizmat|Услуга|Service
Telefon|Телефон|Phone
LMS|LMS|LMS
Mas’ul|Исполнитель|Assignee
Bölim|Отдел|Department
Muddat hali belgilanmagan|Срок ещё не установлен|Deadline not set
Muddat (Toşkent)|Срок (Ташкент)|Deadline (Tashkent)
{days} kun {hours} soat qoldi|Осталось {days} дн. {hours} ч.|{days} days {hours} hours remaining
{days} kun {hours} soat keçikkan|Просрочено на {days} дн. {hours} ч.|{days} days {hours} hours overdue
Fakultet|Факультет|Faculty
Yönaliş|Направление|Programme
Bosqiç|Курс|Year
Ta’lim şakli|Форма обучения|Education form
Guruh|Группа|Group
Holat|Статус|Status
HEMIS ID böyiça qidiriş|Поиск по HEMIS ID|Search by HEMIS ID
Talaba hali biriktirilmagan. HEMIS ID orqali qidiring va kartani saqlang.|Студент ещё не привязан. Найдите по HEMIS ID и сохраните карточку.|No student linked. Search by HEMIS ID and save the request.
Murojaat mazmuni|Содержание обращения|Request content
Qidiriş|Поиск|Search
Qidirilmoqda…|Поиск…|Searching…
Talaba topilmadi.|Студент не найден.|Student not found.
Talaba topilmadi. HEMIS IDni tekşiring.|Студент не найден. Проверьте HEMIS ID.|Student not found. Check the HEMIS ID.
Izoh|Комментарий|Note
Ma’lumotlarni saqlaş|Сохранить данные|Save details
Muddat asosi|Основание срока|Deadline basis
Içki|Внутреннее|Internal
Huquqiy|Правовое|Legal
Tasdiqlanmagan / sinov|Не утверждено / тест|Unapproved / test
Ijroçi javobi|Ответ исполнителя|Assignee response
Çaqiriş|Вызвать|Call
Qayta çaqiriş|Повторный вызов|Call again
Qabulni boşlaş|Начать приём|Start service
Qabulni tugatiş|Завершить приём|Finish service
Yönaltiriş / özimda qoldiriş|Назначить / оставить у себя|Assign / retain
Joyida hal qiliş|Решить на месте|Resolve on site
Tasdiqqa yuboriş|На утверждение|Submit for approval
Menejerga qaytariş|Вернуть менеджеру|Return to manager
Tasdiqlaş va yopiş|Утвердить и закрыть|Approve and close
Tuzatişga qaytariş|Вернуть на доработку|Return for correction
Muddatni özgartiriş|Изменить срок|Change deadline
Jarayon tarixi|История процесса|Process history
Tizim|Система|System
Tarix yöq|Истории пока нет|No history yet
Oyna|Окно|Counter
Kanal|Канал|Channel
Navbat|Очередь|Queue
Mazmun|Содержание|Content
Sabab|Причина|Reason
Javob|Ответ|Response
Natija|Результат|Result
Oldingi muddat|Прежний срок|Previous deadline
Yangi muddat|Новый срок|New deadline
Içki asos|Внутреннее основание|Internal basis
Huquqiy asos|Правовое основание|Legal basis
Oldingi|Прежнее|Previous
Mas’ul va muddatni belgilaş|Назначить исполнителя и срок|Set assignee and deadline
Mas’ul ijroçi|Ответственный исполнитель|Responsible assignee
Bajariş muddati (kompyuteringiz vaqti)|Срок исполнения (время компьютера)|Deadline (your computer time)
Içki xizmat muddati asosi|Основание внутреннего срока|Internal service deadline basis
Lokal sinov qoidasi; işçi foydalanish uçun tasdiqlanmagan|Правило локального теста; не утверждено для эксплуатации|Local test rule; not approved for production
Huquqiy muddat asosi|Правовое основание срока|Legal deadline basis
Tasdiqlanmagan — lokal sinov|Не утверждено — локальный тест|Unapproved — local test
Yönaltiriş / qayta yönaltiriş sababi|Причина назначения / переназначения|Assignment / reassignment reason
Qaytariş sababi|Причина возврата|Return reason
Javobni tasdiqqa yuboriş|Отправить ответ на утверждение|Submit response for approval
Yakuniy javob|Итоговый ответ|Final response
Hal qilindi|Решено|Resolved
Javobni tasdiqlaş|Утвердить ответ|Approve response
Tasdiqlandi va yakunlandi|Утверждено и завершено|Approved and completed
Amaldagi muddatni özgartiriş|Изменение действующего срока|Change current deadline
Yangi muddat (kompyuteringiz vaqti)|Новый срок (время компьютера)|New deadline (your computer time)
Özgartiriş sababi|Причина изменения|Reason for change
Içki muddat asosi|Основание внутреннего срока|Internal deadline basis
Saqlaş va davom etiş|Сохранить и продолжить|Save and continue
Bekor qiliş|Отмена|Cancel
Özgarişlar saqlandi|Изменения сохранены|Changes saved
Amal bajarildi|Действие выполнено|Action completed
Şaxsiy ma’lumotlar va parol xavfsizligi|Личные данные и безопасность пароля|Personal details and password security
F.I.Ş.|Ф.И.О.|Full name
Rol|Роль|Role
Iş oynasi|Рабочее окно|Service counter
Parolni özgartiriş|Изменение пароля|Change password
Davom etiş uçun vaqtinçalik parolni özgartiring.|Для продолжения смените временный пароль.|Change the temporary password to continue.
Joriy parol|Текущий пароль|Current password
Yangi parol|Новый пароль|New password
Yangi parolni tasdiqlaş|Подтверждение нового пароля|Confirm new password
Kamida 12 belgi. Boshqa xizmatlarda ishlatilmagan parol tanlang.|Не менее 12 символов. Выберите пароль, не используемый в других сервисах.|At least 12 characters. Choose a password not used for other services.
Parolni yangilaş|Обновить пароль|Update password
Parollar mos emas|Пароли не совпадают|Passwords do not match
Parol yangilandi. Yangi parol bilan kiring.|Пароль изменён. Войдите с новым паролем.|Password changed. Sign in with your new password.
Yangi telefon murojaati|Новое обращение по телефону|New phone request
Navbatsiz qabul: bu ariza uçun kiosk çeki va TV çaqiruvi yaratilmaydi.|Приём без очереди: талон киоска и вызов на ТВ не создаются.|No queue: this request has no kiosk ticket or TV call.
Talaba tili|Язык студента|Student language
Talaba şaxsi tasdiqlangan tartibda tekşirildi (lokal sinov).|Личность студента проверена установленным способом (локальный тест).|Student identity verified through the approved procedure (local test).
Haqiqiy telefon orqali şaxsni tasdiqlaş tartibi hali tasdiqlanişi kerak.|Порядок проверки личности по телефону ещё необходимо утвердить.|The actual phone identity verification procedure still needs approval.
Röyxatga oliş|Зарегистрировать|Register
Yangi topshiriqlar, qaytarişlar va tasdiq natijalari. Lokal panel xabarlari.|Новые задания, возвраты и результаты утверждений. Уведомления в панели.|New assignments, returns and approvals. In-app notifications.
Bildirişnoma yöq.|Нет уведомлений.|No notifications.
Öqilgan|Прочитано|Read
Hisobot va ijro nazorati|Отчёты и контроль исполнения|Reports and progress monitoring
Saqlangan arizalar reyestridan şakllanadi. Sana-vaqtlar Toşkent böyiça.|Формируется по реестру сохранённых обращений. Время ташкентское.|Generated from saved requests. Dates and times use Tashkent time.
Boshlaniş sanasi|Начальная дата|Start date
Tugaş sanasi|Конечная дата|End date
Xizmat bölimi|Раздел услуг|Service category
Hisobotni şakllantiriş|Сформировать отчёт|Generate report
CSV yuklab oliş|Скачать CSV|Download CSV
Excel yuklab oliş|Скачать Excel|Download Excel
Jami murojaatlar|Всего обращений|Total requests
Ijroda|В работе|In progress
Keçikkan|Просрочено|Overdue
Tanlangan davr|Выбранный период|Selected period
Murojaatlar dinamikasi|Динамика обращений|Request trend
Bölimlar kesimida ijro|Исполнение по отделам|Progress by department
Biriktirilmagan|Не назначено|Unassigned
Jami|Всего|Total
Murojaatlar reyestri|Реестр обращений|Request register
Muddatida yakunlangan|Завершено в срок|Completed on time
Ariza / navbat|Обращение / очередь|Request / queue
Talaba|Студент|Student
Menejer / mas’ul|Менеджер / исполнитель|Manager / assignee
Muddat|Срок|Deadline
Tanlangan davrda ma’lumot yöq.|Нет данных за выбранный период.|No data for the selected period.
Hali ma’lumot yöq.|Данных пока нет.|No data yet.
Murojaatlar soni kunlar böyiça|Число обращений по дням|Requests per day
Lokal yuklangan baza. LMS sinxronizatsiyasi hali ulanmagan.|Локально загруженная база. Синхронизация с LMS пока не подключена.|Locally imported data. LMS synchronization is not connected yet.
F.I.Ş., HEMIS ID, guruh…|Ф.И.О., HEMIS ID, группа…|Full name, HEMIS ID, group…
Talabani qidiriş|Поиск студента|Search students
Fakultet / yönaliş|Факультет / направление|Faculty / programme
Kurs|Курс|Year
Talabalarni JSON fayldan yuklaş|Загрузка студентов из JSON|Import students from JSON
HEMIS ID böyiça yangi yozuv qöşiladi yoki mavjud yozuv yangilanadi. Xato bölsa butun import bekor qilinadi.|Добавление и обновление записей по HEMIS ID. При ошибке весь импорт отменяется.|Records are added or updated by HEMIS ID. An error cancels the entire import.
JSON fayl|Файл JSON|JSON file
Talabalar JSON massivi|JSON-массив студентов|Student JSON array
Bazaga yuklaş|Загрузить в базу|Import into database
Alohida login, rol va vaqtinçalik parol. Parollar oçiq saqlanmaydi.|Отдельные логины, роли и временные пароли. Пароли не хранятся открыто.|Individual usernames, roles and temporary passwords. Passwords are not stored in plain text.
Yangi xodim|Новый сотрудник|New staff account
Operator raqami (menejer uçun)|Номер оператора (для менеджера)|Operator number (for manager)
Vaqtinçalik parol|Временный пароль|Temporary password
Xodim yaratish|Создать сотрудника|Create staff account
Xodim yaratiş|Создать сотрудника|Create staff account
Vaqtinçalik parol beriş|Выдать временный пароль|Set temporary password
Xodim|Сотрудник|Staff member
Yangi vaqtinçalik parol|Новый временный пароль|New temporary password
Xodim keyingi kirişda parolni özgartiradi. Eski sessiyalar bekor qilinadi.|При следующем входе сотрудник сменит пароль. Прежние сеансы отменяются.|The staff member must change the password on next sign-in. Existing sessions are revoked.
Login|Логин|Username
Bölim / oyna|Отдел / окно|Department / counter
Xodim yaratildi|Сотрудник создан|Staff account created
Vaqtinçalik parol berildi|Временный пароль установлен|Temporary password set
Universitet, tarjimalar, katalog logotiplari, chek va TV sozlamalari.|Университет, переводы, логотипы каталога, талон и настройки ТВ.|University, translations, category logos, ticket and TV settings.
Sozlamalar yangi cheklar va ommaviy ekranlarga qöllanadi. Avvalgi arizalardagi mazmun va muddat asoslari saqlanadi.|Настройки применяются к новым талонам и общим экранам. Содержание и основания сроков прежних обращений сохраняются.|Settings apply to new tickets and public screens. Existing request content and deadline bases remain unchanged.
TV va ovoz|ТВ и звук|TV and sound
TV interfeys tili|Язык интерфейса ТВ|TV interface language
Sariq ogohlantiriş (soat)|Жёлтое предупреждение (часы)|Yellow warning threshold (hours)
Ovoz darajasi (0–1)|Громкость (0–1)|Volume (0–1)
Miltillaş soni|Количество миганий|Flash count
Uç tildagi matnlar|Тексты на трёх языках|Texts in three languages
Universitetning töliq nomi|Полное название университета|Full university name
Ofis nomi|Название офиса|Office name
Chek pastki körsatmasi|Инструкция внизу талона|Ticket footer instruction
Ovoz şabloni: {navbat} va {operator}|Шаблон вызова: {navbat} и {operator}|Call template: {navbat} and {operator}
TV: joriy çaqiruv|ТВ: текущий вызов|TV: current call
TV: xizmat körsatilmoqda|ТВ: обслуживаются|TV: now serving
TV: kutilayotganlar|ТВ: ожидающие|TV: waiting
Chek matnini oldindan körish|Предпросмотр талона|Preview ticket
Katalog va operator yorliqlari — kengaytirilgan JSON|Каталог и подписи операторов — расширенный JSON|Catalog and operator labels — advanced JSON
Kengaytirilgan sozlamalar|Расширенные настройки|Advanced settings
Sozlamalarni saqlaş|Сохранить настройки|Save settings
Sozlamalar saqlandi|Настройки сохранены|Settings saved
Bölim logotipi|Логотип раздела|Category logo
PNG yoki JPEG, eng köpi 2 MB. Saqlangan logotip kioskda körinadi.|PNG или JPEG, до 2 МБ. Сохранённый логотип отображается в киоске.|PNG or JPEG, up to 2 MB. The saved logo appears on the kiosk.
Logotip fayli|Файл логотипа|Logo file
Logotipni saqlaş|Сохранить логотип|Save logo
Hozir standart belgi ishlatiladi.|Сейчас используется стандартный значок.|The default icon is currently used.
PNG/JPEG va 2 MBgacha fayl tanlang|Выберите PNG/JPEG размером до 2 МБ|Choose a PNG/JPEG file up to 2 MB
Logotip faylini tanlang|Выберите файл логотипа|Choose a logo file
Logotip saqlandi; kioskda yangilanadi|Логотип сохранён и обновится в киоске|Logo saved; the kiosk will update
Muhim amallar va özgarişlar tarixi.|История важных действий и изменений.|History of important actions and changes.
Sana va vaqt|Дата и время|Date and time
Amal|Действие|Action
Tafsilot|Подробности|Details
Tashqi xizmatlar holati|Состояние внешних сервисов|External service status
Ulanmagan|Не подключено|Not connected
Ulangan|Подключено|Connected
Hozir talabalar lokal fayldan yuklanadi. Haqiqiy ulanish uçun API manzili, maydonlar va universitetning ruxsat etilgan autentifikatsiya tartibi kerak.|Сейчас студенты загружаются из локального файла. Для подключения нужны адрес API, поля и разрешённая университетом аутентификация.|Students are currently imported from a local file. Connection requires an API URL, field definitions and approved authentication.
Bir serverdagi alohida ekranlar. Qurilma protokoli haqiqiy modelga qarab sozlanadi.|Отдельные экраны на одном сервере. Протокол устройства настраивается по реальной модели.|Separate screens on one server. Device protocol depends on the actual model.
Talaba til, bölim va xizmatni tanlaydi. 80 mm chek brauzer orqali chop etiladi.|Студент выбирает язык, раздел и услугу. Талон 80 мм печатается из браузера.|The student selects a language, category and service. The 80 mm ticket is printed through the browser.
Kioskni oçiş|Открыть киоск|Open kiosk
Umumiy TV|Общий ТВ|Main TV
Joriy çaqiruv, xizmat körsatilayotgan oynalar va hali çaqirilmagan navbatlar.|Текущий вызов, обслуживаемые окна и ожидающие номера.|Current call, counters now serving and waiting tickets.
TVni oçiş|Открыть ТВ|Open TV
Oyna tablosi|Табло окна|Counter display
Operator raqami|Номер оператора|Operator number
Tabloni oçiş|Открыть табло|Open display
Info KeyOS, jismoniy printer, LED tablo va avtomatik to‘liq ekran rejimi haqiqiy qurilmalarda hali tekşirilmagan.|Info KeyOS, физический принтер, LED-табло и автоматический полноэкранный режим ещё не проверены на реальных устройствах.|Info KeyOS, physical printer, LED display and automatic fullscreen mode have not been tested on actual hardware.
NavBoTni oçib bölmadi|Не удалось открыть NavBoT|Could not open NavBoT
Qayta uriniş|Повторить|Try again
Sörov bajarilmadi|Запрос не выполнен|Request failed
Server bilan aloqa uzildi|Нет связи с сервером|Connection to server lost
Sozlaş|Настроить|Configure
Saqlaş|Сохранить|Save
Ulanishni sinash|Проверить соединение|Test connection
Talabalarni yangilaş|Обновить студентов|Sync students
Integratsiya turi|Тип интеграции|Integration type
API manzili|Адрес API|API URL
Talabalar API manzili|Адрес API студентов|Student API URL
API kaliti / token|Ключ API / токен|API key / token
Faollashtiriş|Включить|Enable
Saqlangan tokenni öçiriş|Удалить сохранённый токен|Clear saved token
Token saqlangan|Токен сохранён|Token saved
Token kiritilmagan|Токен не задан|No token set
Böş qoldirilsa, avvalgi token saqlanadi.|Если оставить пустым, прежний токен сохранится.|Leave blank to preserve the saved token.
Sirlar saqlangandan keyin qayta körsatilmaydi.|После сохранения секретные значения не отображаются.|Secret values are not displayed after saving.
Oxirgi muvaffaqiyatli ulanish|Последнее успешное соединение|Last successful connection
Oxirgi yangilaniş|Последняя синхронизация|Last synchronization
Sinov natijasi|Результат проверки|Test result
Ulanish hali tekşirilmagan|Соединение ещё не проверено|Connection not tested yet
Öçirilgan|Отключено|Disabled
Xatolik|Ошибка|Error
Integratsiya saqlandi|Интеграция сохранена|Integration saved
Talabalar yangilandi|Данные студентов обновлены|Students synchronized
Manzilni özingiz kiriting. Haqiqiy ulanish faqat muvaffaqiyatli sinovdan keyin körsatiladi.|Введите адрес вручную. Подключение отмечается только после успешной проверки.|Enter the URL manually. Connection is shown only after a successful test.
Ovozli çaqiruv|Голосовой вызов|Voice announcements
Brauzer ovozi|Голос браузера|Browser speech
Yuklangan audio|Загруженные записи|Uploaded audio
Til|Язык|Language
Ovoz rejimi|Режим озвучивания|Voice mode
Audio qismi|Фрагмент аудио|Audio segment
Boshlaniş|Начало|Prefix
Raqamlar orasida|Между номерами|Between numbers
Yakuni|Завершение|Suffix
Navbat raqami audiosi|Аудио номера талона|Ticket number recording
Operator raqami audiosi|Аудио номера оператора|Operator number recording
Töliq çaqiruv|Полный вызов|Full call
Audio nomi|Название записи|Recording label
Audio fayl|Аудиофайл|Audio file
MP3 yoki WAV, eng köpi 5 MB.|MP3 или WAV, до 5 МБ.|MP3 or WAV, up to 5 MB.
Audioni yuklaş|Загрузить аудио|Upload audio
Audio saqlandi|Аудио сохранено|Audio saved
Ovoz rejimi saqlandi|Режим озвучивания сохранён|Voice mode saved
Sinov çaqiruvi|Тестовый вызов|Test announcement
Sinovni işga tuşiriş|Запустить проверку|Play test announcement
Öçiriş|Удалить|Delete
Audio öçirildi|Аудио удалено|Audio deleted
Bu til uçun audio yöq.|Для этого языка нет записей.|No recordings for this language.
Yetishmayotgan qismlar|Недостающие фрагменты|Missing segments
Audio töliq emas. Çaqaruv brauzer ovozi bilan töliq aytiladi.|Запись неполная. Весь вызов будет произнесён голосом браузера.|Recordings are incomplete. The full announcement will use browser speech.
Ovoz avtomatik yoqilmadi. Ekranga bir marta bosing.|Автозапуск звука заблокирован. Нажмите один раз на экран.|Automatic audio was blocked. Tap the screen once.
Interfeys tili|Язык интерфейса|Interface language
Yoruğ rejim|Светлая тема|Light theme
To‘q rejim|Тёмная тема|Dark theme
Formadagi yozuvlar saqlanadi.|Введённые данные сохраняются.|Entered form values are preserved.
Notöğri JSON ma’lumoti|Некорректные данные JSON|Invalid JSON data
Notöğri fayl turi yoki hajmi|Неверный тип или размер файла|Invalid file type or size
`.trim().split('\n').map(line=>line.split('|'));
function uz(text){if(text==='unknown')return 'Noma’lum';return text.replace(/O[‘’ʻ']/g,'Ö').replace(/o[‘’ʻ']/g,'ö').replace(/G[‘’ʻ']/g,'Ğ').replace(/g[‘’ʻ']/g,'ğ').replace(/Sh/g,'Ş').replace(/sh/g,'ş').replace(/Ch/g,'Ç').replace(/ch/g,'ç')}
const entries=new Map(),aliases=new Map();for(const row of rows){if(row.length!==3)continue;const translated=[uz(({active:'Faol',inactive:'Nofaol',unknown:'Noma’lum',academic_leave:'Akademik ta’til'})[row[0]]||row[0]),row[1],row[2]];entries.set(row[0],translated);for(const s of row)aliases.set(s,row[0]);aliases.set(translated[0],row[0])}
let language=['uz','ru','en'].includes(localStorage.getItem('navbot-language'))?localStorage.getItem('navbot-language'):'uz';
function t(value){if(typeof value!=='string')return String(value??'');const trim=value.trim(),key=aliases.get(trim)||trim,index=['uz','ru','en'].indexOf(language);if(entries.has(key))return value.replace(trim,entries.get(key)[index]);const decoration=trim.match(/^([✓＋↓➤◷←→♧▤!\s]*)(.+?)([\s:·→↗.]*)$/u);if(decoration&&entries.has(aliases.get(decoration[2])||decoration[2]))return decoration[1]+entries.get(aliases.get(decoration[2])||decoration[2])[index]+decoration[3];if(value.includes(' · '))return value.split(' · ').map(t).join(' · ');return value}
function fmt(key,values){let text=t(key);for(const [name,value]of Object.entries(values))text=text.replaceAll('{'+name+'}',String(value));return text}
function html(strings,...values){let result='',inside=false,quote=null;for(let i=0;i<strings.length;i++){let part=strings[i];part=part.replace(/\b(placeholder|aria-label|title)="([^"<>]*)"/g,(_,attribute,value)=>attribute+'="'+t(value).replaceAll('"','&quot;')+'"');let text='';for(let j=0;j<part.length;j++){const ch=part[j];if(!inside){if(ch==='<'){result+=t(text);text='';inside=true;result+=ch}else text+=ch}else{result+=ch;if(quote){if(ch===quote)quote=null}else if(ch==='"'||ch==="'")quote=ch;else if(ch==='>')inside=false}}result+=inside?text:t(text);if(i<values.length)result+=values[i]??''}return result}
function staticHTML(text){return html([text])}
return {t,fmt,html,staticHTML,get language(){return language},setLanguage(value,persist=true){if(!['uz','ru','en'].includes(value))return;language=value;if(persist)localStorage.setItem('navbot-language',value)},add(records){for(const [key,ru,en]of records){entries.set(key,[uz(key),ru,en]);aliases.set(key,key)}}};
})();

NavI18n.add([["API tekşirish manzili", "Адрес проверки API", "API test URL"], ["Talabalar API manzili", "Адрес API студентов", "Student API URL"], ["API kaliti / bot tokeni", "Ключ API / токен бота", "API key / bot token"], ["Saqlangan kalitni öçiriş", "Удалить сохранённый ключ", "Delete saved key"], ["Faollashtiriş", "Включить", "Enable"], ["Saqlaş", "Сохранить", "Save"], ["Ulanishni tekşiriş", "Проверить соединение", "Test connection"], ["Talabalarni yangilaş", "Обновить студентов", "Synchronize students"], ["Qöşilgan / yangilangan", "Добавлено / обновлено", "Added / updated"], ["Sirlar saqlangandan keyin qayta körsatilmaydi. Telegram sinovi faqat botni tekşiradi; talabalarga xabar yubormaydi.", "После сохранения секреты не отображаются. Проверка Telegram только проверяет бота, не отправляя сообщения студентам.", "Secrets are not shown after saving. The Telegram test checks the bot without sending messages to students."], ["Talabalar manzili {students: [...]} formatidagi JSON javob qaytarişi kerak. HEMIS ID böyiça yangilanadi. HEMISning boşqa formatiga mos adapter talab qilinişi mumkin.", "API студентов должен возвращать JSON {students: [...]}. Обновление выполняется по HEMIS ID. Для другого формата HEMIS может потребоваться адаптер.", "The student API must return JSON {students: [...]}. Records are updated by HEMIS ID. Other HEMIS formats may require an adapter."], ["Qismlar tartibi: boshlaniş → navbat raqami → oraliq matn → operator raqami → yakun. Boshlaniş audiosida A harfi ham aytiladi. Töliq çaqiruv fayli shu raqamlar uçun qismlardan ustun turadi. Qismlar yetishmasa, çaqiruv tanlangan tilda brauzer ovozi bilan aytiladi.", "Порядок: начало → номер талона → промежуточный текст → номер оператора → завершение. Начало включает букву A. Полная запись имеет приоритет для указанных номеров. Если фрагментов не хватает, весь вызов произносится голосом браузера на выбранном языке.", "Order: prefix → ticket number → connecting text → operator number → suffix. Include the letter A in the prefix. A complete recording overrides fragments for those numbers. If fragments are missing, the entire call uses browser speech in the selected language."], ["Excel yuklab oliş", "Скачать Excel", "Download Excel"], ["Maydonni tekşiring", "Проверьте поле", "Check this field"], ["Özgariş", "Изменение", "Change"], ["Oldingi yozuvlar yuklandi", "Импортированы прежние записи", "Previous records imported"], ["Kanal", "Канал", "Channel"], ["Noma’lum", "Неизвестно", "Unknown"], ["Xizmatni tanlang", "Выберите услугу", "Choose a service"], ["Çekni oling", "Возьмите талон", "Collect your ticket"], ["Navbatingizni kuting", "Ожидайте вызова", "Wait for your turn"], ["Registrar", "Офис регистратора", "Registrar’s Office"], ["O‘quv bo‘limi", "Учебный отдел", "Academic affairs"], ["Sörov bajarilmadi", "Запрос не выполнен", "Request failed"], ["Bot", "Бот", "Bot"], ["LMS tekşirish HTTPS manzilini kiriting", "Введите HTTPS-адрес проверки LMS", "Enter the LMS HTTPS test URL"], ["Avval integratsiyani faollashtiring", "Сначала включите интеграцию", "Enable the integration first"], ["Telegram tokeni saqlanmagan yoki o‘qilmadi", "Токен Telegram не сохранён или недоступен", "Telegram token is missing or unreadable"], ["Ulangan", "Подключено", "Connected"], ["Ulanmagan", "Не подключено", "Disconnected"]]);

NavI18n.add([["ToşDÖTAU", "ТашГУУЯЛ", "TSUULL"], ["Jami murojaatlar", "Всего обращений", "Total requests"], ["Keçikkan", "Просрочено", "Overdue"], ["Qo‘şimça katalog sozlamalari. Mavjud xizmat tartibini özgartirmang.", "Дополнительные настройки каталога. Не изменяйте порядок существующих услуг.", "Additional catalog settings. Keep the existing service order."], ["Qo‘şimça sozlamalar (JSON)", "Дополнительные настройки (JSON)", "Advanced settings (JSON)"]]);

NavI18n.add([["Şaxs tasdiği", "Подтверждение личности", "Identity confirmation"], ["Oldingi içki asos", "Прежнее внутреннее основание", "Previous internal basis"], ["Yangi içki asos", "Новое внутреннее основание", "New internal basis"], ["Oldingi huquqiy asos", "Прежнее правовое основание", "Previous legal basis"], ["Yangi huquqiy asos", "Новое правовое основание", "New legal basis"], ["Qöşilgan", "Добавлено", "Added"], ["Yangilangan", "Обновлено", "Updated"], ["Maydonlar", "Поля", "Fields"], ["Hajm", "Размер", "Size"], ["Format", "Формат", "Format"], ["Integratsiya", "Интеграция", "Integration"], ["Ha", "Да", "Yes"], ["Yöq", "Нет", "No"], ["Universitet nomi", "Название университета", "University name"], ["Ofis nomi", "Название офиса", "Office name"], ["Xizmatlar katalogi", "Каталог услуг", "Service catalog"], ["TV interfeys tili", "Язык интерфейса ТВ", "TV interface language"], ["Ovoz darajasi", "Громкость", "Volume"], ["Miltillaş soni", "Количество миганий", "Blink count"], ["Ogohlantiriş chegarasi", "Порог предупреждения", "Warning threshold"], ["Ovoz şablonlari", "Шаблоны озвучивания", "Voice templates"], ["Çek matni", "Текст талона", "Ticket text"], ["TV sarlavhalari", "Заголовки ТВ", "TV headings"], ["Operator yorliqlari", "Подписи операторов", "Counter labels"], ["Yashirilgan xizmatlar", "Скрытые услуги", "Hidden services"], ["Bölim logotiplari", "Логотипы разделов", "Section logos"]]);

NavI18n.add([["Fayl biriktiriş", "Прикрепить файлы", "Attach files"], ["Biriktirilgan fayllar", "Прикреплённые файлы", "Attachments"], ["Hali fayl biriktirilmagan.", "Файлы ещё не прикреплены.", "No attachments yet."], ["Fayllarni biriktiriş", "Прикрепить файлы", "Upload attachments"], ["Fayllar biriktirildi", "Файлы прикреплены", "Files attached"], ["Fayl biriktirildi", "Файл прикреплён", "File attached"], ["Fayl nomi", "Имя файла", "File name"], ["Har bir fayl 10 MBgacha. Arizaga eng köpi 10 ta fayl.", "До 10 МБ на файл, не более 10 файлов на обращение.", "Up to 10 MB per file and 10 files per request."], ["Har bir fayl 10 MBdan oşmasligi kerak", "Каждый файл должен быть не больше 10 МБ", "Each file must not exceed 10 MB"]]);

NavI18n.add([["Login yoki parol noto‘g‘ri", "Неверное имя пользователя или пароль", "Incorrect username or password"], ["Joriy parol noto‘g‘ri", "Неверный текущий пароль", "Incorrect current password"], ["Parol 12–128 belgi, kamida bitta harf va raqamdan iborat bo‘lsin", "Пароль должен содержать 12–128 символов, букву и цифру", "Password must contain 12–128 characters, a letter and a digit"], ["Tizimga kiring", "Войдите в систему", "Sign in"], ["Ariza özgargan. Yangilab qayta urinib köring", "Обращение изменилось. Обновите и повторите попытку", "The request changed. Refresh and try again"], ["Talaba topilmadi", "Студент не найден", "Student not found"], ["Avval talabani biriktiring", "Сначала привяжите студента", "Link a student first"], ["API HTTP xatosi", "Ошибка HTTP API", "API HTTP error"], ["Tarmoq, vaqt tugashi yoki TLS tekshiruvi xatosi", "Ошибка сети, тайм-аута или проверки TLS", "Network, timeout or TLS verification error"], ["API ulanishni tasdiqlamadi", "API не подтвердил соединение", "The API did not confirm the connection"], ["API application/json qaytarishi kerak; HTML sahifa qabul qilinmaydi", "API должен возвращать application/json, HTML не принимается", "The API must return application/json; HTML is not accepted"], ["Domen DNS orqali topilmadi", "Домен не найден в DNS", "Domain could not be resolved"], ["Ichki yoki maxsus tarmoq manziliga ulanish taqiqlangan", "Подключение к внутренним или специальным сетевым адресам запрещено", "Connections to private or special network addresses are blocked"], ["Faqat ochiq HTTPS domeni, standart port va kalitsiz URL kiriting; query/fragment ishlatilmaydi", "Введите общедоступный HTTPS-домен со стандартным портом, без учётных данных, query и fragment", "Use a public HTTPS domain on the default port without credentials, query or fragment"], ["LMS tekshirish va talabalar manzili bir domenda bo‘lsin", "Адреса проверки LMS и студентов должны быть в одном домене", "The LMS test and student URLs must use the same domain"], ["Faol Telegram uchun bot tokenini kiriting", "Введите токен бота для включения Telegram", "Enter a bot token to enable Telegram"], ["Telegram bot tokeni formatini tekshiring", "Проверьте формат токена Telegram", "Check the Telegram bot token format"], ["Kalitni kiritish yoki tozalashdan birini tanlang", "Выберите ввод нового ключа или удаление прежнего", "Choose either a new key or clearing the saved key"], ["API JSON javobi noto‘g‘ri", "Некорректный ответ JSON API", "Invalid JSON API response"], ["LMS talabalar API manzilini kiriting", "Введите адрес API студентов LMS", "Enter the LMS student API URL"], ["Sozlama sinov vaqtida özgardi; qayta tekşiring", "Настройки изменились во время проверки; повторите её", "Configuration changed during the test; try again"], ["Fayl nomini tekşiring", "Проверьте имя файла", "Check the file name"], ["PDF, Word, Excel, TXT, PNG yoki JPG faylini tanlang", "Выберите файл PDF, Word, Excel, TXT, PNG или JPG", "Choose a PDF, Word, Excel, TXT, PNG or JPG file"], ["Arizaga eng köpi 10 ta fayl va jami 50 MB biriktiriladi", "К обращению можно прикрепить до 10 файлов общим размером 50 МБ", "A request supports up to 10 files totaling 50 MB"], ["Yopilgan arizaga yangi fayl biriktirib bölmaydi", "Нельзя добавлять файлы в закрытое обращение", "Files cannot be added to a closed request"], ["Fayl buzilgan yoki juda katta", "Файл повреждён или слишком большой", "The file is invalid or too large"], ["PDF fayli buzilgan", "Повреждён файл PDF", "Invalid PDF file"], ["PNG fayli buzilgan", "Повреждён файл PNG", "Invalid PNG file"], ["JPG fayli buzilgan", "Повреждён файл JPG", "Invalid JPG file"], ["Word/Excel fayli buzilgan yoki makrosli format qöllanmaydi", "Файл Word/Excel повреждён или содержит неподдерживаемые макросы", "Invalid Word/Excel file or unsupported macro format"], ["TXT fayli UTF-8 bölişi kerak", "Файл TXT должен быть в UTF-8", "TXT files must use UTF-8"], ["Faqat MP3 yoki WAV faylini yuklang", "Загружайте только MP3 или WAV", "Upload only MP3 or WAV files"], ["MP3 ovoz ma’lumoti töliq emas", "Аудиоданные MP3 неполные", "MP3 audio data is incomplete"], ["Ovoz fayli 5 MBdan oşmasligi kerak", "Аудиофайл не должен превышать 5 МБ", "Audio files must not exceed 5 MB"]]);

NavI18n.add([["Faylni tanlang","Выбрать файл","Choose file"],["Fayl tanlanmagan","Файл не выбран","No file selected"]]);

NavI18n.add([["Bölim, navbat harfi va operator", "Отдел, буква очереди и оператор", "Department, queue letter and operator"], ["Navbat harfi", "Буква очереди", "Queue letter"], ["Özgarişlar yangi cheklarga qöllanadi. Avval olingan cheklar harfi va operatori saqlanadi.", "Изменения применяются к новым талонам. Буква и оператор ранее выданных талонов сохраняются.", "Changes apply to new tickets. Existing tickets keep their letter and assigned operator."], ["Har bir harfning navbat raqami alohida yuradi: A-001, B-001, C-001. Menejer faqat öz operatoriga biriktirilgan navbatni çaqiradi.", "Нумерация независима для каждой буквы: A-001, B-001, C-001. Менеджер вызывает только очередь своего оператора.", "Each letter has independent numbering: A-001, B-001, C-001. Managers call only their assigned operator’s queue."], ["Boshlang‘ich e’lon", "Начальное объявление", "Opening announcement"], ["Ovoz tartibi", "Порядок озвучивания", "Announcement sequence"], ["default → harf → raqam → operator", "default → буква → номер → оператор", "default → letter → number → operator"], ["Avvalgi 5 qismli tartib", "Прежний порядок из 5 фрагментов", "Previous 5-part sequence"], ["Ovozlarni birga yuklaş", "Пакетная загрузка аудио", "Bulk audio upload"], ["Audio fayllar", "Аудиофайлы", "Audio files"], ["Yuklangach raqamli ovoz tartibini yoqiş", "После загрузки включить последовательность default–буква–номер–оператор", "Enable the numbered announcement sequence after upload"], ["Birga yuklaş", "Загрузить пакет", "Upload files"], ["Yuklaşni töxtatiş", "Остановить загрузку", "Stop upload"], ["Yuklaş töxtatildi", "Загрузка остановлена", "Upload stopped"], ["Yuklanmoqda: {done}/{total}", "Загружается: {done}/{total}", "Uploading: {done}/{total}"], ["Yuklandi: {saved}, xato: {failed}", "Загружено: {saved}, ошибок: {failed}", "Uploaded: {saved}, failed: {failed}"], ["Ayrim fayllar yuklanmadi", "Некоторые файлы не загружены", "Some files were not uploaded"], ["Fayl nomi tanilmadi", "Неизвестное имя файла", "Unrecognized file name"], ["Bir xil qism uçun takror fayl tanlangan", "Для одного фрагмента выбрано несколько файлов", "Duplicate files selected for the same segment"], ["Bir martada eng köpi 1000 ta fayl tanlang", "Выберите не более 1000 файлов за один раз", "Select no more than 1000 files at once"], ["Berilgan 4 fayl namunasi", "Набор из 4 предоставленных файлов", "Provided 4-file sample pack"], ["Namunani örnatiş", "Установить набор", "Install sample pack"], ["Namuna özbek tilida A-001 va 1-operator uçun. Shu 4 qismning avvalgi yozuvlari almashtiriladi.", "Образец на узбекском для A-001 и оператора 1. Существующие записи этих четырёх фрагментов будут заменены.", "The Uzbek sample is for A-001 and operator 1. Existing recordings for these four segments will be replaced."], ["default → harf → navbat raqami → operator. Fayl nomlari böyiça qismlar avtomatik biriktiriladi. Mavjud shu til/qism yozuvi almashtiriladi.", "default → буква → номер талона → оператор. Фрагменты назначаются по именам файлов. Существующая запись для того же языка и фрагмента заменяется.", "default → letter → ticket number → operator. File names determine the segments. Existing recordings for the same language and segment are replaced."], ["Raqamli tartib: default → harf → navbat raqami → operator. Avvalgi 5 qismli tartib ham tanlanişi mumkin. Töliq çaqiruv fayli shu raqamlar uçun qismlardan ustun turadi. Qismlar yetishmasa, çaqiruv tanlangan tilda brauzer ovozi bilan aytiladi.", "Порядок: default → буква → номер талона → оператор. Прежний порядок из 5 фрагментов также доступен. Полная запись имеет приоритет для указанных номеров. При отсутствии фрагментов весь вызов произносится голосом браузера на выбранном языке.", "Sequence: default → letter → ticket number → operator. The previous 5-part sequence is also available. A complete call recording overrides segments for those numbers. Missing segments trigger whole-call browser speech in the selected language."], ["{count} ta fayl", "{count} файлов", "{count} files"], ["5 ta bölimga takrorlanmaydigan harf va operator biriktiring", "Назначьте пяти отделам уникальные буквы и операторов", "Assign unique letters and operators to all five departments"]]);

NavI18n.add([["Logotiplar va interfeys belgilari", "Логотипы и значки интерфейса", "Logos and interface icons"], ["Har bir joyga alohida PNG yoki JPEG yuklang. Eng köpi 2 MB.", "Загрузите отдельный PNG или JPEG для каждого элемента. Не более 2 МБ.", "Upload a separate PNG or JPEG for each item. Maximum 2 MB."], ["Tizim logotipi", "Логотип системы", "System logo"], ["Kiosk logotipi", "Логотип киоска", "Kiosk logo"], ["Belgi", "Значок", "Icon"], ["Belgi joyi", "Элемент интерфейса", "Interface element"], ["Rasm fayli", "Файл изображения", "Image file"], ["Rasmni saqlaş", "Сохранить изображение", "Save image"], ["Standartga qaytariş", "Вернуть стандартный вид", "Restore default"], ["Rasm saqlandi", "Изображение сохранено", "Image saved"], ["Xizmat belgisi", "Значок услуги", "Service icon"], ["Qöşiş belgisi", "Значок добавления", "Add icon"], ["Oldinga", "Вперёд", "Forward"], ["Havolani oçiş", "Открыть ссылку", "Open link"], ["Tasdiq belgisi", "Значок подтверждения", "Confirmation icon"], ["Muddat belgisi", "Значок срока", "Deadline icon"], ["Qorong‘i rejim", "Тёмный режим", "Dark mode"], ["Belgi joyini tanlang", "Выберите элемент интерфейса", "Choose an interface element"], ["Rasmlar ombori töldi", "Хранилище изображений заполнено", "Image storage is full"], ["Rasm topilmadi", "Изображение не найдено", "Image not found"]]);

NavI18n.add([["Talabalarni Excel fayldan qöşiş", "Добавить студентов из Excel", "Add students from Excel"], ["Mavjud HEMIS ID yozuvlari özgartirilmaydi. Faqat yangi talabalar qöşiladi.", "Записи с существующим HEMIS ID не изменяются. Добавляются только новые студенты.", "Existing HEMIS ID records are preserved. Only new students are added."], ["Excel fayli", "Файл Excel", "Excel file"], ["Bazaga qöşiş", "Добавить в базу", "Add to database"], ["Qöşildi: {added}. Mavjud: {skipped}. Özgartirilgan: 0.", "Добавлено: {added}. Уже есть: {skipped}. Изменено: 0.", "Added: {added}. Existing: {skipped}. Changed: 0."], ["Talabalar qöşildi", "Студенты добавлены", "Students added"], ["Excel fayli 5 MBdan oşmasligi kerak", "Файл Excel не должен превышать 5 МБ", "Excel file must not exceed 5 MB"], ["Excel ustunlari yoki talaba yozuvlarini tekşiring; import bekor qilindi", "Проверьте столбцы Excel или записи студентов; импорт отменён", "Check Excel columns or student records; import cancelled"], ["Excel faylini tekşiring", "Проверьте файл Excel", "Check the Excel file"], ["Jins", "Пол", "Gender"], ["Ta’lim turi", "Тип образования", "Education type"]]);

NavI18n.add([["unknown","Неизвестно","Unknown"]]);

NavI18n.add([["Ogohlantiriş belgisi","Значок предупреждения","Warning icon"]]);

NavI18n.add([["Tilni tanlaş", "Выбрать язык", "Choose language"], ["Körinişni tanlaş", "Выбрать оформление", "Choose appearance"], ["Murojaat va navbatlarni tozalaş", "Очистить обращения и очередь", "Clear requests and queue"], ["Murojaatni öçiriş", "Удалить обращение", "Delete request"], ["Öçiriladigan murojaat yöq", "Нет обращений для удаления", "No requests to delete"], ["Öçiriladigan murojaatlar: {count}", "Обращений для удаления: {count}", "Requests to delete: {count}"], ["Murojaat mazmuni, ilovalari va unga tegishli bildirişnomalar öçiriladi. Talabalar, hisoblar, audio, sozlamalar va audit saqlanadi. Raqamlar qayta ishlatilmaydi.", "Содержимое обращений, вложения и связанные уведомления удаляются. Студенты, учётные записи, аудио, настройки и аудит сохраняются. Номера не используются повторно.", "Request contents, attachments and related notifications are deleted. Students, accounts, audio, settings and audit are preserved. Numbers are not reused."], ["Öçiriş sababi", "Причина удаления", "Deletion reason"], ["Sinov ma’lumotlarini tozalaş", "Очистка тестовых данных", "Clear test data"], ["Tasdiq uçun murojaatlar sonini kiriting", "Введите число обращений для подтверждения", "Enter request count to confirm"], ["Superadmin paroli", "Пароль суперадминистратора", "Superadmin password"], ["Öçirişni tasdiqlaş", "Подтвердить удаление", "Confirm deletion"], ["Öçirildi: {count} ta murojaat", "Удалено обращений: {count}", "Deleted requests: {count}"], ["Öçiriladigan yozuvlar sonini tasdiqlang", "Подтвердите число записей для удаления", "Confirm number of records to delete"], ["Öçirilgan murojaatni qayta yaratib bölmaydi", "Удалённое обращение нельзя создать повторно", "Deleted request cannot be recreated"], ["Murojaatlar öçirildi", "Обращения удалены", "Requests deleted"]]);

NavI18n.add([["Arizalar","Обращения","Requests"],["Soni","Количество","Count"]]);

NavI18n.add([["Talabani qidiriş", "Поиск студента", "Find student"], ["Ism-familiya yoki HEMIS ID", "Ф.И.О. или HEMIS ID", "Full name or HEMIS ID"], ["Ism-familiya yoki HEMIS IDni kiriting (2–120 belgi)", "Введите Ф.И.О. или HEMIS ID (2–120 символов)", "Enter name or HEMIS ID (2–120 characters)"], ["Talaba topilmadi. Ism-familiya yoki HEMIS IDni tekşiring.", "Студент не найден. Проверьте Ф.И.О. или HEMIS ID.", "Student not found. Check the name or HEMIS ID."], ["Natijadan talabani tanlang", "Выберите студента из результатов", "Select a student from results"], ["Natijalar köp. Qidiruvni aniqlashtiring.", "Слишком много результатов. Уточните запрос.", "More results available. Refine your search."], ["Qidiruv natijasidan talabani tanlang", "Выберите студента из результатов поиска", "Select a student from search results"]]);
