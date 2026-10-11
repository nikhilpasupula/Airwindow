"""Reliable, pre-translated tips (English, Hindi, Telugu). Bedrock handles other languages."""

LANGUAGES = {
    "en": "English", "hi": "Hindi", "te": "Telugu", "ta": "Tamil", "bn": "Bengali",
    "mr": "Marathi", "gu": "Gujarati", "kn": "Kannada", "ml": "Malayalam",
    "pa": "Punjabi", "ur": "Urdu",
}

T = {
    "en": {
        "tomorrow": "tomorrow",
        "activity": {"walk": "walk", "run": "run", "commute": "commute"},
        "open": "Best time to open windows: {range}.",
        "no_open_purge": "Outdoor air is poor all day. Keep windows shut and air the room for just 10 minutes at {time}.",
        "no_open": "Outdoor air is poor all day. Keep windows shut and run an air purifier if you have one.",
        "activity_go": "Best time for your {activity}: {range}.",
        "activity_limit": "Air is borderline for a {activity}. Keep it short and easy, around {range}.",
        "activity_avoid": "Air is not good enough for a {activity} today. Do it indoors.",
        "mask_n95": "Wear a well-fitted N95 mask outdoors.",
        "mask_consider": "Consider an N95 mask if you will be outside for long.",
        "trend_worsening": "Air may get worse over the next few hours.",
        "trend_improving": "Air should get better over the next few hours.",
    },
    "hi": {
        "tomorrow": "कल",
        "activity": {"walk": "टहलना", "run": "दौड़ना", "commute": "आना-जाना"},
        "open": "खिड़कियाँ खोलने का सबसे अच्छा समय: {range}।",
        "no_open_purge": "बाहर की हवा दिनभर खराब है। खिड़कियाँ बंद रखें; {time} पर सिर्फ़ 10 मिनट के लिए हवा बदलें।",
        "no_open": "बाहर की हवा दिनभर खराब है। खिड़कियाँ बंद रखें और संभव हो तो एयर प्यूरीफायर चलाएँ।",
        "activity_go": "{activity} के लिए सबसे अच्छा समय: {range}।",
        "activity_limit": "{activity} के लिए हवा सीमा के करीब है। इसे छोटा और हल्का रखें, लगभग {range} के बीच।",
        "activity_avoid": "आज की हवा {activity} के लिए ठीक नहीं है। इसे घर के अंदर करें।",
        "mask_n95": "बाहर जाते समय ठीक से फिट होने वाला N95 मास्क पहनें।",
        "mask_consider": "अगर बाहर ज़्यादा देर रहना हो तो N95 मास्क पहनने पर विचार करें।",
        "trend_worsening": "अगले कुछ घंटों में हवा और बिगड़ सकती है।",
        "trend_improving": "अगले कुछ घंटों में हवा बेहतर होने की उम्मीद है।",
    },
    "te": {
        "tomorrow": "రేపు",
        "activity": {"walk": "నడక", "run": "పరుగు", "commute": "ప్రయాణం"},
        "open": "కిటికీలు తెరవడానికి ఉత్తమ సమయం: {range}.",
        "no_open_purge": "రోజంతా బయటి గాలి బాగాలేదు. కిటికీలు మూసి ఉంచండి; {time} సమయంలో కేవలం 10 నిమిషాలు గాలి మార్చండి.",
        "no_open": "రోజంతా బయటి గాలి బాగాలేదు. కిటికీలు మూసి ఉంచండి, వీలైతే ఎయిర్ ప్యూరిఫైయర్ వాడండి.",
        "activity_go": "{activity} కు ఉత్తమ సమయం: {range}.",
        "activity_limit": "{activity} కు గాలి సరిహద్దులో ఉంది. తక్కువ సమయం, తేలికగా చేయండి, సుమారు {range} మధ్య.",
        "activity_avoid": "ఈ రోజు గాలి {activity} కు సరిపోదు. ఇంటి లోపల చేయండి.",
        "mask_n95": "బయటకు వెళ్లేటప్పుడు సరిగ్గా సరిపోయే N95 మాస్క్ ధరించండి.",
        "mask_consider": "బయట ఎక్కువసేపు ఉండాల్సి వస్తే N95 మాస్క్ ధరించడం గురించి ఆలోచించండి.",
        "trend_worsening": "రాబోయే కొన్ని గంటల్లో గాలి మరింత దిగజారవచ్చు.",
        "trend_improving": "రాబోయే కొన్ని గంటల్లో గాలి మెరుగుపడే అవకాశం ఉంది.",
    },
}
