# -*- coding: utf-8 -*-
"""
Modified from Rydberg lab tweezers_phaseAmplitudeAdjustment.py

Created on Aug 1st 2023
"""


import numpy as np
from scipy import optimize


#updated on 10/30/2020, min fn value 6942.8
phase_dict_0 = {72.5: 148.8741023994702,
 73.0: 349.9567883806162,
 73.5: 0.02509845831742826,
 74.0: 192.8963423924625,
 74.5: 292.31699240998523,
 75.0: 171.8614143230989,
 75.5: 75.5840591863581,
 76.0: 146.260112165292,
 76.5: 170.66479746101072,
 77.0: 183.67292210408237}

phase_dict_1 = {73.0: 308.516369458974,
 74.0: 337.4503024987702,
 75.0: 6.348857368342128,
 76.0: 215.2475412144325,
 77.0: 64.18152477474852}

phase_dict_2 = {70.5: 217.99506294161668,
                 73: 117.41471615711487,
                 73.5: 67.03696186208708,
                 74: 69.38947481951816,
                 74.5: 352.53899326059224,
                 75: 168.74446997146896,
                 75.5: 75.31778870904567,
                 76: 179.8468816159664,
                 76.5: 239.9533050529058,
                 77: 43.92962650499781}

#when the monitoring mirror is flipped
phase_dict_3 = {66.5: 204.96053478943685,
 69.0: 324.00666018641465,
 69.5: 162.43763569418314,
 70.0: 307.69377981547814,
 70.5: 172.3939669401085,
 71.0: 144.0027812580337,
 71.5: 24.989186740472913,
 72.0: 68.21046987356183,
 72.5: 156.01140077348964,
 73.0: 139.66313848089507}

phase_dict_4 = {70.9: 96.15066709765703,
                 73.4: 298.55380386861356,
                 73.9: 263.40820647732096,
                 74.4: 207.80543931520026,
                 74.9: 178.9130322515936,
                 75.4: 292.5172894398082,
                 75.9: 329.3903795251156,
                 76.4: 120.213335538677,
                 76.9: 302.32177306450006,
                 77.4: 159.2789777335294}

phase_dict_5 = {70.0 : 68.63765820775433,
 70.5 : 9.079334050219291,
 71.0 : 298.258528976546,
 71.5 : 181.11304503360705,
 72.0 : 230.92860802582027,
 72.5 : 304.813866991744,
 73.0 : 159.07337559625464,
 73.5 : 279.6437514471459,
 74.0 : 223.09335003201068,
 74.5 : 335.539967302278}

phase_dict_6 = {70.5: 337.7793615264221,
 71.0 : 360.0,
 71.5 : 128.6849399659141,
 72.0 : 137.5631022016933,
 72.5 : 34.48508900214535,
 73.0 : 88.99640791009865,
 73.5 : 173.4076719718469,
 74.0 : 228.78389777756905,
 74.5 : 164.68713533351936,
 75.0 : 83.1049674705877,
 75.5 : 28.25928298977137,
 76.0 : 136.9928434861609,
 76.5 : 77.05490905455129,
 77.0 : 0.0,
 77.5 : 244.79718845610202,
 78.0 : 360.0,
 78.5 : 185.25665288853392,
 79.0 : 10.141673660930334,
 79.5 : 200.50519083206618}

phase_dict_7 = {65.0 : 13.23135655867526,
 65.5 : 268.191256815426,
 66.0: 141.13653382116155,
 66.5 : 281.49295757503023,
 67.0 : 167.40316746762514,
 67.5 : 342.37685051488336,
 68.0 : 277.10184569979987,
 68.5 : 253.35030549318324,
 69.0 : 157.72678689623217,
 69.5 : 220.67627010702935,
 70.0 : 202.0743679350961,
 70.5 : 225.9601354236202,
 71.0 : 2.140605681691938,
 71.5 : 330.0819802282758,
 72.0 : 357.4325400503701,
 72.5 : 127.56012307499199,
 73.0 : 275.79274239529485,
 73.5 : 0.0,
 74.0 : 145.90024525822867,
 74.5 : 195.90746863720298}

phase_dict_8 = {70.0: 308.09917910587654,
 70.5: 0.031335842237412925,
 71.0: 134.2526812098492,
 71.5: 167.01268158107905,
 72.0: 92.51354286958393,
 72.5: 139.27802771922535,
 73.0: 237.74815782077906,
 73.5: 247.35473734394404,
 74.0: 213.78129067024105,
 74.5: 121.45981854930734,
 75.0: 136.3046433048694,
 75.5: 241.4003899989861,
 76.0: 133.8099566427223,
 76.5: 66.94217913743326,
 77.0: 349.41585896007405,
 77.5: 167.96243107365248,
 78.0: 0.6630629165077658,
 78.5: 231.76959814972122,
 79.0: 13.02065645764557,
 79.5: 190.03101519343096}

