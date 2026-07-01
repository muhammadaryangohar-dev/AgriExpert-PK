% ================================================================
%   AgriExpert-PK :: Intelligent Agricultural Expert System
%   Knowledge Base  —  SWI-Prolog
%
%   MODULES IMPLEMENTED:
%     1. Knowledge Representation   Facts about crops, diseases,
%                                    symptoms, soil, weather
%     2. Rule-Based Expert System   IF-THEN disease rules
%     3. Forward Chaining           derive_all/1 collects all
%                                    conclusions from asserted facts
%     4. Backward Chaining          diagnose/3 works goal-first
%     5. Unification                Prolog's native pattern-matching
%     6. Certainty Factors          cf_diagnose/4 returns 0-100%
%
%   AI Techniques: Backward Chaining, Forward Chaining,
%                  Unification, Rule-Based Reasoning,
%                  Certainty Factors
%
%   Author  : AgriExpert-PK Team
%   Version : 2.0  (Full System)
% ================================================================

:- dynamic crop/1.
:- dynamic symptom/1.
:- dynamic weather/1.
:- dynamic soil/1.
:- dynamic season/1.
:- dynamic field_age/1.
:- dynamic derived/1.       % used by forward chaining

% ================================================================
%  MODULE 1 — KNOWLEDGE REPRESENTATION
%  Static encyclopaedic facts about the domain
% ================================================================

%  Crop family membership
crop_family(wheat,      cereal).
crop_family(rice,       cereal).
crop_family(maize,      cereal).
crop_family(barley,     cereal).
crop_family(cotton,     fiber).
crop_family(sugarcane,  cash).
crop_family(potato,     vegetable).
crop_family(tomato,     vegetable).
crop_family(onion,      vegetable).
crop_family(mango,      fruit).
crop_family(citrus,     fruit).
crop_family(sunflower,  oilseed).
crop_family(mustard,    oilseed).

%  Disease taxonomy
disease_class(rice_blast,            fungal).
disease_class(wheat_yellow_rust,     fungal).
disease_class(wheat_brown_rust,      fungal).
disease_class(wheat_loose_smut,      fungal).
disease_class(wheat_powdery_mildew,  fungal).
disease_class(cotton_leaf_curl,      viral).
disease_class(cotton_boll_rot,       bacterial).
disease_class(cotton_fusarium_wilt,  fungal).
disease_class(cotton_alternaria,     fungal).
disease_class(rice_bacterial_blight, bacterial).
disease_class(rice_sheath_blight,    fungal).
disease_class(rice_brown_spot,       fungal).
disease_class(rice_tungro,           viral).
disease_class(maize_smut,            fungal).
disease_class(maize_downy_mildew,    fungal).
disease_class(maize_stalk_rot,       fungal).
disease_class(maize_leaf_blight,     fungal).
disease_class(sugarcane_red_rot,     fungal).
disease_class(sugarcane_smut,        fungal).
disease_class(sugarcane_ratoon_stunt,bacterial).
disease_class(potato_late_blight,    fungal).
disease_class(potato_early_blight,   fungal).
disease_class(potato_blackleg,       bacterial).
disease_class(tomato_early_blight,   fungal).
disease_class(tomato_fusarium_wilt,  fungal).
disease_class(tomato_bacterial_spot, bacterial).
disease_class(mango_anthracnose,     fungal).
disease_class(mango_malformation,    fungal).
disease_class(citrus_canker,         bacterial).
disease_class(citrus_greening,       bacterial).

% ── Pathogen scientific names ────────────────────────────────────
pathogen(rice_blast,            'Magnaporthe oryzae').
pathogen(wheat_yellow_rust,     'Puccinia striiformis').
pathogen(wheat_brown_rust,      'Puccinia triticina').
pathogen(wheat_loose_smut,      'Ustilago tritici').
pathogen(wheat_powdery_mildew,  'Blumeria graminis').
pathogen(cotton_leaf_curl,      'Cotton Leaf Curl Virus / Bemisia tabaci').
pathogen(cotton_boll_rot,       'Xanthomonas / Colletotrichum complex').
pathogen(cotton_fusarium_wilt,  'Fusarium oxysporum').
pathogen(cotton_alternaria,     'Alternaria macrospora').
pathogen(rice_bacterial_blight, 'Xanthomonas oryzae pv. oryzae').
pathogen(rice_sheath_blight,    'Rhizoctonia solani').
pathogen(rice_brown_spot,       'Bipolaris oryzae').
pathogen(rice_tungro,           'Rice Tungro Spherical/Bacilliform Virus').
pathogen(maize_smut,            'Ustilago maydis').
pathogen(maize_downy_mildew,    'Peronosclerospora sorghi').
pathogen(maize_stalk_rot,       'Fusarium/Pythium complex').
pathogen(maize_leaf_blight,     'Exserohilum turcicum').
pathogen(sugarcane_red_rot,     'Colletotrichum falcatum').
pathogen(sugarcane_smut,        'Sporisorium scitamineum').
pathogen(sugarcane_ratoon_stunt,'Leifsonia xyli subsp. xyli').
pathogen(potato_late_blight,    'Phytophthora infestans').
pathogen(potato_early_blight,   'Alternaria solani').
pathogen(potato_blackleg,       'Pectobacterium atrosepticum').
pathogen(tomato_early_blight,   'Alternaria solani').
pathogen(tomato_fusarium_wilt,  'Fusarium oxysporum f.sp. lycopersici').
pathogen(tomato_bacterial_spot, 'Xanthomonas campestris pv. vesicatoria').
pathogen(mango_anthracnose,     'Colletotrichum gloeosporioides').
pathogen(mango_malformation,    'Fusarium mangiferae').
pathogen(citrus_canker,         'Xanthomonas axonopodis pv. citri').
pathogen(citrus_greening,       'Candidatus Liberibacter asiaticus').

