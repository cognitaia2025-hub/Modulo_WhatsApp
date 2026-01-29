from datetime import datetime, timedelta
import pytz

tz = pytz.timezone('America/Tijuana')
ahora = datetime.now(tz)
manana = ahora + timedelta(days=1)

print(f"Hoy: {ahora.strftime('%Y-%m-%d %A')} (weekday={ahora.weekday()})")
print(f"Mañana: {manana.strftime('%Y-%m-%d %A')} (weekday={manana.weekday()})")
print(f"Días de atención: {[0, 3, 4, 5, 6]} = Lun(0), Jue(3), Vie(4), Sáb(5), Dom(6)")
print(f"Mañana es día laborable: {manana.weekday() in [0, 3, 4, 5, 6]}")