phase_dict_9 = {70.0: 204.1887889341771,
 71.0: 100.25091561360212,
 72.0: 186.64048650578903,
 73.0: 90.86140263822887,
 74.0: 88.41171785434582,
 75.0: 305.1963284427483,
 76.0: 138.9364319498382,
 77.0: 165.27647151157936,
 78.0: 238.12441472405854,
 79.0: 321.41512201713687}

phase_dict_10 = {65.5: 9.851732407548301, # Optimized with 500 tries
 66.5: 343.18666858798355,
 67.5: 305.5914746674589,
 68.5: 221.56172252128061,
 69.5: 304.8513085322173,
 70.5: 51.5331807130095,
 71.5: 298.97719764140703,
 72.5: 92.65785833385357,
 73.5: 68.95193648337978,
 74.5: 214.89925551924551}

phase_dict_10b = {65.0: 9.851732407548301, # Optimized with 0 tries
 66.0: 343.18666858798355,
 67.0: 305.5914746674589,
 68.0: 221.56172252128061,
 69.0: 304.8513085322173,
 70.0: 51.5331807130095,
 71.0: 298.97719764140703,
 72.0: 92.65785833385357,
 73.0: 68.95193648337978,
 74.0: 214.89925551924551}

phase_dict_11 = {68.0: 335.9131455461273,
 69.0: 343.8280256662928,
 70.0: 3.3494462283552635,
 71.0: 69.19715503357071,
 72.0: 327.75605375091754,
 73.0: 202.54904500170423,
 74.0: 296.74637758816806,
 75.0: 124.67427532008706,
 76.0: 129.859882450383,
 77.0: 325.6517033522079}

# phase_dict_12 = {67.5: 335,
#  68.0: 343,
#  68.5: 3.3,
#  69.0: 69,
#  69.5: 330,
#  70.0: 202,
#  70.5: 296,
#  71.0: 124,
#  71.5: 130,
#  72.0: 325}

phase_dict_12 = {67.5: 193.91354712815766,
 68.0: 344.52416975642257,
 68.5: 269.7718946173071,
 69.0: 88.30987259079234,
 69.5: 310.5789201409034,
 70.0: 10.295644566783363,
 70.5: 123.28257749448915,
 71.0: 73.6540131959177,
 71.5: 67.91144074183833,
 72.0: 315.08105821379644,
 72.5: 337.32208212243967}

# phase_dict_13 = {67.5: 45.80853678046396,
#  68.0: 85.80643803783421,
#  68.5: 316.23330004969444,
#  69.0: 4.286488757011236,
#  69.5: 145.79789098491665,
#  70.0: 146.58629989069382,
#  70.5: 124.3122172466547,
#  71.0: 294.65193440618447,
#  71.5: 151.5080715422639,
#  72.0: 18.682103314858605}

phase_dict_13 = {67.5: 9.851732407548301, # Optimized with 500 tries
 68: 343.18666858798355,
 68.5: 305.5914746674589,
 69: 221.56172252128061,
 69.5: 304.8513085322173,
 70: 51.5331807130095,
 70.5: 298.97719764140703,
 71: 92.65785833385357,
 71.5: 68.95193648337978,
 72: 214.89925551924551}

phase_dict_14 = {61.5: 347.772406838545, # Optimized wiht 500 tries
 62.5: 146.40187800473691,
 63.5: 135.76385256386695,
 64.5: 302.371307010858,
 65.5: 202.6213806233875,
 66.5: 322.4159790194808,
 67.5: 58.40758050175796,
 68.5: 347.2700855353718,
 69.5: 322.4998702957265,
 70.5: 308.88788240283225}

phase_dict_15 = {69.5: 256.78189669782125,# Optimized wiht 500 tries
 70.5: 121.73489201468901,
 71.5: 336.1210330927816,
 72.5: 143.91389116249562,
 73.5: 119.09019913287545,
 74.5: 117.53448481352943,
 75.5: 256.62181466791134,
 76.5: 302.3932556415688,
 77.5: 170.35086339093877,
 78.5: 207.95960602068138}

phase_dict_16 = {69.5: 210.87882089911938,
 70.0: 237.73581016766656,
 70.5: 56.12449586403126,
 71.0: 205.40396143547375,
 71.5: 241.48665475091357,
 72.0: 220.9320100408633,
 72.5: 30.255899410169956,
 73.0: 46.39968798546106,
 73.5: 140.55034253146505,
 78.5: 229.22548968109615}

phase_dict_17 = {69.5: 210,
 70.1: 121,
 70.7: 336,
 71.3: 143,
 71.9: 120,
 72.5: 120,
 73.1: 255,
 73.7: 300,
 74.3: 170,
 78.5: 229}