% ── Spread mode ─────────────────────────────────────────────────
spread(rice_blast,            airborne_spores).
spread(wheat_yellow_rust,     airborne_urediniospores).
spread(wheat_brown_rust,      airborne_urediniospores).
spread(wheat_loose_smut,      seed_borne).
spread(wheat_powdery_mildew,  airborne_conidia).
spread(cotton_leaf_curl,      whitefly_vector).
spread(cotton_boll_rot,       rain_splash).
spread(cotton_fusarium_wilt,  soil_borne).
spread(cotton_alternaria,     airborne_conidia).
spread(rice_bacterial_blight, water_splash).
spread(rice_sheath_blight,    soil_borne).
spread(rice_brown_spot,       airborne_conidia).
spread(rice_tungro,           leafhopper_vector).
spread(maize_smut,            airborne_teliospores).
spread(maize_downy_mildew,    oospore_soil).
spread(maize_stalk_rot,       soil_borne).
spread(maize_leaf_blight,     airborne_conidia).
spread(sugarcane_red_rot,     infected_setts).
spread(sugarcane_smut,        airborne_teliospores).
spread(sugarcane_ratoon_stunt,infected_setts).
spread(potato_late_blight,    airborne_sporangia).
spread(potato_early_blight,   airborne_conidia).
spread(potato_blackleg,       seed_tuber).
spread(tomato_early_blight,   airborne_conidia).
spread(tomato_fusarium_wilt,  soil_borne).
spread(tomato_bacterial_spot, rain_splash).
spread(mango_anthracnose,     airborne_conidia).
spread(mango_malformation,    airborne_ascospores).
spread(citrus_canker,         wind_rain_splash).
spread(citrus_greening,       psyllid_vector).

% ── Yield loss range (min%, max%) ───────────────────────────────
yield_loss_range(rice_blast,            10, 30).
yield_loss_range(wheat_yellow_rust,     10, 70).
yield_loss_range(wheat_brown_rust,       5, 40).
yield_loss_range(wheat_loose_smut,       5, 25).
yield_loss_range(wheat_powdery_mildew,   5, 20).
yield_loss_range(cotton_leaf_curl,      30, 90).
yield_loss_range(cotton_boll_rot,       10, 40).
yield_loss_range(cotton_fusarium_wilt,  20, 60).
yield_loss_range(cotton_alternaria,      5, 20).
yield_loss_range(rice_bacterial_blight, 10, 50).
yield_loss_range(rice_sheath_blight,    10, 40).
yield_loss_range(rice_brown_spot,        5, 30).
yield_loss_range(rice_tungro,           20, 70).
yield_loss_range(maize_smut,            10, 30).
yield_loss_range(maize_downy_mildew,    10, 60).
yield_loss_range(maize_stalk_rot,       15, 50).
yield_loss_range(maize_leaf_blight,     10, 35).
yield_loss_range(sugarcane_red_rot,     20, 80).
yield_loss_range(sugarcane_smut,        20, 60).
yield_loss_range(sugarcane_ratoon_stunt,10, 40).
yield_loss_range(potato_late_blight,    20, 80).
yield_loss_range(potato_early_blight,    5, 30).
yield_loss_range(potato_blackleg,       10, 50).
yield_loss_range(tomato_early_blight,    5, 25).
yield_loss_range(tomato_fusarium_wilt,  10, 60).
yield_loss_range(tomato_bacterial_spot,  5, 30).
yield_loss_range(mango_anthracnose,     10, 60).
yield_loss_range(mango_malformation,    15, 70).
yield_loss_range(citrus_canker,         10, 50).
yield_loss_range(citrus_greening,       30, 90).

% ── Resistance sources / recommended varieties ──────────────────
resistant_variety(rice_blast,            'KSK-133, IRRI-6, Super Basmati').
resistant_variety(wheat_yellow_rust,     'Seher-06, Pakistan-13, Pirsabak-15').
resistant_variety(wheat_brown_rust,      'Lasani-08, Faisalabad-08').
resistant_variety(wheat_loose_smut,      'Inqilab-91, Uqab-2000').
resistant_variety(wheat_powdery_mildew,  'Fareed-2006, Kohsar-95').
resistant_variety(cotton_leaf_curl,      'MNH-886, CIM-573, IUB-222').
resistant_variety(cotton_fusarium_wilt,  'NIBGE-2, FH-142').
resistant_variety(rice_bacterial_blight, 'IR-64, IRRI-9, Shandar').
resistant_variety(rice_sheath_blight,    'IRRI-6, Kisan Basmati').
resistant_variety(rice_tungro,           'TKM-6, IR-36').
resistant_variety(maize_smut,            'Pak Afgoi, DK-919').
resistant_variety(maize_downy_mildew,    'Pioneer-3025, DK-6142').
resistant_variety(sugarcane_red_rot,     'CPF-246, HSF-240, SPF-238').
resistant_variety(sugarcane_smut,        'HSF-240, CP-77/400').
resistant_variety(potato_late_blight,    'Desiree, Cardinal, Kuroda').
resistant_variety(tomato_fusarium_wilt,  'Rio Grande, Roma VF').
resistant_variety(mango_anthracnose,     'Langra (less susceptible)').
resistant_variety(citrus_canker,         'Kinnow (moderate resistance)').

