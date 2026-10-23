"""Bilingual EIA glossary inventory for NORTHWISE.

This module holds the canonical EIA terminology reference used to answer
plain-language definition questions from the public.  Every entry is:

  1. A plain-language bilingual explanation.
  2. Labelled with category, source, source section, example, etc.
  3. NEVER a quotation of numeric criteria that has not been verified.
  4. NEVER a project-specific claim.

Numeric thresholds (BNLs, AQO limits, Action/Limit Levels, etc.) are NOT
quoted here. Where helpful we say "Refer to the current TM-EIAO" so users
find authoritative values from EPD, rather than us re-stating possibly
out-of-date figures.

Inventory size: 54 unique canonical terms (target range 40-60).
Three previously-existing entries (noise contour map, noise barrier,
hydrological assessment) are retained at the END of their categories.

This is NOT a report-evidence source.  ``_lookup_glossary`` returns this
data with ``source == "glossary"``; report evidence stays in
``evidence`` cards with verified citations.
"""

import re

# ---------------------------------------------------------------------------
# Glossary entries
# ---------------------------------------------------------------------------

_GLOSSARY_ENTRIES = [
    # ===== A. NOISE =====
    {
        "key": "noise_sensitive_receiver",
        "aliases": ["NSR", "nsr", "noise sensitive receivers",
                    "噪音敏感受體", "噪音敏感接收者", "噪音感受體"],
        "category": "noise",
        "en": (
            "A Noise Sensitive Receiver (NSR) is any place where people live, "
            "rest, learn, or receive care, and which therefore deserves "
            "special protection from noise. Typical NSRs include homes, "
            "schools, hospitals, places of worship, libraries, and parks. "
            "An EIA must locate the NSRs near a project and assess how much "
            "noise they will receive during construction and operation."
        ),
        "zh-Hant": (
            "噪音敏感受體（NSR）是指任何有人居住、休息、學習或接受護理、"
            "因此應受較高水平噪音保護的地方。常見例子包括住宅、學校、"
            "醫院、教堂、圖書館及公園。環評報告須找出項目附近的 NSR，"
            "並評估工程在施工及營運期間對它們造成的噪音影響。"
        ),
        "why_it_matters_en": (
            "If you live near a road, railway, or construction site, your "
            "home may be an NSR. The EIA should show how much noise reaches "
            "your home and whether mitigation (such as a barrier) is needed."
        ),
        "why_it_matters_zh": (
            "如果你住在道路、鐵路或建築地盤附近，你的住所可能就是噪音敏"
            "感受體。環評應該顯示有多少噪音傳到你的住所，以及是否需要"
            "安裝隔音屏障等緩解措施。"
        ),
        "example_en": (
            "Illustrative example: a primary school 80 m from a proposed road "
            "would normally be classified as an NSR. The EIA must measure "
            "predicted noise levels at the school building and at the "
            "playground during school hours."
        ),
        "example_zh": (
            "說明例子：一所距離擬建道路 80 米的小學，通常會被分類為噪音"
            "敏感受體。環評須評估上課時段校舍及操場的預測噪音水平。"
        ),
        "interpreting_numbers_en": (
            "Noise levels are measured in dB(A) — see that entry. NSR "
            "impacts are usually reported as the predicted noise level at "
            "the receiver in dB(A) and the change versus the baseline."
        ),
        "common_misunderstanding_en": (
            "An NSR is not a person — it is a place. The same home can be an "
            "NSR for one project and not another, depending on distance and "
            "noise source."
        ),
        "source_name": "EIAO Technical Memorandum on Noise (Annex 5/7)",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "EIAO Noise section / NSR definition",
    },
    {
        "key": "db_a",
        "aliases": ["dB(A)", "dba", "db(a)", "DBA", "分貝（A 加權）", "分貝"],
        "category": "noise",
        "en": (
            "dB(A) stands for A-weighted decibels. It is the standard unit "
            "for measuring environmental noise so that the measurement "
            "matches how the human ear hears sounds of different pitches. "
            "An increase of 10 dB(A) is generally perceived as about "
            "twice as loud; a 3 dB(A) increase is just noticeable."
        ),
        "zh-Hant": (
            "分貝（A 加權），即 dB(A)，是量度環境噪音的標準單位。A 加權"
            "讓量度結果配合人耳對不同頻率聲音的敏感度。一般而言，噪音"
            "增加 10 dB(A) 會令人覺得音量約為原來的兩倍；增加 3 dB(A) "
            "則剛好能察覺得到。"
        ),
        "why_it_matters_en": (
            "When you read a noise contour map or an EIA table, the numbers "
            "are in dB(A). Knowing this helps you judge whether predicted "
            "levels are quiet (below 55 dB(A)) or loud (above 70 dB(A))."
        ),
        "why_it_matters_zh": (
            "閱讀噪音等高線圖或環評表格時，所有單位都是 dB(A)。了解這"
            "點有助你判斷預測水平是偏低（55 dB(A) 以下）還是偏高（70 "
            "dB(A) 以上）。"
        ),
        "interpreting_numbers_en": (
            "Approximate guidance: 35 dB(A) is a quiet bedroom; 55 dB(A) is "
            "normal conversation at 1 m; 75 dB(A) is a busy road; 85 dB(A) "
            "and above can damage hearing over time."
        ),
        "interpreting_numbers_zh": (
            "粗略參考：35 dB(A) 是寧靜的睡房；55 dB(A) 是 1 米外正常對"
            "話；75 dB(A) 是繁忙道路；85 dB(A) 或以上長期暴露會損害聽力。"
        ),
        "common_misunderstanding_en": (
            "An increase from 60 to 63 dB(A) does NOT sound 5% louder — it "
            "doubles the sound energy. dB(A) is logarithmic, not linear."
        ),
        "common_misunderstanding_zh": (
            "由 60 dB(A) 升至 63 dB(A) 並非只響 5%，而是聲能增加一倍。"
            "dB(A) 是對數單位，並非線性。"
        ),
        "source_name": "EPD Noise Criteria / TM-EIAO",
        "source_url": "https://www.epd.gov.hk/epd/noise_education/web/text/ENG_EPD_HTML/m2/types_5.html",
        "source_section": "EPD Noise Education - Basic Noise Levels",
    },
    {
        "key": "noise_barrier",
        "aliases": ["noise barriers", "barrier", "sound barrier",
                    "噪音屏障", "隔音屏障", "隔音牆"],
        "category": "noise",
        "en": (
            "A noise barrier is a solid wall or earth mound built beside a "
            "road or railway to block or reduce sound reaching nearby "
            "buildings. It does not stop the noise at the source; it "
            "shields the area behind it. In an EIA, engineers design "
            "barriers to meet legal noise limits and protect homes, "
            "schools, and hospitals."
        ),
        "zh-Hant": (
            "噪音屏障是建於道路或鐵路旁邊的實心牆或土堤，用以阻擋或減"
            "少聲音傳到附近建築物。它並不在源頭消除噪音，而是保護屏障"
            "後方的區域。在環評中，工程師設計屏障以符合法定噪音限制，"
            "並保護住宅、學校及醫院。"
        ),
        "why_it_matters_en": (
            "Barriers can reduce traffic noise by 5 to 10 dB(A) at nearby "
            "homes. Their height, length, and position matter; a gap or a "
            "thin barrier loses much of the benefit."
        ),
        "why_it_matters_zh": (
            "屏障可將附近住宅的交通噪音減低 5 至 10 dB(A)。屏障的高"
            "度、長度及位置都很重要；如果有缺口或屏障太薄，效益會大"
            "幅降低。"
        ),
        "source_name": "EIAO TM / EPD Noise Education",
        "source_url": "https://www.epd.gov.hk/epd/noise_education/web/text/ENG_EPD_HTML/m2/types_5.html",
        "source_section": "Noise mitigation measures",
    },
    {
        "key": "noise_criteria",
        "aliases": ["noise criterion", "noise standards", "noise limits",
                    "Basic Noise Level", "BNL", "基本噪音水平",
                    "噪音標準", "噪音準則", "設計噪音水平"],
        "category": "noise",
        "en": (
            "Noise criteria are the dB(A) levels an EIA must not exceed at "
            "Noise Sensitive Receivers. They are based on the area type "
            "(for example, a quiet suburban area has a stricter limit than "
            "an urban mixed-use area) and on whether the project is at "
            "construction or operational stage."
        ),
        "zh-Hant": (
            "噪音準則是環評在噪音敏感受體處不可以超過的分貝水平。準則"
            "依據地區類型而定（例如寧靜的住宅區限制比綜合用途區嚴格）"
            "以及工程是處於施工還是營運階段。"
        ),
        "why_it_matters_en": (
            "The criteria decide whether a predicted noise level is "
            "'acceptable' or whether mitigation is required. They appear "
            "in many EIA chapters and refer to TM-EIAO tables."
        ),
        "interpreting_numbers_en": (
            "Refer to the current TM-EIAO Annex 5 (operational road traffic) "
            "and Annex 7 (construction noise) for the exact dB(A) limits. "
            "These values are updated periodically by EPD."
        ),
        "common_misunderstanding_en": (
            "The criterion is not a single value — it varies by area type, "
            "by day vs night, and by construction vs operation. Always "
            "check which one the report is applying."
        ),
        "source_name": "EIAO TM Annex 5 and Annex 7",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "TM-EIAO noise annexes",
    },
    {
        "key": "construction_noise",
        "aliases": ["construction phase noise", "建造工程噪音", "建築噪音", "建造噪音"],
        "category": "noise",
        "en": (
            "Construction noise is the noise produced while a project is "
            "being built, for example from piling, excavation, or the use "
            "of powered mechanical equipment. It is usually louder than "
            "operational noise but lasts for a shorter time."
        ),
        "zh-Hant": (
            "建造工程噪音是工程在施工期間所產生的噪音，例如打樁、開挖"
            "或使用機動設備所發出的噪音。它通常比營運噪音大，但持續時"
            "間較短。"
        ),
        "why_it_matters_en": (
            "Construction noise can disturb nearby residents at any time, "
            "including night work. Hong Kong requires a Construction Noise "
            "Permit (CNP) for restricted-hour work."
        ),
        "source_name": "Noise Control Ordinance Cap. 400 / EPD",
        "source_url": "https://www.epd.gov.hk/epd/english/laws_regulations/enforcement/laws_eflhk.html",
        "source_section": "Noise Control Ordinance (NCO)",
    },
    {
        "key": "ambient_noise",
        "aliases": ["background noise", "noise climate", "背景噪音"],
        "category": "noise",
        "en": (
            "Ambient noise is the existing 'background' noise level at a "
            "site before the project starts. It includes traffic, wind, "
            "and community activities. EIAs measure ambient noise so they "
            "can show how much the project itself adds."
        ),
        "zh-Hant": (
            "背景噪音是項目動工前該地點已經存在的「底層」噪音，包括交"
            "通、風聲及社區活動。環評會量度背景噪音，以便顯示工程本身"
            "額外增加了多少噪音。"
        ),
        "source_name": "EIAO TM Noise section",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "TM-EIAO baseline monitoring",
    },
    {
        "key": "operational_noise",
        "aliases": ["operational phase noise", "運作期間噪音", "營運噪音"],
        "category": "noise",
        "en": (
            "Operational noise is the noise produced while the project is "
            "in normal use, for example road traffic on a new highway or "
            "ventilation fans in a tunnel. EIAs predict this noise for the "
            "design year (often 10-20 years ahead) and compare it to the "
            "criteria."
        ),
        "zh-Hant": (
            "營運噪音是項目正常運作期間所產生的噪音，例如新公路上的交"
            "通或隧道內的通風風扇。環評會為設計年份（通常為 10 至 20 "
            "年後）預測此噪音，並與相關準則比較。"
        ),
        "source_name": "EIAO TM Noise section",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "TM-EIAO operational noise",
    },
    {
        "key": "acoustic_enclosure",
        "aliases": ["acoustic enclosures", "noise enclosure",
                    "隔音罩", "隔音圍封", "噪音圍封"],
        "category": "noise",
        "en": (
            "An acoustic enclosure is a fully or partially sealed cover "
            "around noisy equipment (such as a generator, pump, or HVAC "
            "unit). Sound-absorbent lining inside the enclosure reduces "
            "the noise that escapes to the surrounding area."
        ),
        "zh-Hant": (
            "隔音罩是完全或局部密封的罩殼，包圍嘈吵的設備（例如發電機"
            "、水泵或空調機組）。罩殼內部加入吸音物料，減少噪音外洩。"
        ),
        "source_name": "EIAO / EPD Noise mitigation",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "Noise mitigation measures",
    },

    # ===== B. AIR QUALITY =====
    {
        "key": "air_sensitive_receiver",
        "aliases": ["ASR", "asr", "air sensitive receivers",
                    "空氣敏感受體", "空氣敏感接收者"],
        "category": "air",
        "en": (
            "An Air Sensitive Receiver (ASR) is any place where people "
            "spend time and where air pollution could meaningfully affect "
            "their health. ASRs include homes, schools, hospitals, offices, "
            "and outdoor areas where the public gathers. EIAs identify ASRs "
            "near a project and predict pollutant concentrations at them."
        ),
        "zh-Hant": (
            "空氣敏感受體（ASR）是任何有人長時間停留、空氣污染可能對其"
            "健康造成影響的地方。ASR 包括住宅、學校、醫院、辦公室及公"
            "眾聚集的戶外地方。環評會找出項目附近的 ASR，並預測該處的"
            "污染物濃度。"
        ),
        "why_it_matters_en": (
            "If you live or work near a project, your home or office may be "
            "an ASR. The EIA should report predicted pollution levels at "
            "your location and compare them to the Air Quality Objectives."
        ),
        "interpreting_numbers_en": (
            "Predicted concentrations are reported in micrograms per cubic "
            "metre (µg/m³). They are averaged over different periods "
            "(1-hour, 24-hour, annual) for different pollutants."
        ),
        "source_name": "EIAO TM / Hong Kong Air Quality Objectives",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "TM-EIAO Air Quality section",
    },
    {
        "key": "air_quality_objective",
        "aliases": ["AQO", "aqo", "Air Quality Objectives",
                    "空氣質素指標", "空氣質素目標", "空氣指標"],
        "category": "air",
        "en": (
            "Air Quality Objectives (AQOs) are the maximum concentrations "
            "of key pollutants that should not be exceeded in outdoor air "
            "to protect public health. They are set by the Hong Kong "
            "government for pollutants such as sulphur dioxide, nitrogen "
            "dioxide, ozone, PM10, PM2.5, and carbon monoxide, over "
            "averaging periods from 1 hour to 1 year."
        ),
        "zh-Hant": (
            "空氣質素指標（AQO）是為保障公眾健康而訂定的戶外空氣中主要"
            "污染物不可超出的最高濃度水平。香港政府為二氧化硫、二氧化"
            "氮、臭氧、PM10、PM2.5 及一氧化碳等污染物訂立指標，平均時"
            "間由 1 小時至 1 年不等。"
        ),
        "why_it_matters_en": (
            "When an EIA predicts pollution levels, it compares them to "
            "the AQO. A result above the AQO means mitigation is required."
        ),
        "interpreting_numbers_en": (
            "Refer to the current Hong Kong Air Quality Objectives for "
            "specific µg/m³ values. EPD periodically revises them."
        ),
        "source_name": "Hong Kong Air Quality Objectives (EPD)",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "AQO review (latest published)",
    },
    {
        "key": "tsp",
        "aliases": ["Total Suspended Particulates", "1-hour TSP", "24-hour TSP",
                    "TSP", "tsp", "總懸浮粒子"],
        "category": "air",
        "en": (
            "Total Suspended Particulates (TSP) measures the total mass of "
            "tiny solid or liquid particles suspended in the air. Hong Kong "
            "uses 1-hour and 24-hour TSP limits as Air Quality Objectives. "
            "PM10 is a sub-category of particles smaller than 10 µm; PM2.5 "
            "is the smaller sub-category most linked to health effects."
        ),
        "zh-Hant": (
            "總懸浮粒子（TSP）量度空氣中懸浮的固體或液體粒子的總重量。"
            "香港的空氣質素指標包含 1 小時及 24 小時 TSP 限值。PM10 是"
            "直徑小於 10 微米的粒子；PM2.5 是更細的子類別，與健康影響"
            "關係最密切。"
        ),
        "why_it_matters_en": (
            "Construction sites that handle soil or break concrete can "
            "release large amounts of dust. EIAs often set TSP limits at "
            "the site boundary and require dust-suppression measures."
        ),
        "interpreting_numbers_en": (
            "Refer to the current EPD Air Quality Objectives for the exact "
            "µg/m³ limits. 1-hour and 24-hour averages are reported "
            "separately because peak short-term levels matter as well as "
            "daily exposure."
        ),
        "common_misunderstanding_en": (
            "TSP is not the same as PM10 or PM2.5. TSP counts all "
            "particles of any size, while PM10 and PM2.5 only count "
            "finer fractions. Hong Kong applies separate limits to each."
        ),
        "source_name": "EPD Air Quality Objectives",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "AQO schedule",
    },
    {
        "key": "pm",
        "aliases": ["PM10", "PM2.5", "pm10", "pm2.5", "particulate matter",
                    "懸浮粒子", "微細粒子", "可吸入懸浮粒子"],
        "category": "air",
        "en": (
            "PM10 and PM2.5 are measures of fine particles in the air: "
            "PM10 includes particles 10 micrometres or smaller; PM2.5 "
            "includes those 2.5 micrometres or smaller. The smaller the "
            "particle, the deeper it can enter the lungs, so PM2.5 is "
            "linked to more serious health effects."
        ),
        "zh-Hant": (
            "PM10 和 PM2.5 是量度空氣中微細粒子的指標：PM10 包括直徑 10 "
            "微米或以下的粒子；PM2.5 只包括 2.5 微米或以下的更細粒子。"
            "粒子越細，能進入肺部越深，因此 PM2.5 與較嚴重的健康影響"
            "相關。"
        ),
        "why_it_matters_en": (
            "Busy roads and power plants are common PM2.5 sources. EIAs "
            "model how a project would change PM2.5 levels at ASRs."
        ),
        "interpreting_numbers_en": (
            "Concentrations are reported in µg/m³. WHO publishes "
            "internationally-recommended limits that are stricter than "
            "many countries' standards; Hong Kong's AQO may differ."
        ),
        "common_misunderstanding_en": (
            "PM2.5 is not 'twice as small as PM10'. PM2.5 counts a subset "
            "of the particles that PM10 counts, but the two metrics are "
            "measured and reported separately."
        ),
        "source_name": "EPD AQO; WHO Air Quality Guidelines 2021",
        "source_url": "https://www.who.int/publications/i/item/9789240034228",
        "source_section": "WHO Global Air Quality Guidelines (international reference)",
    },
    {
        "key": "dust_emissions",
        "aliases": ["dust emission", "construction dust",
                    "塵埃排放", "建築塵埃", "揚塵"],
        "category": "air",
        "en": (
            "Dust emissions are visible particles released into the air, "
            "most often from construction sites handling soil, demolition, "
            "stockpiles, or unpaved roads. EIAs require dust-control "
            "measures such as water sprays, wheel washing, and covered "
            "stockpiles."
        ),
        "zh-Hant": (
            "塵埃排放是可見粒子釋放到空氣中，最常見於處理泥土、拆卸工"
            "程、堆料區或行車道的建築地盤。環評要求採取防塵措施，例如"
            "灑水、洗車胎及覆蓋堆料。"
        ),
        "source_name": "EIAO TM Air Quality section / EPD guidance",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "Construction dust best practices",
    },
    {
        "key": "air_quality_modelling",
        "aliases": ["air quality model", "dispersion model",
                    "空氣質素模擬", "擴散模擬"],
        "category": "air",
        "en": (
            "Air quality modelling uses computer simulation to predict how "
            "pollutants from a project will spread through the air, given "
            "wind, terrain, and emission rates. The output is a map of "
            "predicted concentrations at ASRs."
        ),
        "zh-Hant": (
            "空氣質素模擬利用電腦模擬，根據風向、地形及排放率預測項目"
            "所釋放的污染物會如何在空氣中擴散。輸出結果是一張顯示 ASR "
            "預測污染濃度的地圖。"
        ),
        "source_name": "EIAO TM Air Quality",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "TM-EIAO air modelling requirements",
    },

    # ===== C. WATER & HYDROLOGY =====
    {
        "key": "water_quality_impact",
        "aliases": ["water quality impacts", "水質影響"],
        "category": "water",
        "en": (
            "A water quality impact is any change in the physical, "
            "chemical, or biological characteristics of a water body "
            "(river, stream, harbour, groundwater) caused by a project. "
            "Sources include construction site runoff, sewage discharge, "
            "and accidental spills."
        ),
        "zh-Hant": (
            "水質影響是指工程項目令水體（河流、溪流、海港、地下水）的"
            "物理、化學或生物特質所產生的變化。常見源頭包括建築地盤"
            "徑流、污水排放及意外溢漏。"
        ),
        "source_name": "EIAO TM Water Quality section",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "TM-EIAO water quality",
    },
    {
        "key": "sewerage",
        "aliases": ["sewerage system", "sewage treatment", "sewage",
                    "污水處理", "污水渠", "排水系統"],
        "category": "water",
        "en": (
            "Sewerage refers to the network of pipes and treatment works "
            "that collects and treats wastewater from homes, businesses, "
            "and industry before discharge. An EIA evaluates whether the "
            "existing sewerage system can cope with the additional flow "
            "from a project."
        ),
        "zh-Hant": (
            "污水處理系統是指收集和處理住宅、商業及工業廢水，然後才排放"
            "的管道網絡及處理廠。環評會評估現有系統能否應付項目所增加的"
            "流量。"
        ),
        "source_name": "EIAO / Drainage Services Department",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "TM-EIAO sewerage impact",
    },
    {
        "key": "suspended_solids",
        "aliases": ["suspended solid", "SS", "TSS",
                    "懸浮固體"],
        "category": "water",
        "en": (
            "Suspended solids are solid particles that float in water "
            "without dissolving. High levels make water cloudy, block "
            "light to aquatic plants, and smother fish spawning grounds. "
            "Construction runoff often carries large amounts of suspended "
            "solids."
        ),
        "zh-Hant": (
            "懸浮固體是浮於水中而不溶解的固體粒子。含量高會令水變得"
            "混濁，阻礙光線到達水中植物，並堵塞魚類產卵地。建築徑流"
            "常帶有大量懸浮固體。"
        ),
        "interpreting_numbers_en": (
            "Reported in mg/L. Higher values mean dirtier water. Treatment "
            "plant effluent targets are very low mg/L."
        ),
        "source_name": "EIAO TM Water Quality",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "TM-EIAO water quality parameters",
    },
    {
        "key": "surface_runoff",
        "aliases": ["runoff", "stormwater runoff",
                    "地面徑流", "暴雨徑流"],
        "category": "water",
        "en": (
            "Surface runoff is rainwater that flows over the ground rather "
            "than soaking in. On construction sites, runoff picks up soil, "
            "chemicals, and waste before reaching drains or streams. EIAs "
            "require runoff control to stop pollutants reaching water bodies."
        ),
        "zh-Hant": (
            "地面徑流是雨水在地面流過而沒有滲入泥土的部分。在建築地盤，"
            "徑流會帶走泥沙、化學品及廢物，再流入雨水渠或溪流。環評要求"
            "控制徑流，避免污染物進入水體。"
        ),
        "source_name": "EIAO / DSD guidance",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "Stormwater management",
    },
    {
        "key": "dissolved_oxygen",
        "aliases": ["DO", "dissolved oxygen level",
                    "溶解氧", "溶氧"],
        "category": "water",
        "en": (
            "Dissolved oxygen is the amount of oxygen mixed in the water, "
            "which fish and other aquatic life need to breathe. Pollution "
            "and warm water both reduce dissolved oxygen. Below a "
            "certain level, fish die and the ecosystem collapses."
        ),
        "zh-Hant": (
            "溶解氧是水中所含的氧氣份量，魚類及其他水中生物需要用它呼"
            "吸。污染和水温升高都會降低溶解氧。當溶氧低過某一水平，"
            "魚類會死亡，生態系統會崩潰。"
        ),
        "interpreting_numbers_en": (
            "Reported in mg/L. Healthy rivers usually have DO above 6 mg/L. "
            "Levels below 4 mg/L stress fish; below 2 mg/L is dangerous."
        ),
        "source_name": "EIAO TM Water Quality",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "Water quality parameters",
    },
    {
        "key": "catchment_area",
        "aliases": ["catchment", "watershed", "drainage catchment",
                    "集水區", "流域", "排水集水區"],
        "category": "water",
        "en": (
            "A catchment area is the entire area of land where rainfall "
            "drains to a single river, stream, lake, or harbour. Any "
            "project within a catchment can affect water quality and flow "
            "throughout that catchment."
        ),
        "zh-Hant": (
            "集水區是指雨水最終都會流到同一條河流、溪流、湖泊或海港的"
            "整片土地。任何在集水區內的工程，都可能影響整個集水區的"
            "水質及水流。"
        ),
        "source_name": "EIAO / DSD hydrology guidance",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "Drainage impact assessment",
    },
    {
        "key": "dewatering",
        "aliases": ["groundwater lowering", "groundwater pumping",
                    "降水工程", "抽地下水"],
        "category": "water",
        "en": (
            "Dewatering is the removal of groundwater to allow excavation "
            "or construction in a dry area. It can lower the water table "
            "across a wide area, affecting nearby wells, foundations, and "
            "vegetation. EIAs often require re-injection or flow-rate "
            "limits."
        ),
        "zh-Hant": (
            "降水工程是為了在乾爽的環境進行挖掘或施工而抽出地下水的工"
            "程。它可能在大範圍降低地下水位，影響附近的井、地基及植被。"
            "環評通常會要求回灌或限制抽水量。"
        ),
        "source_name": "EIAO TM Groundwater section",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "Groundwater impact",
    },

    # ===== D. ECOLOGY =====
    {
        "key": "wetland",
        "aliases": ["wetlands", "濕地"],
        "category": "ecology",
        "en": (
            "Wetlands are areas where the land is covered by shallow "
            "water, such as marshes, mangroves, and fish ponds. They "
            "support many species, filter pollutants, and buffer floods. "
            "Hong Kong designates some wetlands as 'Wetland Conservation "
            "Areas' under the EIAO."
        ),
        "zh-Hant": (
            "濕地是被淺水覆蓋的區域，例如沼澤、紅樹林及魚塘。它們為眾"
            "多物種提供棲息地、隔濾污染物，並紓緩洪水。香港在環評條例"
            "下劃定部分濕地為「濕地保育區」。"
        ),
        "source_name": "EIAO Wetland Conservation Area provisions",
        "source_url": "https://www.elegislation.gov.hk/hk/cap499",
        "source_section": "EIAO Schedule 5 / Wetland Conservation Areas",
    },
    {
        "key": "vegetation",
        "aliases": ["plant communities", "flora communities",
                    "植被", "植物群落"],
        "category": "ecology",
        "en": (
            "Vegetation refers to the plant cover of an area: trees, "
            "shrubs, grasses, and herbs. EIAs map the existing vegetation, "
            "identify rare or protected species, and propose replacement "
            "planting to compensate for losses."
        ),
        "zh-Hant": (
            "植被是指某地區的植物覆蓋：包括喬木、灌木、草本植物等。環"
            "評會繪製現有植被地圖，識別稀有或受保護品種，並建議補種植"
            "物以補償損失。"
        ),
        "source_name": "EIAO TM Ecology",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "TM-EIAO vegetation survey",
    },
    {
        "key": "fauna",
        "aliases": ["faunal", "animal groups", "animals", "動物群", "動物"],
        "category": "ecology",
        "en": (
            "Fauna means the animal life of an area: mammals, birds, "
            "reptiles, amphibians, insects, and so on. EIAs survey fauna "
            "before construction to identify which species are present "
            "and whether any are protected."
        ),
        "zh-Hant": (
            "動物群是指某地區的動物生命，包括哺乳類、鳥類、爬蟲類、"
            "兩棲類、昆蟲等。環評會在施工前進行動物群調查，以識別該"
            "處有哪些物種，以及有否受保護品種。"
        ),
        "source_name": "EIAO TM Ecology",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "TM-EIAO fauna survey",
    },
    {
        "key": "flora",
        "aliases": ["floral", "plant species", "植物群", "植物"],
        "category": "ecology",
        "en": (
            "Flora means the plant life of an area: trees, shrubs, herbs, "
            "ferns, mosses, and so on. EIAs survey flora to identify rare "
            "or protected species and to plan transplanting where needed."
        ),
        "zh-Hant": (
            "植物群是指某地區的植物生命，包括喬木、灌木、草本、蕨類、"
            "苔蘚等。環評會調查植物群，識別稀有或受保護品種，並在需要"
            "時規劃移植。"
        ),
        "source_name": "EIAO TM Ecology",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "TM-EIAO flora survey",
    },
    {
        "key": "avifauna",
        "aliases": ["bird fauna", "birds", "鳥類", "鳥類群"],
        "category": "ecology",
        "en": (
            "Avifauna means the bird life of an area. EIAs that may affect "
            "wetlands or woodlands survey birds specifically, including "
            "any protected or migratory species, and the seasons when they "
            "are present."
        ),
        "zh-Hant": (
            "鳥類群是指某地區的鳥類生命。可能影響濕地或林地的環評會專"
            "門調查鳥類，包括任何受保護品種或候鳥，以及牠們在哪些季"
            "節出現。"
        ),
        "source_name": "EIAO TM Ecology / AFCD guidance",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "TM-EIAO avifauna survey",
    },
    {
        "key": "species_of_conservation_importance",
        "aliases": ["species of conservation concern",
                    "conservation importance species",
                    "受關注物種", "受保育關注物種"],
        "category": "ecology",
        "en": (
            "Species of conservation importance are plants or animals that "
            "are listed as rare, threatened, endangered, or otherwise "
            "protected under Hong Kong or international frameworks (such "
            "as IUCN Red List). EIAs give them extra protection and may "
            "require translocation or habitat protection."
        ),
        "zh-Hant": (
            "受關注物種是指在香港或國際框架（如 IUCN 紅色名錄）下被列"
            "為稀有、受威脅、瀕危或受保護的動植物。環評會為牠們提供"
            "額外保護，並可能要求遷移或保護棲息地。"
        ),
        "source_name": "EIAO TM / AFCD / IUCN Red List",
        "source_url": "https://www.iucnredlist.org",
        "source_section": "IUCN Red List (international reference)",
    },
    {
        "key": "habitat_loss",
        "aliases": ["habitat destruction", "loss of habitat",
                    "生境損失", "棲息地損失"],
        "category": "ecology",
        "en": (
            "Habitat loss is when a project removes the natural place "
            "where a species lives — for example, clearing woodland or "
            "filling a fish pond. It is the main cause of biodiversity "
            "decline worldwide, and EIAs must quantify and offset it."
        ),
        "zh-Hant": (
            "生境損失是指工程移除了某物種原先生存的自然環境，例如清除"
            "林地或填平魚塘。這是全球生物多樣性下降的主要原因，環評必"
            "須量化及補償。"
        ),
        "source_name": "EIAO TM Ecology / Biodiversity",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "Habitat impact assessment",
    },
    {
        "key": "ecological_baseline",
        "aliases": ["ecological baseline survey", "baseline ecology",
                    "生態基線", "生態基線調查"],
        "category": "ecology",
        "en": (
            "An ecological baseline is the survey of plants, animals, and "
            "habitats that exists at a site before a project starts. "
            "Subsequent monitoring compares later conditions to the "
            "baseline to detect change."
        ),
        "zh-Hant": (
            "生態基線是工程動工前在某地點對植物、動物及生境所作的調"
            "查。之後的監察會將日後的狀況與基線比較，以偵測變化。"
        ),
        "source_name": "EIAO TM Ecology",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "Baseline conditions",
    },
    {
        "key": "habitat_fragmentation",
        "aliases": ["fragmentation of habitat",
                    "生境破碎", "棲息地碎片化"],
        "category": "ecology",
        "en": (
            "Habitat fragmentation happens when a road, railway, or "
            "development splits a large habitat into smaller pieces. "
            "Animals that need a wide range struggle to cross these "
            "barriers. EIAs consider ecological corridors and crossing "
            "structures."
        ),
        "zh-Hant": (
            "生境破碎是指道路、鐵路或發展項目把一大片生境切割成多個"
            "小區。需要大範圍活動的動物難以跨越這些屏障。環評會考慮"
            "生態廊道及動物通道。"
        ),
        "source_name": "EIAO TM Ecology",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "Habitat connectivity",
    },
    {
        "key": "tree_survey",
        "aliases": ["tree surveys", "tree inspection",
                    "樹木調查", "樹木勘察"],
        "category": "ecology",
        "en": (
            "A tree survey records all trees that may be affected by a "
            "project, their species, size, condition, and importance. "
            "EIAs propose to retain, transplant, or fell trees and "
            "compensate by planting replacement trees."
        ),
        "zh-Hant": (
            "樹木調查記錄工程可能影響的所有樹木，包括品種、大小、狀"
            "況及價值。環評建議保留、移植或砍伐樹木，並以補種作補償。"
        ),
        "source_name": "EIAO / Development Bureau Tree Preservation",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "Tree preservation",
    },

    # ===== E. WASTE & LAND CONTAMINATION =====
    {
        "key": "chemical_waste",
        "aliases": ["chemical wastes",
                    "化學廢物"],
        "category": "waste",
        "en": (
            "Chemical waste is any waste that is dangerous because of its "
            "chemical properties — for example, used oils, solvents, "
            "batteries, or laboratory chemicals. Hong Kong requires "
            "chemical waste producers to register with EPD and use "
            "licensed waste collectors."
        ),
        "zh-Hant": (
            "化學廢物是指因化學特性而屬於危險的廢物，例如廢機油、溶劑"
            "、電池或實驗室化學品。香港規定化學廢物產生者須向環保署登"
            "記，並聘用持牌廢物收集商處理。"
        ),
        "source_name": "Waste Disposal Ordinance Cap. 354 / Chemical Waste Scheme",
        "source_url": "https://www.epd.gov.hk/epd/english/laws_regulations/enforcement/laws_eflhk.html",
        "source_section": "Chemical waste control",
    },
    {
        "key": "cd_waste",
        "aliases": ["C&D waste", "construction and demolition waste", "C&D",
                    "拆建廢料", "建築廢料", "建造及拆卸廢物"],
        "category": "waste",
        "en": (
            "Construction and Demolition (C&D) waste is material produced "
            "when something is built or demolished: concrete, bricks, "
            "timber, metal, soil, and so on. EIAs estimate how much C&D "
            "waste a project will produce and how it will be reused, "
            "recycled, or disposed of."
        ),
        "zh-Hant": (
            "拆建廢料（C&D 廢料）是在建造或拆卸過程中產生的廢物：包"
            "括混凝土、磚塊、木材、金屬、泥土等。環評會估算工程產生多"
            "少 C&D 廢料，以及如何重用、回收或棄置。"
        ),
        "source_name": "EIAO Waste Management section",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "C&D waste management",
    },
    {
        "key": "contaminated_land",
        "aliases": ["contaminated land assessment", "land contamination",
                    "受污染土地", "土地污染"],
        "category": "land",
        "en": (
            "Contaminated land is land that contains substances at "
            "concentrations considered harmful to human health or the "
            "environment, usually from past industrial use such as gas "
            "works, petrol stations, or factories. EIAs require site "
            "investigations and remediation where appropriate."
        ),
        "zh-Hant": (
            "受污染土地是指土壤中含有被認為對人體健康或環境有害的物"
            "質，通常源自過往的工業用途，例如煤氣廠、油站或工廠。環"
            "評要求進行地盤勘察，並在適當時進行修復。"
        ),
        "source_name": "EIAO / EPD Contaminated Land Site Audit",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "Land contamination assessment",
    },
    {
        "key": "remediation",
        "aliases": ["site remediation", "soil remediation",
                    "修復", "場地修復", "土壤修復"],
        "category": "land",
        "en": (
            "Remediation is the clean-up of contaminated land to make it "
            "safe for its intended use. Methods include removing "
            "contaminated soil, treating it on site, or capping it under "
            "a clean layer. EIAs evaluate which method is most suitable."
        ),
        "zh-Hant": (
            "修復是清理受污染土地以達到擬定用途安全標準的過程。方法包"
            "括移除受污染泥土、原地處理，或以乾淨的覆蓋層封蓋。環評會"
            "評估哪種方法最為適合。"
        ),
        "source_name": "EIAO / EPD Contaminated Land",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "Remediation methods",
    },
    {
        "key": "risk_based_remediation_goals",
        "aliases": ["risk-based remediation", "remediation goals",
                    "風險為本修復目標", "風險評估修復"],
        "category": "land",
        "en": (
            "Risk-based remediation goals are the cleanup targets set for "
            "a contaminated site, based on how people and ecosystems "
            "might actually contact the contamination (for example, by "
            "playing on the soil or growing vegetables). The cleanup "
            "level is set to be safe for the planned use, not a generic "
            "background level."
        ),
        "zh-Hant": (
            "風險為本修復目標是按人及生態系統可能實際接觸污染物的情況"
            "（例如在泥土上玩耍或種植蔬菜），為受污染地盤訂定的清理目"
            "標。清理水平須配合擬定用途而達至安全，而非追求通用的背景"
            "水平。"
        ),
        "source_name": "EIAO / EPD guidance on contaminated land",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "Risk-based remediation",
    },

    # ===== F. LANDSCAPE & HERITAGE =====
    {
        "key": "lvia",
        "aliases": ["LVIA", "Landscape and Visual Impact Assessment",
                    "景觀及視覺影響評估", "景觀視覺評估"],
        "category": "lvia",
        "en": (
            "A Landscape and Visual Impact Assessment (LVIA) is the "
            "study in an EIA that evaluates how a project would change "
            "the visual character of the landscape and what Visual "
            "Sensitive Receivers (VSRs) would see. It includes photo "
            "simulations from key viewpoints."
        ),
        "zh-Hant": (
            "景觀及視覺影響評估（LVIA）是環評中評估工程如何改變景觀"
            "視覺特色，以及哪些視覺敏感受體（VSR）會受影響的研究。它"
            "包括從主要觀景點拍攝的照片模擬。"
        ),
        "source_name": "EIAO / EPD LVIA Guidance",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "Landscape and Visual section",
    },
    {
        "key": "visual_sensitive_receiver",
        "aliases": ["VSR", "vsr", "visual sensitive receivers",
                    "視覺敏感受體", "視覺敏感接收者"],
        "category": "lvia",
        "en": (
            "A Visual Sensitive Receiver (VSR) is any location where "
            "people view the landscape and where the project would "
            "change that view. VSRs include homes, lookouts, parks, "
            "popular walking trails, and scenic roads."
        ),
        "zh-Hant": (
            "視覺敏感受體（VSR）是指公眾觀賞景觀的某個位置，而工程會"
            "改變該處的景觀。VSR 包括住宅、觀景點、公園、熱門行山徑"
            "及風景優美的道路。"
        ),
        "source_name": "EIAO LVIA section",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "Visual sensitivity",
    },
    {
        "key": "fung_shui",
        "aliases": ["feng shui", "fung shui", "fengshui", "風水"],
        "category": "heritage",
        "en": (
            "Fung shui (or feng shui) is a traditional Chinese practice "
            "of arranging buildings, graves, and landscapes in harmony "
            "with the surrounding terrain and 'qi' (vital energy). Hong "
            "Kong EIAO recognises fung shui as a heritage value that "
            "projects must consider, especially in rural and village "
            "settings."
        ),
        "zh-Hant": (
            "風水是中國傳統的習俗，講求建築、墓地及景觀與周圍地形和"
            "「氣」的配合。香港環評條例把風水列為文物價值之一，工程"
            "（尤其是鄉郊及村落附近的項目）必須加以考慮。"
        ),
        "why_it_matters_en": (
            "Some villagers and clans regard certain trees, hill "
            "outlines, or water courses as having fung shui value. EIAs "
            "consider impact on these views and may propose protection "
            "measures."
        ),
        "source_name": "EIAO Heritage section / AMO guidance",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "Cultural heritage considerations",
    },
    {
        "key": "heritage_impact_assessment",
        "aliases": ["HIA", "heritage impact", "cultural heritage impact",
                    "文物影響評估", "文化遺產影響評估"],
        "category": "heritage",
        "en": (
            "A Heritage Impact Assessment (HIA) evaluates how a project "
            "would affect declared monuments, graded historic buildings, "
            "sites of archaeological interest, and other cultural "
            "heritage assets. It is required when heritage assets are "
            "near a project."
        ),
        "zh-Hant": (
            "文物影響評估（HIA）評估工程對法定古蹟、有級別的歷史建"
            "築、考古地點及其他文化遺產的影響。當工程鄰近有這些資"
            "產時必須進行此評估。"
        ),
        "source_name": "EIAO Heritage section / AMO",
        "source_url": "https://www.amo.gov.hk",
        "source_section": "Heritage Impact Assessment guidance",
    },
    {
        "key": "archaeological_impact_assessment",
        "aliases": ["AIA", "archaeological assessment",
                    "考古影響評估", "考古評估"],
        "category": "heritage",
        "en": (
            "An Archaeological Impact Assessment (AIA) investigates "
            "whether a project would disturb archaeological remains, "
            "either by direct removal or by changing groundwater or "
            "access. It may recommend excavation, monitoring, or "
            "preservation in place."
        ),
        "zh-Hant": (
            "考古影響評估（AIA）調查工程會否干擾考古遺蹟，不論是直"
            "接移除、改變地下水位，或是改變進出通道。評估可能建議"
            "進行考古挖掘、監察，或原地保存。"
        ),
        "source_name": "EIAO / AMO",
        "source_url": "https://www.amo.gov.hk",
        "source_section": "Archaeological investigation",
    },

    # ===== G. ASSESSMENT, MITIGATION & MONITORING =====
    {
        "key": "mitigation_measures",
        "aliases": ["mitigation", "mitigations",
                    "緩解措施", "緩解方法", "減輕措施"],
        "category": "general",
        "en": (
            "Mitigation measures are the actions a project takes to "
            "prevent, reduce, or remedy an environmental impact. "
            "Examples include noise barriers, dust suppression, "
            "transplanting trees, building ecological corridors, and "
            "limiting work hours."
        ),
        "zh-Hant": (
            "緩解措施是工程為防止、減少或補救環境影響所採取的行動。"
            "例子包括安裝噪音屏障、灑水防塵、移植樹木、設置生態廊"
            "道，以及限制施工時間。"
        ),
        "why_it_matters_en": (
            "When you read an EIA, mitigation measures are usually "
            "listed for each impact. They are the practical things the "
            "project will do to address concerns."
        ),
        "source_name": "EIAO TM",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "TM-EIAO mitigation hierarchy",
    },
    {
        "key": "baseline_conditions",
        "aliases": ["baseline", "existing conditions", "baseline survey",
                    "基線情況", "基線狀況", "現有狀況"],
        "category": "general",
        "en": (
            "Baseline conditions are the existing environmental "
            "conditions at a site before a project starts. The EIA "
            "measures and reports these so that any future change can "
            "be compared to them. Baseline studies cover noise, air, "
            "water, ecology, traffic, and other topics as relevant."
        ),
        "zh-Hant": (
            "基線情況是工程動工前該地點的現有環境狀況。環評會量度及"
            "記錄這些狀況，以便日後的變化可以與其比較。基線研究涵蓋"
            "噪音、空氣、水質、生態、交通等相關範疇。"
        ),
        "source_name": "EIAO TM",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "TM-EIAO baseline monitoring",
    },
    {
        "key": "residual_impact",
        "aliases": ["residual impacts", "residual effects",
                    "剩餘影響", "殘餘影響"],
        "category": "general",
        "en": (
            "A residual impact is the environmental effect that remains "
            "after mitigation measures have been applied. An EIA should "
            "report both the impact before mitigation and the residual "
            "impact afterwards, and explain why any residual impact is "
            "considered acceptable."
        ),
        "zh-Hant": (
            "剩餘影響是指實施緩解措施後仍然存在的環境影響。環評應"
            "同時報告緩解前及緩解後的影響，並解釋為何剩餘影響可以"
            "接受。"
        ),
        "source_name": "EIAO TM",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "TM-EIAO residual impact evaluation",
    },
    {
        "key": "cumulative_impact",
        "aliases": ["cumulative impacts", "cumulative effects",
                    "累積影響"],
        "category": "general",
        "en": (
            "A cumulative impact is the combined effect of a project "
            "together with other existing or planned projects in the "
            "same area. The EIA must consider these together, not just "
            "in isolation, because two small impacts can add up to a "
            "large one."
        ),
        "zh-Hant": (
            "累積影響是項目與同一地區內其他現有或規劃中項目加起來"
            "所造成的總體影響。環評須一併考慮，而非只看個別項目，"
            "因為兩個小影響相加可以變成大影響。"
        ),
        "source_name": "EIAO TM / cumulative impact assessments",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "TM-EIAO cumulative impacts",
    },
    {
        "key": "ema",
        "aliases": ["EM&A", "environmental monitoring and audit", "EM&A Manual",
                    "環境監察及審核", "環監", "環境監察"],
        "category": "monitoring",
        "en": (
            "Environmental Monitoring and Audit (EM&A) is the ongoing "
            "checking of environmental conditions during construction "
            "and operation. An EM&A Manual sets out what to measure, "
            "where, when, and the Action and Limit Levels that trigger "
            "responses. Independent auditors verify the results."
        ),
        "zh-Hant": (
            "環境監察及審核（EM&A）是在施工及營運期間對環境狀況作持"
            "續監察的工作。EM&A 手冊訂明量度甚麼、量度地點、頻密程度"
            "及觸發回應的行動水平和極限水平，並由獨立審核人員核實結果。"
        ),
        "why_it_matters_en": (
            "EM&A is what keeps promises honest. After an EIA is "
            "approved, EM&A reports check that the actual conditions on "
            "site match the predictions."
        ),
        "source_name": "EIAO / EPD EM&A Manual guidance",
        "source_url": "https://www.epd.gov.hk/eia/files/applications/en/pp_156/eia_1806/progress/action_2277/3_EM%26A%20Manual/HTML/EMA.htm",
        "source_section": "EM&A Manual example (illustrative)",
    },
    {
        "key": "study_brief",
        "aliases": ["EIA Study Brief", "Study Brief", "ESB",
                    "環評研究概要", "研究概要"],
        "category": "process",
        "en": (
            "An EIA Study Brief is the document issued by EPD that "
            "tells the project proponent exactly what their EIA must "
            "address — which topics, what methods, what assumptions. "
            "It is the 'scope of work' for the EIA study."
        ),
        "zh-Hant": (
            "環評研究概要是由環保署發出的文件，訂明項目倡議人的環評"
            "須涵蓋哪些課題、使用何種方法及假設。它是環評研究的工"
            "作範圍。"
        ),
        "why_it_matters_en": (
            "If you read an EIA report, the Study Brief tells you what "
            "questions the EIA was required to answer."
        ),
        "source_name": "EIAO Section 5",
        "source_url": "https://www.elegislation.gov.hk/hk/cap499",
        "source_section": "EIAO Cap. 499 Section 5",
    },
    {
        "key": "environmental_permit",
        "aliases": ["EP", "environmental permit",
                    "環境許可證", "環評許可證"],
        "category": "process",
        "en": (
            "An Environmental Permit (EP) is the legal document EPD "
            "issues after an EIA has been approved. The permit sets out "
            "the conditions the project must follow during construction "
            "and operation, including the approved mitigation measures "
            "and the EM&A requirements."
        ),
        "zh-Hant": (
            "環境許可證（EP）是環評獲批准後由環保署發出的法定文件。"
            "許可證訂明工程在施工及營運期間須遵守的條件，包括核准"
            "的緩解措施及 EM&A 要求。"
        ),
        "source_name": "EIAO Cap. 499 Section 10",
        "source_url": "https://www.elegislation.gov.hk/hk/cap499",
        "source_section": "EIAO Cap. 499 Section 10 (issue of EP)",
    },
    {
        "key": "action_level_limit_level",
        "aliases": ["Action Level", "Limit Level", "AL", "LL",
                    "行動水平", "極限水平", "行動及極限水平"],
        "category": "monitoring",
        "en": (
            "Action Level and Limit Level are trigger values set in an "
            "EM&A Manual. Action Level is the first threshold where "
            "extra checks, audits, or corrective actions are required. "
            "Limit Level is a stricter threshold that, when crossed, "
            "requires immediate response and may halt work."
        ),
        "zh-Hant": (
            "行動水平和極限水平是 EM&A 手冊所訂定的觸發值。行動水平"
            "是初步門檻，達到時須進行額外檢查、審核或修正措施。極"
            "限水平是更嚴格的門檻，超過時須即時回應，並可能需要暫"
            "停工程。"
        ),
        "interpreting_numbers_en": (
            "Specific µg/m³, dB(A), or mg/L values are set per project "
            "in the EM&A Manual and may differ between pollutants. "
            "Refer to the project's approved EM&A Manual for the exact "
            "values applicable."
        ),
        "common_misunderstanding_en": (
            "Action Level and Limit Level are project-specific — they "
            "are not fixed national standards. Always check the EM&A "
            "Manual of the specific project for its trigger values."
        ),
        "source_name": "EIAO / EPD EM&A Manual guidance",
        "source_url": "https://www.epd.gov.hk/eia/files/applications/en/pp_156/eia_1806/progress/action_2277/3_EM%26A%20Manual/HTML/EMA.htm",
        "source_section": "EM&A Manual Action / Limit Level definitions",
    },
    {
        "key": "landfill_gas",
        "aliases": ["LFG", "landfill gas hazard",
                    "堆填區氣體", "堆填氣體"],
        "category": "landfill",
        "en": (
            "Landfill gas is the mixture of gases (mainly methane and "
            "carbon dioxide) produced when waste in a landfill breaks "
            "down. It can be a safety hazard if it builds up in "
            "enclosed spaces. Some EIAs must study the impact of new "
            "developments near old landfills."
        ),
        "zh-Hant": (
            "堆填區氣體是堆填區內廢物分解時所產生的混合氣體（主要"
            "是甲烷及二氧化碳）。如果聚集於密閉空間，可能構成安全"
            "危險。部分環評須研究新發展項目對附近舊堆填區的影響。"
        ),
        "source_name": "EIAO / EPD Landfill Gas Hazard section",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "Landfill gas assessment",
    },
    {
        "key": "ground_borne_vibration",
        "aliases": ["groundborne vibration", "ground vibration",
                    "地傳振動", "地盤振動"],
        "category": "noise",
        "en": (
            "Ground-borne vibration is shaking of the ground caused by "
            "traffic, construction (especially piling and blasting), or "
            "machinery. Sensitive buildings nearby can be damaged or "
            "disturbed. EIAs predict vibration levels and may set speed "
            "or method limits."
        ),
        "zh-Hant": (
            "地傳振動是由交通、施工（特別是打樁及爆破）或機器所引"
            "起的地面震動。附近的敏感建築物可能受損或受干擾。環評會"
            "預測振動水平，並可能設定速度或施工方法的限制。"
        ),
        "source_name": "EIAO / EPD guidance on vibration",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "Vibration limits (refer to current EPD)",
    },
    {
        "key": "designated_project",
        "aliases": ["DP", "designated projects",
                    "指定工程項目", "指定工程"],
        "category": "process",
        "en": (
            "A Designated Project (DP) is a type of project listed in "
            "the EIAO Schedule 2 (for example, a new highway of certain "
            "length, a new power station, a large reclamation) that "
            "requires an Environmental Permit before construction. "
            "Minor projects below the schedule threshold do not."
        ),
        "zh-Hant": (
            "指定工程項目（DP）是列於環評條例附表 2 的工程類別（例"
            "如某長度的新公路、新電廠、大型填海），在施工前必須取得"
            "環境許可證。未達附表門檻的小型工程則不需。"
        ),
        "source_name": "EIAO Cap. 499 Schedule 2",
        "source_url": "https://www.elegislation.gov.hk/hk/cap499",
        "source_section": "EIAO Cap. 499 Schedule 2 (list of DPs)",
    },

    # ===== Existing entries kept (low corpus frequency, but key concepts) =====
    {
        "key": "noise_contour_map",
        "aliases": ["noise contour map", "noise contour", "contour map",
                    "噪音等高線圖", "噪音等高線", "噪音地圖"],
        "category": "noise",
        "en": (
            "A noise contour map is a diagram that shows noise levels "
            "across an area, similar to how a weather map shows "
            "temperature. Lines on the map connect places with the same "
            "noise level, so you can see which areas are noisier and "
            "which are quieter. In an EIA, it is used to predict how a "
            "project might change noise levels around homes, schools, "
            "and parks."
        ),
        "zh-Hant": (
            "噪音等高線圖是一種顯示區域內噪音水平的圖表，類似天氣圖"
            "顯示温度。圖上的線連接噪音水平相同的地方，讓你可以看到"
            "哪些區域較嘈吵、哪些較安靜。在環評中，它用來預測工程"
            "項目可能如何改變住宅、學校和公園周圍的噪音水平。"
        ),
        "source_name": "EPD Noise Education / EIAO",
        "source_url": "https://www.epd.gov.hk/epd/noise_education/web/text/ENG_EPD_HTML/m2/types_5.html",
        "source_section": "Noise contour illustration",
    },
    {
        "key": "hydrological_assessment",
        "aliases": ["hydrological assessment", "hydrology assessment",
                    "水文評估", "水文分析"],
        "category": "water",
        "en": (
            "A hydrological assessment studies how water moves through "
            "an area — including rainfall, rivers, drainage, and "
            "groundwater — and how a project might change these flows. "
            "It helps predict risks such as flooding, erosion, or "
            "reduced water supply. In an EIA, it ensures that "
            "construction and operation do not harm the natural water "
            "system or nearby communities."
        ),
        "zh-Hant": (
            "水文評估研究水如何在一個區域內流動——包括降雨、河流、"
            "排水和地下水——以及工程項目可能如何改變這些水流。它有助"
            "於預測洪水、侵蝕或供水減少等風險。在環評中，水文評估確"
            "保施工和營運不會損害自然水系統或附近社區。"
        ),
        "source_name": "EIAO TM Water section / DSD",
        "source_url": "https://www.epd.gov.hk/eia/en/faq/index.html",
        "source_section": "Hydrological impact section",
    },
]


