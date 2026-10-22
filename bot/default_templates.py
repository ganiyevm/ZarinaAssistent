"""Birinchi ishga tushganda bazaga yoziladigan standart shablonlar.

O‘zgaruvchilar: {full_name} {first_name} {last_name} {patronymic}
{name} (ism + otasining ismi) {age} {mention}
"""

DEFAULT_TEMPLATES = {
    ("uz_latn", "M"): [
        "🎉 <b>Hurmatli {full_name}!</b>\n\nSizni tug‘ilgan kuningiz bilan chin qalbdan tabriklaymiz! "
        "Sizga mustahkam sog‘liq, oilaviy farovonlik, mehnatingizda ulkan muvaffaqiyatlar tilaymiz. "
        "Har bir kuningiz quvonch va omadga to‘la bo‘lsin!\n\n<i>Hurmat bilan, hamkasblaringiz</i> {mention}",
        "🎂 Bugun hamkasbimiz <b>{full_name}</b>ning tug‘ilgan kuni!\n\nAziz {name}, Sizni chin dildan qutlaymiz! "
        "Hayotingiz sog‘lik, baxt va baraka bilan bezansin, oldingizga qo‘ygan barcha maqsadlaringizga erishing. "
        "Yangi yoshingiz muborak bo‘lsin! 🎉 {mention}",
        "🥳 <b>{full_name}</b>, tug‘ilgan kuningiz muborak!\n\nSizga tinchlik, sihat-salomatlik, "
        "xonadoningizga fayzu baraka, ishlaringizga rivoj tilaymiz. "
        "Jamoamizda Siz kabi hamkasb borligidan faxrlanamiz! {mention}",
    ],
    ("uz_latn", "F"): [
        "🌷 <b>Hurmatli {full_name}!</b>\n\nSizni tug‘ilgan kuningiz bilan samimiy tabriklaymiz! "
        "Sizga sog‘lik, baxt, oilaviy xotirjamlik va ishlaringizda omad tilaymiz. "
        "Har doim shunday go‘zal, mehribon va quvnoq bo‘lib qoling!\n\n<i>Hurmat bilan, hamkasblaringiz</i> 💐 {mention}",
        "💐 Bugun hamkasbimiz <b>{full_name}</b>ning tug‘ilgan kuni!\n\nAziz {name}, hayotingiz gullardek go‘zal, "
        "kunlaringiz quyoshdek yorug‘ bo‘lsin! Barcha orzu-niyatlaringiz ushalsin. "
        "Tug‘ilgan kuningiz muborak! 🌸 {mention}",
        "🌸 <b>{full_name}</b>, tug‘ilgan kuningiz muborak!\n\nSizga mustahkam sog‘liq, cheksiz baxt, "
        "oilangizga tinchlik va farovonlik tilaymiz. Tabassumingiz hech qachon so‘nmasin! {mention}",
    ],
    ("uz_cyrl", "M"): [
        "🎉 <b>Ҳурматли {full_name}!</b>\n\nСизни туғилган кунингиз билан чин қалбдан табриклаймиз! "
        "Сизга мустаҳкам соғлиқ, оилавий фаровонлик, меҳнатингизда улкан муваффақиятлар тилаймиз. "
        "Ҳар бир кунингиз қувонч ва омадга тўла бўлсин!\n\n<i>Ҳурмат билан, ҳамкасбларингиз</i> {mention}",
        "🎂 Бугун ҳамкасбимиз <b>{full_name}</b>нинг туғилган куни!\n\nАзиз {name}, Сизни чин дилдан қутлаймиз! "
        "Ҳаётингиз соғлик, бахт ва барака билан безансин, олдингизга қўйган барча мақсадларингизга эришинг. "
        "Янги ёшингиз муборак бўлсин! 🎉 {mention}",
        "🥳 <b>{full_name}</b>, туғилган кунингиз муборак!\n\nСизга тинчлик, сиҳат-саломатлик, "
        "хонадонингизга файзу барака, ишларингизга ривож тилаймиз. "
        "Жамоамизда Сиз каби ҳамкасб борлигидан фахрланамиз! {mention}",
    ],
    ("uz_cyrl", "F"): [
        "🌷 <b>Ҳурматли {full_name}!</b>\n\nСизни туғилган кунингиз билан самимий табриклаймиз! "
        "Сизга соғлик, бахт, оилавий хотиржамлик ва ишларингизда омад тилаймиз. "
        "Ҳар доим шундай гўзал, меҳрибон ва қувноқ бўлиб қолинг!\n\n<i>Ҳурмат билан, ҳамкасбларингиз</i> 💐 {mention}",
        "💐 Бугун ҳамкасбимиз <b>{full_name}</b>нинг туғилган куни!\n\nАзиз {name}, ҳаётингиз гуллардек гўзал, "
        "кунларингиз қуёшдек ёруғ бўлсин! Барча орзу-ниятларингиз ушалсин. "
        "Туғилган кунингиз муборак! 🌸 {mention}",
        "🌸 <b>{full_name}</b>, туғилган кунингиз муборак!\n\nСизга мустаҳкам соғлиқ, чексиз бахт, "
        "оилангизга тинчлик ва фаровонлик тилаймиз. Табассумингиз ҳеч қачон сўнмасин! {mention}",
    ],
    ("ru", "M"): [
        "🎉 <b>Уважаемый {full_name}!</b>\n\nОт всей души поздравляем Вас с днём рождения! "
        "Желаем крепкого здоровья, благополучия в семье, новых профессиональных достижений и успехов "
        "во всех начинаниях. Пусть каждый день приносит радость и удачу!\n\n<i>С уважением, коллеги</i> {mention}",
        "🎂 Сегодня день рождения у нашего коллеги <b>{full_name}</b>!\n\n{name}, сердечно поздравляем Вас! "
        "Пусть жизнь будет наполнена здоровьем, счастьем и достатком, а все задуманные цели "
        "обязательно будут достигнуты. С днём рождения! 🎉 {mention}",
        "🥳 <b>{full_name}</b>, с днём рождения!\n\nЖелаем мира, здоровья, тепла и уюта в доме, "
        "процветания в делах. Мы гордимся, что в нашей команде есть такой коллега, как Вы! {mention}",
    ],
    ("ru", "F"): [
        "🌷 <b>Уважаемая {full_name}!</b>\n\nСердечно поздравляем Вас с днём рождения! "
        "Желаем здоровья, счастья, семейного уюта и удачи во всех делах. "
        "Оставайтесь всегда такой же прекрасной, доброй и жизнерадостной!\n\n<i>С уважением, коллеги</i> 💐 {mention}",
        "💐 Сегодня день рождения у нашей коллеги <b>{full_name}</b>!\n\n{name}, пусть жизнь будет "
        "прекрасной, как цветы, а дни — светлыми, как солнце! Пусть исполнятся все мечты. "
        "С днём рождения! 🌸 {mention}",
        "🌸 <b>{full_name}</b>, с днём рождения!\n\nЖелаем крепкого здоровья, безграничного счастья, "
        "мира и благополучия Вашей семье. Пусть Ваша улыбка никогда не гаснет! {mention}",
    ],
}