% ── Fungicide/pesticide database ────────────────────────────────
chemical(tricyclazole,    fungicide, 'Beam 75WP',    rice_blast).
chemical(propiconazole,   fungicide, 'Tilt 250EC',   wheat_yellow_rust).
chemical(tebuconazole,    fungicide, 'Folicur 250EW',wheat_brown_rust).
chemical(carboxin,        fungicide, 'Vitavax 200FF', wheat_loose_smut).
chemical(triadimefon,     fungicide, 'Bayleton 25WP', wheat_powdery_mildew).
chemical(imidacloprid,    insecticide,'Confidor 200SL',cotton_leaf_curl).
chemical(spiromesifen,    insecticide,'Oberon 240SC',  cotton_leaf_curl).
chemical(copper_hydroxide,bactericide,'Kocide 77WP',  cotton_boll_rot).
chemical(carbendazim,     fungicide, 'Derosal 50WP', sugarcane_red_rot).
chemical(mancozeb,        fungicide, 'Dithane M-45', rice_brown_spot).
chemical(metalaxyl,       fungicide, 'Ridomil Gold', potato_late_blight).
chemical(chlorothalonil,  fungicide, 'Daconil 720SC',tomato_early_blight).
chemical(streptomycin,    bactericide,'Agrimycin 17', rice_bacterial_blight).
chemical(iprodione,       fungicide, 'Rovral 50WP',  rice_brown_spot).
chemical(hexaconazole,    fungicide, 'Anvil 5SC',    rice_sheath_blight).
chemical(validamycin,     fungicide, 'Validacin 3L', rice_sheath_blight).
chemical(copper_oxychloride, bactericide,'Cupravit OB21', citrus_canker).
chemical(thiram,          fungicide, 'Thiram 80WP',  maize_smut).

% ================================================================
%  MODULE 2 — DISEASE RULES (Rule-Based Expert System)
%  Format:
%    disease_rule(DiseaseName, CropAtom, Certainty, TreatmentList)
%      :- condition1, condition2, ...
%  Certainty: 0–100 (base certainty factor before adjustment)
% ================================================================

% ─────────────────────── WHEAT DISEASES ────────────────────────

disease_rule(wheat_yellow_rust, wheat, 90,
    ['Apply propiconazole (Tilt 250EC) 0.5 ml/litre',
     'Spray tebuconazole at flag-leaf stage',
     'Use rust-resistant varieties: Seher-06, Pakistan-13',
     'Remove and burn infected plant material',
     'Monitor fields weekly during March-May',
     'Apply a second spray if infection persists after 14 days']) :-
    crop(wheat),
    symptom(yellow_pustules),
    weather(cool_wet).

disease_rule(wheat_yellow_rust, wheat, 75,
    ['Apply propiconazole (Tilt 250EC) 0.5 ml/litre',
     'Use rust-resistant varieties: Seher-06',
     'Remove infected tillers immediately']) :-
    crop(wheat),
    symptom(yellow_pustules),
    weather(moderate).

disease_rule(wheat_brown_rust, wheat, 88,
    ['Apply tebuconazole (Folicur 250EW) at first sign',
     'Spray propiconazole as preventive',
     'Use brown-rust resistant varieties: Lasani-08',
     'Avoid dense planting to reduce humidity',
     'Apply fertilizer on schedule — N excess worsens rust']) :-
    crop(wheat),
    symptom(orange_pustules),
    weather(warm_humid).

disease_rule(wheat_loose_smut, wheat, 92,
    ['Treat seed with carboxin (Vitavax 200FF) before sowing',
     'Hot water treatment: 52 deg C for 10 minutes',
     'Use certified smut-free seed only',
     'Avoid seed from infected fields',
     'Apply systemic fungicide seed dressing',
     'Plant resistant varieties: Inqilab-91, Uqab-2000']) :-
    crop(wheat),
    symptom(black_smutted_ears),
    weather(moderate).

disease_rule(wheat_loose_smut, wheat, 80,
    ['Treat seed with carboxin before sowing',
     'Destroy infected plants before spores mature']) :-
    crop(wheat),
    symptom(black_smutted_ears),
    weather(cool_wet).

disease_rule(wheat_powdery_mildew, wheat, 85,
    ['Apply triadimefon (Bayleton 25WP) at early infection',
     'Use sulphur-based dust at 25 kg/hectare',
     'Improve air circulation with correct row spacing',
     'Avoid overhead irrigation',
     'Apply potassium silicate to toughen leaf surface',
     'Plant resistant varieties: Fareed-2006']) :-
    crop(wheat),
    symptom(white_powdery_coating),
    weather(cool_moist).

disease_rule(wheat_powdery_mildew, wheat, 70,
    ['Apply sulphur-based fungicide',
     'Avoid excess nitrogen fertiliser',
     'Improve field air circulation']) :-
    crop(wheat),
    symptom(white_powdery_coating),
    weather(moderate).

% ─────────────────────── RICE DISEASES ─────────────────────────