# ---------------------------------------------------------------------------
# Lookup helpers (used by app.py)
# ---------------------------------------------------------------------------

def _is_ascii_plural(word: str) -> bool:
    """True if `word` is an English word ending in 's' (not 'ss', not 'us')."""
    return (
        bool(word)
        and word[-1].isalpha()
        and ord(word[-1]) < 128
        and word.endswith("s")
        and not word.endswith("ss")
        and not word.endswith("us")
    )


def _maybe_strip_last_s(low: str) -> str:
    """Strip trailing 's' from the last word of a multi-word phrase."""
    if " " in low and _is_ascii_plural(low):
        return low[:-1]
    return ""


# Build lookup index for fast alias -> entry resolution.  For English
# aliases ending in 's' (plural) we also auto-register the singular form
# so that user questions like "What is a noise sensitive receiver?" work
# whether the source alias was plural or singular.  Multi-word English
# phrases also get their last word stripped if it ends in 's' (so
# "mitigation measures" indexes also as "mitigation measure").
_ALIAS_INDEX = {}
for _e in _GLOSSARY_ENTRIES:
    # 1. Register the canonical English key phrase (split underscores)
    canonical_phrase = _e["key"].replace("_", " ")
    _ALIAS_INDEX.setdefault(canonical_phrase.lower(), _e)
    stripped = _maybe_strip_last_s(canonical_phrase.lower())
    if stripped:
        _ALIAS_INDEX.setdefault(stripped, _e)
    # 2. Register every alias, plus its ASCII singular variant if applicable
    for alias in _e["aliases"]:
        low = alias.lower()
        _ALIAS_INDEX.setdefault(low, _e)
        # Auto-register English singular variants (single word)
        if _is_ascii_plural(low):
            _ALIAS_INDEX.setdefault(low[:-1], _e)
        # Multi-word phrase: strip last word's 's'
        stripped = _maybe_strip_last_s(low)
        if stripped:
            _ALIAS_INDEX.setdefault(stripped, _e)