phase_dict_18 = {67.5: 48.21490411058532, 68.0: 305.76394242181664, 68.5: 212.53563360751917, 69.0: 162.84051501258284, 69.5: 224.5187477844103, 70.0: 221.96795145018555, 70.5: 316.19657752504594, 71.0: 125.43357170942826, 71.5: 262.60479529395013, 74.5: 332.59513760331515}
phase_dict_18 = {67.5: 125.40379496978022, 68.0: 0.02755886912439556, 68.5: 225.23759277465993, 69.0: 47.11497598364633, 69.5: 118.10386303777655, 70.0: 252.92938095874715, 70.5: 290.979097589437, 71.0: 254.2600965879005, 71.5: 249.1079551731985, 74.5: 252.75930811415245}
phase_dict_19 = {68.5: 204.42323849431452, 68.75: 204.35931548009586, 69.0: 255.1230612424929, 69.25: 243.69850821793287, 69.5: 109.99595023708181, 69.75: 55.87798215631167, 70.0: 239.81210836557702, 70.25: 0.0, 70.5: 172.59023286114316, 74.5: 106.69102484337473}

phase_dict_20 = {65.5: 156.78663521246568, 67.5: 247.2432523205558, 69.5: 337.7651387482091, 71.5: 248.28922640265625, 73.5: 158.74625228349998}
#optimize 500 times

phase_dict_21 = {61.5: 19.136883340438946, 63.5: 164.35703960380576, 65.5: 140.63014960639953, 67.5: 294.0839726740694, 69.5: 181.0747320914332, 71.5: 287.82656435342057, 73.5: 10.441968507378586, 75.5: 286.12066083042913, 77.5: 248.08109029851826, 79.5: 221.3563514201866}
#optimize 500 times

phase_dict_22 = {69.5: 71.2870079255327, 74.5: 161.28700793362012} #optimize 500 times

phase_dict_23 = {65.5: 167.23371202483855, 67.5: 301.2053489423571, 69.5: 86.52467108351892, 71.5: 278.1473259610753, 73.5: 302.7495044887109, 75.5: 303.32718291519853, 77.5: 163.6563556206256, 79.5: 117.54722635589633, 81.5: 248.60214566598185, 83.5: 210.52176772815787}

phase_dict_24 = {64.5: 289.7668898119288, 65.5: 341.3020615066878, 66.5: 283.85281420738204, 67.5: 309.20022270768186, 68.5: 246.58830863050267, 69.5: 288.75447506615296, 70.5: 15.085900200913825, 71.5: 115.69300846292468, 72.5: 273.671042045809, 73.5: 79.68540623817286, 74.5: 167.8811919594876, 75.5: 115.29610094506995, 76.5: 297.2036006636258, 77.5: 340.29811888067087, 78.5: 270.2348107112738, 79.5: 125.9713180064236, 80.5: 71.55521240819874, 81.5: 250.1584903896888, 82.5: 151.77410293548002, 83.5: 349.0426368086325}
# 20 traps, optimize 500 times

phase_dict_25 = {60.0: 330.1965526271924, 60.5: 36.22311702479663, 61.0: 341.54146856611374, 61.5: 279.3899494844847, 62.0: 288.96003543435666, 62.5: 43.00991928970761, 63.0: 349.4755935791574, 63.5: 171.0427164372359, 64.0: 318.41985785398526, 64.5: 223.64914143764133, 65.0: 261.6136097582406, 65.5: 237.83152183992226, 66.0: 241.67985571374285, 66.5: 217.0533369348169, 67.0: 360.0, 67.5: 138.42452607042904, 68.0: 37.19494010625138, 68.5: 321.2940445353403, 69.0: 339.32796386369387, 69.5: 19.10837369574818, 70.0: 183.1603668603586, 70.5: 201.59842863009945, 71.0: 0.0, 71.5: 232.02536011747716, 72.0: 240.90412975039771, 72.5: 54.08088701376495, 73.0: 0.0, 73.5: 0.0, 74.0: 165.8246840528066, 74.5: 92.30902731676983, 75.0: 12.446361378097421, 75.5: 207.1346473870113, 76.0: 316.2607652857225, 76.5: 8.200898666658437, 77.0: 136.11919966369732, 77.5: 90.48450120357616, 78.0: 169.43460145068585, 78.5: 60.52557915037491, 79.0: 217.68179620135462, 79.5: 0.0, 80.0: 172.60573425709237, 80.5: 202.66608268143213, 81.0: 33.32972066318901, 81.5: 218.5753819548343, 82.0: 360.0, 82.5: 275.24521678072784, 83.0: 148.47962519236577, 83.5: 186.28484534496835, 84.0: 334.53870253225165, 84.5: 355.4045564680201}
# 50 traps start from 60 MHz each step 0.5 MHz, optimize 400 times