disease_rule(rice_blast, rice, 92,
    ['Apply tricyclazole (Beam 75WP) 0.6 g/litre water',
     'Drain field for 3-4 days after spraying',
     'Use blast-resistant varieties: KSK-133, Super Basmati',
     'Avoid excess nitrogen fertiliser',
     'Spray at booting stage as preventive measure',
     'Repeat spray if humidity remains above 80% for 3 days',
     'Burn crop debris after harvest']) :-
    crop(rice),
    symptom(diamond_shaped_lesions),
    weather(warm_humid).

disease_rule(rice_blast, rice, 80,
    ['Apply tricyclazole immediately',
     'Drain field and reduce nitrogen',
     'Use blast-resistant varieties']) :-
    crop(rice),
    symptom(yellow_leaf_spots),
    weather(warm_humid).

disease_rule(rice_bacterial_blight, rice, 90,
    ['Drain field and reduce nitrogen fertiliser',
     'Apply streptomycin sulphate (Agrimycin 17)',
     'Use copper oxychloride bactericide',
     'Use certified disease-free seed',
     'Plant resistant varieties: IR-64, IRRI-9, Shandar',
     'Avoid mechanical damage during transplanting',
     'Do not use water from infected fields for irrigation']) :-
    crop(rice),
    symptom(water_soaked_leaf_margins),
    weather(warm_humid).

disease_rule(rice_bacterial_blight, rice, 75,
    ['Apply copper oxychloride spray',
     'Drain field immediately',
     'Use disease-free seed for next season']) :-
    crop(rice),
    symptom(yellowing_wilting),
    weather(warm_humid).

disease_rule(rice_sheath_blight, rice, 87,
    ['Apply hexaconazole (Anvil 5SC) at 1 ml/litre',
     'Apply validamycin (Validacin 3L) at tillering stage',
     'Reduce plant density to improve air circulation',
     'Drain field periodically',
     'Use silicon fertiliser to strengthen cell walls',
     'Avoid late nitrogen application']) :-
    crop(rice),
    symptom(oval_lesions_on_sheath),
    weather(warm_humid).

disease_rule(rice_brown_spot, rice, 82,
    ['Apply mancozeb (Dithane M-45) 2.5 g/litre',
     'Treat seed with iprodione (Rovral 50WP)',
     'Use balanced NPK fertilisation',
     'Avoid water stress during grain filling',
     'Apply silica fertiliser as preventive']) :-
    crop(rice),
    symptom(brown_circular_spots),
    weather(moderate).

disease_rule(rice_brown_spot, rice, 70,
    ['Apply mancozeb spray',
     'Correct soil nutrition deficiency',
     'Use disease-free seed']) :-
    crop(rice),
    symptom(brown_circular_spots),
    weather(cool_dry).

disease_rule(rice_tungro, rice, 88,
    ['Control leafhopper vector with imidacloprid',
     'Remove and destroy infected plants immediately',
     'Plant tungro-resistant varieties: TKM-6, IR-36',
     'Avoid planting near infected fields',
     'Use reflective mulch to deter leafhoppers',
     'Apply systemic insecticide at transplanting']) :-
    crop(rice),
    symptom(yellow_orange_discolouration),
    weather(warm_humid).

% ─────────────────────── COTTON DISEASES ────────────────────────

disease_rule(cotton_leaf_curl, cotton, 95,
    ['Apply imidacloprid (Confidor 200SL) 0.5 ml/litre for whitefly',
     'Apply spiromesifen (Oberon 240SC) for nymph control',
     'Remove and destroy infected plants immediately',
     'Plant CLCuV-tolerant varieties: MNH-886, IUB-222',
     'Use yellow sticky traps to monitor whitefly population',
     'Avoid planting adjacent to infected fields',
     'Apply neem-based spray as preventive',
     'Rogue infected plants within 3 weeks of appearance']) :-
    crop(cotton),
    symptom(leaf_curling_upward),
    weather(hot_dry).

disease_rule(cotton_leaf_curl, cotton, 85,
    ['Apply imidacloprid for whitefly control',
     'Remove infected plants',
     'Monitor with yellow sticky traps']) :-
    crop(cotton),
    symptom(leaf_curling_upward),
    weather(warm_humid).

disease_rule(cotton_leaf_curl, cotton, 80,
    ['Control whitefly vector urgently',
     'Use tolerant varieties next season',
     'Destroy infected crop if >50% affected']) :-
    crop(cotton),
    symptom(mosaic_pattern),
    symptom(leaf_curling_upward),
    weather(hot_dry).

disease_rule(cotton_boll_rot, cotton, 83,
    ['Spray copper hydroxide (Kocide 77WP) at boll formation',
     'Improve air circulation with correct plant spacing',
     'Avoid excessive irrigation during boll opening',
     'Remove and destroy diseased bolls immediately',
     'Apply preventive spray before monsoon onset',
     'Drain fields after heavy rainfall']) :-
    crop(cotton),
    symptom(rotting_bolls),
    weather(warm_humid).

disease_rule(cotton_fusarium_wilt, cotton, 86,
    ['Use wilt-resistant varieties: NIBGE-2, FH-142',
     'Treat seed with thiram + carbendazim (1:1) mixture',
     'Improve soil drainage before planting',
     'Avoid excessive irrigation',
     'Practice 3-year crop rotation with non-host crops',
     'Solarise soil before planting in severely infected fields']) :-
    crop(cotton),
    symptom(sudden_wilting),
    soil(waterlogged).

