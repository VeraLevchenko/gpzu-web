import os
from dotenv import load_dotenv

load_dotenv()

# Kaiten API
KAITEN_API_TOKEN = os.getenv("KAITEN_API_TOKEN", "")
KAITEN_DOMAIN = os.getenv("KAITEN_DOMAIN", "isogd2019.kaiten.ru")

# Kaiten Board Settings (ОБНОВЛЕНО)
KAITEN_SPACE_ID = int(os.getenv("KAITEN_SPACE_ID", "696620"))
KAITEN_BOARD_ID = int(os.getenv("KAITEN_BOARD_ID", "1578215"))
KAITEN_COLUMN_ID = int(os.getenv("KAITEN_COLUMN_ID", "5474955"))
KAITEN_LANE_ID = int(os.getenv("KAITEN_LANE_ID", "1948738"))
print("DEBUG KAITEN_LANE_ID =", KAITEN_LANE_ID)

# Kaiten Custom Fields
KAITEN_FIELD_CADNUM = os.getenv("KAITEN_FIELD_CADNUM", "id_238069")
KAITEN_FIELD_SUBMIT_METHOD = os.getenv("KAITEN_FIELD_SUBMIT_METHOD", "id_270924")
KAITEN_SUBMIT_METHOD_EPGU = int(os.getenv("KAITEN_SUBMIT_METHOD_EPGU", "93413"))
KAITEN_FIELD_INCOMING_DATE = os.getenv("KAITEN_FIELD_INCOMING_DATE", "id_228500")
KAITEN_FIELD_UNKNOWN = os.getenv("KAITEN_FIELD_UNKNOWN", "id_270916")