phase_dict_26 = {61.0: 328.265550306381, 61.666666666666664: 276.08602608551274, 62.333333333333336: 281.4988321838421, 63.0: 132.92040146183788, 63.666666666666664: 242.42311924952315, 64.33333333333333: 22.185448341169, 65.0: 173.41277177640976, 65.66666666666667: 302.9398133860626, 66.33333333333333: 15.639275814509249, 67.0: 263.4613131730531, 67.66666666666667: 287.63092114735923, 68.33333333333333: 201.4599775721639, 69.0: 206.9774989067338, 69.66666666666667: 204.28978571980963, 70.33333333333333: 0.0, 71.0: 162.00367563842175, 71.66666666666667: 193.37942443475728, 72.33333333333333: 130.20737502287267, 73.0: 360.0, 73.66666666666667: 197.48401056534217, 74.33333333333333: 237.53175951033217, 75.0: 65.75801755104554, 75.66666666666667: 15.506344458762294, 76.33333333333333: 154.7709560707511, 77.0: 278.8237546664119, 77.66666666666666: 278.7442421053036, 78.33333333333333: 324.7886035787779, 79.0: 182.0172668290887, 79.66666666666666: 90.82769684843534, 80.33333333333333: 288.5865512469844, 81.0: 213.96089105200215, 81.66666666666666: 323.30542638856946, 82.33333333333333: 239.520463680507, 83.0: 61.067057421827045, 83.66666666666666: 348.9270187161949, 84.33333333333333: 0.0, 85.0: 50.10345711512885, 85.66666666666666: 63.72425417056895, 86.33333333333333: 168.23108501285782, 87.0: 143.61079840994302}
# 40 traps from 61 to 87, freq = np.linspace(61,87,40), optimize 500 times (~5 um apart)

phase_dictionaries = [phase_dict_26, phase_dict_25, phase_dict_24, phase_dict_23, phase_dict_22, phase_dict_21, phase_dict_17, phase_dict_1, phase_dict_2, phase_dict_5, phase_dict_6, phase_dict_7, phase_dict_8, phase_dict_9, phase_dict_10, phase_dict_10b, phase_dict_11, phase_dict_12, phase_dict_13, phase_dict_14, phase_dict_15, phase_dict_16, phase_dict_18, phase_dict_19, phase_dict_20] #,phase_dict_3, phase_dict_4]

#amp_dict = {
#     60.0: 0.7490241440164751,
#     61.0: 0.7078008757796327,
#     62.0: 0.720090494097406,
#     63.0: 0.7052613529872412,
#     64.0: 0.7341768211012972,
#     65.0: 0.778040002554064,
#     66.0: 0.7483291457719768,
#     67.0: 0.7457056107252535,
#     68.0: 0.7755308786582729,
#     69.0: 0.7797427570457135,
#     70.0: 0.7746141001487719,
#     71.0: 0.7453335433686529,
#     72.0: 0.7684698267210701,
#     73.0: 0.7735203916585116,
#     74.0: 0.7564075965538567,
#     75.0: 0.7751603214857797,
#     76.0: 0.8052946074955515,
#     77.0: 0.8248755924893513,
#     78.0: 0.8241768135925442,
#     79.0: 0.8288365144039795,
#     80.0: 0.8308025085459954,
#     81.0: 0.841187450954061,
#     82.0: 0.8229092461307428,
#     83.0: 0.7872350749332656,
#     84.0: 0.792405656202338,
#     85.0: 0.7736453119731455,
#     86.0: 0.7810413963617777,
#     87.0: 0.773071864543958,
#     88.0: 0.8343711241896894,
#     89.0: 0.8740391709833762,
#     90.0: 1.0
# }

#amplitude calibration obtained on 9/28/2020, bottom tweezer image
# amp_dict = {77.0: 0.9384456094752215,
#  76.5: 1.0,
#  76.0: 0.9642106573139393,
#  75.5: 0.902005876940228,
#  75.0: 0.9533207655180811,
#  74.5: 0.9374593290035979,
#  74.0: 0.8721532224678126,
#  73.5: 0.9553665891831442,
#  73.0: 0.9461067682458977,
#  72.5: 0.8765163817352597}

# #amplitude calibration obtained on 10/1/2020, second iteration, top tweezer image
# amp_dict = {72.5: 0.8648178240683039,
#  73.0: 0.9311228692713878,
#  73.5: 0.9231792149139929,
#  74.0: 0.81835983885432,
#  74.5: 0.8968563523775719,
#  75.0: 0.9978494313123173,
#  75.5: 0.9147065410339843,
#  76.0: 0.990209067250023,
#  76.5: 1.0,
#  77.0: 0.8673003192851122}

#amplitude calibration obtained on 10/5/2020, feeding back on the atom signal
# amp_dict =     {73: 1.0,
#      74: 0.870738280877003,
#      75: 0.7196712898527714,
#      76: 0.40729621274776256,
#      77: 0.6826013626398311}

#amplitude calibration obtained on 10/13/2020, using the first amp_dict amplitudes
#and correcting with shifts in the Ramsey oscillation for different traps
#but without correcting for the quadratic Zeeman shift

# amp_dict = {73: 0.6647634369324736,
#  74: 0.5195276829426677,
#  75: 0.7679110586905217,
#  76: 0.44524906334239417,
#  77: 1.0}

##########################################################################

#amplitude calibration obtained on 10/13/2020, using the first amp_dict amplitudes
#and correcting with shifts in the Ramsey oscillation for different traps
#and with correcting for the quadratic Zeeman shift. Corrections in corr_dict,
#prevampdict taken from amplitude calibration obtained on 9/28/2020 above.