disease_rule(cotton_fusarium_wilt, cotton, 75,
    ['Treat seed with fungicide mixture',
     'Improve field drainage',
     'Practice crop rotation']) :-
    crop(cotton),
    symptom(sudden_wilting),
    soil(normal_moisture).

disease_rule(cotton_alternaria, cotton, 78,
    ['Apply mancozeb + copper mixture spray',
     'Use certified disease-free seed',
     'Apply potassium fertiliser to strengthen plant immunity',
     'Avoid overhead irrigation',
     'Remove infected leaves and burn them']) :-
    crop(cotton),
    symptom(dark_brown_spots_on_leaves),
    weather(warm_humid).

% ─────────────────────── MAIZE DISEASES ─────────────────────────

disease_rule(maize_smut, maize, 84,
    ['Remove and burn infected galls before spores mature',
     'Treat seed with thiram (Thiram 80WP) before planting',
     'Avoid excess nitrogen fertilisation',
     'Use smut-tolerant hybrids: Pak Afgoi, DK-919',
     'Practice crop rotation with legumes or vegetables',
     'Do not incorporate infected plant debris into soil']) :-
    crop(maize),
    symptom(large_black_galls),
    weather(hot_dry).

disease_rule(maize_downy_mildew, maize, 88,
    ['Treat seed with metalaxyl (Apron 35SD) before planting',
     'Use downy-mildew-resistant hybrids: Pioneer-3025',
     'Practice 2-year crop rotation with non-host crops',
     'Apply fosetyl-aluminium foliarly at early infection',
     'Improve field drainage to reduce humidity',
     'Avoid planting during cool-wet spells']) :-
    crop(maize),
    symptom(chlorotic_stripes_on_leaves),
    weather(cool_wet).

disease_rule(maize_stalk_rot, maize, 80,
    ['Harvest early before stalk rot spreads',
     'Improve soil drainage',
     'Balanced potassium application to reduce susceptibility',
     'Use resistant hybrids',
     'Avoid water stress and then over-irrigation cycles',
     'Practice crop rotation']) :-
    crop(maize),
    symptom(stalk_softening_collapse),
    weather(warm_humid).

disease_rule(maize_leaf_blight, maize, 79,
    ['Apply mancozeb or propiconazole spray',
     'Improve air circulation with correct spacing',
     'Use resistant hybrids',
     'Remove severely infected lower leaves']) :-
    crop(maize),
    symptom(long_tan_lesions_on_leaves),
    weather(warm_humid).

% ─────────────────────── SUGARCANE DISEASES ─────────────────────

disease_rule(sugarcane_red_rot, sugarcane, 90,
    ['Use disease-free certified seed cane from SRISA',
     'Treat setts with carbendazim (Derosal 50WP) 2 g/litre',
     'Destroy infected canes immediately by burning',
     'Plant resistant varieties: CPF-246, HSF-240, SPF-238',
     'Improve field drainage before planting',
     'Avoid mechanical injury during planting',
     'Do not ratoon an infected crop']) :-
    crop(sugarcane),
    symptom(red_internal_discolouration),
    weather(warm_humid).

disease_rule(sugarcane_smut, sugarcane, 87,
    ['Remove and destroy whip (smut sorus) immediately',
     'Use certified smut-free seed cane',
     'Plant resistant varieties: HSF-240, CP-77/400',
     'Hot water treat setts at 50 deg C for 2 hours',
     'Avoid ratooning infected crops']) :-
    crop(sugarcane),
    symptom(black_whip_from_growing_point),
    weather(warm_humid).

disease_rule(sugarcane_ratoon_stunt, sugarcane, 83,
    ['Use certified disease-free seed cane',
     'Hot water treatment of setts: 50 deg C for 2 hours',
     'Sterilise cutting tools between stools with 70% alcohol',
     'Rogue stunted plants promptly',
     'Avoid ratooning more than 3 times']) :-
    crop(sugarcane),
    symptom(stunted_ratoon_growth),
    weather(moderate).

% ─────────────────────── POTATO DISEASES ────────────────────────

disease_rule(potato_late_blight, potato, 95,
    ['Apply metalaxyl (Ridomil Gold) 2.5 g/litre immediately',
     'Apply chlorothalonil as protective spray',
     'Remove and destroy infected haulms',
     'Harvest tubers promptly once haulms die',
     'Use certified blight-free seed tubers',
     'Plant resistant varieties: Desiree, Cardinal',
     'Avoid overhead irrigation in evenings',
     'Apply spray every 7 days during wet weather']) :-
    crop(potato),
    symptom(water_soaked_dark_lesions),
    weather(cool_wet).

disease_rule(potato_late_blight, potato, 85,
    ['Apply metalaxyl immediately',
     'Remove infected foliage',
     'Harvest early if infection is severe']) :-
    crop(potato),
    symptom(water_soaked_dark_lesions),
    weather(cool_moist).

disease_rule(potato_early_blight, potato, 80,
    ['Apply mancozeb (Dithane M-45) 2.5 g/litre',
     'Apply chlorothalonil as alternative',
     'Use balanced fertilisation — stressed plants more susceptible',
     'Avoid overhead irrigation',
     'Remove infected lower leaves']) :-
    crop(potato),
    symptom(dark_concentric_ring_spots),
    weather(warm_humid).

