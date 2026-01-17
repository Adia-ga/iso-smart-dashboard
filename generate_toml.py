import json

# טעינת קובץ המפתח
try:
    with open("serviceAccountKey.json", "r", encoding="utf-8") as f:
        key_dict = json.load(f)

    print("\n--- COPY FROM BELOW THIS LINE ---\n")
    print("[firebase]")
    for key, value in key_dict.items():
        # תיקון המפתח הסודי לשורה אחת כדי למנוע טעויות העתקה
        if key == "private_key":
            clean_key = value.replace("\n", "\\n")
            print(f'{key} = "{clean_key}"')
        else:
            print(f'{key} = "{value}"')
    print("\n--- COPY UNTIL ABOVE THIS LINE ---\n")

except FileNotFoundError:
    print("Error: Could not find serviceAccountKey.json")