# amp_dict = {}
# prevampdict = {77.0: 0.9384456094752215,
#                76.0: 0.9642106573139393,
#                75.0: 0.9533207655180811,
#                74.0: 0.8721532224678126,
#                73.0: 0.9461067682458977}
# corr_dict = {73.0: 0.9507000082662317,
#             74.0: 0.9278296662277324,
#             75.0: 0.9891134783750355,
#             76.0: 0.8429764730981057,
#             77.0: 1.0}
# for key,val in corr_dict.items():
#     amp_dict[key] = prevampdict[key] * corr_dict[key]
#amp_dict = {73.0: 0.8994637123921126,
#            74.0: 0.8092096333017518,
#            75.0: 0.9429424183887408,
#            76.0: 0.8128068992261108,
#            77.0: 0.9384456094752215}

############################################################################

#amplitude calibration obtained on 10/15/2020, using the amp_dict amplitudes
#from 10/13 aboveand correcting with shifts in the Ramsey oscillation for different traps
#and with correcting for the quadratic Zeeman shift. Corrections in corr_dict,
#prevampdict taken from amplitude calibration obtained on 10/13/2020 above.

#amp_dict = {}
#prevampdict = {73.0: 0.8994637123921126,
#               74.0: 0.8092096333017518,
#               75.0: 0.9429424183887408,
#               76.0: 0.8128068992261108,
#               77.0: 0.9384456094752215}
#corr_dict = {73: 0.9927543347884916,
#             74: 1.0,
#             75: 0.9972117419067451,
#             76: 0.9828483075307984,
#             77: 0.9982896285095302}
# for key,val in corr_dict.items():
#     amp_dict[key] = prevampdict[key] * corr_dict[key]

########## latest for 5 tweezers

# amp_dict = {73.0: 0.8929464994622189,
#             74.0: 0.8092096333017518,
#             75.0: 0.9403132515591951,
#             76.0: 0.7988658852537392,
#             77.0: 0.9368405188594185}

######### from 10/30, first for 10 tweezers

# amp_dict = {72.5: 0.8984294071079664,
#             73.0: 0.9804871945382002,
#             73.5: 0.9124528046727084,
#             74.0: 0.9256678855324856,
#             74.5: 0.9104854880070556,
#             75.0: 0.9770309183103029,
#             75.5: 0.9046601943360224,
#             76.0: 0.9117081230840373,
#             76.5: 1.0,
#             77.0: 0.8725867964816305} ## without dipole trap at 0.5V

# amp_dict = {70.5: 0.9984294071079664,
#             73.0: 0.9804871945382002,
#             73.5: 0.9124528046727084,
#             74.0: 0.9256678855324856,
#             74.5: 0.9104854880070556,
#             75.0: 0.9770309183103029,
#             75.5: 0.9046601943360224,
#             76.0: 0.9117081230840373,
#             76.5: 1.0,
#             77.0: 0.8725867964816305} ## starting point for 2020/11/30- adding reference tweezer

# amp_dict = {70.5: 0.9621881762881059,
#             73.0: 0.9794859489273955,
#             73.5: 0.9931289470581552,
#             74.0: 1.0,
#             74.5: 0.91,
#             75.0: 0.9957298338625653,
#             75.5: 0.941674237217388,
#             76.0: 0.8636530271615595,
#             76.5: 0.9479869963688436,
#             77.0: 0.907507587146916} ## 2020/11/30- moved reference tweezer off to the side  and adjusted by hand

#2020/12/16 iterating on the Ramsey phase precession measurement
# amp_dict ={70.5: 0.8221327382387105, 73: 0.8736680456556243,
#            73.5: 0.9, 74: 0.8680240724816759, 74.5: 0.7840415070574459,
#            75: 0.8694439382219571, 75.5: 0.8375000923643918, 76: 0.761536552106634,
#            76.5: 0.8269544442485267, 77: 0.7798690420801867}

#2021/01/19
# amp_dict ={70.5: 0.8243153673913384, 73: 0.8359662625391976, 73.5: 0.9,
#            74: 0.9037302901510138, 74.5: 0.8645086253250137, 75: 0.9487879837609768,
#            75.5: 0.9587073776760909, 76: 0.8456637820689497, 76.5: 0.9344665084631123, 77: 0.8909996479463121}

#2021/01/26
# amp_dict = {70.5: 0.8120849378774081, 73: 0.837886018528905, 73.5: 0.9, 74: 0.8998996776093738, 74.5: 0.8661395167207809, 75: 0.9541788142071684, 75.5: 0.9540044040994693, 76: 0.8472345897764819, 76.5: 0.9349138124540658, 77: 0.8896467861923107}

#amp_dict = {72.5: 0.8740245725431363,
#            73.0: 0.9319798147113125,
#            73.5: 0.8725674896611272,
#            74.0: 0.8709645372309103,
#            74.5: 0.9362291610420679,
#            75.0: 0.8688828140671012,
#            75.5: 0.860401726665067,
#            76.0: 0.894175948756347,
#            76.5: 1.0,
#            77.0: 0.877299961451302} ## with dipole trap 0.5V corrected