disease_rule(potato_blackleg, potato, 82,
    ['Remove and destroy infected plants immediately',
     'Use certified blackleg-free seed tubers',
     'Improve soil drainage',
     'Avoid injuring tubers during planting',
     'Apply copper bactericide to cuts before planting']) :-
    crop(potato),
    symptom(black_rotting_at_stem_base),
    soil(waterlogged).

% ─────────────────────── TOMATO DISEASES ────────────────────────

disease_rule(tomato_early_blight, tomato, 82,
    ['Apply chlorothalonil (Daconil 720SC) 1.5 ml/litre',
     'Apply mancozeb as alternative',
     'Remove infected lower leaves immediately',
     'Stake plants to improve air circulation',
     'Mulch to prevent soil splash',
     'Avoid overhead watering']) :-
    crop(tomato),
    symptom(dark_concentric_ring_spots),
    weather(warm_humid).

disease_rule(tomato_fusarium_wilt, tomato, 88,
    ['Use wilt-resistant varieties: Rio Grande, Roma VF',
     'Solarise soil for 4-6 weeks before planting',
     'Practice 4-year crop rotation',
     'Improve soil drainage',
     'Apply trichoderma-based biocontrol agent',
     'Avoid wounding roots during cultivation']) :-
    crop(tomato),
    symptom(sudden_wilting),
    soil(normal_moisture).

disease_rule(tomato_bacterial_spot, tomato, 78,
    ['Apply copper-based bactericide spray',
     'Avoid working in field when plants are wet',
     'Remove infected leaves and burn',
     'Use disease-free transplants only',
     'Rotate crop with non-solanaceous crops']) :-
    crop(tomato),
    symptom(water_soaked_leaf_spots),
    weather(warm_humid).

% ─────────────────────── MANGO DISEASES ─────────────────────────

disease_rule(mango_anthracnose, mango, 85,
    ['Apply copper oxychloride 3 g/litre before flowering',
     'Apply mancozeb or carbendazim after fruit set',
     'Prune to improve air circulation',
     'Avoid overhead irrigation',
     'Collect and destroy fallen infected fruit',
     'Post-harvest hot water treatment at 52 deg C for 5 min']) :-
    crop(mango),
    symptom(dark_sunken_spots_on_fruit),
    weather(warm_humid).

disease_rule(mango_malformation, mango, 80,
    ['Prune and burn malformed vegetative/floral panicles',
     'Apply carbendazim (0.1%) at bud burst',
     'Use Aspergillus niger biocontrol inoculant',
     'Sterilise pruning tools with 70% alcohol',
     'Avoid excessive nitrogen — predisposes to malformation']) :-
    crop(mango),
    symptom(bunchy_top_malformed_panicles),
    weather(cool_moist).

% ─────────────────────── CITRUS DISEASES ────────────────────────

disease_rule(citrus_canker, citrus, 88,
    ['Apply copper oxychloride (Cupravit OB21) 3 g/litre',
     'Prune and burn infected twigs and leaves',
     'Disinfect pruning tools between trees',
     'Windbreaks reduce wound entry sites',
     'Quarantine infected orchards strictly',
     'Plant certified canker-free budwood']) :-
    crop(citrus),
    symptom(raised_corky_lesions_on_leaves),
    weather(warm_humid).

disease_rule(citrus_greening, citrus, 90,
    ['Control psyllid vector with imidacloprid',
     'Remove and destroy infected trees — no cure exists',
     'Use certified greening-free budwood',
     'Quarantine nurseries strictly',
     'Apply reflective mulch to deter psyllids',
     'Plant windbreaks to reduce psyllid migration']) :-
    crop(citrus),
    symptom(blotchy_yellow_mottling),
    weather(warm_humid).

disease_rule(citrus_greening, citrus, 85,
    ['Destroy infected trees immediately',
     'Control psyllid with systemic insecticide',
     'Quarantine orchard',
     'Test new planting material before use']) :-
    crop(citrus),
    symptom(asymmetric_yellowing),
    weather(moderate).

% ================================================================
%  MODULE 3 — FORWARD CHAINING
%  derive_all/1 fires rules iteratively from asserted facts,
%  accumulating derived conclusions until no new ones emerge.
% ================================================================

% Entry point: call derive_all([]) to start with empty derived set
derive_all(Derived) :-
    findall(D, derive_conclusion(D), NewFacts),
    list_to_set(NewFacts, Set),
    subtract(Set, Derived, Fresh),
    (   Fresh = []
    ->  Derived = Derived          % fixed point reached
    ;   append(Derived, Fresh, Updated),
        assert_derived(Fresh),
        derive_all(Updated)
    ).

assert_derived([]).
assert_derived([H|T]) :-
    (derived(H) -> true ; assert(derived(H))),
    assert_derived(T).

% Forward-chaining inference rules:
% "Given observed facts, what can we conclude?"

derive_conclusion(high_fungal_risk) :-
    weather(warm_humid),
    (crop(rice) ; crop(wheat) ; crop(potato) ; crop(tomato)).

derive_conclusion(high_fungal_risk) :-
    weather(cool_wet),
    (crop(wheat) ; crop(potato) ; crop(maize)).

derive_conclusion(vector_borne_risk) :-
    weather(hot_dry),
    crop(cotton).

derive_conclusion(vector_borne_risk) :-
    weather(warm_humid),
    crop(rice).

derive_conclusion(soil_borne_risk) :-
    soil(waterlogged),
    (crop(cotton) ; crop(potato) ; crop(tomato)).