# Aliases written entirely in capitals are acronyms. Keep their written form:
# the index is lowercased, and lowercased acronyms collide with ordinary words
# ("DO" = dissolved oxygen vs. the verb "do").
_ACRONYM_FORMS = {}
for _e in _GLOSSARY_ENTRIES:
    for _a in _e["aliases"]:
        if (2 <= len(_a) <= 5 and _a.isascii() and any(c.isalpha() for c in _a)
                and not any(c.islower() for c in _a)):
            _ACRONYM_FORMS.setdefault(_a.lower(), _a)


def get_glossary_entries():
    """Return the full glossary list. Used by tests and admin views."""
    return _GLOSSARY_ENTRIES


def lookup_entry_by_alias(text: str):
    """Return the entry whose alias matches `text` (case-insensitive).

    `text` may be a multi-word phrase (e.g. "noise sensitive receiver") or
    a short alias (e.g. "NSR").  Whitespace and common trailing characters
    are normalised.  A trailing 's' is also stripped to allow plural
    variants ("receivers" -> "receiver").  Returns None if no alias
    matches.
    """
    if not text:
        return None
    norm = text.strip().lower().strip(".,;:?!？。，；：、")
    # 1. exact lowercase
    entry = _ALIAS_INDEX.get(norm)
    if entry:
        return entry
    # 2. trailing 's'
    if norm.endswith("s") and not norm.endswith("ss"):
        entry = _ALIAS_INDEX.get(norm[:-1])
        if entry:
            return entry
    # 3. trailing "ies" -> "y" (e.g. "species" partial)
    if norm.endswith("ies") and len(norm) > 4:
        entry = _ALIAS_INDEX.get(norm[:-3] + "y")
        if entry:
            return entry
    return None