#2021/02/02
# amp_dict = {70.5: 0.7255017074317516, 73: 0.7545270031870808, 73.5: 0.7940020576895607, 74: 0.7980404979821321, 74.5: 0.7864399356036842, 75: 0.8485169735457619, 75.5: 0.8393388174449411, 76: 0.7806876557312925, 76.5: 0.8343629172894009, 77: 0.8121939580719554}

##
#amp_dict={66.5: 0.8031692570679336, 69: 0.8092359803528526, 69.5: 0.9110891351485954, 70: 0.9016506140032463, 70.5: 0.8589451878729785, 71: 0.9856436264095271, 71.5: 0.9371380668383329, 72: 0.9, 72.5: 0.9794183172797554, 73: 0.927970013495529}

#2021/02/04 - after flipping the tweezer dichroic
# amp_dict ={66.5: 0.7777258265349765, 69: 0.7613705417473895, 69.5: 0.8435020572873517, 70: 0.8356431205566629, 70.5: 0.794893447417365, 71: 0.8999999761581421, 71.5: 0.8635215860087, 72: 0.8352870287719764, 72.5: 0.9123594495766852, 73: 0.8667955532441493}

# amp_dict ={66.5: 0.79244599276479, 69: 0.7713438190496055, 69.5: 0.8612830727603346, 70: 0.8479936947864742, 70.5: 0.7990896212211845, 71: 0.9056624174118042, 71.5: 0.8626572246791389, 72: 0.8286970244984349, 72.5: 0.9024158279571418, 73: 0.8521948788948932}
# amp_dict = {66.5: 0.99, 69: 0.99, 69.5: 0.99, 70: 0.99, 70.5: 0.99, 71: 0.99, 71.5: 0.99, 72: 0.99, 72.5: 0.99, 73: 0.99}
# amp_dict = {66.5: 0.7449570934187002, 69: 0.737785323313624, 69.5: 0.8352389043153438, 70: 0.8250493286245195, 70.5: 0.7853468012164789, 71: 0.9056624174118042, 71.5: 0.8669089096534683, 72: 0.8422131773795052, 72.5: 0.9281769871351724, 73: 0.876647670531087}

# 2021/07/16 - flipping dichroic back, adjusting frequencies
# amp_dict = {70.9: 0.95,
#                 73.4: 0.95,
#                  73.9: 0.95,
#                  74.4: 0.95,
#                  74.9: 0.95,
#                  75.4: 0.95,
#                  75.9: 0.95,
#                  76.4: 0.95,
#                  76.9: 0.95,
#                  77.4: 0.95}

# 2021/07/21
# amp_dict = {70.5: 0.8223411530617516, 73: 0.8269202655552207, 73.5: 0.8847122697757797, 74: 0.8832914108277283, 74.5: 0.8590813295700457, 75: 0.949999988079071, 75.5: 0.9394529237602264, 76: 0.8481311767612347, 76.5: 0.9370779332415297, 77: 0.8865309255254072}

# 2021/07/26
# amp_dict = {70.5: 0.8140786543463744, 73: 0.8148069070131605, 73.5: 0.8663113178476358, 74: 0.8798615699037647, 74.5: 0.8537748511996863, 75: 0.949999988079071, 75.5: 0.9366592002852623, 76: 0.8460484756050208, 76.5: 0.9355626257130655, 77: 0.8909773461255351}

# amp_dict = {70.5: 0.8253836631719708, 73: 0.8330432581822667, 73.5: 0.8834584019190871, 74: 0.8944562665458711, 74.5: 0.8641577795632647, 75: 0.9638509154319763, 75.5: 0.9493245058021598, 76: 0.8484909247625173, 76.5: 0.939412682977885, 77: 0.8941029006945775}

# amp_dict = {70.5: 0.8415702835779952, 73: 0.8328749501644385, 73.5: 0.9018743691341906, 74: 0.9091445374326472, 74.5: 0.8675729705805016, 75: 0.9638509154319763, 75.5: 0.9667688536365138, 76: 0.8561162677876119, 76.5: 0.9431011166563539, 77: 0.8968273930824775}

# amp_dict = {70.5: 0.8237404873528171, 73: 0.8361980090898525, 73.5: 0.8986000083728681, 74: 0.9008404742487233, 74.5: 0.8740891125314504, 75: 0.9638509154319763, 75.5: 0.9591862571363643, 76: 0.8609273593068079, 76.5: 0.9562531038731696, 77: 0.9087418562278847}

# Last optimization before spacing out the tweezers:
# amp_dict = {74.5: 0.8616787156769945, 74.0: 0.8999999761581421, 73.5: 0.8713427458498435, 73.0: 0.8268054639505289, 72.5: 0.8397915653136094, 72.0: 0.8385073635493892, 71.5: 0.8455757669909042, 71.0: 0.8706082207541156, 70.5: 0.861416152484862, 70.0: 0.8237673009518282}