derive_conclusion(drought_stress) :-
    weather(hot_dry),
    soil(dry_cracked).

derive_conclusion(blast_favorable) :-
    crop(rice),
    weather(warm_humid).

derive_conclusion(rust_favorable) :-
    crop(wheat),
    (weather(cool_wet) ; weather(warm_humid)).

derive_conclusion(whitefly_alert) :-
    crop(cotton),
    weather(hot_dry).

derive_conclusion(late_blight_alert) :-
    crop(potato),
    weather(cool_wet).

derive_conclusion(blight_alert) :-
    crop(rice),
    symptom(water_soaked_leaf_margins).

derive_conclusion(seed_treatment_needed) :-
    (crop(wheat) ; crop(rice) ; crop(maize)),
    (symptom(black_smutted_ears) ; symptom(large_black_galls) ;
     symptom(chlorotic_stripes_on_leaves)).

derive_conclusion(immediate_action_needed) :-
    symptom(sudden_wilting),
    (crop(cotton) ; crop(tomato)).

derive_conclusion(vector_control_urgent) :-
    (symptom(leaf_curling_upward) ; symptom(mosaic_pattern)),
    crop(cotton).

derive_conclusion(field_drainage_needed) :-
    soil(waterlogged),
    (crop(cotton) ; crop(potato) ; crop(sugarcane)).

