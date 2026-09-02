from typing import Optional

WELCOME_MESSAGES = {
    "en": "Hello, {name}! Click the menu button or ask me any question directly.",
    "af": "Hallo, {name}! Klik die kieslysknoppie of vra my enige vraag direk.",
    "ar": "مرحبًا، {name}! اضغط على زر القائمة أو اطرح عليّ أي سؤال مباشرةً.",
    "az": "Salam, {name}! Menyu düyməsinə klikləyin və ya sualınızı birbaşa mənə yazın.",
    "bg": "Здравейте, {name}! Натиснете бутона за меню или ми задайте директно въпрос.",
    "bn": "হ্যালো, {name}! মেনু বোতামে ক্লিক করুন অথবা সরাসরি আমাকে যেকোনো প্রশ্ন করুন।",
    "ca": "Hola, {name}! Fes clic al botó del menú o pregunta'm qualsevol cosa directament.",
    "cs": "Ahoj, {name}! Klikněte na tlačítko nabídky nebo se mě přímo na cokoli zeptejte.",
    "da": "Hej, {name}! Klik på menuknappen, eller stil mig et spørgsmål direkte.",
    "de": "Hallo, {name}! Klicke auf die Menüschaltfläche oder stelle mir direkt eine Frage.",
    "el": "Γεια σου, {name}! Πάτησε το κουμπί μενού ή κάνε μου απευθείας οποιαδήποτε ερώτηση.",
    "es": "¡Hola, {name}! Pulsa el botón del menú o hazme cualquier pregunta directamente.",
    "et": "Tere, {name}! Klõpsa menüünuppu või küsi minult otse ükskõik mida.",
    "fa": "سلام {name}! روی دکمهٔ منو بزنید یا سؤال خود را مستقیماً از من بپرسید.",
    "fi": "Hei, {name}! Napsauta valikkopainiketta tai kysy minulta suoraan mitä tahansa.",
    "fr": "Bonjour, {name} ! Cliquez sur le bouton du menu ou posez-moi directement votre question.",
    "he": "שלום, {name}! לחצו על כפתור התפריט או שאלו אותי כל שאלה ישירות.",
    "hi": "नमस्ते, {name}! मेनू बटन पर क्लिक करें या मुझसे सीधे कोई भी सवाल पूछें।",
    "hr": "Bok, {name}! Kliknite gumb izbornika ili mi izravno postavite bilo koje pitanje.",
    "hu": "Szia, {name}! Kattints a menügombra, vagy kérdezz tőlem közvetlenül bármit.",
    "hy": "Բարև, {name}։ Սեղմեք ընտրացանկի կոճակը կամ անմիջապես տվեք ինձ ցանկացած հարց։",
    "id": "Halo, {name}! Klik tombol menu atau tanyakan apa saja langsung kepada saya.",
    "it": "Ciao, {name}! Premi il pulsante del menu o fammi direttamente una domanda.",
    "ja": "こんにちは、{name}さん！メニューボタンを押すか、直接質問してください。",
    "ka": "გამარჯობა, {name}! დააჭირეთ მენიუს ღილაკს ან პირდაპირ დამისვით ნებისმიერი კითხვა.",
    "kk": "Сәлем, {name}! Мәзір түймесін басыңыз немесе маған кез келген сұрақты тікелей қойыңыз.",
    "ko": "안녕하세요, {name}님! 메뉴 버튼을 누르거나 궁금한 점을 바로 질문해 주세요.",
    "lt": "Sveiki, {name}! Spustelėkite meniu mygtuką arba tiesiogiai užduokite man bet kokį klausimą.",
    "lv": "Sveiki, {name}! Noklikšķiniet uz izvēlnes pogas vai uzdodiet man jautājumu tieši.",
    "mn": "Сайн байна уу, {name}! Цэсийн товчийг дарах эсвэл надаас шууд асуултаа асуугаарай.",
    "ms": "Helo, {name}! Klik butang menu atau tanya saya apa-apa soalan secara terus.",
    "nl": "Hallo, {name}! Klik op de menuknop of stel me rechtstreeks een vraag.",
    "no": "Hei, {name}! Klikk på menyknappen eller still meg et spørsmål direkte.",
    "pl": "Cześć, {name}! Kliknij przycisk menu lub zadaj mi dowolne pytanie bezpośrednio.",
    "pt": "Olá, {name}! Clique no botão do menu ou faça-me qualquer pergunta diretamente.",
    "ro": "Salut, {name}! Apasă butonul de meniu sau adresează-mi direct orice întrebare.",
    "ru": "Привет, {name}! Нажмите кнопку меню или задайте мне любой вопрос прямо в чате.",
    "sk": "Ahoj, {name}! Kliknite na tlačidlo ponuky alebo sa ma priamo čokoľvek opýtajte.",
    "sl": "Pozdravljeni, {name}! Kliknite gumb menija ali mi neposredno zastavite katero koli vprašanje.",
    "sr": "Здраво, {name}! Притисните дугме менија или ми директно поставите било које питање.",
    "sv": "Hej, {name}! Klicka på menyknappen eller ställ en fråga direkt till mig.",
    "sw": "Habari, {name}! Bofya kitufe cha menyu au niulize swali lolote moja kwa moja.",
    "th": "สวัสดี {name}! คลิกปุ่มเมนูหรือถามคำถามกับฉันได้โดยตรง",
    "tr": "Merhaba, {name}! Menü düğmesine tıklayın veya sorunuzu doğrudan bana yazın.",
    "uk": "Привіт, {name}! Натисніть кнопку меню або поставте мені будь-яке запитання прямо в чаті.",
    "ur": "سلام، {name}! مینو بٹن پر کلک کریں یا مجھ سے براہِ راست کوئی بھی سوال پوچھیں۔",
    "uz": "Salom, {name}! Menyu tugmasini bosing yoki menga istalgan savolni to‘g‘ridan-to‘g‘ri yozing.",
    "vi": "Xin chào, {name}! Hãy nhấn nút menu hoặc hỏi tôi bất kỳ câu hỏi nào trực tiếp.",
    "zh": "你好，{name}！点击菜单按钮，或直接向我提问。",
}

LANGUAGE_ALIASES = {
    "in": "id",
    "iw": "he",
    "nb": "no",
    "nn": "no",
}


def get_welcome_message(language_code: Optional[str], name: str) -> str:
    language = (language_code or "en").lower().replace("_", "-").split("-", 1)[0]
    language = LANGUAGE_ALIASES.get(language, language)
    template = WELCOME_MESSAGES.get(language, WELCOME_MESSAGES["en"])
    return template.format(name=name)
