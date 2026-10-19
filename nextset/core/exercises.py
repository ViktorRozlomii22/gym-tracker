"""Exercise identities and movement groups; no workout prescriptions."""
EXERCISES = {
 'squat':('Присідання','squat'), 'legpress':('Жим ногами','squat'), 'goblet':('Гоблет-присідання','squat'),
 'bench':('Жим лежачи','horizontal_push'), 'dbbench':('Жим гантелей лежачи','horizontal_push'),
 'chestpress':('Жим у тренажері','horizontal_push'),
 'deadlift':('Станова тяга','hinge'), 'rdl':('Румунська тяга','hinge'), 'dbrdl':('Румунська тяга з гантелями','hinge'),
 'press':('Жим стоячи','vertical_push'), 'dbpress':('Жим гантелей сидячи','vertical_push'),
 'shoulderpress':('Жим плечима у тренажері','vertical_push'),
 'row':('Тяга штанги в нахилі','horizontal_pull'), 'dbrow':('Тяга гантелі','horizontal_pull'),
 'cablerow':('Тяга нижнього блока','horizontal_pull'),
 'pulldown':('Тяга верхнього блока','vertical_pull'), 'neutralpull':('Тяга верхнього блока нейтральним хватом','vertical_pull'),
 'curl':('Згинання рук з гантелями','curl'), 'cablecurl':('Згинання рук на блоці','curl'),
 'triceps':('Розгинання рук на блоці','triceps'), 'dbtriceps':('Розгинання рук з гантеллю','triceps'),
 'legcurl':('Згинання ніг у тренажері','legcurl'), 'seatedcurl':('Згинання ніг сидячи','legcurl'),
 'lateral':('Махи гантелями в сторони','lateral'), 'cablelateral':('Махи на блоці в сторони','lateral'),
 'calf':('Підйоми на носки у тренажері','calf'), 'dbcalf':('Підйоми на носки з гантелями','calf')}
NAMES = {k:v[0] for k,v in EXERCISES.items()}

def alternatives(key):
    return {k:v[0] for k,v in EXERCISES.items() if k!=key and v[1]==EXERCISES[key][1]}