% ================================================================
%  MODULE 4 — BACKWARD CHAINING (Prolog's native mechanism)
%  diagnose/3 attempts to prove a disease hypothesis given
%  currently asserted facts.
%  diagnose(Disease, Type, Treatments)
% ================================================================

diagnose(Disease, Type, Treatments) :-
    disease_rule(Disease, _Crop, _CF, Treatments),
    disease_class(Disease, Type).

% Try all possible diagnoses
diagnose_all(Results) :-
    findall(d(Disease, Type, CF, Treatments),
            diagnose_with_cf(Disease, Type, CF, Treatments),
            Results).

% ================================================================
%  MODULE 5 — UNIFICATION (explicit demonstration predicates)
%  These predicates explicitly show unification steps
%  for educational / trace purposes.
% ================================================================

% Unify a symptom query against known symptom-disease associations
unify_symptom(QuerySymptom, Disease) :-
    disease_rule(Disease, _, _, _),
    % The call below triggers Prolog unification:
    % QuerySymptom is unified with the first argument of symptom/1
    % in the rule body of disease_rule. If the dynamic fact
    % symptom(QuerySymptom) exists, unification succeeds.
    call(symptom(QuerySymptom)).

% Unify crop and symptom together
unify_diagnosis(CropIn, SymptomIn, Disease) :-
    % Pattern match (unify) CropIn with crop fact
    crop(CropIn),
    % Pattern match (unify) SymptomIn with symptom fact
    symptom(SymptomIn),
    % Find a rule where both appear
    disease_rule(Disease, CropIn, _, _).

% Term-level unification demonstration
demonstrate_unification(Term1, Term2) :-
    (Term1 = Term2
    -> write('Unification SUCCEEDED'), nl,
       write('Binding: '), write(Term1), nl
    ;  write('Unification FAILED'), nl
    ).

% ================================================================
%  MODULE 6 — CERTAINTY FACTORS
%  cf_diagnose/4 returns adjusted certainty based on
%  number of matching symptoms, weather match, soil match.
% ================================================================

diagnose_with_cf(Disease, Type, FinalCF, Treatments) :-
    disease_rule(Disease, CropAtom, BaseCF, Treatments),
    crop(CropAtom),
    disease_class(Disease, Type),
    compute_cf(Disease, BaseCF, FinalCF).

compute_cf(Disease, BaseCF, FinalCF) :-
    % Bonus points for weather match
    weather_bonus(Disease, WBonus),
    % Bonus points for soil match
    soil_bonus(Disease, SBonus),
    % Bonus for extra confirming symptoms
    extra_symptom_bonus(Disease, EBonus),
    Raw is BaseCF + WBonus + SBonus + EBonus,
    FinalCF is min(99, Raw).

% Weather-specific bonuses
weather_bonus(D, 5) :-
    disease_class(D, fungal), weather(warm_humid), !.
weather_bonus(D, 5) :-
    disease_class(D, bacterial), weather(warm_humid), !.
weather_bonus(D, 3) :-
    disease_class(D, fungal), weather(cool_wet), !.
weather_bonus(D, 4) :-
    disease_class(D, viral), weather(hot_dry), !.
weather_bonus(_, 0).

% Soil-specific bonuses
soil_bonus(D, 4) :-
    spread(D, soil_borne), soil(waterlogged), !.
soil_bonus(D, 3) :-
    spread(D, soil_borne), soil(dry_cracked), !.
soil_bonus(_, 0).

% Extra symptom bonuses (multiple confirming symptoms)
extra_symptom_bonus(_, Bonus) :-
    findall(1, symptom(_), Syms),
    length(Syms, N),
    Bonus is min(10, (N - 1) * 3).

% ================================================================
%  MODULE 7 — HEURISTIC SEARCH (best-treatment selection)
%  best_treatment/4 ranks treatments by:
%    Cost (1=cheap, 5=expensive)  — lower is better
%    Effectiveness (1–10)         — higher is better
%    Recovery days (lower better)
%  Heuristic score = Effectiveness * 2 - Cost - RecoveryDays/10
% ================================================================

% treatment_score(Disease, TreatmentIndex, Cost, Effectiveness, RecoveryDays)
treatment_score(rice_blast,           1, 2, 9, 7).
treatment_score(rice_blast,           2, 1, 6, 3).   % drain field — free
treatment_score(rice_blast,           3, 3, 8,21).   % resistant variety
treatment_score(wheat_yellow_rust,    1, 2, 9, 7).
treatment_score(wheat_yellow_rust,    2, 2, 8, 7).
treatment_score(wheat_yellow_rust,    3, 3, 9,30).
treatment_score(cotton_leaf_curl,     1, 3, 8,14).
treatment_score(cotton_leaf_curl,     2, 3, 7,14).
treatment_score(cotton_leaf_curl,     3, 1, 9,60).   % resistant variety
treatment_score(potato_late_blight,   1, 3, 9, 5).
treatment_score(potato_late_blight,   2, 2, 7, 7).
treatment_score(sugarcane_red_rot,    1, 1, 8,90).
treatment_score(sugarcane_red_rot,    2, 2, 9, 7).
treatment_score(rice_bacterial_blight,1, 1, 7, 7).
treatment_score(rice_bacterial_blight,2, 2, 8,10).

heuristic_score(Cost, Eff, Days, Score) :-
    Score is (Eff * 2) - Cost - (Days / 10).

best_treatment(Disease, BestTreatmentIdx, BestScore, Explanation) :-
    findall(s(Score, Idx),
           (treatment_score(Disease, Idx, Cost, Eff, Days),
            heuristic_score(Cost, Eff, Days, Score)),
           Scores),
    (   Scores = []
    ->  BestTreatmentIdx = 1, BestScore = 0,
        Explanation = 'No heuristic data — apply recommended treatment 1'
    ;   sort(0, @>=, Scores, [s(BestScore,BestTreatmentIdx)|_]),
        format(atom(Explanation),
               'Treatment ~w selected: score=~2f (higher=better)',
               [BestTreatmentIdx, BestScore])
    ).

% ================================================================
%  MODULE 8 — SEVERITY COMPUTATION (called by Python regression)
%  These predicates are used by Python to get severity estimates.
%  Python computes regression; Prolog validates range clamping.
% ================================================================

severity_clamp(Raw, Clamped) :-
    Clamped is min(max(Raw, 0), 100).

severity_level_label(Loss, Level) :-
    (Loss < 20  -> Level = low    ;
     Loss < 45  -> Level = medium ;
     Loss < 70  -> Level = high   ;
                   Level = critical).

treatment_reduction(Loss, Reduced) :-
    Reduced is Loss * 0.60.   % 40% reduction when treated

% ================================================================
%  MODULE 9 — PREVENTION AND GENERAL ADVICE
% ================================================================

prevention_advice(fungal, [
    'Rotate crops every 2-3 years to break disease cycle',
    'Use certified disease-free seed every season',
    'Apply balanced NPK fertiliser — excess N increases susceptibility',
    'Ensure proper field drainage before planting',
    'Apply preventive fungicide spray at early growth stages',
    'Remove and burn crop debris after harvest',
    'Monitor fields weekly — early detection saves 50% more yield'
]).

prevention_advice(bacterial, [
    'Use certified pathogen-free seed or planting material',
    'Sterilise cutting and grafting tools between plants',
    'Avoid mechanical injury during field operations',
    'Apply copper-based bactericide as preventive spray',
    'Improve field drainage to reduce water splash',
    'Avoid working in fields when foliage is wet'
]).

prevention_advice(viral, [
    'Control vector insects (whitefly, leafhopper, psyllid) early',
    'Remove and destroy infected plants immediately',
    'Plant certified virus-free planting material',
    'Use reflective mulch to deter flying vectors',
    'Establish windbreaks to reduce vector migration',
    'Rogue infected plants within 2-3 weeks of detection'
]).

seasonal_advice(kharif, [    % Summer crop (May-Oct)
    'Monitor for blast and bacterial diseases during monsoon',
    'Ensure field drainage channels are clear before monsoon',
    'Apply pre-monsoon fungicide spray to rice and cotton',
    'Scout fields weekly from July to September',
    'Whitefly risk peaks August-September in cotton'
]).

seasonal_advice(rabi, [      % Winter crop (Nov-Apr)
    'Scout wheat for yellow rust from February onward',
    'Apply preventive spray in February if rust reported nearby',
    'Powdery mildew risk increases in cold humid nights',
    'Ensure rust-resistant varieties are planted',
    'Apply second fungicide if infection exceeds 5% leaf area'
]).

% ================================================================
%  MODULE 10 — RESET (called before each new session)
% ================================================================

reset_facts :-
    retractall(crop(_)),
    retractall(symptom(_)),
    retractall(weather(_)),
    retractall(soil(_)),
    retractall(season(_)),
    retractall(field_age(_)),
    retractall(derived(_)).

% ================================================================
%  QUICK TEST — copy-paste into SWI-Prolog console to verify
%
%  ?- consult('agriexpert_kb.pl').
%  ?- assert(crop(rice)).
%  ?- assert(symptom(diamond_shaped_lesions)).
%  ?- assert(weather(warm_humid)).
%  ?- diagnose_with_cf(D, T, CF, Tr).
%  ?- derive_all([]).
%  ?- best_treatment(rice_blast, Idx, Score, Exp).
%  ?- prevention_advice(fungal, Advice).
% ================================================================