# amp_dict = {65.5: 0.9,
#   66.5: 0.9,
#   67.5: 0.9,
#   68.5: 0.9,
#   69.5: 0.9,
#   70.5: 0.9,
#   71.5: 0.9,
#   72.5: 0.9,
#   73.5: 0.9,
#   74.5: 0.9}

#{74.5: 0.8092169572419846, 73.5: 0.8274034478127364, 72.5: 0.8011831065820334, 71.5: 0.8020525299587267, 70.5: 0.8049355185049384, 69.5: 0.7980167469541399, 68.5: 0.8267371344519002, 67.5: 0.8999999761581421, 66.5: 0.8971759815150427, 65.5: 0.8981139191247092}

# amp_dict = {74.5: 0.7971551902817747, 73.5: 0.8410655919917437, 72.5: 0.8171205738550956, 71.5: 0.8089617722056817, 70.5: 0.8150170693656803, 69.5: 0.8070005658109849, 68.5: 0.825391772696407, 67.5: 0.8999999761581421, 66.5: 0.8778591112746891, 65.5: 0.8714596947019252}

# Amp dict up to 2022/12/16:
# amp_dict = {74.5: 0.8080577008906757, 73.5: 0.8298349107639014, 72.5: 0.8069410930166033, 71.5: 0.8090342937894707, 70.5: 0.8133705523182162, 69.5: 0.8088230425026118, 68.5: 0.8268822153901899, 67.5: 0.8999999761581421, 66.5: 0.8841179419514431, 65.5: 0.8762658015004844}

# amp_dict2 = {72.0: 0.8080577008906757, 71.5: 0.8298349107639014, 71: 0.8069410930166033, 70.5: 0.8090342937894707, 70: 0.8133705523182162, 69.5: 0.8088230425026118, 69.0: 0.8268822153901899, 68.5: 0.8999999761581421, 68.0: 0.8841179419514431, 67.5: 0.8762658015004844}
# amp_dict2 ={72.0: 0.8202022705967094, 71.5: 0.8544793681847273, 71.0: 0.835593479413259, 70.5: 0.811505073483143, 70.0: 0.8310466376815591, 69.5: 0.8304354604167855, 69.0: 0.8460475435442483, 68.5: 0.8999999761581421, 68.0: 0.8862823033023431, 67.5: 0.8644990931169207}

# amp_dict ={69.5: 0.7726729368367679, 70.5: 0.7857831260736271, 71.5: 0.8117332250625579, 72.5: 0.7784749983415662, 73.5: 0.7796166537796376, 74.5: 0.808492526067375, 75.5: 0.8161052932040886, 76.5: 0.8482379196856473, 77.5: 0.8888489767892511, 78.5: 0.8999999761581421}
amp_dict ={74.5: 0.8999999761581421, 71.5: 0.8437356661581821, 71.0: 0.8259190509001721, 70.5: 0.8225394347654894, 70.0: 0.8322114641379137, 69.5: 0.8052045365819663, 69.0: 0.8280006338557352, 68.5: 0.8268403223984785, 68.0: 0.8067844354979709, 67.5: 0.8805111827378531}
amp_dict = {68.5: 0.835958169398912, 68.75: 0.8157068239481068, 69: 0.8204461040246094, 69.25: 0.8120349053436806, 69.5: 0.8208203228954154, 69.75: 0.8109753932669737, 70: 0.8113685348416871, 70.25: 0.8034594059958938, 70.5: 0.8206591043618418, 74.5: 0.8999999761581421}

# amp_dict = {68.3: 0.8439969843585513, 68.6: 0.8219167100072354, 68.9: 0.8222064514249084, 69.2: 0.8208641103653082, 69.5: 0.8284446391808772, 69.8: 0.8177256475289721, 70.1: 0.8167145129217449, 70.4: 0.8172797802160124, 70.7: 0.8346228618009522, 74.5: 0.8999999761581421}


# amp_dict = {74.5: 0.8999999761581421, 71.5: 0.8437356661581821, 71.0: 0.8259190509001721, 70.5: 0.8225394347654894, 70.0: 0.8322114641379137, 69.5: 0.8052045365819663, 69.0: 0.8280006338557352, 68.5: 0.8268403223984785, 68.0: 0.8067844354979709, 67.5: 0.8805111827378531}

#Rydberg lab optimized amp dict for their light shift:
#amp_dict2 ={65.5: 0.8815509676933289, 66.5: 0.8775125710656112, 67.5: 0.8842497878651324, 68.5: 0.810310292693479, 69.5: 0.7886452308841309, 70.5: 0.7899756391155348, 71.5: 0.7834920234602227, 72.5: 0.7865276982111034, 73.5: 0.8126865871357669, 74.5: 0.7904933386700217}

#start with the same amp for each freq
amp_dict = {69.5:0.9, 74.5:0.9}

amp_dict2 ={61.5: 0.9, 63.5: 0.9, 65.5: 0.9, 67.5: 0.9, 69.5: 0.9, 71.5: 0.9, 73.5: 0.9, 75.5: 0.9, 77.5: 0.9, 79.5: 0.9}