def find_entry_in_text(text: str):
    """Search for any known term in arbitrary `text`.

    Returns the longest matching entry or None.  Used when a user writes
    something like "Tell me about NSRs" — there is no explicit "what is"
    but the term appears.

    Word-boundary rules: short acronyms (1-2 chars, e.g. "AL") require
    word-boundary matching to avoid false positives like "AL" inside
    "geotechnical".  Longer aliases use substring matching.

    Acronyms written in capitals must appear in capitals.  Case-insensitive
    matching let the alias "DO" (dissolved oxygen) match the ordinary word
    "do", so "How do I cook pasta?" returned a dissolved-oxygen definition —
    an unrelated source attached to a question the reports never address.
    """
    if not text:
        return None
    lower = text.lower()

    # Try longest aliases first
    candidates = []
    for alias, entry in _ALIAS_INDEX.items():
        if not alias:
            continue
        if alias not in lower:
            continue
        acronym = _ACRONYM_FORMS.get(alias)
        if acronym is not None:
            pattern = r"(?<![A-Za-z])" + re.escape(acronym) + r"s?(?![A-Za-z])"
            if re.search(pattern, text):
                candidates.append((len(alias), alias, entry))
            continue
        # For 1-2 char aliases, require word boundary on both sides
        if len(alias) <= 2:
            pattern = r"(?:^|[^\w])" + re.escape(alias) + r"(?:$|[^\w])"
            if re.search(pattern, lower):
                candidates.append((len(alias), alias, entry))
        else:
            candidates.append((len(alias), alias, entry))

    if not candidates:
        return None
    candidates.sort(key=lambda x: -x[0])
    return candidates[0][2]


def total_entries():
    return len(_GLOSSARY_ENTRIES)
