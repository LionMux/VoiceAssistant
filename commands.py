from Levenshtein import distance

COMMANDS = {
    
    "открой ютуб": {
        "response": "voices/ok1.wav",
        "variations": ["открой ютуб", "открой youtube", "открой ютюб",
                       "запусти ютуб", "кровь ютуб", "включи ютуб"],
        "action": "open_youtube"
    },
    
    "открой телеграмм": {
        "response": "voices/ok1.wav",
        "variations": ["открой телеграмм", "открой telegramm", "открой тг",
                       "откой телегу", "открывай телеграмм", "открой теге", "открой телегу", "про телеграмм"],
        "action": "open_tg"
    },
    
    "пора спать": {
        "response": "voices/ok1.wav",
        "variations": ["спящий режим", "режим сна", "компьютер спать"],
        "action": "sleep_mode"
    },
    
    "открой вк": {
        "response": "voices/ok1.wav",
        "variations": ["открой в контакте", "открой вконтакте", "открой вк",
                       "откой вк", "открывай вкон", "открой вокон", "открой вака"],
        "action": "open_vk"
    },
    
    "включи музыку": {
    "response": "voices/ok1.wav",
    "variations": ["включи музыку", "включи spotify", "играй музыку", "запусти spotify",
                   "включи music", "включи спотик", "включи спотифай", "включи музло",
                   "чем музыку"],
    "action": "spotify_play_track"
    },

    "поставь на паузу": {
        "response": "voices/ok1.wav",
        "variations": ["поставь на паузу", "пауза", "останови музыку", "стоп","заткнись"],
        "action": "spotify_pause"
    },

    "следующий трек": {
        "response": "voices/ok1.wav",
        "variations": ["следующий трек", "следующая песня", "дальше", "некст", "следующую"],
        "action": "spotify_next"
    },

    "предыдущий трек": {
        "response": "voices/ok1.wav",
        "variations": ["предыдущий трек", "предыдущая песня", "назад", "prev"],
        "action": "spotify_previous"
    },

    "что играет": {
        "response": "voices/ok1.wav",
        "variations": ["что играет", "какая песня", "что за трек", "что сейчас играет",
                       "какой трек играет", "что за песня"],
        "action": "spotify_current"
    },
    
    "любимые треки": {
        "response": "voices/ok1.wav",
        "variations": ["включи любимые", "включи любимую музыку",
                       "любимые треки", "включи любимые треки", "включи мою любимую музыку"],
        "action": "spotify_play_liked"
    },
}

ERROR_RESPONSE = "voices/not_found.wav"

LEVENSHTEIN_THRESHOLD = 3

def levenshtein_distance(s1, s2):
    return distance(s1.lower(), s2.lower())

def find_command(user_text):
    if not user_text:
        return None
    
    user_text = user_text.lower().strip()
    #print(f"DEBUG: Ищу команду для '{user_text}' (длина: {len(user_text)})")
    
    best_match = None
    min_distance = float('inf')
    
    for command_name, command_data in COMMANDS.items():
        dist = levenshtein_distance(user_text, command_name)
        #print(f"  - '{command_name}': расстояние {dist}")
        
        if dist < min_distance:
            min_distance = dist
            best_match = {
                "command": command_name,
                "response": command_data["response"],
                "action": command_data.get("action"),
                "distance": dist
            }
        
        for variation in command_data.get("variations", []):
            dist = levenshtein_distance(user_text, variation)
            #print(f"    вариация '{variation}': расстояние {dist}")
            
            if dist < min_distance:
                min_distance = dist
                best_match = {
                    "command": command_name,
                    "response": command_data["response"],
                    "action": command_data.get("action"),
                    "distance": dist
                }
    
    if best_match and min_distance <= LEVENSHTEIN_THRESHOLD:
        print(f"Найдена команда: '{best_match['command']}' (расстояние: {min_distance})")
        return best_match
    
    print(f"Команда не найдена (минимальное расстояние: {min_distance})")
    return None

            
        