amp_dict ={65.5: 0.9, 67.5: 0.9, 69.5: 0.9, 71.5: 0.9, 73.5: 0.9}

amp_dict2 ={65.5: 0.9, 66.5: 0.9, 67.5: 0.9, 68.5: 0.9, 69.5: 0.9, 70.5: 0.9, 71.5: 0.9, 72.5: 0.9, 73.5: 0.9, 74.5: 0.9}

amp_dict = {65.5: 0.9, 67.5: 0.9, 69.5: 0.9, 71.5: 0.9, 73.5: 0.9, 75.5: 0.9, 77.5: 0.9, 79.5: 0.9, 81.5: 0.9, 83.5: 0.9}

amp_dict2 = {64.5: 0.9, 65.5: 0.9, 66.5: 0.9, 67.5: 0.9, 68.5: 0.9, 69.5: 0.9, 70.5: 0.9, 71.5: 0.9, 72.5: 0.9, 73.5: 0.9, 74.5: 0.9, 75.5: 0.9, 76.5: 0.9, 77.5: 0.9, 78.5: 0.9, 79.5: 0.9, 80.5: 0.9, 81.5: 0.9, 82.5: 0.9, 83.5: 0.9}
# 20 traps

# amp_dict2 = {60.0: 0.9, 60.5: 0.9, 61.0: 0.9, 61.5: 0.9, 62.0: 0.9, 62.5: 0.9, 63.0: 0.9, 63.5: 0.9, 64.0: 0.9, 64.5: 0.9, 65.0: 0.9, 65.5: 0.9, 66.0: 0.9, 66.5: 0.9, 67.0: 0.9, 67.5: 0.9, 68.0: 0.9, 68.5: 0.9, 69.0: 0.9, 69.5: 0.9, 70.0: 0.9, 70.5: 0.9, 71.0: 0.9, 71.5: 0.9, 72.0: 0.9, 72.5: 0.9, 73.0: 0.9, 73.5: 0.9, 74.0: 0.9, 74.5: 0.9, 75.0: 0.9, 75.5: 0.9, 76.0: 0.9, 76.5: 0.9, 77.0: 0.9, 77.5: 0.9, 78.0: 0.9, 78.5: 0.9, 79.0: 0.9, 79.5: 0.9, 80.0: 0.9, 80.5: 0.9, 81.0: 0.9, 81.5: 0.9, 82.0: 0.9, 82.5: 0.9, 83.0: 0.9, 83.5: 0.9, 84.0: 0.9, 84.5: 0.9}
# 50 traps, 0.5 MHz apart

# amp_dict2 = {61.0: 0.9, 61.666666666666664: 0.9, 62.333333333333336: 0.9, 63.0: 0.9, 63.666666666666664: 0.9, 64.33333333333333: 0.9, 65.0: 0.9, 65.66666666666667: 0.9, 66.33333333333333: 0.9, 67.0: 0.9, 67.66666666666667: 0.9, 68.33333333333333: 0.9, 69.0: 0.9, 69.66666666666667: 0.9, 70.33333333333333: 0.9, 71.0: 0.9, 71.66666666666667: 0.9, 72.33333333333333: 0.9, 73.0: 0.9, 73.66666666666667: 0.9, 74.33333333333333: 0.9, 75.0: 0.9, 75.66666666666667: 0.9, 76.33333333333333: 0.9, 77.0: 0.9, 77.66666666666666: 0.9, 78.33333333333333: 0.9, 79.0: 0.9, 79.66666666666666: 0.9, 80.33333333333333: 0.9, 81.0: 0.9, 81.66666666666666: 0.9, 82.33333333333333: 0.9, 83.0: 0.9, 83.66666666666666: 0.9, 84.33333333333333: 0.9, 85.0: 0.9, 85.66666666666666: 0.9, 86.33333333333333: 0.9, 87.0: 0.9}
# 40 traps, 0.66 MHz (5 um) apart

def trap_phase(frequencies):
    frequencies = [float(i) for i in frequencies]
    frequencies.sort()

    phases = None
    for phase_dict in phase_dictionaries:
        d_keys = list(phase_dict.keys())
        d_keys.sort()

        if np.all(frequencies == d_keys):
            phases = [phase_dict[i] for i in frequencies]
            break

    if not phases:
        raise Exception("ALL BAD NO GOOD, nah fam you need phases for these new frequencies")


    return phases

def trap_amplitude(frequencies):
    frequencies = [float(i) for i in frequencies]
    print(frequencies)

    try:
        amplitudes = {f: amp_dict[f] for f in frequencies}
    except:
        amplitudes = {f: amp_dict2[f] for f in frequencies}  # CHANGED 11/04 to move tweezers
        #raise Exception('nah fam you need amplitudes for these new frequencies')
    return np.array(list(amplitudes.values()))

def triangle_amplitude(freq):
    if freq<75:
        return np.sqrt(0.5+0.5*(freq-60)/15)
    else:
        return np.sqrt(0.5+0.5*(90-freq)/15)